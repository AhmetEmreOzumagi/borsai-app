"""Skorlama: sınıf (SPEC_SCORING §5), birincil kayıt (§6), eşleşik metrikler (§7), aralıklar ve küçük-n
gösterimi (§8). Çıktılar `scores/scores.json` (şema `borsai.scores/1`; masaüstü uygulaması okur, skor
hesaplamaz) ve `docs/SCORES.md`.

Sınıf ELLE etiketlenmez; git DAG'ı, push kanıtları ve tarihlerden hesaplanır:

    model_prospective(m, a) = is_ancestor(commit_frozen(m), outcome_ingest_commit(a))
                              AND push kanıtı(commit_frozen(m)) var
    record_live(m, a)       = push kanıtı(commit_record).created_at [Istanbul tarihi] < D_1(a)
    inputs_pit_ok(rec)      = her dolu girdi alanının kaynağı D_1'den önce yayımlanmış, belge sha256'sı
                              eşleşiyor; f6 için S0 < ref_date ≤ D_1
    class = LIVE        if model_prospective AND record_live
          = LATE_RECORD if model_prospective AND NOT record_live AND inputs_pit_ok
          = RETRO       otherwise

- commit_frozen(m): `models/<m>.json`'u ekleyen commit. commit_record: kayıt dosyasını ekleyen commit
  (legacy git+push kaydında eski deponun commit'i ve `push_proof.json`'u).
- outcome_ingest_commit(a) = min(data/outcomes/<a>.csv'yi ekleyen commit, D_1…D_10 tarihli bir THB/THM'yi
  ekleyen ilk commit) (§1). Sonuç henüz commit edilmediyse HEAD'e karşı denetlenir: sonuç commit'i
  HEAD'in torunu olacağından HEAD'in her atası onun da atasıdır.
- Legacy self-reported kayıtların (push kanıtı yok) sınıfı LEGACY_SELF_REPORTED'tir: canlı tabloda ayrı
  alt satır, hiçbir kanıtlı n'e girmez (§6). Geçersiz kullanım kayıtları hiçbir n'e girmez.

İki terazi (backtest / canlı) ayrı bloklardadır; hiçbir fonksiyon ikisini birleştirmez (`ScaleMixError`).
Backtest hücreleri var olan fold ledger'larından (docs/MODELS.md ile aynı fonksiyonlar, `random.Random`
aralığı; SPEC_DEVIATIONS C7); canlı hücreler numpy `PCG64(20260921)` blok bootstrap'iyle (§8) ve yalnız
n ≥ 10 olduğunda.

Koşullu canlı skorlar (SPEC_CEILING_PATH_V0 §7 "Canlı skorlama tanımı"; SPEC_APP_EK2 §5 `models[].conditional`):
seri j. günde sürüyorken kaydın S vektöründen S_k / S_j, j = 1..9, j başına ayrı ölçek (`live_conditional`);
farklı j'ler ve koşulsuz tablolar birleştirilmez. Metrikler `borsai/predict_path.py`'nin ortak fonksiyonlarıdır
(`conditional_weights`, `conditional_rps`, `conditional_brier`, `conditional`); burada ikinci bir tanım yoktur.
Yorum kararları: docs/SPEC_DEVIATIONS.md bölüm G.

Kırılma akşamı (Faz 8, SPEC_BREAK_V0 §9; makine sıralı): ölçek `live_break`, ayrı dosya `scores/scores_break.json` ve
`docs/SCORES_BREAK.md` (`--break`; önce eksik makine kayıtlarını `registry/post_break/` altına yazar). Yorum kararları bölüm N.

Kullanım: .venv/bin/python -m borsai.scoring
          .venv/bin/python -m borsai.scoring --oot   (yalnız zaman-dışı eski kohort; SPEC_DEVIATIONS I39)
          .venv/bin/python -m borsai.scoring --break (yalnız kırılma akşamı: makine kayıtları + scores_break.json + SCORES_BREAK.md)
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

from . import freeze as fz
from . import outcomes as oc
from . import predict_break as pbrk
from . import predict_fall as pf
from . import predict_path as pth
from . import push_proof as pp
from . import registry as reg
from . import survival as sv
from .horizons import HORIZONS
from .provenance import ROOT, git_state, identity_hash, pretty_json_bytes, sha256_file, source_tree_sha256

SCHEMA = "borsai.scores/1"
SCORES_PATH = ROOT / "scores" / "scores.json"
DOC_PATH = ROOT / "docs" / "SCORES.md"
LOG_PATH = ROOT / "experiments" / "log.jsonl"

BACKTEST_TITLE = "Geçmiş veri testi (retrospektif, tasarıma maruz)"
LIVE_TITLE = "Canlı sicil (prospektif)"
SCALE_BACKTEST = "backtest"
SCALE_LIVE = "live"
SCALE_LIVE_CONDITIONAL = "live_conditional"    # SPEC_CEILING_PATH_V0 §7; j başına ayrı, koşulsuzla birleşmez

CLASS_LIVE = "LIVE"
CLASS_LATE = "LATE_RECORD"
CLASS_RETRO = "RETRO"
CLASS_LEGACY_SELF = "LEGACY_SELF_REPORTED"
PROSPECTIVE_CLASSES = (CLASS_LIVE, CLASS_LATE)

MIN_N_METRIC = 10      # §8: n < 10 -> yalnız satır tablosu
MIN_N_FULL = 30        # §8: 10 ≤ n < 30 -> "yetersiz örnek"
MIN_BLOCKS = 6
BOOTSTRAP_B = 4000
BOOTSTRAP_SEED = 20260921
LOGLOSS_CLIP = 1e-6    # §7: log-kayıpta p ∈ [1e-6, 1 − 1e-6]

V_PASS = "geçiyor"
V_FAIL = "geçemiyor"
V_NEUTRAL = "ayırt edilemiyor"
V_SMALL = "yetersiz örnek"
V_NO_CI = "aralık için yetersiz"
VERDICTS = (V_PASS, V_FAIL, V_NEUTRAL, V_SMALL, V_NO_CI, None)

ROW_SCORED = "SCORED"
ROW_PENDING = "PENDING"
ROW_REFUSED = "REFUSED"
ROW_TARGET_UNAVAILABLE = "TARGET_UNAVAILABLE"

RETURN_RULES = ("base_always_ceiling", "base_train_median", "base_train_mean", "base_zero")
PROB_RULES = ("base_always_ceiling", "base_rate", "base_last10_rate")
KS = (1, 3, 5, 10)
V15 = "v1_5_h99"
LINEAR_VS_V15 = ("v1_6_h99", "v1_5_market20_v0", "pb_v0")
ALWAYS_CEILING_CURVE = "base_always_ceiling"   # tavan planlarında S_k ≡ 1, P_close ≡ 1 (SPEC_DEVIATIONS C4)
P_UP_AS_CEILING = "v1_5_p_up_as_ceiling"       # SPEC_CEILING_V0 §10-5, SPEC_DEVIATIONS C5

CEILING_PATH_MAIN = "ceiling_path_v0"
CEILING_PATH_ZERO = "ceiling_path_v0@INF"
CEILING_PATH_PB = "pb_ceiling_path_v0"

# SPEC_CEILING_PATH_V0 §5 karşılaştırma tablosu: (metrik, karşılaştırılan), docs/MODELS.md Faz 4 tablolarıyla
# aynı sırada (`borsai/report_faz4.py: section_faz4`). §5'in "bilgi amaçlı" PB ↔ ana model satırları hücre
# DEĞİLDİR (kesimleri farklı). MAE -> getiri, Brier -> p_up.
CEILING_PATH_SPECS: dict[str, tuple[tuple[str, str], ...]] = {
    CEILING_PATH_MAIN: (("MAE", ALWAYS_CEILING_CURVE), ("MAE", "base_train_median"), ("MAE", V15), ("MAE", CEILING_PATH_ZERO),
                        ("Brier", "base_rate"), ("Brier", "base_last10_rate"), ("Brier", V15), ("Brier", CEILING_PATH_ZERO)),
    CEILING_PATH_ZERO: (("MAE", "base_train_median"), ("MAE", ALWAYS_CEILING_CURVE),
                        ("Brier", "base_rate"), ("Brier", "base_last10_rate")),
    CEILING_PATH_PB: (("MAE", "pb_v0"), ("MAE", "base_train_median"), ("MAE", ALWAYS_CEILING_CURVE),
                      ("Brier", "pb_v0"), ("Brier", "base_rate"), ("Brier", "base_last10_rate")),
}
CELL_OUTPUT = {"MAE": "return", "Brier": "p_up"}

# §5: canlıda kurallara ek olarak karşılaştırılan MODELLER (getiri ve p_up hücrelerinin ikisinde de). Kural
# kimlikleri canlı sicilin kendi kurallarıdır; PB planının ayrı kural koşuları yalnız backtest'tedir
# (SPEC_DEVIATIONS F17).
CEILING_PATH_MODEL_COMPARATORS: dict[str, tuple[str, ...]] = {
    CEILING_PATH_MAIN: (V15, CEILING_PATH_ZERO),
    CEILING_PATH_ZERO: (),
    CEILING_PATH_PB: ("pb_v0",),
}

# §7: önceden ilan edilmiş birincil hücre (çoklu karşılaştırmaya karşı). Diğer hücreler "keşif".
PRIMARY_CELLS: dict[str, dict[str, Any]] = {
    "v1_5_h99": {"output": "return", "horizon_or_k": "D5", "metric": "MAE", "rule_ids": ["base_train_median"]},
    "pb_v0": {"output": "return", "horizon_or_k": "D5", "metric": "MAE", "rule_ids": ["base_train_median"]},
    "v1_5_market20_v0": {"output": "return", "horizon_or_k": "D5", "metric": "MAE", "rule_ids": [V15]},
    "v1_6_h99": {"output": "return", "horizon_or_k": "D10", "metric": "MAE", "rule_ids": [V15]},
    "ceiling_hazard_v0": {"output": "S", "horizon_or_k": None, "metric": "RPS",
                          "rule_ids": ["base_km_last10", "base_km_expanding"]},
    "pb_ceiling_v0": {"output": "S", "horizon_or_k": None, "metric": "RPS",
                      "rule_ids": ["base_km_last10", "base_km_expanding"]},
    # SPEC_CEILING_PATH_V0 §5: önceden ilan edilen TEK birincil hücre; `@INF` ve PB varyantı yalnız "keşif".
    CEILING_PATH_MAIN: {"output": "return", "horizon_or_k": "D5", "metric": "MAE", "rule_ids": ["base_train_median"]},
}

# ---- koşullu canlı skorlar (SPEC_CEILING_PATH_V0 §7; kararlar SPEC_DEVIATIONS G1–G12), sonuç görülmeden yazıldı
CONDITIONAL_SCHEMA = "borsai.scores_conditional/1"                  # SPEC_APP_EK2 §5 okuyucu sözleşmesi
CONDITIONAL_TITLE = "Koşullu tavan skorları (canlı, j başına)"
CONDITIONAL_JS = tuple(range(1, sv.DAYS))                           # j = 1..9
CONDITIONAL_KINDS = ("hazard", "km", "ceiling_path")                # kaydında S vektörü olan türler (G2)
CONDITIONAL_PATH_HS = (3, 5, 10)                                    # ikinciller: h ∈ {3, 5, 10}, yalnız h > j
ROW_UNDEFINED = "CONDITION_UNDEFINED"                               # modelin S_j'si 0: koşul tanımsız (G6)
MEMBER, NOT_MEMBER, UNDETERMINED = "MEMBER", "NOT_MEMBER", "UNDETERMINED"
LABEL_PRIMARY, LABEL_EXPLORATORY, LABEL_UNCONDITIONAL_REF = "birincil", "keşif", "koşulsuz referans"
KM_RULES = ("base_km_expanding", "base_km_last10")

# §7 "Kurallar (aynı j, aynı arzlar)", S kısmı: koşullu KM (iki kural), koşullu @INF (modelin S kaynağının sıfır modeli),
# koşullu her-zaman-tavan (S_k / S_j = 1, C4). Koşulsuz canlı blokta karşılaştırıcısı olan modeller alır (G3); KM
# kuralları ve seri sıfır modelleri yalnız satır verir. `ceiling_path_v0@INF`'in S kaynağı zaten sıfır modeldir.
CONDITIONAL_S_COMPARATORS: dict[str, tuple[str, ...]] = {
    "ceiling_hazard_v0": ("ceiling_hazard_v0@INF",) + KM_RULES + (ALWAYS_CEILING_CURVE,),
    "pb_ceiling_v0": ("pb_ceiling_v0@INF",) + KM_RULES + (ALWAYS_CEILING_CURVE,),
    CEILING_PATH_MAIN: ("ceiling_hazard_v0@INF",) + KM_RULES + (ALWAYS_CEILING_CURVE,),
    CEILING_PATH_ZERO: KM_RULES + (ALWAYS_CEILING_CURVE,),
    CEILING_PATH_PB: ("pb_ceiling_v0@INF",) + KM_RULES + (ALWAYS_CEILING_CURVE,),
}
# §7 ikinciller (yalnız ceiling_path_* / pb_ceiling_path_*): koşullu sıfır model yolu (`ceiling_path_v0@INF`'in koşullu
# karışımı; kendisi için yok) ve koşulsuz `base_train_median` / `base_rate` (yalnız referans, hükümsüz).
CONDITIONAL_PATH_COMPARATORS: dict[str, tuple[str, ...]] = {
    CEILING_PATH_MAIN: (CEILING_PATH_ZERO,),
    CEILING_PATH_ZERO: (),
    CEILING_PATH_PB: (CEILING_PATH_ZERO,),
}
CONDITIONAL_UNCONDITIONAL_REFS = {"return_cond": "base_train_median", "p_up_cond": "base_rate"}
# §7 "Koşullu RPS_j … Birincil": karşılaştırılan, koşulsuz S birincil hücresininkiyle aynı (KM kuralları; G4).
CONDITIONAL_PRIMARY = {"output": "S_cond", "horizon_or_k": None, "metric": "RPS", "rule_ids": ["base_km_last10",
                                                                                              "base_km_expanding"]}


# ---- Faz 7: tavan serisi v1 hücre tanımları (SPEC_HAZARD_V1 §5.2 kasa, §5.3 canlı; SPEC_DEVIATIONS L). Kasa açılmadan, sonuç
# görülmeden yazıldı. Var olan `PRIMARY_CELLS` / `OOT_PRIMARY_CELLS` anahtar kümeleri testlerle pinli olduğundan (Faz 7C kalıbı) ayrı
# sözlüklerdir; okuma `primary_cell_of` / `oot_primary_cell_of` üzerinden. Birincil (kasa ve canlı): RPS − `base_km_expanding`
# (kayıttaki donmuş H99 KM'si). Kural satırı `ceiling_hazard_v1_pooled@INF` aday değildir (hücresi yok; karşılaştırılandır).
FAZ7_CANDIDATES: tuple[str, ...] = ("ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled")
FAZ7_RULE_ROW = "ceiling_hazard_v1_pooled@INF"
LABEL_SECONDARY = "ikincil"


def _s_cell(k: Optional[int], rule_id: str) -> dict[str, Any]:
    return {"output": "S", "horizon_or_k": k, "metric": "RPS" if k is None else "Brier", "rule_id": rule_id}


FAZ7_PRIMARY_CELLS: dict[str, dict[str, Any]] = {
    m: {"output": "S", "horizon_or_k": None, "metric": "RPS", "rule_ids": ["base_km_expanding"]} for m in FAZ7_CANDIDATES}
FAZ7_OOT_PRIMARY_CELLS: dict[str, dict[str, Any]] = {
    m: {"output": "S", "horizon_or_k": None, "metric": "RPS", "rule_ids": ["base_km_expanding"]} for m in FAZ7_CANDIDATES}
# §5.2 ilan edilmiş ikinciller (kasa): RPS − v0 (kasa S2 kaydı), Brier k = 10 − KM ve − v0, RPS − v0@INF; real: + RPS − v1_clip;
# pooled: + RPS − v1_real, RPS − v1_pooled@INF, Brier k = 10 − v1_pooled@INF.
_FAZ7_OOT_COMMON = (_s_cell(None, "ceiling_hazard_v0"), _s_cell(10, "base_km_expanding"), _s_cell(10, "ceiling_hazard_v0"),
                    _s_cell(None, "ceiling_hazard_v0@INF"))
FAZ7_OOT_SECONDARY_CELLS: dict[str, list[dict[str, Any]]] = {
    "ceiling_hazard_v1_clip": [*_FAZ7_OOT_COMMON],
    "ceiling_hazard_v1_real": [*_FAZ7_OOT_COMMON, _s_cell(None, "ceiling_hazard_v1_clip")],
    "ceiling_hazard_v1_pooled": [*_FAZ7_OOT_COMMON, _s_cell(None, "ceiling_hazard_v1_real"), _s_cell(None, FAZ7_RULE_ROW),
                                 _s_cell(10, FAZ7_RULE_ROW)],
}
# §5.3 canlı ikinciller: RPS − v0 (aynı kayıt) ve Brier k = 10 (birincilin karşılaştırılanı KM ve v0).
FAZ7_LIVE_SECONDARY_CELLS: dict[str, list[dict[str, Any]]] = {
    m: [_s_cell(None, "ceiling_hazard_v0"), _s_cell(10, "base_km_expanding"), _s_cell(10, "ceiling_hazard_v0")]
    for m in FAZ7_CANDIDATES}


# ---- Faz 7C: düşen arz modeli v0 hücre tanımları (SPEC_C_V0 §5.1–§5.4; KARARLAR_C; SPEC_DEVIATIONS K). Commit A'da, sonuç
# görülmeden sabitlendi. Var olan `PRIMARY_CELLS` / `OOT_PRIMARY_CELLS` anahtar kümeleri testlerle pinli olduğundan ayrı sözlüklerdir;
# modeller `models/INDEX.json`'da değilken hiçbir skor dosyasına girmez (skorlar bu görevde yeniden üretilmez). Kasa anahtarı
# (`oot_pre_h99_sealed`) ve model başına kapı kasa açılış görevindedir. Hücreler p_up = P(kapanış > arz) Brier'idir (kırpmasız);
# "düşme olasılığı" 1 − p_up aynı Brier'i verir.
FAZ7C_CANDIDATES: tuple[str, ...] = ("fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_addsale")
FAZ7C_RULE_ROW = "fall_d10_v0_pooled@ZERO"


def _fall_cell(horizon: str, rule_id: str) -> dict[str, Any]:
    return {"output": "p_up", "horizon_or_k": horizon, "metric": "Brier", "rule_id": rule_id}


# Birincil (üç terazide aynı biçim): D10 Brier − `base_rate` (canlıda kayıttaki kural değeri; kasada kayıttaki donmuş H99 oranı).
FAZ7C_PRIMARY_CELLS: dict[str, dict[str, Any]] = {
    m: {"output": "p_up", "horizon_or_k": "D10", "metric": "Brier", "rule_ids": ["base_rate"]} for m in FAZ7C_CANDIDATES}
FAZ7C_OOT_PRIMARY_CELLS: dict[str, dict[str, Any]] = {
    m: {"output": "p_up", "horizon_or_k": "D10", "metric": "Brier", "rule_ids": ["base_rate"]} for m in FAZ7C_CANDIDATES}
_FAZ7C_COMMON_SECONDARY = (_fall_cell("D10", V15), _fall_cell("D10", "base_last10_rate"), _fall_cell("D5", "base_rate"),
                           _fall_cell("D5", V15))
# §5.2 ilan edilmiş ikinciller (kasa): merdiven (addsale; pooled için ayrıca h99 ve @ZERO) dahil.
FAZ7C_OOT_SECONDARY_CELLS: dict[str, list[dict[str, Any]]] = {
    "fall_d10_v0_h99": [*_FAZ7C_COMMON_SECONDARY, _fall_cell("D10", "fall_d10_v0_addsale")],
    "fall_d10_v0_pooled": [*_FAZ7C_COMMON_SECONDARY, _fall_cell("D10", "fall_d10_v0_addsale"), _fall_cell("D10", "fall_d10_v0_h99"),
                           _fall_cell("D10", FAZ7C_RULE_ROW)],
    "fall_d10_v0_addsale": [*_FAZ7C_COMMON_SECONDARY, _fall_cell("D5", "base_last10_rate")],
}
# §5.2 bilgi satırları (kasa; hüküm yok): V1.5'in kendi D10 hücresi ve kalibrasyon (ort. P(y4) ve gözlenen oran).
FAZ7C_OOT_INFO_CELLS: list[dict[str, Any]] = [
    {**_fall_cell("D10", "base_rate"), "model_id": V15, "role": "bilgi"},
    *({"output": "p_fall", "horizon_or_k": "D10", "metric": "calibration_mean_vs_observed", "model_id": m, "role": "bilgi"}
      for m in FAZ7C_CANDIDATES),
]
# §5.3 canlı ikinciller: − v1_5_h99 (f3 isteyen adaylarda aynı ret kümesi), − base_last10_rate; D5 aynı üçlü.
FAZ7C_LIVE_SECONDARY_CELLS: dict[str, list[dict[str, Any]]] = {
    m: [*_FAZ7C_COMMON_SECONDARY, _fall_cell("D5", "base_last10_rate")] for m in FAZ7C_CANDIDATES}
# §5.1 backtest (yakın dönem, H99 walk-forward): birincil `pooled − h99` D10 Brier + etiket; ilan edilmiş ikinciller.
FAZ7C_BACKTEST_NEAR_ERA: dict[str, Any] = {
    "primary": {"model_id": "fall_d10_v0_pooled", **_fall_cell("D10", "fall_d10_v0_h99"), "first_trading_date_from": "2024-01-01",
                "label_rule": "alt > 0 → bozuyor; üst ≤ δ → tolerans içinde; diğer → belirsiz (borsai.backtest.near_era_label_fall)"},
    "secondary": [{"model_id": m, **_fall_cell(h, r)} for m in FAZ7C_CANDIDATES
                  for h, r in (("D10", "base_rate"), ("D5", "base_rate"), ("D10", V15))]
                 + [{"model_id": "fall_d10_v0_pooled", **_fall_cell("D10", FAZ7C_RULE_ROW)}],
}
FAZ7C_PANEL_TITLE = "(C) yakın dönem"

# ---- Dondurulmuş Faz 7 ve 7C modellerinin karşılaştırılanları (canlı ve kasa hücrelerinin tek tanımı; `live_cell_specs`). İlan
# edilmiş hücrelerin karşılaştırılanları: v1 §5.2/§5.3, (C) §5.2/§5.3. Kural satırlarının hücresi yoktur. Listede olup ilan
# edilmemiş (model, ufuk/k, metrik) bileşimleri "keşif"tir. SPEC_DEVIATIONS L.
NEW_MODEL_COMPARATORS: dict[str, tuple[str, ...]] = {
    "ceiling_hazard_v1_clip": ("base_km_expanding", "ceiling_hazard_v0", "ceiling_hazard_v0@INF"),
    "ceiling_hazard_v1_real": ("base_km_expanding", "ceiling_hazard_v0", "ceiling_hazard_v0@INF", "ceiling_hazard_v1_clip"),
    "ceiling_hazard_v1_pooled": ("base_km_expanding", "ceiling_hazard_v0", "ceiling_hazard_v0@INF", "ceiling_hazard_v1_real",
                                 FAZ7_RULE_ROW),
    FAZ7_RULE_ROW: (),
    "fall_d10_v0_h99": ("base_rate", "base_last10_rate", V15, "fall_d10_v0_addsale"),
    "fall_d10_v0_pooled": ("base_rate", "base_last10_rate", V15, "fall_d10_v0_addsale", "fall_d10_v0_h99", FAZ7C_RULE_ROW),
    "fall_d10_v0_addsale": ("base_rate", "base_last10_rate", V15),
    FAZ7C_RULE_ROW: (),
}
LIVE_SECONDARY_CELLS: dict[str, list[dict[str, Any]]] = {**FAZ7_LIVE_SECONDARY_CELLS, **FAZ7C_LIVE_SECONDARY_CELLS}
OOT_SECONDARY_CELLS: dict[str, list[dict[str, Any]]] = {**FAZ7_OOT_SECONDARY_CELLS, **FAZ7C_OOT_SECONDARY_CELLS}


def _cell_key(c: Mapping[str, Any]) -> tuple[Any, Any, Any, Any]:
    return c["output"], c["horizon_or_k"], c["metric"], c["rule_id"]


def primary_cell_of(model_id: str) -> Optional[dict[str, Any]]:
    """Canlı birincil hücre: var olan `PRIMARY_CELLS` (değişmedi) + Faz 7 (§5.3) + Faz 7C (§5.3)."""
    return PRIMARY_CELLS.get(model_id) or FAZ7_PRIMARY_CELLS.get(model_id) or FAZ7C_PRIMARY_CELLS.get(model_id)


# ---- Yakın dönem bloğu (SPEC_APP_EK3 §5.5 okuyucu sözleşmesi Ö1; SPEC_DEVIATIONS L): `models[].backtest.near_era`, yalnız
# dondurulmuş Faz 7 ve 7C modellerinde. Değerler altın ledger'lardan, günlükteki satırlarla aynı fonksiyonlarla (bayt-eşit, testli).
NEAR_ERA_SCHEMA = "borsai.near_era/1"
NEAR_ERA_SCALE = "backtest_near_era"
NEAR_ERA_SUBSET = "first_trading_date >= 2024-01-01"
NEAR_ERA_LABELS = ("tolerans içinde", "bozuyor", "belirsiz")


def _near_era_block(p: Mapping[str, Any], label: str, comparator: str, metric: str, tolerance: float, source: str) -> dict[str, Any]:
    if label not in NEAR_ERA_LABELS:
        raise ScoringError(f"yakın dönem etiketi {label!r} üç değerden biri değil")
    return {"schema_version": NEAR_ERA_SCHEMA, "scale": NEAR_ERA_SCALE, "label": label, "comparator": comparator, "metric": metric,
            "subset": NEAR_ERA_SUBSET, "diff": p["mean"], "ci95": None if p["ci95"] is None else list(p["ci95"]), "n": p["n"],
            "n_blocks": p["n_months"], "tolerance": tolerance, "source": source}


def near_era_blocks(faz7_dir: Optional[Path] = None, faz7c_dir: Optional[Path] = None) -> dict[str, dict[str, Any]]:
    """model_id -> EK3 §5.5 bloğu. v1 (dört kimlik): aday − `ceiling_hazard_v0`, RPS, δ = 0.010 (`backtest.near_era_cell`, SPEC_HAZARD_V1
    §5.1). (C): `fall_d10_v0_pooled` birincil hücreyi taşır (− `fall_d10_v0_h99`, D10 Brier, δ = 0.008; `near_era_cell_fall`); h99,
    addsale ve kural satırı @ZERO §5.5 k3'ün "yakın dönem − `base_rate`" hücresini aynı şemada taşır (`paired_p_up`, etiket
    `near_era_label_fall`: alt > 0 → bozuyor, yani k3'teki "tamamen 0'ın üstünde"). Altın dizin yoksa o aile yok."""
    from . import backtest as bt
    from . import report_faz7 as r7
    from . import report_faz7c as r7c

    out: dict[str, dict[str, Any]] = {}
    d7 = Path(faz7_dir) if faz7_dir is not None else r7.GOLDEN_FAZ7_DIR
    if r7.golden_available(d7):
        runs = r7.load_faz7(d7)[0]
        v0 = bt.read_pinned_ledger(bt.FAZ7_COMPARATOR_LEDGERS["ceiling_hazard_v0"])
        for m in FAZ7_CANDIDATES + (FAZ7_RULE_ROW,):
            p = bt.near_era_cell(runs[m], v0)
            if p is not None:
                out[m] = _near_era_block(p, p["label"], "ceiling_hazard_v0", "RPS", bt.NEAR_ERA_TOLERANCE,
                                         "experiments/log.jsonl near_era; backtest.near_era_cell")
    d7c = Path(faz7c_dir) if faz7c_dir is not None else r7c.GOLDEN_FAZ7C_DIR
    if r7c.golden_available(d7c):
        runs = r7c.load_faz7c(d7c)[0]
        base = bt.read_pinned_ledger(bt.FAZ7C_COMPARATOR_LEDGERS["base_rate"])
        for m in FAZ7C_CANDIDATES + (FAZ7C_RULE_ROW,):
            if m == "fall_d10_v0_pooled":
                p = bt.near_era_cell_fall(runs[m], runs["fall_d10_v0_h99"])
                if p is not None:
                    out[m] = _near_era_block(p, p["label"], "fall_d10_v0_h99", "D10 Brier", bt.NEAR_ERA_TOLERANCE_FALL,
                                             "experiments/log.jsonl near_era; backtest.near_era_cell_fall")
                continue
            p = bt.paired_p_up(runs[m], base, horizon=bt.FALL_PRIMARY_HORIZON, start=bt.NEAR_ERA_START)
            if p is not None:
                out[m] = _near_era_block(p, bt.near_era_label_fall(p["ci95"]), "base_rate", "D10 Brier", bt.NEAR_ERA_TOLERANCE_FALL,
                                         "experiments/log.jsonl near_era_secondary base_rate|D10; backtest.paired_p_up, "
                                         "near_era_label_fall")
    return out


def faz7c_near_era_block(faz7c_dir: Optional[Path] = None) -> Optional[dict[str, Any]]:
    """SCORES.md §5 "(C) yakın dönem" satırının verisi (backtest terazisi): Faz 7C altın ledger'larından `pooled − h99` D10 Brier,
    ilk işlem ≥ 2024-01-01, §5.1 etiketiyle. Altın dizin yoksa None."""
    from . import backtest as bt
    from . import report_faz7c as r7c

    d = Path(faz7c_dir) if faz7c_dir is not None else r7c.GOLDEN_FAZ7C_DIR
    if not r7c.golden_available(d):
        return None
    runs = r7c.load_faz7c(d)[0]
    p = bt.near_era_cell_fall(runs["fall_d10_v0_pooled"], runs["fall_d10_v0_h99"])
    if p is None:
        return None
    return {"title": FAZ7C_PANEL_TITLE, "model_id": "fall_d10_v0_pooled", "rule_id": "fall_d10_v0_h99", "output": "p_up",
            "horizon_or_k": "D10", "metric": "Brier", "first_trading_date_from": bt.NEAR_ERA_START, "n": p["n"],
            "n_blocks": p["n_months"], "model_value": p["model_metric"], "rule_value": p["rule_metric"], "diff": p["mean"],
            "ci95": p["ci95"], "label": p["label"], "tolerance": bt.NEAR_ERA_TOLERANCE_FALL, "scale": SCALE_BACKTEST}


def render_faz7c_panel_row(b: Mapping[str, Any]) -> str:
    """SCORES.md §5 tablosunun (C) satırı: hüküm sütunu §5.1 etiketidir (backtest; "geçiyor" kullanılmaz)."""
    ci = "—" if b["ci95"] is None else f"[{_s(b['ci95'][0])}, {_s(b['ci95'][1])}]"
    return (f"| {b['title']}: `{b['model_id']}` | {b['output']} {b['horizon_or_k']} {b['metric']} (ilk işlem ≥ "
            f"{b['first_trading_date_from']}) | `{b['rule_id']}` | {b['n']} ({b['n_blocks']}) | {_p(b['model_value'])} | "
            f"{_p(b['rule_value'])} | {_s(b['diff'])} | {ci} | {b['label']} (§5.1 etiketi, δ = {b['tolerance']:+.3f}) |")


class ScoringError(RuntimeError):
    pass


class ScaleMixError(ScoringError):
    """İki terazi (backtest / canlı) birleştirilemez (CLAUDE.md kural 3; SPEC_SCORING §5, §8)."""


# ============================================================ git ve kanıtlar

class Git:
    def __init__(self, root: Path = ROOT):
        self.root = Path(root)
        self._added: dict[str, Optional[str]] = {}
        self._anc: dict[tuple[str, str], bool] = {}
        self._proof: dict[str, Optional[str]] = {}
        self._head: Optional[str] = None
        self._cache: dict[tuple[str, str], Any] = {}

    def run(self, *args: str) -> str:
        return subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True, text=True).stdout.strip()

    def head(self) -> str:
        if self._head is None:
            self._head = self.run("rev-parse", "HEAD")
        return self._head

    def added_commit(self, rel: str) -> Optional[str]:
        """`rel` yolunu ekleyen en erken commit (HEAD geçmişinde); yoksa None."""
        if rel not in self._added:
            out = self.run("log", "--diff-filter=A", "--format=%H", "--", rel).splitlines()
            self._added[rel] = out[-1] if out else None
        return self._added[rel]

    def is_ancestor(self, a: str, b: str) -> bool:
        key = (a, b)
        if key not in self._anc:
            self._anc[key] = pp.is_ancestor(a, b, self.root)
        return self._anc[key]

    def history(self, rel: str) -> list[str]:
        """`rel`'e dokunan commit'ler, eskiden yeniye (HEAD geçmişinde; yeniden adlandırma izlenmez)."""
        key = ("history", rel)
        if key not in self._cache:
            self._cache[key] = self.run("log", "--reverse", "--format=%H", "--", rel).splitlines()
        return self._cache[key]

    def show(self, commit: str, rel: str) -> str:
        return self.run("show", f"{commit}:{rel}")

    def added_under(self, prefix: str) -> dict[str, str]:
        """`prefix` altındaki her dosya -> onu ekleyen en erken commit (tek `git log`)."""
        key = ("added_under", prefix)
        if key not in self._cache:
            out: dict[str, str] = {}
            commit = None
            for line in self.run("log", "--diff-filter=A", "--format=@%H", "--name-only", "--", prefix).splitlines():
                if line.startswith("@"):
                    commit = line[1:]
                elif line.strip() and commit:
                    out[line.strip()] = commit     # log yeniden eskiye: son yazılan en erken
            self._cache[key] = out
        return self._cache[key]

    def earliest(self, commits: Iterable[str]) -> Optional[str]:
        """DAG'da en erken commit (diğerlerinin hepsinin atası); doğrusal geçmişte ilk giren."""
        best: Optional[str] = None
        for c in commits:
            if best is None or (c != best and self.is_ancestor(c, best)):
                best = c
        return best


def proof_time(git: Git, commit: Optional[str], proofs: Sequence[Mapping[str, Any]]) -> Optional[str]:
    """commit'i kapsayan (kendisi ya da torunu için) en erken push kanıtının created_at'i."""
    if commit is None:
        return None
    if commit not in git._proof:
        covering = [d["created_at"] for d in proofs if git.is_ancestor(commit, d["proven_commit_sha"])]
        git._proof[commit] = min(covering) if covering else None
    return git._proof[commit]


def model_evidence(git: Git, model_file: str, proofs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    commit = git.added_commit(f"models/{model_file}")
    return {"commit": commit, "push_proof_created_at": proof_time(git, commit, proofs)}


def outcome_ingest_commit(git: Git, ticker: str, session_dates: Sequence[str], *,
                          outcomes_rel: str = "data/outcomes", bist_rel: str = "data/raw/bist") -> Optional[str]:
    """§1: min(arz dosyasını ekleyen commit, D_1…D_10 tarihli herhangi bir ham THB/THM'yi ekleyen ilk commit)."""
    paths = [f"{outcomes_rel}/{ticker}.csv"]
    for d in session_dates:
        for kind in oc.KINDS:
            paths.append(f"{bist_rel}/{kind}/{d[:4]}/{kind}{oc.compact(d)}1.zip")
    commits = [c for c in (git.added_commit(p) for p in paths) if c is not None]
    return git.earliest(commits)


def classify(model_prospective: bool, record_live: bool, inputs_pit_ok: bool) -> str:
    """SPEC_SCORING §5 formülü (saf)."""
    if model_prospective and record_live:
        return CLASS_LIVE
    if model_prospective and inputs_pit_ok:
        return CLASS_LATE
    return CLASS_RETRO


def istanbul_before(timestamp: Optional[str], d1: str) -> bool:
    return timestamp is not None and reg.istanbul_date(timestamp) < d1


def pair_class(git: Git, model_ev: Mapping[str, Any], outcome_commit: Optional[str], cand: reg.Candidate,
               d1: str) -> tuple[str, dict[str, Any]]:
    """(sınıf, kanıt). Sonuç commit edilmediyse HEAD'e karşı."""
    target = outcome_commit or git.head()
    prospective = (model_ev["commit"] is not None and model_ev["push_proof_created_at"] is not None
                   and git.is_ancestor(model_ev["commit"], target))
    live = istanbul_before(cand.push_created_at, d1)
    if cand.track == "SELF_REPORTED":
        cls = CLASS_LEGACY_SELF if prospective else CLASS_RETRO
    else:
        cls = classify(prospective, live, cand.inputs_pit_ok)
    return cls, {
        "model_commit": model_ev["commit"], "model_push_proof_created_at": model_ev["push_proof_created_at"],
        "outcome_ingest_commit": outcome_commit, "checked_against": target if outcome_commit is None else outcome_commit,
        "outcome_ingest_basis": "COMMITTED" if outcome_commit else "UNCOMMITTED_CHECKED_AGAINST_HEAD",
        "model_prospective": prospective, "record_track": cand.track, "record_push_proof_created_at": cand.push_created_at,
        "record_live": live, "inputs_pit_ok": cand.inputs_pit_ok, "d1": d1,
    }


# ============================================================ sıra kuralı (CLAUDE.md; SPEC_SCORING §5, §10-10)

LISTING_CUTOFF = "2026-08-06"
OUTCOME_CUTOFF = "2026-08-19"
_BULLETIN = re.compile(r"^(th[bm])(20\d{6})1\.zip$")


def faz1_model_ids() -> tuple[str, ...]:
    """Sıra kuralının bağladığı modeller: Faz 1 dondurmasındaki 16 model. Sonradan eklenen bir model sonuçtan
    sonra dondurulursa bekçi kırmızı olmaz; o model o arz için RETRO'ya düşer (sınıflamanın işi)."""
    from .specs import FAZ1A_MODEL_IDS, FAZ1B_MODEL_IDS

    return tuple(FAZ1A_MODEL_IDS) + tuple(FAZ1B_MODEL_IDS)


def sequence_violations(root: Path = ROOT, model_ids: Optional[Sequence[str]] = None) -> list[str]:
    """Sonuç ancak sırayla: (1) 2026-08-19 sonrası tarihli ya da post-08-06 bir arzın işlem gününü kapsayan her
    THB/THM zip'i ve (2) post-08-06 her arzın data/outcomes/<T>.csv dosyası için, dosyayı ekleyen commit'in
    (commit edilmemişse HEAD'in) ataları (a) Faz 1 model JSON'larını ekleyen commit'leri ve (b) ilgili her
    FROZEN arzın ilk tahmin kaydını ekleyen commit'i içermeli. Boş liste = kural tutuyor.

    POST_D1 dizini (models/INDEX_POST_D1.json; proje sahibi kararı 4, SPEC_DEVIATIONS H) varsa listelediği her model
    dosyası da sıraya bağlanır: dosya commit edilmiş olmalı ve her hedef dosya ya modelden SONRA (model commit'i atası)
    ya da modelden ÖNCE (hedef commit'i modelin atası: o arz bu model için RETRO'dur, sınıflamanın işi) girmiş olmalı;
    modelle sırasız (paralel dal) giren hedef ihlaldir.

    POST_BREAK dizini (models/INDEX_POST_BREAK.json; SPEC_BREAK_V0 §9.2, K-LB-9) varsa listelediği her model dosyası POST_D1 dalıyla
    AYNI kurala bağlanır (yalnız ekleme; POST_D1 dalı değişmedi). registry/post_break/ makine kayıtları hedef değildir (sonuçtan
    sonra yazılır)."""
    root = Path(root)
    git = Git(root)
    index = json.loads((root / "models" / "INDEX.json").read_text(encoding="utf-8"))
    files = {e["model_id"]: e["file"] for e in index["models"]}
    model_commits = {m: (git.added_commit(f"models/{files[m]}") if m in files else None)
                     for m in (model_ids if model_ids is not None else faz1_model_ids())}
    post_path = root / "models" / "INDEX_POST_D1.json"
    post_commits = ({e["model_id"]: git.added_commit(f"models/{e['file']}")
                     for e in json.loads(post_path.read_text(encoding="utf-8"))["models"]} if post_path.exists() else {})
    break_path = root / "models" / fz.INDEX_POST_BREAK_NAME
    break_commits = ({e["model_id"]: git.added_commit(f"models/{e['file']}")
                      for e in json.loads(break_path.read_text(encoding="utf-8"))["models"]} if break_path.exists() else {})
    _, ipos = reg.read_ipos(root / "registry" / "ipos.csv")
    post = {r["ticker"]: r for r in ipos if r["status"] in reg.IPO_STATUSES and r["first_trading_date"] > LISTING_CUTOFF}
    record_commits = {t: git.earliest(c for c in (git.added_commit(p.relative_to(root).as_posix())
                                                  for p in sorted((root / "registry" / "records" / t).glob("*.json"))) if c)
                      for t in post}
    targets: list[tuple[str, list[str]]] = []
    bist = root / "data" / "raw" / "bist"
    for p in sorted(bist.rglob("*.zip")) if bist.exists() else []:
        m = _BULLETIN.match(p.name)
        if m is None:
            continue
        d = f"{m.group(2)[:4]}-{m.group(2)[4:6]}-{m.group(2)[6:]}"
        relevant = [t for t, r in post.items() if r["first_trading_date"] <= d]
        if d > OUTCOME_CUTOFF or relevant:
            targets.append((p.relative_to(root).as_posix(), relevant))
    outcomes_dir = root / "data" / "outcomes"
    for p in sorted(outcomes_dir.glob("*.csv")) if outcomes_dir.exists() else []:
        if p.stem in post:
            targets.append((p.relative_to(root).as_posix(), [p.stem]))
    head = git.head()
    out: list[str] = []
    for rel, relevant in targets:
        c = git.added_commit(rel) or head
        for m, mc in model_commits.items():
            if mc is None or not git.is_ancestor(mc, c):
                out.append(f"{rel}: model {m} JSON'unu ekleyen commit ({mc}) {c[:12]}'nin atası değil")
        for m, mc in post_commits.items():
            if mc is None or not (git.is_ancestor(mc, c) or git.is_ancestor(c, mc)):
                out.append(f"{rel}: POST_D1 modeli {m} JSON'unu ekleyen commit ({mc}) {c[:12]} ile sıralı değil "
                           "(commit edilmemiş ya da paralel dal)")
        for m, mc in break_commits.items():
            if mc is None or not (git.is_ancestor(mc, c) or git.is_ancestor(c, mc)):
                out.append(f"{rel}: POST_BREAK modeli {m} JSON'unu ekleyen commit ({mc}) {c[:12]} ile sıralı değil "
                           "(commit edilmemiş ya da paralel dal)")
        for t in relevant:
            rc = record_commits.get(t)
            if post[t]["status"] == "FROZEN" and (rc is None or not git.is_ancestor(rc, c)):
                out.append(f"{rel}: {t} tahmin kaydını ekleyen commit ({rc}) {c[:12]}'nin atası değil")
    return out


# ============================================================ girdi zamanlaması (inputs_pit_ok)

def record_inputs_pit_problems(rec: Mapping[str, Any], d1: str, *, root: Path = ROOT) -> list[str]:
    """Kaydın girdi belgesi: yapısal denetim, belge sha256'ları, her dolu alanın kaynağı D_1'den (gerçekleşen)
    önce; f6 varsa S0 < ref_date ≤ D_1."""
    doc = rec["inputs"]["document"]
    problems = reg.inputs_pit_problems(doc, root=root)
    for name in reg.INPUT_FIELDS:
        f = doc["fields"].get(name) or {}
        if f.get("value") is not None and f.get("source_published_at") and not reg.istanbul_date(f["source_published_at"]) < d1:
            problems.append(f"{name}: kaynak yayını D_1 {d1}'den önce değil")
    m = rec.get("market20") or {}
    if m.get("f6") is not None and not (m["S0_date"] < m["ref_date"] <= d1):
        problems.append(f"f6: S0 {m['S0_date']} < ref_date {m['ref_date']} ≤ D_1 {d1} değil")
    return problems


LEGACY_FIELD_MAP = {"ipo_price_tl": "ipo_price_tl", "shares_offered_final": "shares_offered",
                    "capital_increase_shares": "capital_increase_shares", "post_ipo_share_capital": "post_ipo_share_capital",
                    "f3": "total_demand_multiple"}


def legacy_inputs_pit_problems(entry: Mapping[str, Any], doc: Optional[Mapping[str, Any]], d1: str, *,
                               root: Path = ROOT) -> list[str]:
    """Legacy kaydın girdileri: pretrade paketindeki V1.5 girdileri, resmi belgelerden toplanan sicil
    girdileriyle (registry/inputs/<T>.json) Decimal-eşit ve o girdiler D_1'den önce yayımlanmış."""
    packet = next((p for p in entry["files"] if p.endswith("_pretrade_evidence_packet.csv")), None)
    if packet is None:
        return ["pretrade paketi yok"]
    if doc is None:
        return ["sicil girdi belgesi yok"]
    with (root / packet).open(encoding="utf-8-sig", newline="") as fh:
        values = {r["field"]: r["normalized_value"] for r in csv.DictReader(fh)}
    problems = []
    for legacy_name, name in LEGACY_FIELD_MAP.items():
        a, b = values.get(legacy_name), doc["fields"][name]["value"]
        da, db = oc.dec(a or ""), oc.dec(b or "")
        if da is None or db is None or da != db:
            problems.append(f"{legacy_name}: legacy {a!r} != sicil {b!r}")
    problems += record_inputs_pit_problems({"inputs": {"document": doc}, "market20": {}}, d1, root=root)
    return problems


def legacy_push_time(entry: Mapping[str, Any], *, root: Path = ROOT) -> Optional[str]:
    """GIT_PUSH legacy kaydı: kanıt dosyasındaki `created_at` (legacy_roles.json'daki değerle ve eski commit'le
    tutarlı olmalı)."""
    if entry["time_proof"] != "GIT_PUSH":
        return None
    proof = json.loads((root / entry["push_proof_file"]).read_text(encoding="utf-8"))
    if proof["created_at"] != entry["push_proof_created_at"] or not str(proof.get("url", "")).endswith(
            f"/statuses/{entry['old_repo_commit']}"):
        raise ScoringError(f"{entry['record']}: push kanıtı legacy_roles ile tutarsız")
    return proof["created_at"]


# ============================================================ tahminler

def _f(x: Any) -> Optional[float]:
    return None if x is None or x == "" else float(x)


def prediction_of_cell(cell: Mapping[str, Any]) -> dict[str, Any]:
    """Kayıttaki model hücresi -> skorlanan çıktılar (dondurulmuş değer, yeniden hesap yok)."""
    if cell["status"] != fz.STATUS_PREDICTED:
        return {"refused": cell["refusal"]}
    o = cell["output"]
    if cell["kind"] in ("hazard", "km"):
        return {"S": list(o["S"]), "P_close_ceiling": list(o["P_close_ceiling"])}
    if cell["kind"] == "ceiling_path":  # SPEC_CEILING_PATH_V0 §4: D1/D3/D5/D10 return (karışım medyanı) ve p_up
        return {h: {"return": o[h]["return"], "p_up": o[h]["p_up"]} for h in HORIZONS}
    if cell["kind"] == "fall":          # SPEC_C_V0 §2, §8: yalnız D5 ve D10 p_up (getiri başlığı yok); V1.5 yolu (SPEC_DEVIATIONS K22)
        return {h: {"return": o[h]["return"], "p_up": o[h]["p_up"]} for h in pf.FALL_HORIZONS}
    return {h: {"return": o[h]["return"], "p_up": o[h]["p_up"]} for h in HORIZONS}


def legacy_prediction(entry: Mapping[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    """Legacy V1.5 ledger'ı (içerik değiştirilmez): ufuk başına getiri ve P(kapanış > arz)."""
    ledger = next((p for p in entry["files"] if p.endswith("_frozen_prediction_ledger.csv")), None)
    if ledger is not None:
        with (root / ledger).open(encoding="utf-8-sig", newline="") as fh:
            rows = {r["horizon"]: r for r in csv.DictReader(fh)}
        out = {}
        for h in HORIZONS:
            r = rows[h]
            ret = r.get("ridge_predicted_return") or r.get("ridge_point_prediction_return")
            p = r.get("p_up") or r.get("logistic_probability_above_ipo_raw")
            out[h] = {"return": _f(ret), "p_up": _f(p)}
        return out
    md = next((p for p in entry["files"] if p.endswith(".md")), None)
    if md is None:
        raise ScoringError(f"{entry['record']}: tahmin dosyası yok")
    block = _json_block((root / md).read_text(encoding="utf-8"), "freeze_timestamp_istanbul")
    return {h: {"return": block["horizons"][h]["ridge"]["predicted_return"],
                "p_up": block["horizons"][h]["logistic"]["p_up"]} for h in HORIZONS}


def _json_block(text: str, marker: str) -> dict[str, Any]:
    """Metindeki `marker` anahtarını içeren ilk üst düzey JSON nesnesi (TKNKA freeze belgesi)."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "{":
            depth, buf = 0, []
            for line2 in lines[i:]:
                buf.append(line2)
                depth += line2.count("{") - line2.count("}")
                if depth == 0:
                    break
            chunk = "\n".join(buf)
            if f'"{marker}"' in chunk:
                return json.loads(chunk)
    raise ScoringError(f"JSON bloğu bulunamadı ({marker})")


# ============================================================ gerçekleşen

@dataclass(frozen=True)
class Realized:
    ticker: str
    rows: tuple[dict[str, str], ...]

    @property
    def d1(self) -> Optional[str]:
        return self.rows[0]["session_date"] or None

    @property
    def session_dates(self) -> list[str]:
        return [r["session_date"] for r in self.rows if r["session_date"]]

    def row(self, h: int) -> dict[str, str]:
        return self.rows[h - 1]

    def target(self, horizon: str) -> tuple[str, Optional[Decimal], Optional[int]]:
        r = self.row(int(horizon[1:]))
        if r["status"] in (oc.STATUS_OK, oc.STATUS_NA_LIMIT):
            return "OK", Decimal(r["R_h"]), int(r["Y_h"])
        return r["status"], None, None

    def labels(self) -> list[Optional[int]]:
        out = []
        for r in self.rows:
            if r["status"] in (oc.STATUS_OK, oc.STATUS_NA_LIMIT):
                out.append(None if r["ceiling_close"] == oc.NA else int(r["ceiling_close"]))
            else:
                break
        return out

    def streak(self) -> tuple[str, Optional[int]]:
        """(durum, L). L bilinmiyorsa durum PENDING / TARGET_UNAVAILABLE / NA_LIMIT."""
        labels = self.labels()
        L = oc.streak(labels)
        if L is not None:
            return "OK", L
        if None in labels:
            return oc.STATUS_NA_LIMIT, None
        nxt = self.rows[len(labels)]["status"] if len(labels) < oc.N_SESSIONS else oc.STATUS_TARGET_UNAVAILABLE
        return nxt, None

    def close_label(self, k: int) -> tuple[str, Optional[int]]:
        r = self.row(k)
        if r["status"] == oc.STATUS_OK:
            return "OK", int(r["ceiling_close"])
        return r["status"], None

    def as_json(self) -> dict[str, Any]:
        st, L = self.streak()
        return {
            "d1": self.d1,
            "sessions": [r["session_date"] or None for r in self.rows],
            "row_status": [r["status"] for r in self.rows],
            "R": {h: (self.row(int(h[1:]))["R_h"] or None) for h in HORIZONS},
            "Y": {h: (int(self.row(int(h[1:]))["Y_h"]) if self.row(int(h[1:]))["Y_h"] else None) for h in HORIZONS},
            "ceiling_close": [None if r["ceiling_close"] in ("", oc.NA) else int(r["ceiling_close"]) for r in self.rows],
            "L": L, "L_status": st,
            "half_day": [int(r["half_day"] or 0) for r in self.rows],
            "halt_flag": [int(r["halt_flag"] or 0) for r in self.rows],
            "shifted_by_suspension": [int(r["shifted_by_suspension"] or 0) for r in self.rows],
        }


def load_realized(ticker: str, outcomes_dir: Path = oc.OUTCOMES_DIR) -> Optional[Realized]:
    p = oc.outcome_path(ticker, outcomes_dir)
    return Realized(ticker, tuple(oc.read_outcome(p))) if p.exists() else None


# ============================================================ kayıplar ve eşleşik metrik

def clip(p: float, eps: float = LOGLOSS_CLIP) -> float:
    return min(max(p, eps), 1.0 - eps)


def loss_mae(pred: float, R: Decimal) -> float:
    return abs(pred - float(R))


def loss_dir_miss(pred: float, Y: int) -> float:
    """1 − yön isabeti: işaret(R̂) (> 0 yukarı) ile Y_h."""
    return float(int(pred > 0) != Y)


def loss_brier(p: float, y: int) -> float:
    return (p - y) ** 2


def loss_log(p: float, y: int) -> float:
    q = clip(p)
    return -(y * math.log(q) + (1 - y) * math.log(1 - q))


def loss_hit_miss(p: float, y: int) -> float:
    """1 − 0.5 eşikli isabet (p > 0.5 yukarı)."""
    return float(int(p > 0.5) != y)


def loss_rps(S: Sequence[float], L: int) -> float:
    return sv.rps(S, L)


@dataclass(frozen=True)
class PairedObs:
    scale: str
    ticker: str
    block: str        # gerçekleşen D_1'in takvim ayı (YYYY-MM)
    model_loss: float
    rule_loss: float
    klass: str = ""
    j: Optional[int] = None   # koşullu gözlemde seri günü (§7); farklı j'ler birleştirilmez


def verdict(n: int, ci: Optional[Sequence[float]]) -> Optional[str]:
    """§8 dil kuralları. "geçiyor" yalnız n ≥ 30 ve aralık tamamen 0'ın altında."""
    if n < MIN_N_METRIC:
        return None
    if n < MIN_N_FULL:
        return V_SMALL
    if ci is None:
        return V_NO_CI
    lo, hi = ci
    if hi < 0:
        return V_PASS
    if lo > 0:
        return V_FAIL
    return V_NEUTRAL


def block_bootstrap_ci(d: Sequence[float], blocks: Sequence[str], *, B: int = BOOTSTRAP_B,
                       seed: int = BOOTSTRAP_SEED) -> Optional[list[float]]:
    """§9: n ≥ 10 ve ≥ 6 blok yoksa None. Bloklar sıralı; rng.choice(ids, iadeli); istatistik = çekilen
    blokların bütün farklarının ortalaması; yüzdelik [2.5, 97.5]."""
    import numpy as np

    if len(d) != len(blocks):
        raise ValueError("uzunluk uyuşmazlığı")
    if len(d) < MIN_N_METRIC or len(set(blocks)) < MIN_BLOCKS:
        return None
    rng = np.random.Generator(np.random.PCG64(seed))
    ids = sorted(set(blocks))
    by = {b: [x for x, bb in zip(d, blocks) if bb == b] for b in ids}
    stats = []
    for _ in range(B):
        sample = [x for b in rng.choice(ids, size=len(ids), replace=True) for x in by[str(b)]]
        stats.append(sum(sample) / len(sample))
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return [float(lo), float(hi)]


def _one_scale(obs: Sequence[PairedObs]) -> str:
    scales = {o.scale for o in obs}
    if len(scales) > 1:
        raise ScaleMixError(f"iki terazi birleştirilemez: {sorted(scales)}")
    js = {o.j for o in obs}
    if len(js) > 1:   # SPEC_CEILING_PATH_V0 §7: farklı j'ler toplanmaz (aynı arz birden çok j'de bulunur)
        raise ScaleMixError(f"farklı j'ler birleştirilemez: {sorted(js, key=str)}")
    return scales.pop() if scales else SCALE_LIVE


def merge_scales(*blocks: Mapping[str, Any]) -> None:
    """Backtest, canlı ve koşullu canlı (`live_conditional`, j başına) blokları birleştiren her çağrı reddedilir."""
    scales = {b.get("scale") for b in blocks}
    if len(scales) > 1:
        raise ScaleMixError(f"iki terazi birleştirilemez: {sorted(map(str, scales))}")
    raise ScaleMixError("terazi blokları birleştirilmez; her blok ayrı raporlanır")


def paired_metric(obs: Sequence[PairedObs]) -> dict[str, Any]:
    """fark = model − kural (negatif = model iyi), aynı arz kümesinde. n < 10 -> metrik alanları null."""
    scale = _one_scale(obs)
    n = len(obs)
    base = {"scale": scale, "n": n, "n_blocks": len({o.block for o in obs}),
            "n_live": sum(o.klass == CLASS_LIVE for o in obs), "n_late": sum(o.klass == CLASS_LATE for o in obs)}
    if n < MIN_N_METRIC:
        return {**base, "model_value": None, "rule_value": None, "diff": None, "ci95": None, "wins": None,
                "losses": None, "ties": None, "verdict": None}
    d = [o.model_loss - o.rule_loss for o in obs]
    ci = block_bootstrap_ci(d, [o.block for o in obs])
    return {**base, "model_value": sum(o.model_loss for o in obs) / n, "rule_value": sum(o.rule_loss for o in obs) / n,
            "diff": sum(d) / n, "ci95": ci, "wins": sum(x < 0 for x in d), "losses": sum(x > 0 for x in d),
            "ties": sum(x == 0 for x in d), "verdict": verdict(n, ci)}


# ============================================================ backtest hücreleri (fold ledger'larından)

def _bt_cell(output: str, hk: Any, metric: str, rule_id: str, p: Optional[Mapping[str, Any]], label: str) -> dict[str, Any]:
    if p is None:
        return {"output": output, "horizon_or_k": hk, "metric": metric, "rule_id": rule_id, "model_value": None,
                "rule_value": None, "diff": None, "ci95": None, "n": 0, "n_blocks": 0, "wins": None, "losses": None,
                "ties": None, "verdict": None, "label": label, "scale": SCALE_BACKTEST}
    return {"output": output, "horizon_or_k": hk, "metric": metric, "rule_id": rule_id,
            "model_value": p["model_metric"], "rule_value": p["rule_metric"], "diff": p["mean"], "ci95": list(p["ci95"]),
            "n": p["n"], "n_blocks": p["n_months"], "wins": p["model_better_n"], "losses": p["rule_better_n"],
            "ties": p["tie_n"], "verdict": verdict(p["n"], p["ci95"]), "label": label, "scale": SCALE_BACKTEST,
            "bootstrap": "random.Random(20260921), ilk işlem ayı blokları, 4000 tekrar (SPEC_DEVIATIONS C7)"}


def _label(model_id: str, output: str, hk: Any, metric: str, rule_id: str) -> str:
    """birincil | ikincil (yalnız Faz 7/7C'nin §5.3 ilan edilmiş ikincilleri) | keşif. Var olan modellerin etiketi değişmedi."""
    pc = primary_cell_of(model_id)
    if pc and pc["output"] == output and pc["horizon_or_k"] == hk and pc["metric"] == metric and rule_id in pc["rule_ids"]:
        return "birincil"
    if (output, hk, metric, rule_id) in {_cell_key(c) for c in LIVE_SECONDARY_CELLS.get(model_id, ())}:
        return LABEL_SECONDARY
    return "keşif"


def backtest_cells(model_id: str, runs: Optional[Mapping[str, list]] = None,
                   runs4: Optional[Mapping[str, list]] = None) -> list[dict[str, Any]]:
    """docs/MODELS.md'deki eşleşik tabloların hücreleri; aynı ledger'lar ve aynı fonksiyonlar."""
    from . import report as r1
    from . import report_faz1b as rf

    runs = runs if runs is not None else rf.load_runs()
    cells: list[dict[str, Any]] = []

    def add(output, hk, metric, rule_id, p):
        cells.append(_bt_cell(output, hk, metric, rule_id, p, _label(model_id, output, hk, metric, rule_id)))

    if model_id == V15:
        for h in HORIZONS:
            for rule in RETURN_RULES:
                add("return", h, "MAE", rule, r1.paired(runs[V15], runs[rule], h, "return"))
        for h in HORIZONS:
            for rule in PROB_RULES:
                add("p_up", h, "Brier", rule, r1.paired(runs[V15], runs[rule], h, "p_up"))
    elif model_id in LINEAR_VS_V15:
        rows = runs[model_id]
        suffix = "__pb" if model_id == "pb_v0" else ""
        for h in HORIZONS:
            add("return", h, "MAE", V15, rf.paired(rows, runs[V15], rf.mae_model, rf.mae_model, rf.ok_ridge, rf.ok_ridge, horizon=h))
            add("p_up", h, "Brier", V15, rf.paired(rows, runs[V15], rf.brier_model, rf.brier_model, rf.ok_logit, rf.ok_logit, horizon=h))
        for h in HORIZONS:
            for rule in RETURN_RULES:
                add("return", h, "MAE", rule, rf.paired(rows, runs[rule + suffix], rf.mae_model, rf.mae_rule, rf.ok_ridge,
                                                        rf.ok_rule_ret, horizon=h))
        for h in HORIZONS:
            for rule in PROB_RULES:
                add("p_up", h, "Brier", rule, rf.paired(rows, runs[rule + suffix], rf.brier_model, rf.brier_rule, rf.ok_logit,
                                                        rf.ok_rule_p, horizon=h))
    elif model_id in ("ceiling_hazard_v0", "pb_ceiling_v0"):
        rows = runs[model_id]
        suffix = "" if model_id == "ceiling_hazard_v0" else "__pb_ceiling"
        comps = {f"{model_id}@INF": runs[f"{model_id}@INF"], "base_km_expanding": runs["base_km_expanding" + suffix],
                 "base_km_last10": runs["base_km_last10" + suffix],
                 "base_always_ceiling": runs["base_always_ceiling__" + ("ceiling" if not suffix else "pb_ceiling")]}
        rps_cells = {}
        for name, other in comps.items():
            p = rf.paired(rows, other, rf.rps, rf.rps, rf.ok_ceiling, rf.ok_ceiling)
            rps_cells[name] = p
            add("S", None, "RPS", name, p)
        best = min(("base_km_expanding", "base_km_last10"), key=lambda n: rps_cells[n]["rule_metric"])
        for k in range(1, sv.DAYS + 1):
            for name in (best, f"{model_id}@INF"):
                add("S", k, "Brier", name, rf.paired(rows, comps[name], rf.s_brier(k), rf.s_brier(k), rf.ok_ceiling, rf.ok_ceiling))
        for k in KS:
            for name, other in comps.items():
                add("P_close_ceiling", k, "Brier", name, rf.paired(rows, other, rf.pc_brier(k), rf.pc_brier(k), rf.ok_ceiling,
                                                                   rf.ok_ceiling))
            if not suffix:
                v15 = [r for r in runs[V15] if r["horizon"] == f"D{k}"]
                add("P_close_ceiling", k, "Brier", P_UP_AS_CEILING, rf.paired(
                    rows, v15, rf.pc_brier(k), None, rf.ok_ceiling, rf.ok_logit, key=lambda r: r["ticker"],
                    other_target=lambda o, r, k=k: (float(o["logit_probability"]) - int(r[f"realized_close_D{k}"])) ** 2))
        if suffix:
            add("S", None, "RPS", "ceiling_hazard_v0", rf.paired(rows, runs["ceiling_hazard_v0"], rf.rps, rf.rps, rf.ok_ceiling,
                                                                 rf.ok_ceiling, key=lambda r: r["ticker"]))
    elif model_id in CEILING_PATH_SPECS:
        from . import report_faz4 as r4      # aynı Faz 4 ledger'ları ve aynı eşleştirme; yeni hesap yok

        runs4 = runs4 if runs4 is not None else r4.load_faz4_runs()
        for h in HORIZONS:
            for metric, comp in CEILING_PATH_SPECS[model_id]:
                add(CELL_OUTPUT[metric], h, metric, comp, r4.compare(model_id, comp, h, metric, runs, runs4))
    return cells


# ============================================================ canlı sicil

@dataclass
class Context:
    git: Git
    proofs: list[dict[str, Any]]
    index: dict[str, Any]
    models: dict[str, dict[str, Any]]           # model_id -> INDEX kaydı
    legacy: dict[str, Any]
    ipos: list[dict[str, str]]
    realized: dict[str, Optional[Realized]]
    records: dict[str, list[tuple[Path, dict[str, Any]]]]
    cancelled: dict[str, dict[str, dict[str, Any]]]
    inputs_docs: dict[str, Optional[dict[str, Any]]]
    root: Path = ROOT
    cache: dict = field(default_factory=dict)


def load_context(*, root: Path = ROOT, outcomes_dir: Path = oc.OUTCOMES_DIR) -> Context:
    git = Git(root)
    index = json.loads((root / "models" / "INDEX.json").read_text(encoding="utf-8"))
    legacy = reg.load_legacy_roles()
    problems = reg.validate_legacy_roles(legacy, root=root)
    if problems:
        raise ScoringError("legacy_roles: " + "; ".join(problems))
    _, ipos = reg.read_ipos()
    frozen = [r for r in ipos if r["status"] in reg.IPO_STATUSES]
    records, cancelled, inputs_docs, realized = {}, {}, {}, {}
    for r in frozen:
        t = r["ticker"]
        recs = fz.list_records(t)
        records[t] = [(p, d) for p, d in recs if d.get("record_type") == fz.RECORD_PREDICTION]
        cancelled[t] = {d["cancels"]["file"]: d for _, d in recs if d.get("record_type") == fz.RECORD_CANCELLATION}
        ip = reg.INPUTS_DIR / f"{t}.json"
        inputs_docs[t] = reg.load_inputs(ip)[0] if ip.exists() else None
        realized[t] = load_realized(t, outcomes_dir)
    return Context(git, pp.load_proofs(), index, {e["model_id"]: e for e in index["models"]}, legacy, frozen, realized,
                   records, cancelled, inputs_docs, root)


def _rel(path: Path, root: Path) -> str:
    return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()


def _rel_or_none(path: Path, root: Path) -> Optional[str]:
    try:
        return _rel(path, root)
    except ValueError:
        return None


def registry_candidates(git: Git, records: Sequence[tuple[Path, Mapping[str, Any]]], cancelled: Iterable[str], model_id: str,
                        d1: str, proofs: Sequence[Mapping[str, Any]], root: Path) -> list[tuple[reg.Candidate, dict[str, Any]]]:
    """Sicil (registry/records) kayıtlarından (aday, ek bilgi). Skorlama (§6) ve POST_D1 kaydının base_record seçimi
    (`freeze.select_base_record`, SPEC_POST_D1_V0 §7.4) aynı kurucuyu kullanır."""
    cancelled = set(cancelled)
    out: list[tuple[reg.Candidate, dict[str, Any]]] = []
    for path, rec in records:
        cell = next((c for c in rec["models"] if c["model_id"] == model_id), None)
        if cell is None:
            continue
        rel = _rel_or_none(path, root)
        commit = git.added_commit(rel) if rel is not None else None
        pit = record_inputs_pit_problems(rec, d1, root=root)
        fields = rec["inputs"]["document"]["fields"]
        cand = reg.Candidate(record_id=path.name, model_id=model_id, track="REGISTRY",
                             has_official_f3=fields["total_demand_multiple"]["value"] is not None,
                             recorded_at=rec["recorded_at_utc"], push_created_at=proof_time(git, commit, proofs),
                             inputs_pit_ok=not pit, cancelled=path.name in cancelled,
                             bookbuilding_start=fields["bookbuilding_start"]["value"])
        out.append((cand, {"source": "REGISTRY", "path": rel, "commit": commit, "cell": cell, "pit_problems": pit,
                           "recorded_at_utc": rec["recorded_at_utc"]}))
    return out


def candidates_for(ctx: Context, ticker: str, model_id: str, d1: str) -> list[tuple[reg.Candidate, dict[str, Any]]]:
    """(aday, ek bilgi): sicil kayıtları + legacy kayıtlar. Ek bilgi: kaynak (kayıt/legacy) ve tahmin."""
    out = registry_candidates(ctx.git, ctx.records.get(ticker, []), ctx.cancelled.get(ticker, {}), model_id, d1, ctx.proofs,
                              ctx.root)
    for e in ctx.legacy["records"]:
        if e["ticker"] != ticker or e["model_id"] != model_id:
            continue
        pit = legacy_inputs_pit_problems(e, ctx.inputs_docs.get(ticker), d1, root=ctx.root)
        cand = reg.Candidate(record_id=e["record"], model_id=model_id,
                             track="GIT_PUSH" if e["time_proof"] == "GIT_PUSH" else "SELF_REPORTED",
                             has_official_f3=bool(e["has_official_f3"]),
                             recorded_at=e.get("prediction_timestamp_self_reported") or "",
                             push_created_at=legacy_push_time(e, root=ctx.root), inputs_pit_ok=not pit,
                             invalid_use=e["role"] == "INVALID_USE")
        out.append((cand, {"source": "LEGACY", "entry": e, "pit_problems": pit}))
    return out


def _row_status(pred: Mapping[str, Any], needs: Sequence[str]) -> str:
    """REFUSED | SCORED (modelin en az bir hedefi gerçekleşti; satır en az bir hücreye girer) | PENDING
    (hiçbiri gerçekleşmedi, bekleyen var) | TARGET_UNAVAILABLE (hiçbiri gerçekleşmedi ve gerçekleşmeyecek)."""
    if "refused" in pred:
        return ROW_REFUSED
    if any(s == "OK" for s in needs):
        return ROW_SCORED
    if any(s == oc.STATUS_PENDING for s in needs):
        return ROW_PENDING
    return ROW_TARGET_UNAVAILABLE


POST_D1_KS = tuple(range(2, sv.DAYS + 1))   # SPEC_POST_D1_V0 §7.3: yalnız h ≥ 2; D1 hedefi hiçbir zaman skorlanmaz


def _need_names(kind: str, path: bool = False) -> list[str]:
    """Modelin skorlanan hedefleri. `post_d1`: k = 2..10 tavan etiketleri (+ `path_conditional` varsa D3/D5/D10 getirisi);
    D1 hiçbir zaman (§7.3). `fall` (Faz 7C): yalnız D5 ve D10 (SPEC_C_V0 §2; SPEC_DEVIATIONS L)."""
    if kind == "post_d1":
        return [f"ceiling_close_D{k}" for k in POST_D1_KS] + ([f"D{h}" for h in CONDITIONAL_PATH_HS] if path else [])
    if kind in ("hazard", "km"):
        return ["L"] + [f"ceiling_close_D{k}" for k in KS]
    if kind == "fall":
        return list(pf.FALL_HORIZONS)
    return list(HORIZONS)


def _needs(kind: str, realized: Optional[Realized], path: bool = False) -> list[str]:
    """Modelin hedeflerinin durumu (OK | PENDING | TARGET_UNAVAILABLE | NA_LIMIT), `_need_names` sırasıyla."""
    if realized is None:
        return [oc.STATUS_PENDING] * len(_need_names(kind, path))
    if kind == "post_d1":
        return ([realized.row(k)["status"] for k in POST_D1_KS]
                + ([realized.target(f"D{h}")[0] for h in CONDITIONAL_PATH_HS] if path else []))
    if kind in ("hazard", "km"):
        return [realized.streak()[0]] + [realized.close_label(k)[0] for k in KS]
    if kind == "fall":
        return [realized.target(h)[0] for h in pf.FALL_HORIZONS]
    return [realized.target(h)[0] for h in HORIZONS]


def select(ctx: Context, ticker: str, model_id: str, d1: str) -> dict[str, Any]:
    key = (ticker, model_id, d1)
    if key not in ctx.cache:
        cands = candidates_for(ctx, ticker, model_id, d1)
        sel = reg.select_primary(model_id, [c for c, _ in cands], d1)
        ctx.cache[key] = {"selection": sel, "by_id": {c.record_id: (c, x) for c, x in cands}, "candidates": cands}
    return ctx.cache[key]


def _model_prediction(info: Mapping[str, Any], root: Path) -> dict[str, Any]:
    if info["source"] == "REGISTRY":
        return prediction_of_cell(info["cell"])
    return legacy_prediction(info["entry"], root=root)


def rule_values(ctx: Context, ticker: str, rule_id: str, d1: str, kind: str) -> dict[str, Any]:
    """Karşılaştırılan kuralın dondurma kaydındaki değeri (kendi birincil kaydı; sonradan hesaplanmaz)."""
    if rule_id == ALWAYS_CEILING_CURVE and kind in ("hazard", "km"):
        return {"record_id": None, "values": {"S": [1.0] * sv.DAYS, "P_close_ceiling": [1.0] * sv.DAYS},
                "source": "SPEC_DEVIATIONS C4: tavan planlarında her zaman tavan, tanım gereği S_k = 1"}
    if rule_id == P_UP_AS_CEILING:
        v = rule_values(ctx, ticker, V15, d1, "linear")
        if "refused" in v["values"]:
            return {"record_id": v["record_id"], "values": v["values"], "source": "v1_5_h99 p_up (SPEC_DEVIATIONS C5)"}
        return {"record_id": v["record_id"], "source": "v1_5_h99 p_up (SPEC_DEVIATIONS C5)",
                "values": {"P_close_ceiling_k": {str(k): v["values"][f"D{k}"]["p_up"] for k in KS}}}
    s = select(ctx, ticker, rule_id, d1)
    rid = s["selection"]["proven"]["record_id"]
    if rid is None:
        return {"record_id": None, "values": {"refused": {"code": "NO_ELIGIBLE_RECORD", "field": None,
                                                           "reason": s["selection"]["proven"]["rule"]}}}
    _, info = s["by_id"][rid]
    return {"record_id": rid, "values": _model_prediction(info, ctx.root)}


def comparators(model_id: str, kind: str) -> list[str]:
    if model_id in NEW_MODEL_COMPARATORS:          # dondurulmuş Faz 7 ve 7C (SPEC_HAZARD_V1 §5.2–§5.3, SPEC_C_V0 §5.2–§5.3)
        return list(NEW_MODEL_COMPARATORS[model_id])
    if kind in ("hazard", "km"):
        if model_id in ("ceiling_hazard_v0", "pb_ceiling_v0"):
            out = [f"{model_id}@INF", "base_km_expanding", "base_km_last10", ALWAYS_CEILING_CURVE]
            if model_id == "ceiling_hazard_v0":
                out.append(P_UP_AS_CEILING)
            return out
        return []
    if kind == "rule":
        return []
    out = list(dict.fromkeys(RETURN_RULES + PROB_RULES))
    if kind == "ceiling_path":                      # SPEC_CEILING_PATH_V0 §5
        return list(CEILING_PATH_MODEL_COMPARATORS.get(model_id, ())) + out
    if model_id in LINEAR_VS_V15:
        out.insert(0, V15)
    return out


def _row(ctx: Context, ipo: Mapping[str, str], model_id: str, kind: str, cand: reg.Candidate, info: Mapping[str, Any],
         d1: str, d1_basis: str, rule: str, extra: Mapping[str, Any]) -> dict[str, Any]:
    t = ipo["ticker"]
    realized = ctx.realized.get(t)
    oc_commit = outcome_ingest_commit(ctx.git, t, realized.session_dates if realized else [])
    cls, evidence = pair_class(ctx.git, model_evidence(ctx.git, ctx.models[model_id]["file"], ctx.proofs), oc_commit, cand, d1)
    pred = _model_prediction(info, ctx.root)
    rules = {r: rule_values(ctx, t, r, d1, kind) for r in comparators(model_id, kind)}
    evidence["record_commit"] = info["commit"] if info["source"] == "REGISTRY" else info["entry"].get("old_repo_commit")
    evidence["record_commit_repo"] = "this" if info["source"] == "REGISTRY" else "legacy (~/Desktop/Halka_Arz_Modeli)"
    row = {"ticker": t, "d1": d1, "d1_basis": d1_basis, "listed_first_trading_date": ipo["first_trading_date"],
           "class": cls, "record_id": cand.record_id, "record_source": info["source"], "selection_rule": rule,
           "prediction": pred, "rules": rules, "realized": realized.as_json() if realized else None,
           "status": _row_status(pred, _needs(kind, realized)),
           "targets": dict(zip(_need_names(kind), _needs(kind, realized))), "class_evidence": evidence,
           "inputs_pit_problems": info["pit_problems"]}
    row.update(extra)
    return row


NO_RECORD_RETRO_BASIS = ("MODEL_FROZEN_AFTER_OUTCOME_NO_RECORD: model bu arzın sonucu repoya girdikten sonra donduruldu; "
                         "arz için bu modelin kaydı yoktur (CLAUDE.md kural 3, SPEC_SCORING §5). Yalnız bilgi: hiçbir "
                         "metriğe, hiçbir canlı n'e girmez.")


def _no_record_retro(ctx: Context, ipo: Mapping[str, str], model_id: str, d1: str) -> Optional[dict[str, Any]]:
    """Kaydı olmayan (model, arz) çifti için RETRO bilgi satırı; model prospektifse None (satır üretilmez).

    Kanıt commit hash'i taşımaz: model dosyası scores.json ile AYNI commit'e girebilir ve o commit'in hash'i
    dosyaya yazılamaz (model JSON'undaki borsai_source_sha256 ile aynı gerekçe). Sınıf yine de tarihlerden
    kesindir: dosyası sonucun commit'inin atası olmayan (ya da push kanıtı olmayan) model prospektif değildir."""
    t = ipo["ticker"]
    realized = ctx.realized.get(t)
    oc_commit = outcome_ingest_commit(ctx.git, t, realized.session_dates if realized else [])
    ev = model_evidence(ctx.git, ctx.models[model_id]["file"], ctx.proofs)
    prospective = (ev["commit"] is not None and ev["push_proof_created_at"] is not None
                   and ctx.git.is_ancestor(ev["commit"], oc_commit or ctx.git.head()))
    if prospective:
        return None
    e = ctx.models[model_id]
    return {
        "model_id": model_id, "ticker": t, "record_id": None,
        "class_evidence": {"model_prospective": False, "model_frozen_at": e["frozen_at"],
                           "model_params_sha256": e["sha256"], "outcome_ingest_commit": oc_commit,
                           "checked_against": oc_commit or ctx.git.head(),
                           "outcome_ingest_basis": "COMMITTED" if oc_commit else "UNCOMMITTED_CHECKED_AGAINST_HEAD",
                           "d1": d1, "basis": NO_RECORD_RETRO_BASIS},
        "inputs_pit_problems": [],
    }


def live_block(ctx: Context, model_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """(canlı blok, RETRO bilgi satırları)."""
    params_kind = fz.model_kind(json.loads((ctx.root / "models" / ctx.models[model_id]["file"]).read_text(encoding="utf-8")))
    rows, self_rows, invalid_rows, cancelled_rows, retro = [], [], [], [], []
    for ipo in ctx.ipos:
        if ipo["status"] != "FROZEN":
            continue
        t = ipo["ticker"]
        realized = ctx.realized.get(t)
        d1 = realized.d1 if realized and realized.d1 else ipo["first_trading_date"]
        d1_basis = "REALIZED_THB" if realized and realized.d1 else "LISTED_NOT_YET_TRADED"
        s = select(ctx, t, model_id, d1)
        sel = s["selection"]
        for track, target in (("proven", rows), ("self_reported", self_rows)):
            e = sel[track]
            rid = e["record_id"]
            extra = {k: v for k, v in e.items() if k not in ("record_id", "rule")}
            if rid is None:
                if track != "proven":
                    continue
                # §4: model düzeyi ret atlama değildir: f3'süz kayıtta f3 modeli için hücre "ret + neden"
                refused = sorted((c for c, x in s["candidates"] if x["source"] == "REGISTRY" and not c.cancelled
                                  and x["cell"]["status"] == fz.STATUS_REFUSED), key=lambda c: c.recorded_at)
                if not refused:
                    no_rec = _no_record_retro(ctx, ipo, model_id, d1)
                    if no_rec is not None:
                        retro.append(no_rec)
                    continue
                rid, e = refused[0].record_id, {"rule": "REFUSED_IN_EARLIEST_RECORD"}
            cand, info = s["by_id"][rid]
            row = _row(ctx, ipo, model_id, params_kind, cand, info, d1, d1_basis, e["rule"], extra)
            if row["class"] == CLASS_RETRO:
                retro.append({"model_id": model_id, "ticker": t, "record_id": rid, "class_evidence": row["class_evidence"],
                              "inputs_pit_problems": row["inputs_pit_problems"]})
                continue
            target.append(row)
        for c, x in s["candidates"]:
            if c.invalid_use:
                invalid_rows.append({"ticker": t, "record_id": c.record_id, "note": "f3'süz; model bugün RET eder "
                                     "(SPEC_SCORING §6: geçersiz kullanım, hiçbir metriğe ve n'e girmez)",
                                     "prediction": legacy_prediction(x["entry"], root=ctx.root)})
            if c.cancelled:
                cd = ctx.cancelled[t][c.record_id]
                cancelled_rows.append({"ticker": t, "record_id": c.record_id, "cancelled_at": cd["recorded_at_utc"],
                                       "reason": cd["reason"]})
    count = lambda st: sum(r["status"] == st for r in rows)  # noqa: E731
    scored = [r for r in rows if r["status"] == ROW_SCORED]
    self_scored = [r for r in self_rows if r["status"] == ROW_SCORED]
    block = {
        "title": LIVE_TITLE,
        "n_live": sum(r["class"] == CLASS_LIVE for r in scored),     # skorlananların kırılımı: n_live + n_late = n_scored
        "n_late": sum(r["class"] == CLASS_LATE for r in scored),
        "n_scored": len(scored), "n_refused": count(ROW_REFUSED),
        "n_skipped": sum(r["status"] == "SKIPPED" for r in ctx.ipos),
        "n_target_unavailable": count(ROW_TARGET_UNAVAILABLE), "n_pending": count(ROW_PENDING),
        "n_rows": len(rows),
        "n_partial_pending": sum(oc.STATUS_PENDING in r["targets"].values() for r in scored),
        "rows": rows,
        "cells": live_cells(model_id, params_kind, scored) if len(scored) >= MIN_N_METRIC else [],
        "descriptive": live_descriptive(model_id, params_kind, scored) if len(scored) >= MIN_N_METRIC else [],
        "self_reported_rows": self_rows,
        "n_self_reported_scored": len(self_scored),
        "self_reported_cells": (live_cells(model_id, params_kind, scored + self_scored)
                                if self_rows and len(scored) + len(self_scored) >= MIN_N_METRIC else []),
        "invalid_use_rows": invalid_rows,
        "cancelled_records": cancelled_rows,
    }
    return block, retro


def _month(d1: str) -> str:
    return d1[:7]


def live_obs(model_id: str, kind: str, rows: Sequence[Mapping[str, Any]], output: str, hk: Any, metric: str,
             rule_id: str) -> list[PairedObs]:
    """Bir hücrenin eşleşik gözlemleri: model ve kural değeri olan, hedefi gerçekleşmiş canlı satırlar."""
    out = []
    for r in rows:
        if r["class"] not in PROSPECTIVE_CLASSES + (CLASS_LEGACY_SELF,) or r["status"] == ROW_REFUSED or r["realized"] is None:
            continue
        pred, rv = r["prediction"], r["rules"].get(rule_id, {}).get("values", {})
        if "refused" in rv:
            continue
        R = r["realized"]
        pair = _losses(kind, output, hk, metric, pred, rv, R)
        if pair is not None:
            out.append(PairedObs(SCALE_LIVE, r["ticker"], _month(r["d1"]), pair[0], pair[1], r["class"]))
    return out


def _losses(kind, output, hk, metric, pred, rv, R) -> Optional[tuple[float, float]]:
    if output in ("return", "p_up"):
        h = hk
        if R["row_status"][int(h[1:]) - 1] not in (oc.STATUS_OK, oc.STATUS_NA_LIMIT):
            return None
        Rv, Y = Decimal(R["R"][h]), R["Y"][h]
        m, q = (pred.get(h) or {}), (rv.get(h) or {})
        if output == "return":
            a, b = m.get("return"), q.get("return")
            if a is None or b is None:
                return None
            if metric == "MAE":
                return loss_mae(a, Rv), loss_mae(b, Rv)
            return loss_dir_miss(a, Y), loss_dir_miss(b, Y)
        a, b = m.get("p_up"), q.get("p_up")
        if a is None or b is None:
            return None
        fn = {"Brier": loss_brier, "LogLoss": loss_log, "HitMiss": loss_hit_miss}[metric]
        return fn(a, Y), fn(b, Y)
    if output == "S":
        if R["L"] is None:
            return None
        L = R["L"]
        a, b = pred.get("S"), rv.get("S")
        if a is None or b is None:
            return None
        if metric == "RPS":
            return loss_rps(a, L), loss_rps(b, L)
        k = hk
        y = 1.0 if L >= k else 0.0
        return (a[k - 1] - y) ** 2, (b[k - 1] - y) ** 2
    if output == "P_close_ceiling":
        k = hk
        lab = R["ceiling_close"][k - 1]
        if lab is None or R["row_status"][k - 1] != oc.STATUS_OK:
            return None
        a = (pred.get("P_close_ceiling") or [None] * sv.DAYS)[k - 1]
        b = rv["P_close_ceiling_k"][str(k)] if "P_close_ceiling_k" in rv else (rv.get("P_close_ceiling") or [None] * sv.DAYS)[k - 1]
        if a is None or b is None:
            return None
        return (a - lab) ** 2, (b - lab) ** 2
    raise ScoringError(f"bilinmeyen çıktı {output}")


def live_cell_specs(model_id: str, kind: str) -> list[tuple[str, Any, str, str]]:
    """Canlı hücre tanımları (§7), sonuç görülmeden: (çıktı, ufuk/k, metrik, kural)."""
    specs: list[tuple[str, Any, str, str]] = []
    comps = comparators(model_id, kind)
    if not comps:
        return specs
    if kind in ("hazard", "km"):
        for c in comps:
            if c != P_UP_AS_CEILING:
                specs.append(("S", None, "RPS", c))
        for k in KS:
            for c in comps:
                if c != P_UP_AS_CEILING:
                    specs.append(("S", k, "Brier", c))
        for k in KS:
            for c in comps:
                specs.append(("P_close_ceiling", k, "Brier", c))
        return specs
    if kind == "fall":        # SPEC_C_V0 §2: yalnız D5 ve D10 p_up (getiri başlığı yok); Brier kırpmasız, LogLoss, 0.5 eşikli isabet
        for h in pf.FALL_HORIZONS:
            for c in comps:
                specs.append(("p_up", h, "Brier", c))
                specs.append(("p_up", h, "LogLoss", c))
            specs.append(("p_up", h, "HitMiss", "base_rate"))
        return specs
    models = [c for c in comps if c not in RETURN_RULES and c not in PROB_RULES]   # iki çıktıda da karşılaştırılır
    for h in HORIZONS:
        for c in comps:
            if c in RETURN_RULES or c in models:
                specs.append(("return", h, "MAE", c))
        specs.append(("return", h, "DirMiss", "base_always_ceiling"))   # yön isabeti, "hep yukarı" ile yan yana
    for h in HORIZONS:
        for c in comps:
            if c in PROB_RULES or c in models:
                specs.append(("p_up", h, "Brier", c))
                specs.append(("p_up", h, "LogLoss", c))
        specs.append(("p_up", h, "HitMiss", "base_rate"))               # 0.5 eşikli isabet, taban oranıyla yan yana
    return specs


def live_cells(model_id: str, kind: str, rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """§8: yalnız n ≥ 10 olan hücreler üretilir; n < 10 -> boş liste (yalnız satır tablosu)."""
    out = []
    for output, hk, metric, rule_id in live_cell_specs(model_id, kind):
        obs = live_obs(model_id, kind, rows, output, hk, metric, rule_id)
        if len(obs) < MIN_N_METRIC:
            continue
        res = paired_metric(obs)
        out.append({"output": output, "horizon_or_k": hk, "metric": metric, "rule_id": rule_id, **res,
                    "label": _label(model_id, output, hk, metric, rule_id)})
    return out


def live_descriptive(model_id: str, kind: str, rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """§7'nin eşleşik fark olmayan ikincil ölçüleri (betimsel; aralık ve hüküm yok): getiri için medyan mutlak
    hata (model ve her getiri kuralı, aynı arz kümesi), tavan için kalibrasyon (ortalama S_k ve gözlenen
    P(L ≥ k)). Yalnız n ≥ 10 olduğunda üretilir."""
    import statistics

    comps = comparators(model_id, kind)
    out: list[dict[str, Any]] = []
    if not comps or kind == "fall":      # (C): getiri başlığı yok, canlıda betimsel satır tanımlı değil (SPEC_C_V0 §5.3)
        return out
    if kind in ("hazard", "km"):
        for k in KS:
            use = [r for r in rows if r["realized"] and r["realized"]["L"] is not None and "S" in r["prediction"]]
            if len(use) < MIN_N_METRIC:
                continue
            entry = {"output": "S", "horizon_or_k": k, "metric": "calibration_mean_S_vs_observed", "n": len(use),
                     "model_value": statistics.mean(r["prediction"]["S"][k - 1] for r in use),
                     "observed": statistics.mean(1.0 if r["realized"]["L"] >= k else 0.0 for r in use), "rules": {}}
            for c in comps:
                vals = [r["rules"][c]["values"].get("S") for r in use]
                if c != P_UP_AS_CEILING and all(v is not None for v in vals):
                    entry["rules"][c] = statistics.mean(v[k - 1] for v in vals)
            out.append(entry)
        return out
    for h in HORIZONS:
        use = [r for r in rows if r["realized"] and r["realized"]["R"].get(h) and "refused" not in r["prediction"]
               and r["prediction"][h]["return"] is not None]
        if len(use) < MIN_N_METRIC:
            continue
        err = lambda v, r: abs(v - float(r["realized"]["R"][h]))  # noqa: E731
        entry = {"output": "return", "horizon_or_k": h, "metric": "MedAE", "n": len(use),
                 "model_value": statistics.median(err(r["prediction"][h]["return"], r) for r in use), "rules": {}}
        models = [c for c in comps if c not in RETURN_RULES and c not in PROB_RULES]
        for c in comps:
            if c in RETURN_RULES or c in models:
                vals = [(r["rules"][c]["values"].get(h) or {}).get("return") for r in use]
                if all(v is not None for v in vals):
                    entry["rules"][c] = statistics.median(err(v, r) for v, r in zip(vals, use))
        out.append(entry)
    return out


# ============================================================ koşullu canlı skorlar (SPEC_CEILING_PATH_V0 §7)

def conditional_membership(realized: Optional[Realized], j: int) -> str:
    """(a, j) paydası: D_1..D_j'nin resmi THM tavan etiketi 1 ise L ≥ j bilinir (MEMBER). İlk j içinde bir 0 varsa
    L < j (NOT_MEMBER; önündeki NA sonucu değiştirmez). Aksi halde (etiket bekleniyor ya da NA) UNDETERMINED."""
    if realized is None:
        return UNDETERMINED
    labels = []
    for k in range(1, j + 1):
        r = realized.row(k)
        ok = r["status"] in (oc.STATUS_OK, oc.STATUS_NA_LIMIT) and r["ceiling_close"] not in ("", oc.NA)
        labels.append(int(r["ceiling_close"]) if ok else None)
    if 0 in labels:
        return NOT_MEMBER
    return MEMBER if all(x == 1 for x in labels) else UNDETERMINED


def conditional_target(realized: Realized, j: int) -> tuple[str, Optional[int], Optional[str]]:
    """Paydadaki (a, j) çiftinin hedef durumu, bütün modeller için aynı (G1): D_{j+1}..D_10'un hepsi girmiş ve L
    biliniyorsa SCORED; biri bekleniyorsa PENDING; biri oluşmayacaksa ya da NA etiket L'yi belirsiz bırakıyorsa
    TARGET_UNAVAILABLE. Dönen: (durum, L, neden)."""
    sts = [realized.row(k)["status"] for k in range(j + 1, sv.DAYS + 1)]
    if oc.STATUS_PENDING in sts:
        return ROW_PENDING, None, f"D_{j + 1}..D_10 seanslarından en az birinin sonucu bekleniyor"
    if oc.STATUS_TARGET_UNAVAILABLE in sts:
        return ROW_TARGET_UNAVAILABLE, None, "SESSION_NOT_FORMED"
    _, L = realized.streak()
    if L is None:
        return ROW_TARGET_UNAVAILABLE, None, "NA_LIMIT"
    return ROW_SCORED, L, None


def _l_at_least(realized: Realized) -> int:
    """Bilinen baştaki ardışık tavan sayısı (L henüz bilinmiyorsa alt sınır)."""
    n = 0
    for x in realized.labels():
        if x != 1:
            break
        n += 1
    return n


def conditional_rule_ids(model_id: str) -> list[str]:
    return list(dict.fromkeys(CONDITIONAL_S_COMPARATORS.get(model_id, ()) + CONDITIONAL_PATH_COMPARATORS.get(model_id, ())
                              + (tuple(CONDITIONAL_UNCONDITIONAL_REFS.values()) if model_id in CONDITIONAL_PATH_COMPARATORS
                                 else ())))


def _s_part(S: Sequence[float], j: int, L: Optional[int]) -> Optional[dict[str, Any]]:
    """S_cond = S_k / S_j (k = j+1..10) ve L biliniyorsa satır kayıpları (ortak fonksiyonlar). S_j ≤ 0 -> None."""
    try:
        s_cond, _ = pth.conditional_weights(S, j)
    except ValueError:
        return None
    out: dict[str, Any] = {"S_cond": {str(k): v for k, v in s_cond.items()}, "rps_cond": None, "brier_next": None,
                           "brier_10": None}
    if L is not None:
        out.update(rps_cond=pth.conditional_rps(S, j, L), brier_next=pth.conditional_brier(S, j, L, j + 1),
                   brier_10=pth.conditional_brier(S, j, L, sv.DAYS))
    return out


def _path_part(params: Mapping[str, Any], output: Mapping[str, Any], j: int, realized: Realized,
               scored: bool) -> Optional[dict[str, Any]]:
    """§7 durum 1 koşullu karışımı (`predict_path.conditional`) h ∈ {3, 5, 10}, h > j; C_t yerine gözlenen kapanış
    (D_1..D_j). Skorlanan çiftte medyanın mutlak hatası ve p_up Brier'i. Koşul tanımsızsa None."""
    closes = [realized.row(k)["close_raw"] for k in range(1, j + 1)]
    try:
        cond = pth.conditional(params, output, j, closes)
    except ValueError:
        return None
    out: dict[str, Any] = {"limit_path_mismatch": cond["limit_path_mismatch"]}
    for h in CONDITIONAL_PATH_HS:
        if h <= j:
            continue
        d = cond[f"D{h}"]
        e: dict[str, Any] = {"status": d["status"], "return": d["return"], "p_up": d["p_up"], "R": None, "Y": None,
                             "abs_error": None, "brier": None}
        if scored:
            _, R, Y = realized.target(f"D{h}")
            e.update(R=str(R), Y=Y)
            if d["status"] == pth.STATUS_OK:
                e.update(abs_error=loss_mae(d["return"], R), brier=loss_brier(d["p_up"], Y))
        out[f"D{h}"] = e
    return out


def _unconditional_ref(output: Mapping[str, Any], cell_output: str, j: int, realized: Realized,
                       scored: bool) -> dict[str, Any]:
    """Koşulsuz `base_train_median` (getiri) / `base_rate` (p_up): kayıttaki D_h değeri aynen, yalnız referans."""
    key, loss_key = ("return", "abs_error") if cell_output == "return_cond" else ("p_up", "brier")
    out: dict[str, Any] = {}
    for h in CONDITIONAL_PATH_HS:
        if h <= j:
            continue
        v = (output.get(f"D{h}") or {}).get(key)
        e: dict[str, Any] = {key: v, loss_key: None}
        if scored and v is not None:
            _, R, Y = realized.target(f"D{h}")
            e[loss_key] = loss_mae(v, R) if key == "return" else loss_brier(v, Y)
        out[f"D{h}"] = e
    return out


def conditional_row(model_id: str, unit: Mapping[str, Any], j: int, params: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Paydadaki (arz, j) satırı. Sınıf ve kayıt, koşulsuz canlı satırdan AYNEN (§7: j'ye göre yeniden sınıflanmaz)."""
    realized = unit["realized"]
    target, L, reason = conditional_target(realized, j)
    scored = target == ROW_SCORED
    row: dict[str, Any] = {"ticker": unit["ticker"], "d1": unit["d1"], "class": unit["class"], "record_id": unit["record_id"],
                           "L": L, "L_at_least": _l_at_least(realized), "S_cond": None, "rps_cond": None,
                           "brier_next": None, "brier_10": None, "status": target, "target_status": target,
                           "target_reason": reason, "rules": {}}
    for rid in CONDITIONAL_S_COMPARATORS.get(model_id, ()):
        src = unit["rules"][rid]
        if "refused" in src:
            row["rules"][rid] = {"record_id": src["record_id"], "refused": src["refused"]}
            continue
        sp = _s_part(src["output"]["S"], j, L)
        row["rules"][rid] = {"record_id": src["record_id"], **(sp if sp is not None else {"undefined": f"S_{j} = 0"})}
    path = model_id in CONDITIONAL_PATH_COMPARATORS
    if path:
        for rid in CONDITIONAL_PATH_COMPARATORS[model_id]:
            src = unit["rules"][rid]
            entry = {"record_id": src["record_id"]}
            if "refused" in src:
                entry["refused"] = src["refused"]
            else:
                part = _path_part(params[rid], src["output"], j, realized, scored)
                entry.update({"path": part} if part is not None else {"undefined": f"S_{j} = 0"})
            row["rules"][rid] = entry
        for cell_output, rid in CONDITIONAL_UNCONDITIONAL_REFS.items():
            src = unit["rules"][rid]
            entry = {"record_id": src["record_id"], "unconditional": True}
            if "refused" in src:
                entry["refused"] = src["refused"]
            else:
                entry["path"] = _unconditional_ref(src["output"], cell_output, j, realized, scored)
            row["rules"][rid] = entry
    if unit["refused"] is not None:
        row.update(status=ROW_REFUSED, refused=unit["refused"])
        return row
    sp = _s_part(unit["output"]["S"], j, L)
    if sp is None:
        row["status"] = ROW_UNDEFINED
        return row
    row.update(sp)
    if path:
        row["path"] = _path_part(params[model_id], unit["output"], j, realized, scored)
    return row


def conditional_cell_specs(model_id: str, j: int) -> list[tuple[str, Any, str, str]]:
    """j'deki hücre tanımları (§7), sonuç görülmeden: (çıktı, k ya da ufuk, metrik, karşılaştırılan)."""
    specs: list[tuple[str, Any, str, str]] = []
    comps = CONDITIONAL_S_COMPARATORS.get(model_id, ())
    specs += [("S_cond", None, "RPS", c) for c in comps]
    for k in sorted({j + 1, sv.DAYS}):            # "yarın" ve "sonuna kadar"; j = 9'da tek hücre (k = 10)
        specs += [("S_cond", k, "Brier", c) for c in comps]
    if model_id in CONDITIONAL_PATH_COMPARATORS:
        for output, metric in (("return_cond", "MAE"), ("p_up_cond", "Brier")):
            for h in CONDITIONAL_PATH_HS:
                if h > j:
                    specs += [(output, f"D{h}", metric, c) for c in CONDITIONAL_PATH_COMPARATORS[model_id]
                              + (CONDITIONAL_UNCONDITIONAL_REFS[output],)]
    return specs


def _cond_losses(row: Mapping[str, Any], output: str, hk: Any, metric: str, rule_id: str) -> Optional[tuple[float, float]]:
    rv = row["rules"].get(rule_id) or {}
    if output == "S_cond":
        key = "rps_cond" if metric == "RPS" else ("brier_10" if hk == sv.DAYS else "brier_next")
        a, b = row.get(key), rv.get(key)
    else:
        key = "abs_error" if output == "return_cond" else "brier"
        a = ((row.get("path") or {}).get(hk) or {}).get(key)
        b = ((rv.get("path") or {}).get(hk) or {}).get(key)
    return None if a is None or b is None else (a, b)


def conditional_obs(j: int, rows: Sequence[Mapping[str, Any]], output: str, hk: Any, metric: str,
                    rule_id: str) -> list[PairedObs]:
    """Bir koşullu hücrenin eşleşik gözlemleri: skorlanan satırlar, model ve karşılaştırılan değeri olan."""
    out = []
    for r in rows:
        if r["status"] != ROW_SCORED or r["class"] not in PROSPECTIVE_CLASSES:
            continue
        pair = _cond_losses(r, output, hk, metric, rule_id)
        if pair is not None:
            out.append(PairedObs(SCALE_LIVE_CONDITIONAL, r["ticker"], _month(r["d1"]), pair[0], pair[1], r["class"], j))
    return out


def _cond_label(output: str, hk: Any, metric: str, rule_id: str) -> str:
    if output != "S_cond" and rule_id == CONDITIONAL_UNCONDITIONAL_REFS.get(output):
        return LABEL_UNCONDITIONAL_REF
    p = CONDITIONAL_PRIMARY
    if (output, hk, metric) == (p["output"], p["horizon_or_k"], p["metric"]) and rule_id in p["rule_ids"]:
        return LABEL_PRIMARY
    return LABEL_EXPLORATORY


def conditional_cells(model_id: str, j: int, rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """§8 j başına: yalnız n ≥ 10 olan hücreler. Koşulsuz referans hücresi hüküm taşımaz (yalnız referans)."""
    out = []
    for output, hk, metric, rule_id in conditional_cell_specs(model_id, j):
        obs = conditional_obs(j, rows, output, hk, metric, rule_id)
        if len(obs) < MIN_N_METRIC:
            continue
        cell = {"output": output, "horizon_or_k": hk, "metric": metric, "rule_id": rule_id, **paired_metric(obs),
                "label": _cond_label(output, hk, metric, rule_id)}
        if cell["label"] == LABEL_UNCONDITIONAL_REF:
            cell.update(verdict=None, reference_only=True)
        out.append(cell)
    return out


def conditional_block(model_id: str, units: Sequence[Mapping[str, Any]], params: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """`models[].conditional` (SPEC_APP_EK2 §5). `units`: `conditional_units` çıktısı (ipos.csv sırası)."""
    by_j = []
    for j in CONDITIONAL_JS:
        rows: list[dict[str, Any]] = []
        n = dict.fromkeys(("n_skipped", "n_retro", "n_no_record", "n_undetermined"), 0)
        for u in units:
            mem = conditional_membership(u["realized"], j)
            if mem == NOT_MEMBER:
                continue
            if u["ipo_status"] == "SKIPPED":          # L < j kesinleşmedikçe atlanan sayılır (G7)
                n["n_skipped"] += 1
            elif mem == UNDETERMINED:
                n["n_undetermined"] += 1
            elif u["class"] is None:
                n["n_retro" if u["retro"] else "n_no_record"] += 1
            else:
                if u["class"] not in PROSPECTIVE_CLASSES:
                    raise ScoringError(f"{model_id}/{u['ticker']}: koşullu satır yalnız kanıtlı izden ({u['class']})")
                rows.append(conditional_row(model_id, u, j, params))
        count = lambda st: sum(r["status"] == st for r in rows)  # noqa: E731
        scored = [r for r in rows if r["status"] == ROW_SCORED]
        by_j.append({
            "j": j, "n_scored": len(scored), "n_refused": count(ROW_REFUSED), "n_skipped": n["n_skipped"],
            "n_target_unavailable": count(ROW_TARGET_UNAVAILABLE), "n_pending": count(ROW_PENDING),
            "n_undefined": count(ROW_UNDEFINED),
            "n_live": sum(r["class"] == CLASS_LIVE for r in scored), "n_late": sum(r["class"] == CLASS_LATE for r in scored),
            "n_retro": n["n_retro"], "n_no_record": n["n_no_record"], "n_undetermined": n["n_undetermined"],
            "rows": rows,
            "cells": conditional_cells(model_id, j, scored) if len(scored) >= MIN_N_METRIC else [],
        })
    s_comps = list(CONDITIONAL_S_COMPARATORS.get(model_id, ()))
    return {
        "schema_version": CONDITIONAL_SCHEMA, "title": CONDITIONAL_TITLE, "scale": SCALE_LIVE_CONDITIONAL,
        "definition": "SPEC_CEILING_PATH_V0 §7: seri j. günde sürüyorken S_k / S_j; RPS_j = (1/(10 − j)) Σ_{k>j} "
                      "(S_k/S_j − 1[L ≥ k])², Brier k = j + 1 ve k = 10; j başına ayrı, koşulsuzla birleşmez",
        "primary_cell": CONDITIONAL_PRIMARY if s_comps else None,
        "comparators": {"S_cond": s_comps, "path": list(CONDITIONAL_PATH_COMPARATORS.get(model_id, ())),
                        "unconditional_reference": (dict(CONDITIONAL_UNCONDITIONAL_REFS)
                                                    if model_id in CONDITIONAL_PATH_COMPARATORS else {})},
        "by_j": by_j,
    }


def _record_output(ctx: Context, ticker: str, model_id: str, d1: str, record_id: str) -> Mapping[str, Any]:
    """Birincil kayıttaki modelin tam çıktısı (dondurulmuş değer, yeniden hesap yok)."""
    _, info = select(ctx, ticker, model_id, d1)["by_id"][record_id]
    cell = info.get("cell")
    if info["source"] != "REGISTRY" or cell is None or cell["status"] != fz.STATUS_PREDICTED:
        raise ScoringError(f"{model_id}/{ticker}: {record_id} kaydında S çıktısı yok")
    return cell["output"]


def _cond_rule_source(ctx: Context, ticker: str, rule_id: str, d1: str) -> dict[str, Any]:
    """Koşullu karşılaştırılanın kendi birincil kaydındaki çıktısı (§6); her-zaman-tavan tanım gereği S ≡ 1 (C4)."""
    if rule_id == ALWAYS_CEILING_CURVE:
        return {"record_id": None, "output": {"S": [1.0] * sv.DAYS}}
    s = select(ctx, ticker, rule_id, d1)
    rid = s["selection"]["proven"]["record_id"]
    if rid is None:
        return {"record_id": None, "refused": {"code": "NO_ELIGIBLE_RECORD", "field": None,
                                               "reason": s["selection"]["proven"]["rule"]}}
    _, info = s["by_id"][rid]
    cell = info.get("cell")
    if info["source"] != "REGISTRY" or cell is None:
        return {"record_id": rid, "refused": {"code": "NO_RECORD_OUTPUT", "field": None, "reason": "legacy kayıt"}}
    if cell["status"] != fz.STATUS_PREDICTED:
        return {"record_id": rid, "refused": cell["refusal"]}
    return {"record_id": rid, "output": cell["output"]}


def conditional_units(ctx: Context, model_id: str, live: Mapping[str, Any], retro: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Payda adayları (ipos.csv'de FROZEN/SKIPPED, sırasıyla): sınıf ve kayıt koşulsuz canlı satırdan (kanıtlı iz)."""
    rows = {r["ticker"]: r for r in live["rows"]}
    retro_t = {x["ticker"] for x in retro}
    rule_ids = conditional_rule_ids(model_id)
    units = []
    for ipo in ctx.ipos:
        t = ipo["ticker"]
        realized = ctx.realized.get(t)
        lr = rows.get(t)
        u: dict[str, Any] = {"ticker": t, "ipo_status": ipo["status"], "realized": realized, "retro": t in retro_t,
                             "d1": realized.d1 if realized and realized.d1 else ipo["first_trading_date"],
                             "class": None, "record_id": None, "output": None, "refused": None, "rules": {}}
        if lr is not None:
            u.update({"class": lr["class"], "record_id": lr["record_id"], "d1": lr["d1"],
                      "rules": {rid: _cond_rule_source(ctx, t, rid, lr["d1"]) for rid in rule_ids}})
            if lr["status"] == ROW_REFUSED:
                u["refused"] = lr["prediction"]["refused"]
            else:
                u["output"] = _record_output(ctx, t, model_id, lr["d1"], lr["record_id"])
        units.append(u)
    return units


# ============================================================ POST_D1 aşaması (SPEC_POST_D1_V0 §7; SPEC_DEVIATIONS H28–H47)
#
# Canlı D1 sonrası kayıtlar (registry/post_d1/) ayrı terazidir (`live_post_d1`): koşulsuz canlı sicil, Faz 2C koşullu blokları
# ve backtest ile hiçbir tabloda birleşmez. Çıktı `scores/scores_post_d1.json` (şema borsai.scores_post_d1/1; L1: scores.json
# yapısına blok eklenmez) ve docs/SCORES.md §7. Satır alan adları Faz 2C j = 1 satırlarıyla aynıdır (EK 3 aynı okuyucu).

POST_D1_SCHEMA = "borsai.scores_post_d1/1"
POST_D1_SCORES_PATH = ROOT / "scores" / "scores_post_d1.json"
POST_D1_TITLE = "D1 sonrası güncelleme (canlı POST_D1, j = 1)"
SCALE_LIVE_POST_D1 = "live_post_d1"            # hiçbir ölçekle birleşmez (§6.1-10'un canlı karşılığı)
POST_D1_J = 1
POST_D1_COMPARATORS = fz.POST_D1_COMPARATORS   # kayıttaki comparators_conditional sırası
POST_D1_PATH_COMPARATOR = CEILING_PATH_MAIN   # §4: path_conditional ikincili, ceiling_path_v0'ın kendi j = 1 karışımı
LABEL_RULE, LABEL_SECONDARY = "kural", "ikincil"
POST_D1_PRIMARY = {"output": "S_cond", "horizon_or_k": None, "metric": "RPS", "rule_ids": ["ceiling_hazard_v0"]}
ROW_NOT_APPLICABLE = "NOT_APPLICABLE"
ROW_NOT_PRODUCED = "NOT_PRODUCED"
# §7.5 payda satırı (ipos.csv'de FROZEN her arz): aşama durumu
STAGE_RECORD = "RECORD"
STAGE_SKIPPED = "SKIPPED_POST_D1"
STAGE_NOT_APPLICABLE = "NOT_APPLICABLE"
STAGE_D1_LABEL_NA = "NOT_SCORABLE_D1_LABEL_NA"
STAGE_D1_PENDING = "D1_PENDING"
STAGE_RETRO = "RETRO"
STAGE_CALENDAR = reg.CALENDAR_NOT_AVAILABLE
SKIP_NO_POST_D1_RECORD = "NO_POST_D1_RECORD"
SKIP_NO_PRE_LISTING_RECORD = "NO_PRE_LISTING_RECORD"
POST_D1_PARITY_TOL = 1e-12
POST_D1_CLASS_DEFINITION = (
    "SPEC_POST_D1_V0 §7.3: LIVE = model_prospective_post_d1 VE push_kanıtı(kayıt commit'i).created_at < T_open; "
    "LATE_RECORD = model_prospective_post_d1 VE değil VE inputs_pit_ok_post_d1; RETRO aksi. T_open = D_1'i izleyen ilk resmi "
    "seans (ilan dışı kapanışlar düşülmüş) 09:40:00+03:00. model_prospective_post_d1 = commit_frozen(m) atası "
    "outcome_ingest_commit_post_d1 (tarihi > D_1 ilk bülten ya da h ≥ 2 dolu satır) VE modelin push kanıtı var.")


def outcome_ingest_commit_post_d1(git: Git, ticker: str, d1: str, *, outcomes_rel: str = "data/outcomes",
                                  bist_rel: str = "data/raw/bist") -> Optional[str]:
    """§7.3: min(data/raw/bist/ altına tarihi > D_1 olan ilk THB/THM'yi ekleyen commit, data/outcomes/<a>.csv'ye h ≥ 2 için
    dolu satırı (OK ya da NA_LIMIT; H34) ilk yazan commit). İkisi de yoksa None (sonuç commit edilmedi: HEAD'e karşı)."""
    commits = []
    for rel, c in git.added_under(bist_rel).items():
        m = _BULLETIN.match(Path(rel).name)
        if m is not None and f"{m.group(2)[:4]}-{m.group(2)[4:6]}-{m.group(2)[6:]}" > d1:
            commits.append(c)
    rel = f"{outcomes_rel}/{ticker}.csv"
    for c in git.history(rel):
        try:
            rows = list(csv.DictReader(git.show(c, rel).splitlines()))
        except subprocess.CalledProcessError:       # o commit'te dosya silinmiş
            continue
        if any(int(r["h"]) >= 2 and r["status"] in (oc.STATUS_OK, oc.STATUS_NA_LIMIT) for r in rows):
            commits.append(c)
            break
    return git.earliest(commits)


def model_prospective_post_d1(git: Git, model_ev: Mapping[str, Any], outcome_commit: Optional[str]) -> bool:
    """§7.3: is_ancestor(commit_frozen(m), outcome_ingest_commit_post_d1(a)) VE push kanıtı(commit_frozen(m)) var. Sonuç
    commit edilmediyse HEAD'e karşı (sonuç commit'i HEAD'in torunu olacaktır; E15 kalıbı)."""
    target = outcome_commit or git.head()
    return (model_ev["commit"] is not None and model_ev["push_proof_created_at"] is not None
            and git.is_ancestor(model_ev["commit"], target))


def record_live_post_d1(record_push_created_at: Optional[str], t_open_at: datetime) -> bool:
    """§7.3: push kanıtı(commit_record).created_at < T_open (saat dilimli an karşılaştırması; yerel saat yok)."""
    return reg.before_t_open(record_push_created_at, t_open_at)


def inputs_pit_problems_post_d1(rec: Mapping[str, Any], d1: str, *, root: Path = ROOT,
                                manifest: Optional[Mapping[tuple[str, str], Mapping[str, str]]] = None) -> list[str]:
    """§7.3 inputs_pit_ok_post_d1: (i) dayandığı listeleme öncesi kaydın inputs_pit_ok'u (SPEC_SCORING §5; dosya ve sha256
    aynı) VE (ii) her bülten atfı tam D_1 VE (iii) sha256 MANIFEST'e ve dosyaya eşit VE (iv) D_1 dışı seans alanı yok
    (`registry.post_d1_record_problems`, bekçiyle tek tanım). Boş liste = pit tamam."""
    root = Path(root)
    manifest = manifest if manifest is not None else {(r["date"], r["kind"]): r
                                                      for r in oc.read_manifest(root / "data" / "raw" / "bist")}
    problems: list[str] = []
    base = rec.get("base_record") or {}
    bp = root / str(base.get("file", ""))
    if not base.get("file") or not bp.is_file():
        problems.append(f"(i) base_record dosyası yok: {base.get('file')!r}")
    elif sha256_file(bp) != base.get("sha256"):
        problems.append("(i) base_record sha256 dosyayla aynı değil")
    else:
        problems += [f"(i) base_record: {x}" for x in record_inputs_pit_problems(json.loads(bp.read_text(encoding="utf-8")), d1,
                                                                                    root=root)]
    if (rec.get("d1") or {}).get("session_date") != d1:
        problems.append(f"(ii) kaydın D_1'i {(rec.get('d1') or {}).get('session_date')!r} gerçekleşen D_1 {d1} değil")
    problems += [f"(ii–iv) {x}" for x in reg.post_d1_record_problems(rec, manifest)]
    for kind in oc.KINDS:
        ref = (rec.get("d1") or {}).get(kind) or {}
        fp = root / str(ref.get("file", ""))
        if not ref.get("file") or not fp.is_file() or sha256_file(fp) != ref.get("sha256"):
            problems.append(f"(iii) d1.{kind} dosyası yok ya da sha256 dosyayla aynı değil")
    return problems


def class_post_d1(git: Git, model_ev: Mapping[str, Any], outcome_commit: Optional[str], record_push_created_at: Optional[str],
                  t_open_at: datetime, pit_ok: bool, d1: str) -> tuple[str, dict[str, Any]]:
    """§7.3 `class_post_d1` (= §7.6 `pair_class_post_d1`); formül SPEC_SCORING §5 ile aynı saf `classify`."""
    prospective = model_prospective_post_d1(git, model_ev, outcome_commit)
    live = record_live_post_d1(record_push_created_at, t_open_at)
    return classify(prospective, live, pit_ok), {
        "model_commit": model_ev["commit"], "model_push_proof_created_at": model_ev["push_proof_created_at"],
        "outcome_ingest_commit": outcome_commit, "checked_against": outcome_commit or git.head(),
        "outcome_ingest_basis": "COMMITTED" if outcome_commit else "UNCOMMITTED_CHECKED_AGAINST_HEAD",
        "model_prospective": prospective, "record_push_proof_created_at": record_push_created_at,
        "t_open": t_open_at.isoformat(), "record_live": live, "inputs_pit_ok": pit_ok, "d1": d1,
    }


def post_d1_outcome_order_violations(root: Path = ROOT) -> list[str]:
    """§7.3 bekçisi: data/outcomes/<T>.csv'de h ≥ 2 dolu satırı (OK / NA_LIMIT) ilk yazan commit, o satırın seansının THB ve
    THM bültenini ekleyen commit'in torunu (ya da kendisi) olmalı; bülten commit edilmemişse ihlal."""
    git = Git(root)
    added = git.added_under("data/raw/bist")
    out: list[str] = []
    d = Path(root) / "data" / "outcomes"
    for p in sorted(d.glob("*.csv")) if d.exists() else []:
        if p.name == oc.COMPLETENESS_NAME:
            continue
        rel = f"data/outcomes/{p.name}"
        first: dict[int, tuple[str, str]] = {}
        for c in git.history(rel):
            try:
                rows = list(csv.DictReader(git.show(c, rel).splitlines()))
            except subprocess.CalledProcessError:
                continue
            for r in rows:
                h = int(r["h"])
                if h >= 2 and r["status"] in (oc.STATUS_OK, oc.STATUS_NA_LIMIT) and h not in first:
                    first[h] = (c, r["session_date"])
        for h, (c, day) in sorted(first.items()):
            for kind in oc.KINDS:
                b = added.get(f"data/raw/bist/{kind}/{day[:4]}/{kind}{oc.compact(day)}1.zip")
                if b is None or not git.is_ancestor(b, c):
                    out.append(f"{rel} h={h} ({day}): satırı yazan {c[:12]}, {kind.upper()} bülten commit'i ({b}) atası değil")
    return out


@dataclass
class PostD1Context:
    index_sha256: Optional[str]
    entries: list[dict[str, Any]]                                   # models/INDEX_POST_D1.json kayıtları
    params: dict[str, dict[str, Any]]
    records: dict[str, list[tuple[Path, dict[str, Any]]]]           # arz -> POST_D1 tahmin kayıtları
    cancelled: dict[str, set[str]]
    manifest: dict[tuple[str, str], dict[str, str]]
    calendar: Any


def load_post_d1_context(root: Path = ROOT, *, calendar: Any = None) -> PostD1Context:
    root = Path(root)
    path = root / "models" / fz.INDEX_POST_D1_NAME
    entries, params, sha = [], {}, None
    if path.exists():
        raw = path.read_bytes()
        sha = hashlib_sha256(raw)
        entries = json.loads(raw)["models"]
        for e in entries:
            data = (root / "models" / e["file"]).read_bytes()
            if hashlib_sha256(data) != e["sha256"]:
                raise ScoringError(f"{e['model_id']}: dosya sha256 INDEX_POST_D1.json ile aynı değil")
            params[e["model_id"]] = json.loads(data)
    records, cancelled = {}, {}
    post_dir = root / "registry" / "post_d1"
    for d in sorted(post_dir.iterdir()) if post_dir.exists() else []:
        if d.is_dir():
            recs = fz.list_records(d.name, post_dir)
            records[d.name] = [(p, r) for p, r in recs if r.get("record_type") == fz.RECORD_PREDICTION]
            cancelled[d.name] = {r["cancels"]["file"] for _, r in recs if r.get("record_type") == fz.RECORD_CANCELLATION}
    manifest = {(r["date"], r["kind"]): r for r in oc.read_manifest(root / "data" / "raw" / "bist")}
    return PostD1Context(sha, entries, params, records, cancelled, manifest,
                         calendar if calendar is not None else oc.load_calendar(bist_dir=root / "data" / "raw" / "bist"))


def hashlib_sha256(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _d1_label(realized: Optional[Realized]) -> tuple[str, Optional[int]]:
    """D1 tavan etiketi (resmi THM, SPEC_SCORING §3): (durum, etiket). Durum PENDING | NA | OK."""
    if realized is None or realized.row(1)["status"] not in (oc.STATUS_OK, oc.STATUS_NA_LIMIT):
        return "PENDING", None
    lab = realized.row(1)["ceiling_close"]
    return ("NA", None) if lab in ("", oc.NA) else ("OK", int(lab))


def _post_d1_path_part(stored: Optional[Mapping[str, Any]], realized: Realized, scored: bool) -> Optional[dict[str, Any]]:
    """Kayıttaki (dondurulmuş) path_conditional'ın h ∈ {3, 5, 10} değerleri ve skorlanan çiftte satır kayıpları
    (`_path_part` ile aynı kayıp tanımları: medyanın mutlak hatası, p_up Brier)."""
    if stored is None:
        return None
    out: dict[str, Any] = {"limit_path_mismatch": stored.get("limit_path_mismatch")}
    for h in CONDITIONAL_PATH_HS:
        d = stored[f"D{h}"]
        e: dict[str, Any] = {"status": d["status"], "return": d["return"], "p_up": d["p_up"], "R": None, "Y": None,
                             "abs_error": None, "brier": None}
        if scored:
            _, R, Y = realized.target(f"D{h}")
            e.update(R=str(R), Y=Y)
            if d["status"] == pth.STATUS_OK:
                e.update(abs_error=loss_mae(d["return"], R), brier=loss_brier(d["p_up"], Y))
        out[f"D{h}"] = e
    return out


def post_d1_comparator_parity(row_rules: Mapping[str, Mapping[str, Any]], faz2c_row: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    """§7.4: kaydın comparators_conditional kopyasının S_cond'u Faz 2C j = 1 satırıyla |Δ| ≤ 1e-12 (aynı arz, ceiling_hazard_v0
    bloğu; karşılaştırıcılar o satırın `rules`'u). Faz 2C satırı yoksa (ceiling_hazard_v0 için RETRO/kayıtsız) NOT_AVAILABLE.
    Aşım -> ScoringError (sessiz sapma yok; H39)."""
    if faz2c_row is None:
        return {"status": "NOT_AVAILABLE", "max_abs_diff": None}
    worst = 0.0
    for rid, mine in row_rules.items():
        if rid == ALWAYS_CEILING_CURVE:
            theirs = (faz2c_row["rules"].get(rid) or {}).get("S_cond")
        elif rid == "ceiling_hazard_v0":
            theirs = faz2c_row.get("S_cond")
        else:
            theirs = (faz2c_row["rules"].get(rid) or {}).get("S_cond")
        a = mine.get("S_cond")
        if a is None or theirs is None:
            if (a is None) != (theirs is None):
                raise ScoringError(f"POST_D1 karşılaştırıcı {rid}: kayıt kopyası ile Faz 2C satırından biri eksik")
            continue
        if set(a) != set(theirs):
            raise ScoringError(f"POST_D1 karşılaştırıcı {rid}: S_cond anahtarları farklı")
        worst = max(worst, max(abs(a[k] - theirs[k]) for k in a))
    if worst > POST_D1_PARITY_TOL:
        raise ScoringError(f"POST_D1 karşılaştırıcı kopyası Faz 2C j = 1 satırından {worst} farklı (> 1e-12)")
    return {"status": "OK", "max_abs_diff": worst}


def post_d1_row(model_id: str, ticker: str, d1: str, klass: str, record_path: Path, rec: Mapping[str, Any],
                realized: Realized, t_open_at: datetime, evidence: Mapping[str, Any], pit: Sequence[str],
                faz2c_row: Optional[Mapping[str, Any]], path_params: Optional[Mapping[str, Any]], root: Path) -> dict[str, Any]:
    """Bir (POST_D1 modeli, arz) satırı, Faz 2C j = 1 satır alan adlarıyla. Hedef durumu bütün modellerde aynı
    (`conditional_target`, yalnız D2..D10); model S'i ve karşılaştırıcı kopyaları kayıttan (dondurulmuş, yeniden hesap yok)."""
    target, L, reason = conditional_target(realized, POST_D1_J)
    scored = target == ROW_SCORED
    cell = next(c for c in rec["models"] if c["model_id"] == model_id)
    base_name = Path(rec["base_record"]["file"]).name
    row: dict[str, Any] = {"ticker": ticker, "d1": d1, "class": klass, "record_id": record_path.name, "t_open": t_open_at.isoformat(),
                           "L": L, "L_at_least": _l_at_least(realized), "S_cond": None, "rps_cond": None, "brier_next": None,
                           "brier_10": None, "status": target, "target_status": target, "target_reason": reason, "rules": {},
                           "path": None, "path_status": None, "class_evidence": dict(evidence), "inputs_pit_problems": list(pit),
                           "base_record": rec["base_record"]["file"]}
    for rid in POST_D1_COMPARATORS:
        src = rec["comparators_conditional"][rid]
        rid_rec = None if rid == ALWAYS_CEILING_CURVE else base_name
        if src["S"] is None:
            row["rules"][rid] = {"record_id": rid_rec, "refused": {"code": "NO_S_IN_BASE_RECORD", "field": None,
                                                                   "reason": "base_record hücresinde S yok (ret ya da model yok)"}}
            continue
        sp = _s_part(src["S"], POST_D1_J, L)
        row["rules"][rid] = {"record_id": rid_rec, **(sp if sp is not None else {"undefined": "S_1 = 0"})}
    row["comparator_parity"] = post_d1_comparator_parity(row["rules"], faz2c_row)
    base_cells = {}
    bp = Path(root) / rec["base_record"]["file"]
    if bp.is_file():
        base_cells = {c["model_id"]: c for c in json.loads(bp.read_text(encoding="utf-8"))["models"]}
    pc = base_cells.get(POST_D1_PATH_COMPARATOR)
    if pc is not None and pc["status"] == fz.STATUS_PREDICTED and path_params is not None:
        part = _path_part(path_params, pc["output"], POST_D1_J, realized, scored)
        row["rules"][POST_D1_PATH_COMPARATOR] = {"record_id": base_name,
                                                 **({"path": part} if part is not None else {"undefined": "S_1 = 0"})}
    else:
        row["rules"][POST_D1_PATH_COMPARATOR] = {"record_id": base_name if pc is not None else None, "not_produced": True}
    if cell["status"] == fz.STATUS_REFUSED:
        row.update(status=ROW_REFUSED, refused=cell["refusal"])
        return row
    if cell["status"] == fz.STATUS_NOT_APPLICABLE:
        row.update(status=ROW_NOT_APPLICABLE, not_applicable=cell["refusal"])
        return row
    sp = _s_part(cell["output"]["S"], POST_D1_J, L)
    if sp is None:
        row["status"] = ROW_UNDEFINED
        return row
    row.update(sp)
    stored = cell["output"].get("path_conditional")
    row["path"] = _post_d1_path_part(stored, realized, scored)
    row["path_status"] = ROW_NOT_PRODUCED if stored is None else ("OK" if scored else target)
    return row


def post_d1_cell_specs() -> list[tuple[str, Any, str, str]]:
    """§4 hücreleri (sonuç görülmeden): RPS_1 beş karşılaştırılana karşı (birincil: ceiling_hazard_v0), Brier k = 2 ve k = 10,
    path_conditional h ∈ {3, 5, 10} MAE ve p_up Brier (ceiling_path_v0'ın kendi j = 1 karışımı)."""
    specs: list[tuple[str, Any, str, str]] = [("S_cond", None, "RPS", c) for c in POST_D1_COMPARATORS]
    for k in (POST_D1_J + 1, sv.DAYS):
        specs += [("S_cond", k, "Brier", c) for c in POST_D1_COMPARATORS]
    for output, metric in (("return_cond", "MAE"), ("p_up_cond", "Brier")):
        specs += [(output, f"D{h}", metric, POST_D1_PATH_COMPARATOR) for h in CONDITIONAL_PATH_HS]
    return specs


def _post_d1_label(output: str, hk: Any, metric: str, rule_id: str) -> str:
    p = POST_D1_PRIMARY
    if (output, hk, metric) == (p["output"], p["horizon_or_k"], p["metric"]):
        return LABEL_PRIMARY if rule_id in p["rule_ids"] else LABEL_RULE
    return LABEL_SECONDARY


def post_d1_obs(rows: Sequence[Mapping[str, Any]], output: str, hk: Any, metric: str, rule_id: str) -> list[PairedObs]:
    out = []
    for r in rows:
        if r["status"] != ROW_SCORED or r["class"] not in PROSPECTIVE_CLASSES:
            continue
        pair = _cond_losses(r, output, hk, metric, rule_id)
        if pair is not None:
            out.append(PairedObs(SCALE_LIVE_POST_D1, r["ticker"], _month(r["d1"]), pair[0], pair[1], r["class"], POST_D1_J))
    return out


def post_d1_cells(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """SPEC_SCORING §8: yalnız n ≥ 10 hücreler; aralık n ≥ 10 ve ≥ 6 blokta; hüküm yalnız n ≥ 30."""
    out = []
    for output, hk, metric, rule_id in post_d1_cell_specs():
        obs = post_d1_obs(rows, output, hk, metric, rule_id)
        if len(obs) < MIN_N_METRIC:
            continue
        out.append({"output": output, "horizon_or_k": hk, "metric": metric, "rule_id": rule_id, **paired_metric(obs),
                    "label": _post_d1_label(output, hk, metric, rule_id)})
    return out


def post_d1_descriptive(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """§4 kalibrasyon (ikincil, betimsel; aralık ve hüküm yok, n ≥ 10): ort(h_2) = ort(1 − S_cond[2]) ile gözlenen D2
    kırılma oranı; ort(S_cond[k]) ile gözlenen P(L ≥ k | L ≥ 1), k = 2, 3, 5, 10."""
    use = [r for r in rows if r["status"] == ROW_SCORED and r["class"] in PROSPECTIVE_CLASSES]
    if len(use) < MIN_N_METRIC:
        return []
    import statistics

    out = [{"output": "p_break_next", "horizon_or_k": 2, "metric": "calibration_mean_vs_observed", "n": len(use),
            "model_value": statistics.fmean(1.0 - r["S_cond"]["2"] for r in use),
            "observed": statistics.fmean(0.0 if r["L"] >= 2 else 1.0 for r in use)}]
    for k in (2, 3, 5, 10):
        out.append({"output": "S_cond", "horizon_or_k": k, "metric": "calibration_mean_vs_observed", "n": len(use),
                    "model_value": statistics.fmean(r["S_cond"][str(k)] for r in use),
                    "observed": statistics.fmean(1.0 if r["L"] >= k else 0.0 for r in use)})
    return out


def post_d1_card(entry: Mapping[str, Any], model_id: str) -> dict[str, Any]:
    """Model kartı. L8: donmuş JSON'un `training.cutoff_date` / INDEX `training_cutoff_date` (2026-08-13) δ eğitim arzlarının
    10 seansının en geç tarihidir; "kesim" olarak gösterilmez. Şartnamenin eğitim kesimi (§3.5) ayrı alan."""
    nv, nr = _n_variants_same_data(entry["data_version_sha256"], model_id)
    return {"training_n": entry["training_n"], "params_sha256_8": entry["sha256"][:8], "n_variants_same_data": nv,
            "n_runs_same_data": nr, "training_last_session_date": entry["training_cutoff_date"],
            "training_last_session_date_meaning": "δ eğitim arzlarının 10 seansının en geç tarihi (JSON alanı training.cutoff_date; "
                                                  "kesim değil, SPEC_DEVIATIONS H43)",
            "spec_training_cutoff": OUTCOME_CUTOFF,     # SPEC_POST_D1_V0 §3.5 "Kesim 2026-08-19" (eğitim verisinin sınırı)
            "stage": entry.get("stage"), "parent_model_id": entry.get("parent_model_id")}


def post_d1_block(ctx: Context, pctx: PostD1Context, entry: Mapping[str, Any],
                  faz2c_j1: Mapping[str, Mapping[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """(j = 1 blok, RETRO bilgi satırları). `faz2c_j1`: arz -> scores.json'daki ceiling_hazard_v0 koşullu j = 1 satırı."""
    model_id = entry["model_id"]
    model_ev = model_evidence(ctx.git, entry["file"], ctx.proofs)
    params = pctx.params[model_id]
    path_params = None
    sec = params.get("path_secondary") or {}
    if sec.get("model_id") in ctx.models:
        path_params = json.loads((ctx.root / "models" / ctx.models[sec["model_id"]]["file"]).read_text(encoding="utf-8"))
    rows, denom, retro = [], [], []
    n = dict.fromkeys(("n_skipped", "n_not_applicable", "n_d1_label_na", "n_undetermined", "n_retro", "n_no_record",
                       "n_calendar_not_available"), 0)
    for ipo in ctx.ipos:
        if ipo["status"] != "FROZEN":
            continue
        t = ipo["ticker"]
        realized = ctx.realized.get(t)
        d1 = realized.d1 if realized and realized.d1 else None
        oc_commit = outcome_ingest_commit_post_d1(ctx.git, t, d1) if d1 else None
        d_row: dict[str, Any] = {"ticker": t, "d1": d1, "listed_first_trading_date": ipo["first_trading_date"],
                                 "ceiling_close_D1": None, "stage_status": None, "skip_reason": None, "class": None,
                                 "record_id": None}
        denom.append(d_row)
        label_state, label = _d1_label(realized)
        d_row["ceiling_close_D1"] = label if label_state == "OK" else (oc.NA if label_state == "NA" else None)
        recs = [(p, r) for p, r in pctx.records.get(t, []) if any(c["model_id"] == model_id for c in r["models"])]
        if not model_prospective_post_d1(ctx.git, model_ev, oc_commit):
            n["n_retro"] += 1
            d_row["stage_status"] = STAGE_RETRO
            retro.append({"model_id": model_id, "ticker": t, "record_id": None, "d1": d1,
                          "class_evidence": {"model_prospective": False, "model_frozen_at": entry["frozen_at"],
                                             "model_params_sha256": entry["sha256"], "outcome_ingest_commit": oc_commit,
                                             "checked_against": oc_commit or ctx.git.head(),
                                             "outcome_ingest_basis": "COMMITTED" if oc_commit else "UNCOMMITTED_CHECKED_AGAINST_HEAD",
                                             "d1": d1, "n_post_d1_records": len(recs),
                                             "basis": "MODEL_FROZEN_AFTER_D2_OUTCOME: model, D_1'den sonraki ilk sonuç verisi "
                                                      "repoya girdikten sonra donduruldu (SPEC_POST_D1_V0 §7.3, §7.5). Yalnız "
                                                      "bilgi: hiçbir n'e girmez."}})
            continue
        if label_state == "PENDING":
            n["n_undetermined"] += 1
            d_row["stage_status"] = STAGE_D1_PENDING
            continue
        if label_state == "NA":
            n["n_d1_label_na"] += 1
            d_row["stage_status"] = STAGE_D1_LABEL_NA
            continue
        if label == 0:
            n["n_not_applicable"] += 1
            d_row["stage_status"] = STAGE_NOT_APPLICABLE
            continue
        try:
            t_open_at = reg.t_open(d1, pctx.calendar)
        except reg.CalendarNotAvailable:
            n["n_calendar_not_available"] += 1
            d_row["stage_status"] = STAGE_CALENDAR
            continue
        cands, info = [], {}
        for p, r in recs:
            rel = _rel_or_none(p, ctx.root)
            push = proof_time(ctx.git, ctx.git.added_commit(rel) if rel else None, ctx.proofs)
            pit = inputs_pit_problems_post_d1(r, d1, root=ctx.root, manifest=pctx.manifest)
            cands.append(reg.PostD1Candidate(p.name, r["recorded_at_utc"], push, not pit, p.name in pctx.cancelled.get(t, set())))
            info[p.name] = (p, r, push, pit)
        sel = reg.select_primary_post_d1(cands, t_open_at)
        if sel["record_id"] is None:
            base = select(ctx, t, fz.BASE_MODEL_ID, d1)["selection"]["proven"]["record_id"]
            n["n_skipped"] += 1
            if base is not None:
                n["n_no_record"] += 1
            d_row.update(stage_status=STAGE_SKIPPED, skip_reason=SKIP_NO_POST_D1_RECORD if base is not None else SKIP_NO_PRE_LISTING_RECORD)
            continue
        p, r, push, pit = info[sel["record_id"]]
        cls, ev = class_post_d1(ctx.git, model_ev, oc_commit, push, t_open_at, not pit, d1)
        ev["selection_rule"] = sel["rule"]
        d_row.update(record_id=p.name, **{"class": cls})
        if cls == CLASS_RETRO:
            n["n_retro"] += 1
            d_row["stage_status"] = STAGE_RETRO
            retro.append({"model_id": model_id, "ticker": t, "record_id": p.name, "d1": d1, "class_evidence": ev,
                          "inputs_pit_problems": pit})
            continue
        d_row["stage_status"] = STAGE_RECORD
        rows.append(post_d1_row(model_id, t, d1, cls, p, r, realized, t_open_at, ev, pit, faz2c_j1.get(t), path_params, ctx.root))
    count = lambda st: sum(x["status"] == st for x in rows)  # noqa: E731
    scored = [x for x in rows if x["status"] == ROW_SCORED]
    block = {
        "title": POST_D1_TITLE, "scale": SCALE_LIVE_POST_D1, "j": POST_D1_J,
        "definition": "SPEC_POST_D1_V0 §4, §7: D1'i tavanda kapatan arzda S_cond[k] = S_k / S_1, k = 2..10; RPS_1 = (1/9) "
                      "Σ_{k=2..10} (S_cond[k] − 1[L ≥ k])², Brier k = 2 ve k = 10; D1 hedefi skorlanmaz; hiçbir ölçekle birleşmez",
        "class_definition": POST_D1_CLASS_DEFINITION,
        "primary_cell": POST_D1_PRIMARY,
        "comparators": {"S_cond": list(POST_D1_COMPARATORS), "path": [POST_D1_PATH_COMPARATOR]},
        "n_scored": len(scored), "n_refused": count(ROW_REFUSED), "n_skipped": n["n_skipped"],
        "n_not_applicable": n["n_not_applicable"] + count(ROW_NOT_APPLICABLE),
        "n_target_unavailable": count(ROW_TARGET_UNAVAILABLE), "n_pending": count(ROW_PENDING), "n_undefined": count(ROW_UNDEFINED),
        "n_live": sum(x["class"] == CLASS_LIVE for x in scored), "n_late": sum(x["class"] == CLASS_LATE for x in scored),
        "n_retro": n["n_retro"], "n_no_record": n["n_no_record"], "n_undetermined": n["n_undetermined"],
        "n_d1_label_na": n["n_d1_label_na"], "n_calendar_not_available": n["n_calendar_not_available"],
        "rows": rows,
        "cells": post_d1_cells(scored) if len(scored) >= MIN_N_METRIC else [],
        "descriptive": post_d1_descriptive(scored),
        "denominator": denom,
    }
    return block, retro


def build_post_d1_scores(scores: Mapping[str, Any], *, root: Path = ROOT, outcomes_dir: Path = oc.OUTCOMES_DIR,
                         now: Optional[datetime] = None, calendar: Any = None) -> dict[str, Any]:
    """`scores/scores_post_d1.json`. `scores`: aynı anda üretilen scores.json içeriği (karşılaştırıcı paritesi için Faz 2C
    ceiling_hazard_v0 j = 1 satırları oradan okunur; tek tanım)."""
    ctx = load_context(root=root, outcomes_dir=outcomes_dir)
    pctx = load_post_d1_context(root, calendar=calendar)
    haz = next((m for m in scores["models"] if m["model_id"] == fz.BASE_MODEL_ID), None)
    j1 = next((b for b in (haz or {}).get("conditional", {}).get("by_j", []) if b["j"] == POST_D1_J), {"rows": []})
    faz2c_j1 = {r["ticker"]: r for r in j1["rows"]}
    models_out, retro_all = [], []
    for e in pctx.entries:
        block, retro = post_d1_block(ctx, pctx, e, faz2c_j1)
        retro_all += retro
        models_out.append({"model_id": e["model_id"], "kind": fz.model_kind(pctx.params[e["model_id"]]), "stage": e.get("stage"),
                           "card": post_d1_card(e, e["model_id"]), "primary_cell": POST_D1_PRIMARY, "conditional_j1": block})
    state = git_state(root)
    post_files = sorted((Path(root) / "registry" / "post_d1").rglob("*.json"))
    outcome_files = sorted(Path(outcomes_dir).glob("*.csv"))
    return {
        "schema_version": POST_D1_SCHEMA,
        "generated_at_utc": (now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
        .isoformat().replace("+00:00", "Z"),
        "as_of_session": scores.get("as_of_session"),
        "code": {"git_head": state["commit"], "borsai_source_sha256": source_tree_sha256(Path(root) / "borsai")["tree_sha256"],
                 "borsai_dirty": state["borsai_dirty"]},
        "inputs": {"post_d1_records_sha256": _tree_sha(post_files, Path(root)) if post_files else None,
                   "models_index_post_d1_sha256": pctx.index_sha256,
                   "models_index_sha256": sha256_file(Path(root) / "models" / "INDEX.json"),
                   "outcomes_sha256": _tree_sha(outcome_files, Path(root)) if outcome_files else None,
                   "calendar_sha256": getattr(pctx.calendar, "sha256", None),
                   "unannounced_closures": list(getattr(pctx.calendar, "closures", ()))},
        "definitions": {"scale": SCALE_LIVE_POST_D1, "class": POST_D1_CLASS_DEFINITION,
                        "t_open": "D_1'i izleyen ilk resmi seans (ilan dışı kapanışlar düşülmüş) 09:40:00+03:00 (Ek-9)",
                        "targets": "yalnız h ≥ 2: k = 2..10 tavan etiketleri; path_conditional varsa D3/D5/D10; D1 skorlanmaz",
                        "small_n": {"row_table_only_below": MIN_N_METRIC, "insufficient_below": MIN_N_FULL, "min_blocks": MIN_BLOCKS},
                        "comparators_source": "kayıttaki comparators_conditional kopyası; Faz 2C j = 1 satırıyla |Δ| ≤ 1e-12 parite",
                        "diff": "model − karşılaştırılan; negatif = model iyi"},
        "models": models_out,
        "retro_info": retro_all,
    }


def write_post_d1_scores(post: Mapping[str, Any], path: Path = POST_D1_SCORES_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pretty_json_bytes(post))
    return path


def load_post_d1_scores(path: Path = POST_D1_SCORES_PATH) -> Optional[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")) if Path(path).exists() else None


# ============================================================ zaman-dışı eski kohort (Faz 6; SPEC_OOT_PRE_H99_V0 §2, §3, §6)
#
# Üçüncü terazi `OOT_PRE_H99`: donmuş modellerin H99 öncesi kohortta (2020-01-01…2023-09-21), sonuç repoya girmeden push
# edilmiş kayıtlarla skoru. Backtest, canlı, koşullu canlı ve canlı POST_D1 ile hiçbir tabloda birleşmez (`_one_scale`,
# `merge_scales`: farklı `scale` -> ScaleMixError). Çıktı AYRI dosya `scores/scores_oot.json` (şema borsai.scores_oot/1;
# SPEC_DEVIATIONS I1: scores.json'a üst anahtar eklenmez, uygulama scores.json'u gömer). Bayraksız `main()` bu dosyayı yazmaz;
# `python -m borsai.scoring --oot` yalnız onu ve docs/SCORES_OOT.md'yi yazar (S6, I39). `post_d1_hazard_v0` satırları ayrı alt
# tablodadır (MACHINE_SEQUENCED; ayrı ölçek).

SCALE_OOT = reg.OOT_SCALE                                         # "OOT_PRE_H99"
SCALE_OOT_POST_D1 = "OOT_PRE_H99_POST_D1_MACHINE_SEQUENCED"       # KARARLAR D5: ayrı alt tablo, birincil tabloya girmez
OOT_SCHEMA = "borsai.scores_oot/1"
OOT_SCORES_PATH = ROOT / "scores" / "scores_oot.json"
OOT_TITLE = "Zaman-dışı test: H99 öncesi kohort (2020–2023), tahminler sonuç repoya girmeden dondurulmuş (rejim farklı)"
OOT_POST_D1_TITLE = "Zaman-dışı test, D1 sonrası (makine sıralı: makine bütün zip'i gördü, insan görmedi)"
CLASS_OOT_BLIND = "OOT_BLIND"
CLASS_OOT_RETRO = "OOT_RETRO"            # yalnız bilgi listesinde; hiçbir n'e girmez
ROW_NOT_APPLICABLE_REGIME = "NOT_APPLICABLE_REGIME"
ROW_SKIPPED = "SKIPPED"
OOT_SUBSET_OPEN = "oot_pre_h99"          # birincil tablo: açık küme; kasa açılınca `_sealed` ve `_all` ayrı anahtarlar (§6)
# §6 birincil hücreler (değişmez; SPEC_DEVIATIONS I11). KM karşılaştırması yalnız base_km_expanding (last10 donmuş H99
# değeridir, kronolojik değil). pb_ceiling_path_v0: SPEC_CEILING_PATH_V0 §5 birincil hücresi (D5 MAE vs medyan).
OOT_PRIMARY_CELLS: dict[str, dict[str, Any]] = {
    "v1_5_h99": {"output": "return", "horizon_or_k": "D5", "metric": "MAE", "rule_ids": ["base_train_median"]},
    "v1_6_h99": {"output": "return", "horizon_or_k": "D10", "metric": "MAE", "rule_ids": [V15]},
    "v1_5_market20_v0": {"output": "return", "horizon_or_k": "D5", "metric": "MAE", "rule_ids": [V15]},
    "pb_v0": {"output": "return", "horizon_or_k": "D5", "metric": "MAE", "rule_ids": ["base_train_median"]},
    "ceiling_hazard_v0": {"output": "S", "horizon_or_k": None, "metric": "RPS", "rule_ids": ["base_km_expanding"]},
    "pb_ceiling_v0": {"output": "S", "horizon_or_k": None, "metric": "RPS", "rule_ids": ["base_km_expanding"]},
    CEILING_PATH_MAIN: {"output": "return", "horizon_or_k": "D5", "metric": "MAE", "rule_ids": ["base_train_median"]},
    CEILING_PATH_PB: {"output": "return", "horizon_or_k": "D5", "metric": "MAE", "rule_ids": ["base_train_median"]},
}
OOT_POST_D1_PRIMARY = POST_D1_PRIMARY                              # SPEC_POST_D1_V0 §4 (j = 1 koşullu RPS vs ceiling_hazard_v0)
OOT_CLASS_DEFINITION = (
    "SPEC_OOT_PRE_H99_V0 §2 + KARARLAR D6-5: oot_ingest_commit(a) = min(data/outcomes_oot/<a>.csv, data/outcomes_oot/raw/<a>.json "
    "ve registry/oot/d1_rows/<a>.json'u ekleyen commit, tarihi [D_1(a), D_10(a)] olan herhangi bir THB/THM zip'ini ekleyen "
    "commit); OOT_BLIND = model commit'i ve kayıt commit'i onun atası VE modelin push kanıtı var VE push_kanıtı(kayıt) < "
    "push_kanıtı(oot_ingest_commit) VE kohortun HER MEMBER'ının S2 kaydı onun atası; aksi OOT_RETRO (yalnız bilgi). "
    "SPEC_HAZARD_V1 §7.2–§7.3 (model başına): kayıt = (model, üye) için modeli içeren en erken etkin kayıt; kohort kapısı = HER "
    "MEMBER için o modeli içeren kayıt ingest'in atası VE push kanıtı ingest'inkinden önce.")
OOT_SUBSET_SEALED = "oot_pre_h99_sealed"   # kasa (SEALED üyeler); yalnız kasa açılınca (bir SEALED üyenin sonuç dosyası varken)
OOT_SUBSET_ALL = "oot_pre_h99_all"         # açık + kasa; yalnız açık kümede OOT_BLIND olan modeller (SPEC_HAZARD_V1 §7.1-5)
OOT_SEALED_TITLE = ("Zaman-dışı test, kasa (tek seferlik açılış): H99 öncesi kohortun SEALED üyeleri, tahminler sonuç repoya "
                    "girmeden dondurulmuş")
OOT_ALL_TITLE = ("Zaman-dışı test, toplam (açık küme + kasa): yalnız açık kümede de OOT_BLIND olan modeller; açık kümesi OOT_RETRO "
                 "olan model için tanımsız")
OOT_ALL_UNDEFINED = ("açık küme satırları OOT_RETRO (model açık kümenin sonucu repoya girdikten sonra donduruldu): `oot_pre_h99_all` "
                     "bu model için tanımsızdır ve birleştirilmez (SPEC_HAZARD_V1 §7.1-5, SPEC_C_V0 §7.1-5); yalnız "
                     "`oot_pre_h99_sealed`")
OOT_POST_D1_SEALED = "post_d1_sealed"    # M-F: kasa satırları (MACHINE_SEQUENCED); yalnız kasa açılınca
OOT_POST_D1_ALL = "post_d1_all"          # M-F: açık + kasa; yalnız açık kümede OOT_BLIND olan POST_D1 modelleri
OOT_POST_D1_SEALED_TITLE = ("Zaman-dışı test, D1 sonrası, kasa (tek seferlik açılış; makine sıralı: makine bütün zip'i gördü, insan "
                            "görmedi)")
OOT_POST_D1_ALL_TITLE = ("Zaman-dışı test, D1 sonrası, toplam (açık küme + kasa; makine sıralı): yalnız açık kümede de OOT_BLIND olan "
                         "POST_D1 modelleri")
OOT_POST_D1_ALL_UNDEFINED = ("açık küme satırlarında OOT_BLIND yok ya da OOT_RETRO çift var: `post_d1_all` bu model için tanımsızdır ve "
                             "birleştirilmez (SPEC_DEVIATIONS M-F; `all_eligible` kalıbı); yalnız `post_d1_sealed`")
SKIP_NO_RECORD_FOR_MODEL = "NO_RECORD_FOR_MODEL"   # üyenin kaydı var ama bu modeli içeren etkin kaydı yok (model prospektif)
NO_RECORD_OOT_RETRO_BASIS = ("MODEL_FROZEN_AFTER_OUTCOME_NO_RECORD: model bu üyenin sonucu repoya girdikten sonra donduruldu ve "
                             "üyenin bu modeli içeren kaydı yok (canlıdaki `_no_record_retro` kalıbı). Yalnız bilgi: hiçbir n'e girmez.")


def oot_primary_cell_of(model_id: str) -> Optional[dict[str, Any]]:
    """Kasa/eski kohort birincil hücresi: `OOT_PRIMARY_CELLS` (§6, değişmez) + Faz 7 (§5.2) + Faz 7C (§5.2)."""
    return OOT_PRIMARY_CELLS.get(model_id) or FAZ7_OOT_PRIMARY_CELLS.get(model_id) or FAZ7C_OOT_PRIMARY_CELLS.get(model_id)


class OotContext:
    """Eski kohort skorlaması için okunan her şey (kök-göreli; sentetik testler geçici repo verir)."""

    def __init__(self, root: Path = ROOT, *, outcomes_dir: Optional[Path] = None,
                 spk_corporate_action_seen: Optional[Iterable[str]] = None):
        self.root = Path(root)
        self.git = Git(self.root)
        self.proofs = pp.load_proofs(self.root / "registry" / "push_proofs") if (self.root / "registry" / "push_proofs").exists() else []
        self.cohort_path = self.root / "registry" / "oot" / "cohort_pre_h99.csv"
        header, rows = reg.read_cohort(self.cohort_path)
        problems = reg.validate_cohort(header, rows)
        if problems:
            raise ScoringError("kohort dosyası geçmedi: " + "; ".join(problems[:3]))
        self.rows = rows
        self.members = reg.cohort_members(rows)
        self.index = json.loads((self.root / "models" / "INDEX.json").read_text(encoding="utf-8"))
        self.models = {e["model_id"]: e for e in self.index["models"]}
        self.outcomes_dir = Path(outcomes_dir or self.root / "data" / "outcomes_oot")
        self.records_dir = self.root / "registry" / "oot" / "records"
        self.spk_seen = None if spk_corporate_action_seen is None else set(spk_corporate_action_seen)
        self.realized: dict[str, Realized] = {}
        from . import outcomes_oot as oo

        for r in self.members:
            p = oo.outcome_path(r["ticker"], self.outcomes_dir)
            if p.exists():
                self.realized[r["ticker"]] = Realized(r["ticker"], tuple(oo.read_outcome_oot(p)))
        self._record_commit: dict[tuple[str, Optional[str]], Optional[str]] = {}
        self._active: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
        self._cells: dict[str, tuple[dict[str, Any], dict[str, str]]] = {}
        self._gate: dict[tuple[Optional[str], tuple[str, ...]], tuple[bool, list[str]]] = {}
        self._calendar: Any = None

    def active(self, ticker: str) -> list[tuple[Path, dict[str, Any]]]:
        if ticker not in self._active:
            self._active[ticker] = fz.active_oot_records(ticker, self.records_dir)
        return self._active[ticker]

    def record(self, ticker: str) -> Optional[tuple[Path, dict[str, Any]]]:
        """Arzın en erken etkin eski kohort kaydı (`freeze.oot_base_record`, SPEC_DEVIATIONS I12; S2 kaydı); yoksa None."""
        recs = self.active(ticker)
        return min(recs, key=lambda x: (x[1]["recorded_at_utc"], x[0].name)) if recs else None

    def record_for(self, ticker: str, model_id: str) -> Optional[tuple[Path, Mapping[str, Any]]]:
        """(model, üye) birincil kaydı: modeli içeren en erken etkin kayıt (`freeze.oot_primary_of`; SPEC_HAZARD_V1 §7.3)."""
        return fz.oot_primary_of(self.active(ticker), model_id)

    def cells_for(self, ticker: str) -> tuple[dict[str, Any], dict[str, str]]:
        """(model_id -> hücre, model_id -> kayıt dosya adı): her INDEX modelinin kendi birincil kaydından (karşılaştırılanlar da
        kendi birincil kayıtlarından; eski 19 model için hepsi S2 kaydı)."""
        if ticker not in self._cells:
            cells: dict[str, Any] = {}
            names: dict[str, str] = {}
            for m in self.models:
                rec = self.record_for(ticker, m)
                if rec is not None:
                    cells[m] = next(c for c in rec[1]["models"] if c["model_id"] == m)
                    names[m] = rec[0].name
            self._cells[ticker] = (cells, names)
        return self._cells[ticker]

    def gate_model(self, model_id: str) -> str:
        """Kohort kapısının kayıtlarına bakılan model: INDEX modeli kendisi; INDEX dışındaki POST_D1 modeli listeleme öncesi taban
        kaydının modeli (`freeze.BASE_MODEL_ID`, ceiling_hazard_v0; I13, I23)."""
        return model_id if model_id in self.models else fz.BASE_MODEL_ID

    def vault_opened(self) -> bool:
        """Kasa açıldı mı: bir SEALED üyenin sonuç dosyası repoda (tarihlerden/dosyalardan; elle bayrak yok)."""
        return any(r["vault"] == reg.VAULT_SEALED and r["ticker"] in self.realized for r in self.members)

    def calendar(self) -> Any:
        if self._calendar is None:
            from . import outcomes_oot as oo

            self._calendar = oo.load_calendar_oot(bist_dir=self.root / "data" / "raw" / "bist")
        return self._calendar

    def record_commit(self, ticker: str, model_id: Optional[str] = None) -> Optional[str]:
        """Arzın birincil kaydını ekleyen commit: `model_id` verilirse o modeli içeren en erken etkin kayıt, verilmezse en erken
        etkin kayıt (S2); commit'siz ya da kayıtsız -> None."""
        key = (ticker, model_id)
        if key not in self._record_commit:
            rec = self.record(ticker) if model_id is None else self.record_for(ticker, model_id)
            self._record_commit[key] = None if rec is None else self.git.added_commit(_rel(rec[0], self.root))
        return self._record_commit[key]


def oot_ingest_commit(git: Git, ticker: str, session_dates: Sequence[str], *, outcomes_rel: str = "data/outcomes_oot",
                      d1_rows_rel: str = "registry/oot/d1_rows", bist_rel: str = "data/raw/bist",
                      include_d1_rows: bool = True) -> Optional[str]:
    """§2 `oot_ingest_commit(a)` (SPEC_DEVIATIONS I10: ham kopya ve D_1 satırı dosyası da sonuç taşır, dahil). Zip terimi D6'dan
    sonra boş olmalıdır (zip repoya girmez; bekçi); yine de repoda bir zip varsa en erken giriş sayılır."""
    paths = [f"{outcomes_rel}/{ticker}.csv", f"{outcomes_rel}/raw/{ticker}.json"]
    if include_d1_rows:
        paths.append(f"{d1_rows_rel}/{ticker}.json")
    for d in session_dates:
        for kind in oc.KINDS:
            paths.append(f"{bist_rel}/{kind}/{d[:4]}/{kind}{oc.compact(d)}1.zip")
    return git.earliest([c for c in (git.added_commit(p) for p in paths) if c is not None])


def cohort_gate_ok(ctx: OotContext, ingest: Optional[str], model_id: Optional[str] = None) -> tuple[bool, list[str]]:
    """D6-5, model başına (SPEC_HAZARD_V1 §7.3; SPEC_DEVIATIONS L): kohortun HER MEMBER'ı için modeli içeren birincil kayıt
    (`OotContext.record_for`) sonuç commit'inin atası (sonuç commit edilmediyse HEAD) VE kaydın push kanıtı sonucunkinden önce.
    `model_id` None ise INDEX'teki bütün modeller (bir modelde eksik olan üye listelenir); INDEX dışındaki POST_D1 modeli için taban
    kaydın modeli (`gate_model`). Sonuç commit edilmemişse kanıt sırası gösterilemez: kapı kapalı (I13 (c))."""
    models = (ctx.gate_model(model_id),) if model_id is not None else tuple(ctx.models)
    key = (ingest, models)
    if key not in ctx._gate:
        git = ctx.git
        target = ingest or git.head()
        ing_proof = proof_time(git, ingest, ctx.proofs) if ingest else None
        missing = []
        for r in ctx.members:
            for m in models:
                rc = ctx.record_commit(r["ticker"], m)
                rp = proof_time(git, rc, ctx.proofs) if rc is not None else None
                if rc is None or not git.is_ancestor(rc, target) or rp is None or ing_proof is None or not rp < ing_proof:
                    missing.append(r["ticker"])
                    break
        ctx._gate[key] = (not missing, missing)
    ok, missing = ctx._gate[key]
    return ok, list(missing)


def class_oot(ctx: OotContext, model_id: str, ticker: str, ingest: Optional[str], *, model_file: Optional[str] = None,
              extra_ok: bool = True, extra_reason: Optional[str] = None,
              record_commit: Optional[str] = None) -> tuple[str, dict[str, Any]]:
    """§2 `class_oot(m, a)` (saf formül; elle etiket yok). `ingest` None ise sonuç commit edilmemiş: DAG koşulları HEAD'e
    karşı denetlenir (E15), push-kanıtı sırası tanımsızdır -> OOT_RETRO (kanıt önce gelmeli). Kayıt: (m, a) birincil kaydı (modeli
    içeren en erken etkin kayıt; SPEC_HAZARD_V1 §7.3); kapı model başına (`cohort_gate_ok`)."""
    git = ctx.git
    target = ingest or git.head()
    mev = model_evidence(git, model_file or ctx.models[model_id]["file"], ctx.proofs)
    rc = record_commit if record_commit is not None else ctx.record_commit(ticker, ctx.gate_model(model_id))
    frozen_ok = mev["commit"] is not None and mev["push_proof_created_at"] is not None and git.is_ancestor(mev["commit"], target)
    record_ok = rc is not None and git.is_ancestor(rc, target)
    rec_proof = proof_time(git, rc, ctx.proofs)
    ing_proof = proof_time(git, ingest, ctx.proofs) if ingest else None
    proof_ok = rec_proof is not None and ing_proof is not None and rec_proof < ing_proof
    gate, missing = cohort_gate_ok(ctx, ingest, model_id)
    blind = frozen_ok and record_ok and proof_ok and gate and extra_ok
    return (CLASS_OOT_BLIND if blind else CLASS_OOT_RETRO), {
        "model_commit": mev["commit"], "model_push_proof_created_at": mev["push_proof_created_at"],
        "record_commit": rc, "record_push_proof_created_at": rec_proof, "oot_ingest_commit": ingest,
        "oot_ingest_push_proof_created_at": ing_proof, "checked_against": target,
        "outcome_ingest_basis": "COMMITTED" if ingest else "UNCOMMITTED_CHECKED_AGAINST_HEAD",
        "model_frozen_before_ingest": frozen_ok, "record_before_ingest": record_ok, "record_proof_before_ingest_proof": proof_ok,
        "cohort_gate_ok": gate, "cohort_gate_missing_n": len(missing), "extra_ok": extra_ok, "extra_reason": extra_reason}


def _oot_rule_values(cells: Mapping[str, Mapping[str, Any]], rule_id: str, kind: str,
                     record_of: Mapping[str, str]) -> dict[str, Any]:
    """Karşılaştırılanın değeri kendi eski kohort birincil kaydından (kural 1; donmuş H99 değeri; `record_of`: model_id -> o
    modeli içeren en erken etkin kaydın dosya adı; eski 19 model için hepsi S2 kaydı). Rejim yüzünden uygulanamayan kural
    hücresi ve her-zaman-tavan'ın tavan eğrisi (C4) o arzda karşılaştırılmaz."""
    na = lambda c, rid: {"record_id": record_of.get(rid), "values": {"refused": {  # noqa: E731
        "code": ROW_NOT_APPLICABLE_REGIME, "field": None, "reason": (c.get("not_applicable") or {}).get("code")}}}
    if rule_id == ALWAYS_CEILING_CURVE and kind in ("hazard", "km"):
        c = cells.get(ALWAYS_CEILING_CURVE)
        if c is not None and c["status"] == fz.STATUS_NOT_APPLICABLE_REGIME:
            return na(c, ALWAYS_CEILING_CURVE)
        return {"record_id": None, "values": {"S": [1.0] * sv.DAYS, "P_close_ceiling": [1.0] * sv.DAYS},
                "source": "SPEC_DEVIATIONS C4: tavan planlarında her zaman tavan, tanım gereği S_k = 1"}
    if rule_id == P_UP_AS_CEILING:
        v = _oot_rule_values(cells, V15, "linear", record_of)
        if "refused" in v["values"]:
            return v
        return {"record_id": record_of.get(V15), "source": "v1_5_h99 p_up (SPEC_DEVIATIONS C5)",
                "values": {"P_close_ceiling_k": {str(k): v["values"][f"D{k}"]["p_up"] for k in KS}}}
    c = cells.get(rule_id)
    if c is None:
        return {"record_id": None, "values": {"refused": {"code": "NO_ELIGIBLE_RECORD", "field": None, "reason": "kayıtta yok"}}}
    if c["status"] == fz.STATUS_NOT_APPLICABLE_REGIME:
        return na(c, rule_id)
    return {"record_id": record_of.get(rule_id), "values": prediction_of_cell(c)}


def oot_model_rows(ctx: OotContext, model_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(satırlar, OOT_RETRO bilgi satırları), kohortun bütün MEMBER'ları (açık ve kasa; blokları süzen çağıran). Her MEMBER bir
    satırdır: hiç kaydı olmayan SKIPPED (INPUTS_NOT_AVAILABLE, §1); kaydı olup bu modeli içeren kaydı olmayan üye, model sonuçtan
    sonra dondurulduysa OOT_RETRO bilgi satırı (kayıt kimliği yok), değilse SKIPPED (NO_RECORD_FOR_MODEL); rejimle uygulanamayan
    NOT_APPLICABLE_REGIME, model reddi REFUSED; kalanlar hedef durumuyla (SCORED / PENDING / TARGET_UNAVAILABLE). Kayıt ve
    karşılaştırılanlar (m, a) birincil kayıtlarından (SPEC_HAZARD_V1 §7.3)."""
    kind = fz.model_kind(json.loads((ctx.root / "models" / ctx.models[model_id]["file"]).read_text(encoding="utf-8")))
    rows, retro = [], []
    for m in ctx.members:
        t = m["ticker"]
        base = {"ticker": t, "year": m["year"], "vault": m["vault"], "open": reg.is_open(m["vault"]),
                "regime_tags": reg.parse_regime_tags(m["regime_tags"]), "listed_first_trading_date": m["first_trading_date"]}
        if ctx.record(t) is None:
            rows.append({**base, "status": ROW_SKIPPED, "skip_reason": "INPUTS_NOT_AVAILABLE", "class": None, "record_id": None})
            continue
        realized = ctx.realized.get(t)
        d1 = realized.d1 if realized is not None and realized.d1 else m["first_trading_date"]
        ingest = oot_ingest_commit(ctx.git, t, realized.session_dates if realized else [])
        rec = ctx.record_for(t, model_id)
        if rec is None:
            klass, evidence = class_oot(ctx, model_id, t, ingest)
            if not evidence["model_frozen_before_ingest"]:
                retro.append({"model_id": model_id, "ticker": t, "record_id": None,
                              "class_evidence": {**evidence, "basis": NO_RECORD_OOT_RETRO_BASIS}})
            else:
                rows.append({**base, "d1": d1, "status": ROW_SKIPPED, "skip_reason": SKIP_NO_RECORD_FOR_MODEL, "class": None,
                             "record_id": None, "class_evidence": evidence})
            continue
        path, _ = rec
        cells, record_of = ctx.cells_for(t)
        cell = cells[model_id]
        klass, evidence = class_oot(ctx, model_id, t, ingest)
        row = {**base, "d1": d1, "class": klass, "record_id": path.name, "class_evidence": evidence,
               "realized": realized.as_json() if realized else None, "cell_status": cell["status"]}
        if klass == CLASS_OOT_RETRO:
            retro.append({"model_id": model_id, "ticker": t, "record_id": path.name, "class_evidence": evidence})
            continue
        if cell["status"] == fz.STATUS_NOT_APPLICABLE_REGIME:
            rows.append({**row, "status": ROW_NOT_APPLICABLE_REGIME, "not_applicable": cell["not_applicable"],
                         "prediction": None, "rules": {}, "targets": {}})
            continue
        pred = prediction_of_cell(cell)
        rules = {r: _oot_rule_values(cells, r, kind, record_of) for r in comparators(model_id, kind)}
        row.update(prediction=pred, rules=rules, status=_row_status(pred, _needs(kind, realized)),
                   targets=dict(zip(_need_names(kind), _needs(kind, realized))))
        rows.append(row)
    return rows, retro


def oot_obs(model_id: str, kind: str, rows: Sequence[Mapping[str, Any]], output: str, hk: Any, metric: str, rule_id: str,
            scale: str = SCALE_OOT) -> list[PairedObs]:
    """Eşleşik gözlemler: OOT_BLIND, skorlanan, açık küme (kasa açılmadan SEALED satır zaten sonuçsuzdur)."""
    out = []
    for r in rows:
        if r["class"] != CLASS_OOT_BLIND or r["status"] != ROW_SCORED or r["realized"] is None:
            continue
        rv = r["rules"].get(rule_id, {}).get("values", {})
        if "refused" in rv:
            continue
        pair = _losses(kind, output, hk, metric, r["prediction"], rv, r["realized"])
        if pair is not None:
            out.append(PairedObs(scale, r["ticker"], _month(r["d1"]), pair[0], pair[1], r["class"]))
    return out


def _oot_label(model_id: str, output: str, hk: Any, metric: str, rule_id: str) -> str:
    """birincil | ikincil (yalnız Faz 7/7C'nin §5.2 ilan edilmiş ikincilleri) | keşif. Var olan modellerin etiketi değişmedi."""
    pc = oot_primary_cell_of(model_id)
    if pc and (pc["output"], pc["horizon_or_k"], pc["metric"]) == (output, hk, metric) and rule_id in pc["rule_ids"]:
        return LABEL_PRIMARY
    if (output, hk, metric, rule_id) in {_cell_key(c) for c in OOT_SECONDARY_CELLS.get(model_id, ())}:
        return LABEL_SECONDARY
    return LABEL_EXPLORATORY


def oot_cells(model_id: str, kind: str, rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Canlı hücre tanımlarının aynısı (§6 "Diğer hücreler keşif"); etiket OOT birincil hücresinden; yalnız n ≥ 10."""
    out = []
    for output, hk, metric, rule_id in live_cell_specs(model_id, kind):
        obs = oot_obs(model_id, kind, rows, output, hk, metric, rule_id)
        if len(obs) >= MIN_N_METRIC:
            out.append({"output": output, "horizon_or_k": hk, "metric": metric, "rule_id": rule_id, **paired_metric(obs),
                        "label": _oot_label(model_id, output, hk, metric, rule_id)})
    return out


def oot_breakdowns(model_id: str, kind: str, rows: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """§6 ikincil satırlar: yıl kırılımı ve rejim alt kümeleri (keşif), yalnız birincil hücre; n < 10 -> metrik null."""
    pc = oot_primary_cell_of(model_id)
    out: dict[str, list[dict[str, Any]]] = {"by_year": [], "by_regime": []}
    if pc is None:
        return out
    subsets: list[tuple[str, str, Callable[[Mapping[str, Any]], bool]]] = [
        ("by_year", y, (lambda r, y=y: r["year"] == y)) for y in sorted({r["year"] for r in rows})]
    subsets += [("by_regime", "SALE_ON_EXCHANGE", lambda r: bool(r["regime_tags"].get("SALE_ON_EXCHANGE"))),
                ("by_regime", "OFF_EXCHANGE", lambda r: not r["regime_tags"].get("SALE_ON_EXCHANGE"))]
    subsets += [("by_regime", f"ALLOC_REGIME={v}", (lambda r, v=v: r["regime_tags"].get("ALLOC_REGIME") == v))
                for v in reg.REGIME_VALUES["ALLOC_REGIME"]]
    for key, name, keep in subsets:
        sub = [r for r in rows if keep(r)]
        for rule_id in pc["rule_ids"]:
            obs = oot_obs(model_id, kind, sub, pc["output"], pc["horizon_or_k"], pc["metric"], rule_id)
            out[key].append({"subset": name, "rule_id": rule_id, **paired_metric(obs),
                             "label": LABEL_EXPLORATORY if key == "by_regime" else "ikincil"})
    return out


def oot_counters(ctx: OotContext, rows: Sequence[Mapping[str, Any]], retro: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    count = lambda st: sum(r["status"] == st for r in rows)  # noqa: E731
    return {"n_scored": count(ROW_SCORED), "n_refused": count(ROW_REFUSED),
            "n_not_applicable_regime": count(ROW_NOT_APPLICABLE_REGIME), "n_target_unavailable": count(ROW_TARGET_UNAVAILABLE),
            "n_pending": count(ROW_PENDING), "n_skipped": count(ROW_SKIPPED), "n_oot_retro": len(retro)}


def cohort_counters(ctx: OotContext, subset: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    """§6 sayaçları (kohort düzeyi) + D5/D8-1: n_exposed_codex, n_spk_corporate_action_seen (üye listesi verilmediyse null;
    kohort toplamı KARARLAR D8-1'den)."""
    active = reg.active_cohort(ctx.rows).values()
    v = lambda name: sum(r["vault"] == name for r in ctx.members)  # noqa: E731
    return {"n_member": len(ctx.members), "n_out_of_scope": sum(r["status"] == reg.COHORT_OUT_OF_SCOPE for r in active),
            "n_pending_membership": sum(r["status"] == reg.COHORT_PENDING for r in active),
            "n_open": sum(reg.is_open(r["vault"]) for r in ctx.members), "n_sealed": v(reg.VAULT_SEALED),
            "n_exposed_archive": v(reg.VAULT_EXPOSED_ARCHIVE), "n_exposed_codex": v(reg.VAULT_EXPOSED_CODEX),
            "n_in_table": len(subset),
            "n_spk_corporate_action_seen": (None if ctx.spk_seen is None
                                            else sum(r["ticker"] in ctx.spk_seen for r in subset)),
            "n_spk_corporate_action_seen_cohort_total": reg.N_SPK_CORPORATE_ACTION_ROW_SEEN}


def oot_subset_block(ctx: OotContext, model_id: str, rows: Sequence[Mapping[str, Any]], retro: Sequence[Mapping[str, Any]],
                     subset: str = OOT_SUBSET_OPEN) -> dict[str, Any]:
    """Bir alt kümenin model bloğu: `oot_pre_h99` (açık küme: OPEN ∪ EXPOSED_*), `oot_pre_h99_sealed` (SEALED) ya da
    `oot_pre_h99_all` (hepsi). Hücreler ve sayaçlar yalnız o alt kümenin satırlarından; üç anahtar birbirine eklenmez (§6)."""
    kind = fz.model_kind(json.loads((ctx.root / "models" / ctx.models[model_id]["file"]).read_text(encoding="utf-8")))
    keep = _SUBSET_KEEP[subset]
    sub = [r for r in rows if keep(r["vault"])]
    scored = [r for r in sub if r["status"] == ROW_SCORED]
    block = {"model_id": model_id, "kind": kind, "scale": SCALE_OOT, "primary_cell": oot_primary_cell_of(model_id),
             "subset": subset, **oot_counters(ctx, sub, [x for x in retro if keep(ctx_vault(ctx, x))]),
             "rows": list(sub),
             "cells": oot_cells(model_id, kind, scored) if len(scored) >= MIN_N_METRIC else [],
             **oot_breakdowns(model_id, kind, scored)}
    if model_id in FAZ7C_CANDIDATES:
        block["info"] = oot_fall_info(model_id, scored)
    return block


def oot_model_block(ctx: OotContext, model_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows, retro = oot_model_rows(ctx, model_id)
    return oot_subset_block(ctx, model_id, rows, retro, OOT_SUBSET_OPEN), retro


def oot_fall_info(model_id: str, scored: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """SPEC_C_V0 §5.2 bilgi satırı (hüküm yok): kalibrasyon, ort. P(y4) = ort. (1 − p_up D10) ve gözlenen oran (1 − Y_D10),
    OOT_BLIND skorlanan satırlarda; n < 10 ise değer yok. v1 için kalibrasyon satırı üretilmez (SPEC_HAZARD_V1 §5.2: yalnız raporda;
    I46)."""
    use = [r for r in scored if r["class"] == CLASS_OOT_BLIND and r["realized"] is not None
           and "refused" not in r["prediction"] and r["realized"]["Y"].get("D10") is not None
           and r["realized"]["row_status"][9] in (oc.STATUS_OK, oc.STATUS_NA_LIMIT)]
    n = len(use)
    return [{"output": "p_fall", "horizon_or_k": "D10", "metric": "calibration_mean_vs_observed", "role": "bilgi", "n": n,
             "model_value": sum(1 - r["prediction"]["D10"]["p_up"] for r in use) / n if n >= MIN_N_METRIC else None,
             "observed": sum(1 - r["realized"]["Y"]["D10"] for r in use) / n if n >= MIN_N_METRIC else None}]


_SUBSET_KEEP: dict[str, Callable[[str], bool]] = {
    OOT_SUBSET_OPEN: reg.is_open,
    OOT_SUBSET_SEALED: lambda v: v == reg.VAULT_SEALED,
    OOT_SUBSET_ALL: lambda v: True,
}


def all_eligible(ctx: OotContext, rows: Sequence[Mapping[str, Any]], retro: Sequence[Mapping[str, Any]]) -> tuple[bool, int, int]:
    """`oot_pre_h99_all`'a girer mi (SPEC_HAZARD_V1 §7.1-5: "all yalnız açık kümede OOT_BLIND olan modeller"): açık kümede en az bir
    OOT_BLIND satır VE hiç OOT_RETRO çift yok. (girer, açık OOT_BLIND satır, açık OOT_RETRO çift). Tarihlerden; elle liste yok."""
    n_blind = sum(1 for r in rows if r["open"] and r.get("class") == CLASS_OOT_BLIND)
    n_retro = sum(1 for x in retro if reg.is_open(ctx_vault(ctx, x)))
    return n_blind > 0 and n_retro == 0, n_blind, n_retro


def oot_vault_blocks(ctx: OotContext, per_model: Mapping[str, tuple[list[dict[str, Any]], list[dict[str, Any]]]]
                     ) -> dict[str, dict[str, Any]]:
    """Kasa açılınca (`OotContext.vault_opened`) iki ayrı anahtar (§6; SPEC_HAZARD_V1 §7.1-5, SPEC_C_V0 §7.1-5):
    `oot_pre_h99_sealed` — INDEX'in bütün modelleri, yalnız SEALED satırları (kendi `retro_info`'su: kasa çiftleri);
    `oot_pre_h99_all` — yalnız açık kümede OOT_BLIND olan modeller (`all_eligible`), açık + kasa satırları; açık kümesi OOT_RETRO
    olan model (Faz 7/7C) birleştirilmez, `excluded_models`'ta nedeniyle. Kasa açılmadan boş sözlük (kasa kodu hiçbir çıktıda)."""
    if not ctx.vault_opened():
        return {}
    sealed_members = [r for r in ctx.members if r["vault"] == reg.VAULT_SEALED]
    sealed_retro = [x for _, (_, retro) in per_model.items() for x in retro if ctx_vault(ctx, x) == reg.VAULT_SEALED]
    all_models, excluded = [], []
    for m, (rows, retro) in per_model.items():
        ok, n_blind, n_retro = all_eligible(ctx, rows, retro)
        if ok:
            all_models.append(oot_subset_block(ctx, m, rows, retro, OOT_SUBSET_ALL))
        else:
            excluded.append({"model_id": m, "n_open_oot_blind": n_blind, "n_open_oot_retro": n_retro, "reason": OOT_ALL_UNDEFINED})
    return {
        OOT_SUBSET_SEALED: {"title": OOT_SEALED_TITLE, "scale": SCALE_OOT, **cohort_counters(ctx, sealed_members),
                            "models": [oot_subset_block(ctx, m, rows, retro, OOT_SUBSET_SEALED)
                                       for m, (rows, retro) in per_model.items()],
                            "retro_info": sealed_retro},
        OOT_SUBSET_ALL: {"title": OOT_ALL_TITLE, "scale": SCALE_OOT, **cohort_counters(ctx, ctx.members), "models": all_models,
                         "excluded_models": excluded},
    }


def ctx_vault(ctx: OotContext, row: Mapping[str, Any]) -> str:
    return next(m["vault"] for m in ctx.members if m["ticker"] == row["ticker"])


def _oot_post_d1_params(ctx: OotContext, entry: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    """POST_D1 modelinin path_secondary JSON'u (canlı `load_post_d1_context` + `post_d1_block` ile aynı; S6_FIX F3): model
    dosyasının sha256'sı INDEX_POST_D1.json'la denetlenir; `path_secondary.model_id` models/INDEX.json'daysa o dosya, değilse None."""
    data = (ctx.root / "models" / entry["file"]).read_bytes()
    if hashlib_sha256(data) != entry["sha256"]:
        raise ScoringError(f"{entry['model_id']}: dosya sha256 INDEX_POST_D1.json ile aynı değil")
    sec = json.loads(data).get("path_secondary") or {}
    if sec.get("model_id") not in ctx.models:
        return None
    return json.loads((ctx.root / "models" / ctx.models[sec["model_id"]]["file"]).read_text(encoding="utf-8"))


def _oot_d1_label_agrees(ticker: str, rec: Mapping[str, Any], model_id: str, d1: Optional[str], label_state: str,
                         label: Optional[int]) -> None:
    """S6_FIX F1 ek denetimi: kayıttaki hücre NOT_APPLICABLE (D1_NOT_CEILING) ⇔ gerçekleşen D1 etiketi 0; uyuşmazlık
    ScoringError. Denetlenmez: ret hücresi (SPEC_POST_D1_V0 §12 sırası: ana model ve üst limit reddi tavan denetiminden önce;
    ret D1 tavanı hakkında hüküm taşımaz), etiketi beklenen üye ve D_1'i gerçekleşen D_1 olmayan kayıt (başka seans; etiketi 1
    ise sınıf formülünün d1_ok terimiyle OOT_RETRO, I13)."""
    cell = next(c for c in rec["models"] if c["model_id"] == model_id)
    if cell["status"] == fz.STATUS_REFUSED or label_state == "PENDING" or rec["d1"]["session_date"] != d1:
        return
    if (cell["status"] == fz.STATUS_NOT_APPLICABLE) != (label_state == "OK" and label == 0):
        raise ScoringError(f"{ticker}: POST_D1 kaydının hücresi {cell['status']} ama gerçekleşen D1 tavan etiketi "
                           f"{label if label_state == 'OK' else label_state} (kayıt ile resmi sonuç uyuşmuyor)")


def oot_post_d1_block(ctx: OotContext, subset: str = OOT_SUBSET_OPEN, only: Optional[Iterable[str]] = None) -> dict[str, Any]:
    """KARARLAR D5: `post_d1_hazard_v0` satırları ayrı alt tabloda (MACHINE_SEQUENCED). `subset` (M-F): açık küme (varsayılan;
    `post_d1`), kasa (`post_d1_sealed`) ya da hepsi (`post_d1_all`; `only`: dahil edilen modeller) — formül, satır kapısı ve
    hücreler üçünde aynı; yalnız dolaşılan üyeler farklı. Payda ve satır kapısı canlı
    `post_d1_block`'la aynı (SPEC_POST_D1_V0 §7.5; S6_FIX F1): model D_1 sonrası sonuçtan sonra dondurulduysa ya da push kanıtı
    yoksa üye RETRO (yalnız bilgi); D1 etiketi bekleniyor -> n_undetermined, NA -> n_d1_label_na, 0 -> n_not_applicable (satır
    yok); yalnız etiketi 1 olan üye satırdır. Kayıt: en erken etkin kayıt (I12, I23); yoksa n_skipped (+ n_no_record). Sınıf: §2
    formülü, ingest terimi D_1 sonrası sonuç (d1_rows hariç: modelin girdisidir) VE d1_rows sha'sı kayıttakiyle ve D_1 zip pini
    MANIFEST_OOT'la aynı. path_conditional ikincili canlıdaki gibi ceiling_path_v0 JSON'uyla (F3)."""
    from . import outcomes_oot as oo

    path = ctx.root / "models" / fz.INDEX_POST_D1_NAME
    entries = json.loads(path.read_text(encoding="utf-8"))["models"] if path.exists() else []
    manifest = {(r["date"], r["kind"]): r for r in oo.read_manifest_oot(ctx.root / "data" / "raw" / "bist" / "MANIFEST_OOT.csv")}
    post_dir = ctx.root / "registry" / "oot" / "post_d1"
    keep = _SUBSET_KEEP[subset]
    models = []
    for e in entries:
        if only is not None and e["model_id"] not in set(only):
            continue
        path_params = _oot_post_d1_params(ctx, e)
        model_ev = model_evidence(ctx.git, e["file"], ctx.proofs)
        rows, retro = [], []
        n = dict.fromkeys(("n_skipped", "n_not_applicable", "n_d1_label_na", "n_undetermined", "n_retro", "n_no_record"), 0)
        for m in ctx.members:
            if not keep(m["vault"]):
                continue
            t = m["ticker"]
            realized = ctx.realized.get(t)
            d1 = realized.d1 if realized is not None and realized.d1 else None
            ingest = oot_ingest_commit(ctx.git, t, [s for s in realized.session_dates if s > d1] if d1 else [],
                                       include_d1_rows=False)
            if not model_prospective_post_d1(ctx.git, model_ev, ingest):
                n["n_retro"] += 1
                retro.append({"model_id": e["model_id"], "ticker": t, "record_id": None, "d1": d1,
                              "class_evidence": {"model_prospective": False, "model_commit": model_ev["commit"],
                                                 "model_push_proof_created_at": model_ev["push_proof_created_at"],
                                                 "model_params_sha256": e["sha256"], "oot_ingest_commit": ingest,
                                                 "checked_against": ingest or ctx.git.head(),
                                                 "outcome_ingest_basis": "COMMITTED" if ingest else "UNCOMMITTED_CHECKED_AGAINST_HEAD",
                                                 "n_post_d1_records": len(fz.active_records(t, post_dir)),
                                                 "basis": "MODEL_FROZEN_AFTER_D2_OUTCOME: model, D_1 sonrası sonuç repoya girmeden "
                                                          "push kanıtlı olarak dondurulmamış (SPEC_POST_D1_V0 §7.5 kalıbı; I13 "
                                                          "(a)). Yalnız bilgi: hiçbir n'e girmez."}})
                continue
            primary = oo.oot_post_d1_primary(t, post_dir)
            label_state, label = _d1_label(realized)
            if primary is not None:
                _oot_d1_label_agrees(t, primary[1], e["model_id"], d1, label_state, label)
            if label_state == "PENDING":
                n["n_undetermined"] += 1
                continue
            if label_state == "NA":
                n["n_d1_label_na"] += 1
                continue
            if label == 0:
                n["n_not_applicable"] += 1
                continue
            if primary is None:
                n["n_skipped"] += 1
                if ctx.record(t) is not None:              # listeleme öncesi (S2) kaydı var, POST_D1 kaydı yok
                    n["n_no_record"] += 1
                continue
            rpath, rec = primary
            d1p = ctx.root / "registry" / "oot" / "d1_rows" / f"{t}.json"
            d1_ok = d1p.exists() and canonical_sha(d1p) == rec["d1_rows"]["sha256"] and rec["d1"]["session_date"] == d1 and all(
                (manifest.get((d1, k)) or {}).get("sha256") == rec["d1"][k]["sha256"] for k in oc.KINDS)
            rc = ctx.git.added_commit(_rel(rpath, ctx.root))
            klass, ev = class_oot(ctx, e["model_id"], t, ingest, model_file=e["file"], extra_ok=d1_ok, record_commit=rc,
                                  extra_reason=None if d1_ok else "d1_rows sha / D_1 / MANIFEST_OOT pini tutmuyor")
            if klass == CLASS_OOT_RETRO:
                n["n_retro"] += 1
                retro.append({"model_id": e["model_id"], "ticker": t, "record_id": rpath.name, "class_evidence": ev})
                continue
            t_open_at = reg.t_open(d1, ctx.calendar())
            row = post_d1_row(e["model_id"], t, d1, klass, rpath, rec, realized, t_open_at, ev, [], None, path_params, ctx.root)
            row["exposure_class"] = fz.EXPOSURE_MACHINE_SEQUENCED
            rows.append(row)
        cells = []
        for output, hk, metric, rule_id in post_d1_cell_specs():
            obs = [PairedObs(SCALE_OOT_POST_D1, r["ticker"], _month(r["d1"]), *pair, r["class"], POST_D1_J)
                   for r in rows if r["status"] == ROW_SCORED and r["class"] == CLASS_OOT_BLIND
                   for pair in [_cond_losses(r, output, hk, metric, rule_id)] if pair is not None]
            if len(obs) >= MIN_N_METRIC:
                cells.append({"output": output, "horizon_or_k": hk, "metric": metric, "rule_id": rule_id, **paired_metric(obs),
                              "label": _post_d1_label(output, hk, metric, rule_id)})
        count = lambda st: sum(r["status"] == st for r in rows)  # noqa: E731
        models.append({"model_id": e["model_id"], "scale": SCALE_OOT_POST_D1, "exposure_class": fz.EXPOSURE_MACHINE_SEQUENCED,
                       "primary_cell": OOT_POST_D1_PRIMARY, "rows": rows, "cells": cells, "n_rows": len(rows),
                       "n_scored": count(ROW_SCORED), "n_refused": count(ROW_REFUSED), "n_skipped": n["n_skipped"],
                       "n_not_applicable": n["n_not_applicable"] + count(ROW_NOT_APPLICABLE),
                       "n_target_unavailable": count(ROW_TARGET_UNAVAILABLE), "n_pending": count(ROW_PENDING),
                       "n_undefined": count(ROW_UNDEFINED), "n_retro": n["n_retro"], "n_no_record": n["n_no_record"],
                       "n_undetermined": n["n_undetermined"], "n_d1_label_na": n["n_d1_label_na"],
                       "n_oot_retro": len(retro), "retro_info": retro})
    if subset == OOT_SUBSET_OPEN:
        return {"title": OOT_POST_D1_TITLE, "scale": SCALE_OOT_POST_D1, "models": models}
    title = OOT_POST_D1_SEALED_TITLE if subset == OOT_SUBSET_SEALED else OOT_POST_D1_ALL_TITLE
    return {"title": title, "scale": SCALE_OOT_POST_D1, "subset": subset, "models": models}


def oot_post_d1_vault_blocks(ctx: OotContext, open_block: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """M-F: kasa açılınca (`OotContext.vault_opened`) iki ayrı anahtar; açılmadan boş sözlük (kasa kodu hiçbir çıktıda).
    `post_d1_sealed`: kasa üyeleri, `post_d1` ile aynı formül, satır kapısı ve hücreler. `post_d1_all`: açık + kasa, yalnız açık
    blokta en az bir OOT_BLIND satırı olan ve hiç OOT_RETRO çifti olmayan POST_D1 modelleri (tarihlerden; `all_eligible` kalıbı);
    dışarıda kalanlar `excluded_models`'ta nedeniyle. `post_d1` (açık küme) bu fonksiyondan etkilenmez; üçü birbirine eklenmez."""
    if not ctx.vault_opened():
        return {}
    eligible, excluded = [], []
    for m in open_block["models"]:
        n_blind = sum(r["class"] == CLASS_OOT_BLIND for r in m["rows"])
        if n_blind > 0 and m["n_oot_retro"] == 0:
            eligible.append(m["model_id"])
        else:
            excluded.append({"model_id": m["model_id"], "n_open_oot_blind": n_blind, "n_open_oot_retro": m["n_oot_retro"],
                             "reason": OOT_POST_D1_ALL_UNDEFINED})
    total = oot_post_d1_block(ctx, OOT_SUBSET_ALL, only=eligible)
    total["excluded_models"] = excluded
    return {OOT_POST_D1_SEALED: oot_post_d1_block(ctx, OOT_SUBSET_SEALED), OOT_POST_D1_ALL: total}


def canonical_sha(path: Path) -> str:
    from .provenance import canonical_sha256

    return canonical_sha256(json.loads(Path(path).read_text(encoding="utf-8")))


def build_oot_scores(*, root: Path = ROOT, now: Optional[datetime] = None, outcomes_dir: Optional[Path] = None,
                     spk_corporate_action_seen: Optional[Iterable[str]] = None) -> dict[str, Any]:
    """scores/scores_oot.json içeriği (yazmaz). Birincil tablo açık küme (`oot_pre_h99`); kasa açılınca `oot_pre_h99_sealed` ve
    `oot_pre_h99_all` ayrı anahtarlar olarak eklenir (§6; birbirine eklenmez); POST_D1 için de aynı koşulla `post_d1_sealed` ve
    `post_d1_all` (SPEC_DEVIATIONS M-F; `post_d1` açık küme bloğu değişmez)."""
    ctx = OotContext(root, outcomes_dir=outcomes_dir, spk_corporate_action_seen=spk_corporate_action_seen)
    models, retro_all = [], []
    per_model = {e["model_id"]: oot_model_rows(ctx, e["model_id"]) for e in ctx.index["models"]}
    for m, (rows, retro) in per_model.items():
        models.append(oot_subset_block(ctx, m, rows, retro, OOT_SUBSET_OPEN))
        # S6_FIX F2 (B2): yalnız açık küme çiftleri. Kasadaki üyenin sonucu yok; kodu hiçbir çıktıda yazılmaz (sayaç n_sealed).
        retro_all += [x for x in retro if reg.is_open(ctx_vault(ctx, x))]
    state = git_state(ctx.root)
    open_members = [r for r in ctx.members if reg.is_open(r["vault"])]
    post = oot_post_d1_block(ctx)
    return {
        "schema_version": OOT_SCHEMA,
        "generated_at_utc": (now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
        .isoformat().replace("+00:00", "Z"),
        "scale": SCALE_OOT,
        "code": {"git_head": state["commit"], "borsai_dirty": state["borsai_dirty"],
                 "borsai_source_sha256": source_tree_sha256(ctx.root / "borsai")["tree_sha256"]
                 if (ctx.root / "borsai").exists() else None},
        "cohort_sha256": sha256_file(ctx.cohort_path),
        "definitions": {"class": OOT_CLASS_DEFINITION, "primary_cells": OOT_PRIMARY_CELLS,
                        "small_n": {"row_table_only_below": MIN_N_METRIC, "insufficient_below": MIN_N_FULL,
                                    "min_blocks": MIN_BLOCKS},
                        "bootstrap": {"B": BOOTSTRAP_B, "generator": "numpy PCG64", "seed": BOOTSTRAP_SEED,
                                      "block": "gerçekleşen D_1'in takvim ayı", "percentiles": [2.5, 97.5]},
                        "diff": "model − kural; negatif = model iyi", "outcome_basis": "MACHINE_EXTRACTED",
                        "comparators": "H99'da donmuş kural değerleri (kayıtta); last10: FROZEN_H99_LAST10_NOT_CHRONOLOGICAL",
                        "primary_cells_faz7": {**FAZ7_OOT_PRIMARY_CELLS, **FAZ7C_OOT_PRIMARY_CELLS},
                        "secondary_cells_faz7": OOT_SECONDARY_CELLS,
                        "record_rule": "(model, üye) için modeli içeren en erken etkin kayıt; karşılaştırılan kendi birincil "
                                       "kaydından (SPEC_HAZARD_V1 §7.3)",
                        "subsets": {OOT_SUBSET_OPEN: "açık küme (OPEN ∪ EXPOSED_*)", OOT_SUBSET_SEALED: "kasa (SEALED); kasa "
                                    "açılınca", OOT_SUBSET_ALL: "açık + kasa; yalnız açık kümede OOT_BLIND olan modeller"}},
        OOT_SUBSET_OPEN: {"title": OOT_TITLE, "scale": SCALE_OOT, **cohort_counters(ctx, open_members), "models": models},
        "post_d1": post,
        "retro_info": retro_all,
        **oot_vault_blocks(ctx, per_model),
        **oot_post_d1_vault_blocks(ctx, post),
    }


def write_oot_scores(scores: Mapping[str, Any], path: Path = OOT_SCORES_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pretty_json_bytes(scores))
    return path


# ---- S6 (BORSAI_FAZ6_S6_SCORING; SPEC_DEVIATIONS I39–I41): `--oot` komutu, docs/SCORES_OOT.md ve SPK maruziyet kümesi (F5).
# Skor tanımları (kayıp, eşleşme, sınıf, bootstrap, n kuralları) burada değişmez; yalnız okuma, yazma ve gösterim.
OOT_DOC_PATH = ROOT / "docs" / "SCORES_OOT.md"
SPK_EXPOSURE_REL = "docs/faz6/dogrulama/EXPOSURE.md"      # KARARLAR D8-1: `verified/EXPOSURE.md`'nin repodaki kopyası
SPK_EXPOSURE_SECTION = "## 3."
SPK_EXPOSURE_FIRST_COLUMN = "Kohort üyesi"
_EXPOSURE_CODE = re.compile(r"[A-Z0-9]{2,6}")
_TABLE_RULE = re.compile(r":?-{3,}:?")
OOT_V_PASS = "geçiyor (zaman-dışı terazide)"             # SPEC_SCORING §8 dili; "geçiyor" terazinin adıyla birlikte


def spk_corporate_action_members(path: Optional[Path] = None, *, cohort_path: Optional[Path] = None,
                                 expected_n: Optional[int] = None) -> frozenset[str]:
    """KARARLAR D8-1 (F5; SPEC_DEVIATIONS I14, I41): `EXPOSURE.md` §3 tablosunun ilk sütunu ("Kohort üyesi") kodla okunur.
    Denetim: §3 başlığı tek; tablo başlığı ve ayırıcısı beklenen biçimde; her veri satırı başlık genişliğinde, ilk hücresi kod
    biçiminde ve kod tek satırda; küme ⊆ kohortun etkin MEMBER'ları; eleman sayısı = `registry.N_SPK_CORPORATE_ACTION_ROW_SEEN`
    (28). Küme hiçbir yere basılmaz, yazılmaz, loglanmaz: hata iletileri yalnız sayı ve satır numarası taşır."""
    path = Path(path) if path is not None else ROOT / SPK_EXPOSURE_REL
    cohort_path = Path(cohort_path) if cohort_path is not None else reg.COHORT_PATH
    expected = reg.N_SPK_CORPORATE_ACTION_ROW_SEEN if expected_n is None else expected_n
    lines = path.read_text(encoding="utf-8").splitlines()
    starts = [i for i, ln in enumerate(lines) if ln.startswith(SPK_EXPOSURE_SECTION)]
    if len(starts) != 1:
        raise ScoringError(f"EXPOSURE §3: '{SPK_EXPOSURE_SECTION}' başlığı {len(starts)} kez var (1 olmalı)")
    end = next((i for i in range(starts[0] + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    table = [(i + 1, lines[i]) for i in range(starts[0] + 1, end) if lines[i].lstrip().startswith("|")]

    def cells(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    if (len(table) < 3 or cells(table[0][1])[0] != SPK_EXPOSURE_FIRST_COLUMN
            or not all(_TABLE_RULE.fullmatch(c) for c in cells(table[1][1]))):
        raise ScoringError("EXPOSURE §3: tablo başlığı ya da ayırıcı satırı beklenen biçimde değil")
    width = len(cells(table[0][1]))
    codes: list[str] = []
    for no, line in table[2:]:
        row = cells(line)
        if len(row) != width or not _EXPOSURE_CODE.fullmatch(row[0]):
            raise ScoringError(f"EXPOSURE §3: {no}. satır beklenen biçimde değil")
        codes.append(row[0])
    found = frozenset(codes)
    if len(found) != len(codes):
        raise ScoringError(f"EXPOSURE §3: {len(codes) - len(found)} kod birden çok satırda")
    _, rows = reg.read_cohort(cohort_path)
    outside = len(found - {r["ticker"] for r in reg.cohort_members(rows)})
    if outside:
        raise ScoringError(f"EXPOSURE §3: {outside} kod kohortun etkin MEMBER'ı değil")
    if len(found) != expected:
        raise ScoringError(f"EXPOSURE §3: {len(found)} kod var, {expected} olmalı (registry.N_SPK_CORPORATE_ACTION_ROW_SEEN)")
    return found


def _oot_verdict(c: Mapping[str, Any]) -> str:
    """SPEC_SCORING §8 dili (SCORES.md ile aynı): n < 10 metrik yok; 10 ≤ n < 30 "yetersiz örnek"; aralık 0'ın altında
    "geçiyor (zaman-dışı terazide)", üstünde "geçemiyor", 0'ı içeriyorsa "ayırt edilemiyor"."""
    if c.get("diff") is None:
        return f"metrik yok (n < {MIN_N_METRIC})"
    return OOT_V_PASS if c["verdict"] == V_PASS else str(c["verdict"])


def _oot_ci(c: Mapping[str, Any]) -> str:
    return "—" if c.get("ci95") is None else f"[{_s(c['ci95'][0])}, {_s(c['ci95'][1])}]"


def _oot_hk(c: Mapping[str, Any]) -> str:
    return f"{c['output']}{'' if c['horizon_or_k'] is None else ' ' + str(c['horizon_or_k'])} {c['metric']}"


def _oot_wlt(c: Mapping[str, Any]) -> str:
    return "—" if c.get("wins") is None else f"{c['wins']} / {c['losses']} / {c['ties']}"


def _oot_cell_row(c: Mapping[str, Any], lead: Sequence[str]) -> str:
    return ("| " + " | ".join([*lead, _oot_hk(c), f"`{c['rule_id']}`", f"{c['n']} ({c['n_blocks']})", _p(c.get("model_value")),
                                _p(c.get("rule_value")), _s(c.get("diff")), _oot_ci(c), _oot_wlt(c), _oot_verdict(c)]) + " |")


OOT_CELL_HEAD = ("| {lead}Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | "
                 "hüküm |")


def render_oot_doc(scores: Mapping[str, Any]) -> str:
    """docs/SCORES_OOT.md: yalnız `scores/scores_oot.json`'dan (üçüncü terazi). Backtest ya da canlı sayısı, terazi ya da model
    toplamı/ortalaması, üye başına değer tablosu ve üye kodu yoktur (satırlar JSON'da). Sıra listelerden ve sabitlerden (yazılmış
    dosyanın sıralı anahtarlarından bağımsız)."""
    L: list[str] = []
    w = L.append
    b = scores[OOT_SUBSET_OPEN]
    d = scores["definitions"]
    bs = d["bootstrap"]
    code = scores["code"]
    w(f"# {b['title']}")
    w("")
    w("Bu sayfa `python -m borsai.scoring --oot` ile `scores/scores_oot.json`'dan üretilir; elle düzenlenmez. Tanımlar: "
      "`docs/specs_faz6/SPEC_OOT_PRE_H99_V0.md` (§2 sınıf, §3 üçüncü terazi, §6 skorlama), `docs/specs_faz6/KARARLAR.md`, "
      "`docs/specs/SPEC_SCORING.md` §7–§8; yorum kararları `docs/SPEC_DEVIATIONS.md` bölüm I. Kod: `borsai/scoring.py`.")
    w("")
    w(f"- **Üçüncü terazi (`{scores['scale']}`), asla toplanmaz.** Bu sayfadaki her sayı zaman-dışı teraziye aittir. Geçmiş veri "
      "testi (retrospektif) ve canlı sicil (prospektif) `docs/SCORES.md`'dedir; üç terazi arasında toplam ya da ortalama yoktur "
      "(CLAUDE.md kural 3).")
    w("- Kohort: ilk işlem günü 2020-01-01…2023-09-21 olan H99 öncesi arzlar. Tablolar yalnız açık kümedir (`oot_pre_h99`: OPEN ∪ "
      "EXPOSED_*). Kasadaki üyelerin sonucu repoda yoktur; skorlanmaz, kasa açılınca ayrı anahtarla raporlanır.")
    w(f"- Sınıf koddan hesaplanır, elle etiket yok: {d['class']} OOT_RETRO çift hiçbir n'e girmez.")
    w(f"- Sonuç: resmi THB/THM'den makineyle ayıklanmış satırlar (`outcome_basis = {d['outcome_basis']}`). Karşılaştırılanlar: "
      f"{d['comparators']}.")
    w(f"- Fark = {d['diff']}. Aralık: ay-blok bootstrap (blok = {bs['block']}), B = {bs['B']}, {bs['generator']} tohum {bs['seed']}, "
      f"yüzdelik [{bs['percentiles'][0]}, {bs['percentiles'][1]}]; koşul n ≥ {d['small_n']['row_table_only_below']} ve "
      f"≥ {d['small_n']['min_blocks']} blok.")
    w(f"- Dil (SPEC_SCORING §8): n < {MIN_N_METRIC} → metrik yok; {MIN_N_METRIC} ≤ n < {MIN_N_FULL} → \"{V_SMALL}\"; "
      f"n ≥ {MIN_N_FULL} → aralık tamamen 0'ın altındaysa \"{OOT_V_PASS}\", tamamen üstündeyse \"{V_FAIL}\", 0'ı içeriyorsa "
      f"\"{V_NEUTRAL}\". Noktasal fark tek başına hüküm değildir.")
    w(f"- Üretim {scores['generated_at_utc']}; HEAD `{code['git_head']}`; borsai kaynak sha256 "
      f"`{(code['borsai_source_sha256'] or '—')[:12]}`; borsai kirli: {'evet' if code['borsai_dirty'] else 'hayır'}; kohort "
      f"sha256 `{scores['cohort_sha256'][:12]}`.")
    w("- Üye başına satırlar (tahmin, gerçekleşen, kayıplar, sınıf kanıtı) yalnız `scores/scores_oot.json`'dadır; bu sayfada üye "
      "kodu yoktur.")
    w("")
    w("## 1. Kohort sayaçları")
    w("")
    w("| MEMBER | kapsam dışı | üyelik bekleyen | açık küme | kasa (SEALED) | EXPOSED_ARCHIVE | EXPOSED_CODEX | tabloya giren | "
      "SPK kurumsal işlem satırı görülen (tabloda / kohortta) |")
    w("|---|---|---|---|---|---|---|---|---|")
    spk = b["n_spk_corporate_action_seen"]
    w(f"| {b['n_member']} | {b['n_out_of_scope']} | {b['n_pending_membership']} | {b['n_open']} | {b['n_sealed']} | "
      f"{b['n_exposed_archive']} | {b['n_exposed_codex']} | {b['n_in_table']} | {'—' if spk is None else spk} / "
      f"{b['n_spk_corporate_action_seen_cohort_total']} |")
    w("")
    w("## 2. Birincil hücreler (önceden ilan edilmiş, değişmez; SPEC_OOT_PRE_H99_V0 §6)")
    w("")
    w(OOT_CELL_HEAD.format(lead="Model | "))
    w("|---|---|---|---|---|---|---|---|---|---|")
    _render_oot_primary(w, b)
    w("")
    w("## 3. Satır sayaçları (model başına, açık küme)")
    w("")
    w("| Model | tür | skorlanan | ret | rejimle uygulanamaz | hedef oluşmadı | bekleyen | atlanan (kayıt yok) | OOT_RETRO |")
    w("|---|---|---|---|---|---|---|---|---|")
    for m in b["models"]:
        w(f"| `{m['model_id']}` | {m['kind']} | {m['n_scored']} | {m['n_refused']} | {m['n_not_applicable_regime']} | "
          f"{m['n_target_unavailable']} | {m['n_pending']} | {m['n_skipped']} | {m['n_oot_retro']} |")
    w("")
    w("## 4. Birincil hücrenin kırılımları")
    w("")
    for key, title, lab in (("by_year", "4.1 İlk işlem yılı (ikincil)", "ikincil"),
                            ("by_regime", "4.2 Rejim alt kümeleri (keşif)", LABEL_EXPLORATORY)):
        w(f"### {title}")
        w("")
        w("| Model | Alt küme | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | "
          f"hüküm ({lab}) |")
        w("|---|---|---|---|---|---|---|---|---|---|")
        for m in b["models"]:
            for c in m[key]:
                w("| " + " | ".join([f"`{m['model_id']}`", str(c["subset"]), f"`{c['rule_id']}`", f"{c['n']} ({c['n_blocks']})",
                                     _p(c.get("model_value")), _p(c.get("rule_value")), _s(c.get("diff")), _oot_ci(c),
                                     _oot_wlt(c), _oot_verdict(c)]) + " |")
        w("")
    w("## 5. Keşif hücreleri (önceden ilan edilmemiş)")
    w("")
    w("Canlı hücre tanımlarının aynısı (SPEC_OOT_PRE_H99_V0 §6, SPEC_DEVIATIONS I11); yalnız n ≥ "
      f"{MIN_N_METRIC} olanlar. Etiket \"{LABEL_EXPLORATORY}\": önceden ilan edilmediler ve çok sayıdalar (çoklu karşılaştırma); "
      "hüküm sözcüğü yalnız §8 dil kuralının çıktısıdır, bir modelin \"geçtiği\" iddiası değildir.")
    w("")
    for m in b["models"]:
        rest = [c for c in m["cells"] if c["label"] != LABEL_PRIMARY]
        if not rest:
            continue
        w(f"### `{m['model_id']}` ({LABEL_EXPLORATORY})")
        w("")
        w(OOT_CELL_HEAD.format(lead=""))
        w("|---|---|---|---|---|---|---|---|---|")
        for c in rest:
            w(_oot_cell_row(c, []))
        w("")
    _render_oot_post_d1(w, scores["post_d1"])
    w("## 7. OOT_RETRO (yalnız bilgi)")
    w("")
    w(f"`retro_info`: {len(scores['retro_info'])} (model, arz) çifti; hiçbir n'e girmez. Kodlar ve sınıf kanıtı "
      "`scores/scores_oot.json`'dadır.")
    w("")
    if OOT_SUBSET_SEALED in scores:           # yalnız kasa açılınca (SPEC_HAZARD_V1 §7.1-5, SPEC_C_V0 §7.1-5; SPEC_DEVIATIONS L)
        _render_oot_vault(w, scores[OOT_SUBSET_SEALED], scores[OOT_SUBSET_ALL])
    if OOT_POST_D1_SEALED in scores:          # yalnız kasa açılınca (SPEC_DEVIATIONS M-F)
        _render_oot_post_d1_vault(w, scores[OOT_POST_D1_SEALED], scores[OOT_POST_D1_ALL])
    return "\n".join(L)


def _render_oot_primary(w: Callable[[str], None], b: Mapping[str, Any]) -> None:
    """Birincil hücre satırları (blok sırası = INDEX sırası). Açık kümesi OOT_RETRO olan model (Faz 7/7C; model açık kümenin sonucu
    repoya girdikten sonra donduruldu) "metrik yok" değil, OOT_RETRO sayısıyla yazılır."""
    for m in b["models"]:
        pc = m["primary_cell"]
        if pc is None:
            continue
        for rid in pc["rule_ids"]:
            c = next((x for x in m["cells"] if x["label"] == LABEL_PRIMARY and x["rule_id"] == rid), None)
            hk = "" if pc["horizon_or_k"] is None else f" {pc['horizon_or_k']}"
            if c is None and m["n_scored"] == 0 and m["n_oot_retro"] > 0:
                w(f"| `{m['model_id']}` | {pc['output']}{hk} {pc['metric']} | `{rid}` | 0 | — | — | — | — | — | "
                  f"OOT_RETRO ({m['n_oot_retro']} çift; bu alt küme bu model için test değil) |")
            elif c is None:
                w(f"| `{m['model_id']}` | {pc['output']}{hk} {pc['metric']} | `{rid}` | < {MIN_N_METRIC} | — | — | — | — | — | "
                  f"metrik yok (n < {MIN_N_METRIC}) |")
            else:
                w(_oot_cell_row(c, [f"`{m['model_id']}`"]))


def _render_oot_counts(w: Callable[[str], None], b: Mapping[str, Any]) -> None:
    w("| MEMBER | açık küme | kasa (SEALED) | tabloya giren |")
    w("|---|---|---|---|")
    w(f"| {b['n_member']} | {b['n_open']} | {b['n_sealed']} | {b['n_in_table']} |")
    w("")
    w("| Model | tür | skorlanan | ret | rejimle uygulanamaz | hedef oluşmadı | bekleyen | atlanan | OOT_RETRO |")
    w("|---|---|---|---|---|---|---|---|---|")
    for m in b["models"]:
        w(f"| `{m['model_id']}` | {m['kind']} | {m['n_scored']} | {m['n_refused']} | {m['n_not_applicable_regime']} | "
          f"{m['n_target_unavailable']} | {m['n_pending']} | {m['n_skipped']} | {m['n_oot_retro']} |")
    w("")


def _render_oot_vault(w: Callable[[str], None], sealed: Mapping[str, Any], total: Mapping[str, Any]) -> None:
    """§8 kasa (`oot_pre_h99_sealed`) ve §9 toplam (`oot_pre_h99_all`): ayrı anahtarlar, açık küme tablolarıyla (§2–§5) toplanmaz.
    Üye kodu yok; hüküm dili §2 ile aynı ("(zaman-dışı terazide)")."""
    w(f"## 8. {sealed['title']}")
    w("")
    w("- Ayrı anahtar `oot_pre_h99_sealed`: yalnız kasadaki (SEALED) üyeler; açık küme tablolarıyla (§2–§5) ve toplamla (§9) "
      "toplanmaz. Kayıt kuralı: (model, üye) için modeli içeren en erken etkin kayıt (SPEC_HAZARD_V1 §7.3). Birincil hücreler "
      "önceden ilan edilmiştir: §6'daki 8 hücre, `ceiling_hazard_v1_*` için RPS − `base_km_expanding` (SPEC_HAZARD_V1 §5.2), "
      "`fall_d10_v0_*` için D10 Brier − `base_rate` (SPEC_C_V0 §5.2).")
    w("")
    _render_oot_counts(w, sealed)
    w("### 8.1 Birincil hücreler")
    w("")
    w(OOT_CELL_HEAD.format(lead="Model | "))
    w("|---|---|---|---|---|---|---|---|---|---|")
    _render_oot_primary(w, sealed)
    w("")
    w(f"### 8.2 İlan edilmiş ikinciller ({LABEL_SECONDARY}; SPEC_HAZARD_V1 §5.2, SPEC_C_V0 §5.2)")
    w("")
    w(OOT_CELL_HEAD.format(lead="Model | "))
    w("|---|---|---|---|---|---|---|---|---|---|")
    for m in sealed["models"]:
        for c in m["cells"]:
            if c["label"] == LABEL_SECONDARY:
                w(_oot_cell_row(c, [f"`{m['model_id']}`"]))
    w("")
    info = [(m["model_id"], x) for m in sealed["models"] for x in m.get("info", [])]
    if info:
        w("### 8.3 Bilgi (hüküm yok): kalibrasyon, ort. P(D10 kapanışı ≤ arz) ve gözlenen oran")
        w("")
        w("| Model | n | ort. tahmin | gözlenen |")
        w("|---|---|---|---|")
        for mid, x in info:
            w(f"| `{mid}` | {x['n']} | {_p(x['model_value'])} | {_p(x['observed'])} |")
        w("")
    w(f"### 8.4 Keşif hücreleri ({LABEL_EXPLORATORY}; önceden ilan edilmemiş)")
    w("")
    for m in sealed["models"]:
        rest = [c for c in m["cells"] if c["label"] == LABEL_EXPLORATORY]
        if not rest:
            continue
        w(f"`{m['model_id']}`:")
        w("")
        w(OOT_CELL_HEAD.format(lead=""))
        w("|---|---|---|---|---|---|---|---|---|")
        for c in rest:
            w(_oot_cell_row(c, []))
        w("")
    w(f"Kasa OOT_RETRO: {len(sealed['retro_info'])} (model, arz) çifti; hiçbir n'e girmez.")
    w("")
    w(f"## 9. {total['title']}")
    w("")
    w("- Ayrı anahtar `oot_pre_h99_all`: açık küme + kasa, yalnız açık kümede OOT_BLIND olan modeller (SPEC_HAZARD_V1 §7.1-5). "
      "Açık küme satırları OOT_RETRO olan modeller birleştirilmez: "
      + (", ".join(f"`{x['model_id']}`" for x in total["excluded_models"]) or "yok") + ".")
    w("")
    _render_oot_counts(w, total)
    w("### 9.1 Birincil hücreler")
    w("")
    w(OOT_CELL_HEAD.format(lead="Model | "))
    w("|---|---|---|---|---|---|---|---|---|---|")
    _render_oot_primary(w, total)
    w("")


def _render_oot_post_d1(w: Callable[[str], None], post: Mapping[str, Any]) -> None:
    """KARARLAR D5: `post_d1_hazard_v0` ayrı alt tablo, ayrı ölçek (MACHINE_SEQUENCED); §2–§5 ile toplanmaz."""
    w(f"## 6. {post['title']}")
    w("")
    w(f"- **Ayrı ölçek** (`{post['scale']}`): birincil tabloya (§2) girmez, §2–§5'teki hiçbir sayıyla toplanmaz (KARARLAR D5). "
      f"Satırlar `exposure_class = {fz.EXPOSURE_MACHINE_SEQUENCED}`: D_1 satırını makine ayıkladı; makine bütün zip'i gördü, "
      "insan görmedi.")
    w("- Satır: D1'i tavanda kapatan (resmi D1 tavan etiketi 1), D1 sonrası kaydı olan ve sınıfı OOT_BLIND olan her açık üye "
      "(ret dahil). D1'i tavan kapanmayan üye satır değildir, paydada \"D1 tavan değil\" olarak sayılır; D1 etiketi NA ya da "
      "bekleniyorsa da öyle (canlı blokla aynı kapı: SPEC_POST_D1_V0 §7.5; SPEC_DEVIATIONS I42). Açık küme = satır + payda "
      "sayaçları. Hedef D_2…D_10; D1 skorlanmaz. Birincil hücre SPEC_POST_D1_V0 §4: j = 1 koşullu RPS, `ceiling_hazard_v0`'ın "
      "koşullu eğrisi karşısında. §4'ün kalibrasyon satırları bu terazide üretilmez (SPEC_DEVIATIONS I46).")
    w("")
    _render_oot_post_d1_tables(w, post, "açık küme")


def _render_oot_post_d1_vault(w: Callable[[str], None], sealed: Mapping[str, Any], total: Mapping[str, Any]) -> None:
    """M-F: §10 kasa (`post_d1_sealed`) ve §11 toplam (`post_d1_all`); ayrı anahtarlar, §6 ve birbirleriyle toplanmaz. Üye kodu yok."""
    w(f"## 10. {sealed['title']}")
    w("")
    w(f"- Ayrı anahtar `{OOT_POST_D1_SEALED}`, ayrı ölçek (`{sealed['scale']}`): yalnız kasadaki (SEALED) üyeler; §6 (açık küme) "
      f"ve §11 (toplam) ile toplanmaz. Formül, satır kapısı, birincil hücre ve payda sayaçları §6 ile aynı (SPEC_DEVIATIONS M-F); "
      f"satırlar `exposure_class = {fz.EXPOSURE_MACHINE_SEQUENCED}`.")
    w("")
    _render_oot_post_d1_tables(w, sealed, "kasa")
    w(f"## 11. {total['title']}")
    w("")
    w(f"- Ayrı anahtar `{OOT_POST_D1_ALL}`: açık küme + kasa, yalnız açık kümede OOT_BLIND olan POST_D1 modelleri; §6 ve §10 ile "
      "toplanmaz. Açık kümesi OOT_BLIND olmayan modeller birleştirilmez: "
      + (", ".join(f"`{x['model_id']}`" for x in total["excluded_models"]) or "yok") + ".")
    w("")
    _render_oot_post_d1_tables(w, total, "toplam")


def _render_oot_post_d1_tables(w: Callable[[str], None], post: Mapping[str, Any], set_label: str) -> None:
    w("| Model | satır | skorlanan | ret | hedef oluşmadı | bekleyen | S_1 = 0 | D1 tavan değil | D1 etiketi NA | D1 bekleniyor | "
      f"atlanan (S2 kaydı olan) | OOT_RETRO | {set_label} |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for m in post["models"]:
        na_rows = sum(r["status"] == ROW_NOT_APPLICABLE for r in m["rows"])       # satır olan NOT_APPLICABLE ikinci kez sayılmaz
        total = (m["n_rows"] + m["n_not_applicable"] - na_rows + m["n_d1_label_na"] + m["n_undetermined"] + m["n_skipped"]
                 + m["n_retro"])
        w(f"| `{m['model_id']}` | {m['n_rows']} | {m['n_scored']} | {m['n_refused']} | {m['n_target_unavailable']} | "
          f"{m['n_pending']} | {m['n_undefined']} | {m['n_not_applicable']} | {m['n_d1_label_na']} | {m['n_undetermined']} | "
          f"{m['n_skipped']} ({m['n_no_record']}) | {m['n_oot_retro']} | {total} |")
    w("")
    w(OOT_CELL_HEAD.format(lead="Model | "))
    w("|---|---|---|---|---|---|---|---|---|---|")
    for m in post["models"]:
        pc = m["primary_cell"]
        for rid in pc["rule_ids"]:
            c = next((x for x in m["cells"] if x["label"] == LABEL_PRIMARY and x["rule_id"] == rid), None)
            if c is None:
                w(f"| `{m['model_id']}` | {pc['output']} {pc['metric']} | `{rid}` | < {MIN_N_METRIC} | — | — | — | — | — | "
                  f"metrik yok (n < {MIN_N_METRIC}) |")
            else:
                w(_oot_cell_row(c, [f"`{m['model_id']}`"]))
    w("")
    for m in post["models"]:
        rest = [c for c in m["cells"] if c["label"] != LABEL_PRIMARY]
        if not rest:
            continue
        w(f"Öbür hücreler, `{m['model_id']}` ({LABEL_EXPLORATORY}; kod etiketi parantez içinde):")
        w("")
        w(OOT_CELL_HEAD.format(lead=""))
        w("|---|---|---|---|---|---|---|---|---|")
        for c in rest:
            w(_oot_cell_row({**c, "metric": f"{c['metric']} ({c['label']})"}, []))
        w("")


def write_oot_doc(scores: Mapping[str, Any], path: Path = OOT_DOC_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_oot_doc(scores), encoding="utf-8")
    return path


def main_oot(root: Path = ROOT, *, now: Optional[datetime] = None) -> int:
    """T1 (SPEC_DEVIATIONS I39): yalnız `scores/scores_oot.json` ve `docs/SCORES_OOT.md`. Belge yazılmış JSON dosyasından
    üretilir (SCORES.md kalıbı). scores.json, scores_post_d1.json ve SCORES.md'ye dokunulmaz (üç terazi ayrı dosyada)."""
    root = Path(root)
    seen = spk_corporate_action_members(root / SPK_EXPOSURE_REL, cohort_path=root / "registry" / "oot" / "cohort_pre_h99.csv")
    out = write_oot_scores(build_oot_scores(root=root, now=now, spk_corporate_action_seen=seen),
                           root / "scores" / "scores_oot.json")
    print(out)
    print(write_oot_doc(json.loads(out.read_text(encoding="utf-8")), root / "docs" / "SCORES_OOT.md"))
    return 0


# ============================================================ kırılma akşamı: canlı POST_BREAK (Faz 8; SPEC_BREAK_V0 §5, §8, §9)
#
# Ölçek `live_break`: satırlar LIVE ∪ MACHINE_SEQUENCED (v0'da insan kaydı üreticisi yok: satırların hepsi MACHINE_SEQUENCED); RETRO
# yalnız `retro_info` (bilgi). Backtest, canlı listeleme öncesi, koşullu canlı, POST_D1 ve eski kohort ile hiçbir tabloda birleşmez
# (`_one_scale`, `merge_scales`). Çıktı AYRI dosyalar: `scores/scores_break.json` (şema borsai.scores_break/1) ve `docs/SCORES_BREAK.md`
# (SPEC_DEVIATIONS N: §9.6'daki "SCORES.md §8" yerine; I39 kalıbı). Bayraksız `main()` bunlara dokunmaz. `python -m borsai.scoring
# --break` sırayla (i) eksik makine kayıtlarını yazar (`freeze.write_post_break_machine_record`; mükerrer yok, K-LB-3), (ii)
# scores_break.json'ı, (iii) yazılmış JSON'dan belgeyi üretir. Model ve skor tanımı şartnamedekidir; burada yalnız kanıt, payda,
# eşleşik hücre ve gösterim vardır.

SCALE_LIVE_BREAK = "live_break"
BREAK_SCHEMA = "borsai.scores_break/1"
BREAK_SCORES_PATH = ROOT / "scores" / "scores_break.json"
BREAK_DOC_PATH = ROOT / "docs" / "SCORES_BREAK.md"
BREAK_TITLE = "Kırılma akşamı sicili (canlı, makine sıralı; ölçek `live_break`)"
CLASS_MACHINE = pbrk.CLASS_MACHINE_SEQUENCED
BREAK_PROSPECTIVE_CLASSES = (CLASS_LIVE, CLASS_MACHINE)
BREAK_MODEL_ID = "break_floor_v0"
BREAK_ZERO_ID = "break_floor_v0@ZERO"
BREAK_PRODUCT = pbrk.PRODUCT_COMPARATOR
BREAK_BY_TYPE = "base_floor_by_type"
BREAK_HEADS = pbrk.HEADS
BREAK_PARITY_TOL = 1e-12
LABEL_INFO = "bilgi"
ROW_TARGET_LABEL_NA = "TARGET_LABEL_NA"
ROW_TARGET_UNDEFINED_F2 = pbrk.TARGET_UNDEFINED_F2
BREAK_STAGE_RECORD = "RECORD"
# §9.3 / K-LB-8 payda sırası (ipos.csv'de FROZEN her arz için bir satır; ilk tutan durum yazılır). STREAK_TARGET_UNAVAILABLE: seri
# bozulmadan 15 seans sınırı doldu (SPEC_DEVIATIONS N; seri durumlarından biri).
BREAK_DENOMINATOR_ORDER = (STAGE_RETRO, fz.STREAK_PENDING, fz.STREAK_TARGET_UNAVAILABLE, fz.NOT_SCORABLE_STREAK_NA,
                           fz.NOT_APPLICABLE_NO_BREAK, fz.NOT_APPLICABLE_B10, fz.BULLETIN_NOT_PINNED, fz.INPUTS_NOT_AVAILABLE,
                           reg.CALENDAR_NOT_AVAILABLE, BREAK_STAGE_RECORD)
BREAK_STAGE_COUNTERS = {STAGE_RETRO: "n_retro", fz.STREAK_PENDING: "n_streak_pending",
                        fz.STREAK_TARGET_UNAVAILABLE: "n_streak_target_unavailable",
                        fz.NOT_SCORABLE_STREAK_NA: "n_not_scorable_streak_na", fz.NOT_APPLICABLE_NO_BREAK: "n_not_applicable_no_break",
                        fz.NOT_APPLICABLE_B10: "n_not_applicable_b10", fz.BULLETIN_NOT_PINNED: "n_bulletin_not_pinned",
                        fz.INPUTS_NOT_AVAILABLE: "n_inputs_not_available", reg.CALENDAR_NOT_AVAILABLE: "n_calendar_not_available"}
BREAK_ROW_COUNTERS = {ROW_SCORED: "n_scored", ROW_REFUSED: "n_refused", ROW_TARGET_UNAVAILABLE: "n_target_unavailable",
                      ROW_TARGET_LABEL_NA: "n_target_label_na", ROW_PENDING: "n_pending"}
BREAK_PRIMARY = {"output": "p_floor", "horizon_or_k": "F1", "metric": "Brier", "rule_ids": [BREAK_PRODUCT]}
# §5.2 hücreleri (sonuç görülmeden; satır başına eşleşik, karşılaştırıcısı olmayan çift o hücreden düşer): (model tarafı, başlık,
# karşılaştırılan, etiket). Son satır bilgi hücresi: ürün − @ZERO.
BREAK_CELL_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (BREAK_MODEL_ID, "F1", BREAK_PRODUCT, LABEL_PRIMARY),
    (BREAK_MODEL_ID, "F1", BREAK_ZERO_ID, LABEL_SECONDARY),
    (BREAK_MODEL_ID, "F2", BREAK_PRODUCT, LABEL_SECONDARY),
    (BREAK_MODEL_ID, "F2", BREAK_ZERO_ID, LABEL_SECONDARY),
    (BREAK_MODEL_ID, "F1", BREAK_BY_TYPE, LABEL_SECONDARY),
    (BREAK_PRODUCT, "F1", BREAK_ZERO_ID, LABEL_INFO),
)
# §8 öne çıkan kuralı (önceden yazılı): aşama 1 canlı n_scored < 30 (backtest k1), aşama 2 n_scored ≥ 30 (yalnız canlı k2).
BREAK_PROMOTION_STAGE1 = "ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = {n}"
BREAK_PROMOTION_STAGE2 = "canlı sicil (prospektif, n = {n}; makine sıralı {n_machine} / LIVE {n_live})"
BREAK_BACKTEST_PASS = "backtest'te geçiyor (tasarıma maruz)"
BREAK_BACKTEST_NEUTRAL = "basit kuraldan ayırt edilemiyor (backtest)"
BREAK_CALIBRATION_SHIFT = 0.15            # §6 (d): |ort(p_F1) − gözlenen| > 0.15 (n ≥ 30) -> "düzey kayması" notu
BREAK_CLASS_DEFINITION = (
    "SPEC_BREAK_V0 §9.3: MACHINE_SEQUENCED = model_prospective_break VE insan kaydı yok VE inputs_pit_ok_break; LIVE = "
    "model_prospective_break VE push kanıtlı insan kaydı < T_open VE inputs_pit_ok_break (v0'da insan kaydı üreticisi yok); RETRO aksi. "
    "model_prospective_break = commit_frozen(m) atası outcome_ingest_commit_after(D_b, h ≥ b + 1) (tarihi > D_b ilk THB/THM ya da h ≥ b + 1 "
    "dolu satırı ilk yazan commit) VE modelin push kanıtı var. inputs_pit_ok_break = girdi dosyası PIT (shares_offered < D_1) VE kayıt "
    "bekçisi temiz VE D_1..D_b bülten sha'ları MANIFEST'e ve dosyaya eşit.")


def outcome_ingest_commit_after(git: Git, ticker: str, day: str, h_min: int, *, outcomes_rel: str = "data/outcomes",
                                bist_rel: str = "data/raw/bist") -> Optional[str]:
    """K-LB-5 (§9.3 `outcome_ingest_commit_break`): min(data/raw/bist/ altına tarihi > `day` olan ilk THB/THM'yi ekleyen commit,
    data/outcomes/<T>.csv'ye h ≥ `h_min` için dolu satırı (OK ya da NA_LIMIT) ilk yazan commit). İkisi de yoksa None (sonuç commit
    edilmedi: HEAD'e karşı). Kırılma için day = D_b, h_min = b + 1; day = D_1, h_min = 2 iken `outcome_ingest_commit_post_d1` ile
    bit-eşit (o fonksiyon değişmedi; testli)."""
    commits = []
    for rel, c in git.added_under(bist_rel).items():
        m = _BULLETIN.match(Path(rel).name)
        if m is not None and f"{m.group(2)[:4]}-{m.group(2)[4:6]}-{m.group(2)[6:]}" > day:
            commits.append(c)
    rel = f"{outcomes_rel}/{ticker}.csv"
    for c in git.history(rel):
        try:
            rows = list(csv.DictReader(git.show(c, rel).splitlines()))
        except subprocess.CalledProcessError:       # o commit'te dosya silinmiş
            continue
        if any(int(r["h"]) >= h_min and r["status"] in (oc.STATUS_OK, oc.STATUS_NA_LIMIT) for r in rows):
            commits.append(c)
            break
    return git.earliest(commits)


def model_prospective_break(git: Git, model_ev: Mapping[str, Any], outcome_commit: Optional[str]) -> bool:
    """§9.3: is_ancestor(commit_frozen(m), outcome_ingest_commit_after(D_b)) VE push kanıtı(commit_frozen(m)) var. Sonuç commit
    edilmediyse HEAD'e karşı (sonuç commit'i HEAD'in torunu olacaktır; E15 kalıbı)."""
    target = outcome_commit or git.head()
    return (model_ev["commit"] is not None and model_ev["push_proof_created_at"] is not None
            and git.is_ancestor(model_ev["commit"], target))


def record_live_break(human_record_push_created_at: Optional[str], t_open_at: datetime) -> bool:
    """§9.3 `record_live_break`: isteğe bağlı insan kaydının push kanıtı T_open(D_b)'den kesin önce (an karşılaştırması). v0'da insan
    kaydı üreticisi yoktur; skorlama None verir (hep False)."""
    return reg.before_t_open(human_record_push_created_at, t_open_at)


def inputs_pit_problems_break(rec: Mapping[str, Any], d1: str, *, root: Path = ROOT,
                              manifest: Optional[Mapping[tuple[str, str], Mapping[str, str]]] = None) -> list[str]:
    """§9.3 / K-LB-6 inputs_pit_ok_break: (i) kayıttaki girdi dosyası var, sha256'sı aynı, `registry.post_break_inputs_pit_problems`
    boş ve kaydın `inputs_pit_ok`'u doğru; (ii) kayıt bekçisi temiz (`registry.post_break_record_problems`) ve kaydın D_1'i gerçekleşen
    D_1; (iii) D_1..D_b bülten dosyaları var ve sha256'ları kayıttakiyle (bekçide MANIFEST'le) aynı. Boş liste = PIT."""
    root = Path(root)
    manifest = manifest if manifest is not None else {(r["date"], r["kind"]): r
                                                      for r in oc.read_manifest(root / "data" / "raw" / "bist")}
    problems: list[str] = []
    ref = rec.get("inputs_ref") or {}
    ip = root / str(ref.get("file", ""))
    if not ref.get("file") or not ip.is_file():
        problems.append(f"(i) girdi dosyası yok: {ref.get('file')!r}")
    elif sha256_file(ip) != ref.get("sha256"):
        problems.append("(i) girdi dosyası sha256 kayıttakiyle aynı değil")
    else:
        problems += [f"(i) {x}" for x in reg.post_break_inputs_pit_problems(reg.load_inputs(ip)[0], d1, root=root)]
    if ref.get("inputs_pit_ok") is not True:
        problems.append("(i) kaydın inputs_pit_ok'u doğru değil")
    sessions = (rec.get("streak") or {}).get("sessions") or []
    if not sessions or sessions[0].get("date") != d1:
        problems.append(f"(ii) kaydın D_1'i {sessions[0].get('date') if sessions else None!r} gerçekleşen D_1 {d1} değil")
    problems += [f"(ii) {x}" for x in reg.post_break_record_problems(rec, manifest)]
    for s in sessions:
        for kind in oc.KINDS:
            r = s.get(kind) or {}
            fp = root / str(r.get("file", ""))
            if not r.get("file") or not fp.is_file() or sha256_file(fp) != r.get("sha256"):
                problems.append(f"(iii) h={s.get('h')} {kind} dosyası yok ya da sha256 kayıttakiyle aynı değil")
    return problems


def class_break_evidence(git: Git, model_ev: Mapping[str, Any], outcome_commit: Optional[str], pit_ok: bool, d_b: str,
                         t_open_at: datetime) -> tuple[str, dict[str, Any]]:
    """§9.3 sınıfı: saf formül `predict_break.class_break` (N12) + git kanıtları (K-LB-6). v0: record_live hep False."""
    prospective = model_prospective_break(git, model_ev, outcome_commit)
    live = record_live_break(None, t_open_at)
    return pbrk.class_break(prospective, live, pit_ok), {
        "model_commit": model_ev["commit"], "model_push_proof_created_at": model_ev["push_proof_created_at"],
        "outcome_ingest_commit": outcome_commit, "checked_against": outcome_commit or git.head(),
        "outcome_ingest_basis": "COMMITTED" if outcome_commit else "UNCOMMITTED_CHECKED_AGAINST_HEAD",
        "model_prospective": prospective, "record_live": live,
        "record_live_basis": "v0: insan kaydı üreticisi yok (SPEC_BREAK_V0 §9.1; LIVE yolu formülde hazır)",
        "t_open": t_open_at.isoformat(), "inputs_pit_ok": pit_ok, "d_b": d_b,
    }


@dataclass
class BreakContext:
    """Kırılma akşamı skorlaması için okunan her şey (kök-göreli; sentetik testler geçici repo verir)."""

    root: Path
    git: Git
    proofs: list[dict[str, Any]]
    index_sha256: Optional[str]
    entries: list[dict[str, Any]]                                   # models/INDEX_POST_BREAK.json kayıtları
    params: dict[str, dict[str, Any]]
    ipos: list[dict[str, str]]                                      # ipos.csv FROZEN satırları
    records: dict[str, list[tuple[Path, dict[str, Any]]]]           # arz -> registry/post_break makine kayıtları
    manifest: dict[tuple[str, str], dict[str, str]]
    calendar: Any
    cache: dict = field(default_factory=dict)

    @property
    def dirs(self) -> dict[str, Path]:
        return {"models_dir": self.root / "models", "records_dir": self.root / "registry" / "records",
                "inputs_dir": self.root / "registry" / "inputs", "bist_dir": self.root / "data" / "raw" / "bist",
                "outcomes_dir": self.root / "data" / "outcomes", "root": self.root}


def load_break_context(root: Path = ROOT, *, calendar: Any = None) -> BreakContext:
    root = Path(root)
    path = root / "models" / fz.INDEX_POST_BREAK_NAME
    entries, params, sha = [], {}, None
    if path.exists():
        raw = path.read_bytes()
        sha = hashlib_sha256(raw)
        entries = json.loads(raw)["models"]
        for e in entries:
            data = (root / "models" / e["file"]).read_bytes()
            if hashlib_sha256(data) != e["sha256"]:
                raise ScoringError(f"{e['model_id']}: dosya sha256 {fz.INDEX_POST_BREAK_NAME} ile aynı değil")
            params[e["model_id"]] = json.loads(data)
    _, ipos = reg.read_ipos(root / "registry" / "ipos.csv")
    post_dir = root / "registry" / "post_break"
    records = {d.name: fz.list_post_break_records(d.name, post_dir)
               for d in (sorted(post_dir.iterdir()) if post_dir.exists() else []) if d.is_dir()}
    bist = root / "data" / "raw" / "bist"
    return BreakContext(root, Git(root), pp.load_proofs(root / "registry" / "push_proofs"), sha, entries, params,
                        [r for r in ipos if r["status"] == "FROZEN"], records,
                        {(r["date"], r["kind"]): r for r in oc.read_manifest(bist)},
                        calendar if calendar is not None else oc.load_calendar(bist_dir=bist))


def _break_outcome_rows(ctx: BreakContext, ticker: str) -> list[dict[str, str]]:
    p = oc.outcome_path(ticker, ctx.root / "data" / "outcomes")
    return oc.read_outcome(p) if p.exists() else []


def _break_bulletin(ctx: BreakContext, day: str, kind: str) -> Optional["oc.Bulletin"]:
    key = ("bulletin", day, kind)
    if key not in ctx.cache:
        ctx.cache[key] = oc.local_bulletin(day, kind, ctx.root / "data" / "raw" / "bist")
    return ctx.cache[key]


def _floor_label(ctx: BreakContext, ticker: str, row: Mapping[str, str]) -> tuple[str, Optional[int]]:
    """Taban etiketi (§2.1): 1[Decimal(kapanış(D_h)) == Decimal(alt limit(D_h))], kapanış sonuç dosyasından (pinli THB), alt limit o
    seansın pinli THM'sinden; satır PENDING/TARGET_UNAVAILABLE ise o durum; THM satırı yok ya da alt limit boş/≤ 0 ise TARGET_LABEL_NA."""
    if row["status"] not in (oc.STATUS_OK, oc.STATUS_NA_LIMIT):
        return row["status"], None
    day = row["session_date"]
    for kind in oc.KINDS:
        m = ctx.manifest.get((day, kind))
        if m is None or m["sha256"] != row[f"{kind}_sha256"] or _break_bulletin(ctx, day, kind) is None:
            raise ScoringError(f"{ticker} {day}: {kind.upper()} bülteni yerelde yok ya da sonuç dosyasındaki sha256 pinli değerle aynı değil")
    lim = _break_bulletin(ctx, day, "thm").get(oc.equity_code(ticker))
    lo = oc.dec(lim.lower) if lim is not None else None
    if lo is None or lo <= 0:
        return ROW_TARGET_LABEL_NA, None
    return oc.STATUS_OK, int(Decimal(row["close_raw"]) == lo)


def break_labels(ctx: BreakContext, ticker: str, rows: Sequence[Mapping[str, str]], b: int) -> dict[str, dict[str, Any]]:
    """Gerçekleşen F1 (D_{b+1} taban) ve F2 (D_{b+1} ve D_{b+2} taban; b ≤ 8): {status, y, session_date}. F1 = 0 ise F2 = 0
    (backtest etiket kuralıyla aynı: `post_break.load_break_table`); b = 9'da F2 TARGET_UNDEFINED_F2."""
    r1 = rows[b]
    s1, y1 = _floor_label(ctx, ticker, r1)
    out = {"F1": {"status": s1, "y": y1, "session_date": r1["session_date"] or None}}
    if b > pbrk.F2_B_MAX:
        out["F2"] = {"status": ROW_TARGET_UNDEFINED_F2, "y": None, "session_date": None}
        return out
    r2 = rows[b + 1]
    if s1 != oc.STATUS_OK:
        out["F2"] = {"status": s1, "y": None, "session_date": r2["session_date"] or None}
    elif y1 == 0:
        out["F2"] = {"status": oc.STATUS_OK, "y": 0, "session_date": r2["session_date"] or None}
    else:
        s2, y2 = _floor_label(ctx, ticker, r2)
        out["F2"] = {"status": s2, "y": y2, "session_date": r2["session_date"] or None}
    return out


def select_primary_break(ctx: BreakContext, ticker: str, fresh: Mapping[str, Any]) -> Optional[tuple[Path, dict[str, Any]]]:
    """§9.3 birincil makine kaydı: INDEX_POST_BREAK sha'sı ve D_1..D_b bülten sha'ları bugünküyle (bellekte yeniden üretilen kayıtla)
    eşit EN ERKEN kayıt (produced_at_utc, sonra dosya adı). Yoksa None."""
    want = (fresh["models_index"]["sha256"], fz.post_break_record_key(fresh)[1])
    same = [(p, r) for p, r in ctx.records.get(ticker, [])
            if r.get("record_type") == fz.RECORD_MACHINE and (r["models_index"]["sha256"], fz.post_break_record_key(r)[1]) == want]
    return min(same, key=lambda x: (x[1]["produced_at_utc"], x[0].name)) if same else None


def _p_of(cell: Optional[Mapping[str, Any]], head: str) -> Optional[float]:
    return (((cell or {}).get("output") or {}).get(head) or {}).get("p_floor")


def break_record_parity(rec: Mapping[str, Any], fresh: Mapping[str, Any]) -> dict[str, Any]:
    """K-LB-3: birincil kaydın tahmini bugünkü kod ve dosyalarla bellekte yeniden üretilir (`freeze.build_post_break_machine_record`)
    ve kayıtla karşılaştırılır: her modelin durumu ve p_floor'ları, ürün karşılaştırıcısının durumu ve değerleri; |Δ| > 1e-12 ya da
    durum farkı ScoringError (sessiz sapma yok)."""
    a = {c["model_id"]: c for c in rec["models"]}
    b = {c["model_id"]: c for c in fresh["models"]}
    if list(a) != list(b):
        raise ScoringError(f"{rec['ticker']}: makine kaydının modelleri bugünkü dizinle aynı değil (parite)")
    pairs = []
    for mid in a:
        if a[mid]["status"] != b[mid]["status"]:
            raise ScoringError(f"{rec['ticker']} {mid}: kayıt durumu {a[mid]['status']} ≠ yeniden üretim {b[mid]['status']} (parite)")
        pairs += [(f"{mid} {h}", _p_of(a[mid], h), _p_of(b[mid], h)) for h in BREAK_HEADS]
    pa, pb = rec["comparators"][BREAK_PRODUCT], fresh["comparators"][BREAK_PRODUCT]
    if pa["status"] != pb["status"]:
        raise ScoringError(f"{rec['ticker']}: ürün karşılaştırıcısı durumu {pa['status']} ≠ {pb['status']} (parite)")
    pairs += [(f"{BREAK_PRODUCT} {h}", pa[h], pb[h]) for h in BREAK_HEADS]
    worst = 0.0
    for name, x, y in pairs:
        if (x is None) != (y is None):
            raise ScoringError(f"{rec['ticker']} {name}: kayıt ile yeniden üretimden biri boş (parite)")
        if x is not None:
            worst = max(worst, abs(x - y))
    if worst > BREAK_PARITY_TOL:
        raise ScoringError(f"{rec['ticker']}: makine kaydının tahmini yeniden üretimden {worst} farklı (> 1e-12; parite)")
    return {"status": "OK", "max_abs_diff": worst, "basis": "IN_MEMORY_REBUILD"}


def break_comparators(rec: Mapping[str, Any], params: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """K-LB-7: `@ZERO` = kayıttaki donmuş `@ZERO` çıktısı (donmuş JSON'un oranı; parite yeniden üretimle), `base_floor_by_type` =
    donmuş `comparators.by_type_F1` sınıf oranı (yalnız F1), ürün = kayıttaki `PRODUCT_BREAK_FLOOR`."""
    cells = {c["model_id"]: c for c in rec["models"]}
    zc = cells.get(BREAK_ZERO_ID)
    b_floor = rec["break_day"]["b_floor"]
    by_type = (params.get("comparators") or {}).get("by_type_F1") or {}
    prod = rec["comparators"][BREAK_PRODUCT]
    return {BREAK_ZERO_ID: {h: (_p_of(zc, h) if zc is not None and zc["status"] == fz.STATUS_PREDICTED else None) for h in BREAK_HEADS},
            BREAK_BY_TYPE: {"F1": (by_type.get(str(b_floor)) or {}).get("rate") if b_floor is not None else None, "F2": None},
            BREAK_PRODUCT: {"F1": prod["F1"], "F2": prod["F2"], "status": prod["status"], "source_record": prod["source_record"],
                            "source_model_id": prod["source_model_id"]}}


def _warning_codes(warnings: Sequence[Mapping[str, Any]]) -> list[str]:
    out: list[str] = []
    for w in warnings:
        if w.get("code") not in out:
            out.append(w["code"])
    return out


def break_record_summary(path: Path, rec: Mapping[str, Any], params: Mapping[str, Any], d1: str) -> dict[str, Any]:
    """Satır ve RETRO bilgi satırının kayıttan okunan ortak alanları."""
    cells = {c["model_id"]: c for c in rec["models"]}
    cell = cells.get(BREAK_MODEL_ID) or {}
    return {"record_id": path.name, "L": rec["streak"]["L"], "b": rec["streak"]["b"], "break_date": rec["streak"]["break_date"],
            "b_floor": rec["break_day"]["b_floor"], "model_status": cell.get("status"), "refused": cell.get("refused"),
            "p": {h: _p_of(cell, h) for h in BREAK_HEADS}, "comparators": break_comparators(rec, params),
            "regime_tags": pbrk.regime_tags(d1, rec["break_day"]["band_ratio"]["rule_ok"]),
            "warnings": _warning_codes(((cell.get("output") or {}).get("warnings") or [])), "t_open": rec["t_open"]}


def break_row(ticker: str, d1: str, klass: str, evidence: Mapping[str, Any], path: Path, rec: Mapping[str, Any],
              params: Mapping[str, Any], labels: Mapping[str, Mapping[str, Any]], pit: Sequence[str],
              parity: Mapping[str, Any]) -> dict[str, Any]:
    """Bir (break_floor_v0, arz) satırı: tahmin ve karşılaştırıcılar kayıttan (dondurulmuş; yeniden hesap yok, parite ayrı), etiketler
    sonuç dosyası + pinli THM'den; Brier kırpmasız (SPEC_BREAK_V0 §5). Durum F1 hedefinden (F2'ninki `f2_status`)."""
    s = break_record_summary(path, rec, params, d1)
    row: dict[str, Any] = {"ticker": ticker, "d1": d1, "class": klass, **s, "realized": {h: dict(labels[h]) for h in BREAK_HEADS},
                           "losses": {}, "status": None, "f2_status": labels["F2"]["status"], "class_evidence": dict(evidence),
                           "inputs_pit_problems": list(pit), "parity": dict(parity)}
    if s["model_status"] == fz.STATUS_REFUSED:
        row["status"] = ROW_REFUSED
        return row
    st = labels["F1"]["status"]
    row["status"] = {oc.STATUS_OK: ROW_SCORED, oc.STATUS_PENDING: ROW_PENDING, oc.STATUS_TARGET_UNAVAILABLE: ROW_TARGET_UNAVAILABLE,
                     ROW_TARGET_LABEL_NA: ROW_TARGET_LABEL_NA}[st]
    for h in BREAK_HEADS:
        lab = labels[h]
        if lab["status"] != oc.STATUS_OK or row["p"][h] is None:
            continue
        y = lab["y"]
        row["losses"][h] = {"model": loss_brier(row["p"][h], y),
                            **{rid: (None if row["comparators"][rid][h] is None else loss_brier(row["comparators"][rid][h], y))
                               for rid in (BREAK_ZERO_ID, BREAK_BY_TYPE, BREAK_PRODUCT)}}
    return row


def break_obs(rows: Sequence[Mapping[str, Any]], head: str, model_side: str, rule_side: str) -> list[PairedObs]:
    """Eşleşik gözlemler: yalnız LIVE ∪ MACHINE_SEQUENCED satırlar, F1'i skorlanmış (SCORED) ve başlığın etiketi OK; iki tarafın
    değeri de olan satır (karşılaştırıcısı olmayan çift o hücreden düşer). Blok = gerçekleşen D_1'in ayı (SPEC_SCORING §8)."""
    out = []
    for r in rows:
        if r["status"] != ROW_SCORED or r["class"] not in BREAK_PROSPECTIVE_CLASSES:
            continue
        loss = r["losses"].get(head)
        if loss is None:
            continue
        a = loss["model"] if model_side == BREAK_MODEL_ID else loss.get(model_side)
        c = loss.get(rule_side)
        if a is None or c is None:
            continue
        out.append(PairedObs(SCALE_LIVE_BREAK, r["ticker"], _month(r["d1"]), a, c, r["class"]))
    return out


def break_cells(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """§5.2 hücreleri, SPEC_SCORING §8 kurallarıyla: yalnız n ≥ 10 hücre; aralık n ≥ 10 ve ≥ 6 blokta; hüküm ("geçiyor") yalnız
    n ≥ 30 ve aralık tamamen 0'ın altında (`verdict`). Her hücre n_live / n_machine kırılımıyla."""
    out = []
    for model_side, head, rule_side, label in BREAK_CELL_SPECS:
        obs = break_obs(rows, head, model_side, rule_side)
        if len(obs) < MIN_N_METRIC:
            continue
        out.append({"model_id": model_side, "output": "p_floor", "horizon_or_k": head, "metric": "Brier", "rule_id": rule_side,
                    **paired_metric(obs), "n_machine": sum(o.klass == CLASS_MACHINE for o in obs), "label": label})
    return out


def break_descriptive(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Betimsel (aralık ve hüküm yok; n_scored ≥ 10): kalibrasyon ort(p_F1) − gözlenen F1 oranı (bütün satırlar ve b_floor sınıfına
    göre; n ≥ 30 ve |fark| > 0.15 -> "düzey kayması", §6 d) ve rejim kırılımı (FON_KRIZI_2026; n'den düşülmez; n < 30 "yetersiz örnek")."""
    use = [r for r in rows if r["status"] == ROW_SCORED and r["class"] in BREAK_PROSPECTIVE_CLASSES and "F1" in r["losses"]]
    if len(use) < MIN_N_METRIC:
        return []
    import statistics

    def calib(name: str, subset: Sequence[Mapping[str, Any]], **extra: Any) -> dict[str, Any]:
        if not subset:
            return {"output": "p_floor", "horizon_or_k": "F1", "metric": "calibration_mean_vs_observed", "subset": name, "n": 0,
                    "model_value": None, "observed": None, "diff": None, "note": None, **extra}
        mv = statistics.fmean(r["p"]["F1"] for r in subset)
        ob = statistics.fmean(float(r["realized"]["F1"]["y"]) for r in subset)
        note = "düzey kayması" if len(subset) >= MIN_N_FULL and abs(mv - ob) > BREAK_CALIBRATION_SHIFT else None
        return {"output": "p_floor", "horizon_or_k": "F1", "metric": "calibration_mean_vs_observed", "subset": name,
                "n": len(subset), "model_value": mv, "observed": ob, "diff": mv - ob, "note": note, **extra}

    tag = pbrk.REGIME_FON_KRIZI_2026["tag"]
    regime = [r for r in use if tag in r["regime_tags"]]
    return [calib("all", use), calib("b_floor_0", [r for r in use if r["b_floor"] == 0]),
            calib("b_floor_1", [r for r in use if r["b_floor"] == 1]),
            calib(f"regime_{tag}", regime, label=V_SMALL if len(regime) < MIN_N_FULL else None)]


def break_backtest_info(golden_dir: Optional[Path] = None) -> Optional[dict[str, Any]]:
    """§8 aşama 1'in ön eleme ayağı (bilgi; backtest terazisi, toplanmaz): yakın dönem backtest'inde F1 − ürün ve F1 − `@ZERO`
    hücreleri (docs/faz8/backtest/, `report_faz8` ile aynı hesap) ve k1 (iki üst uç < 0). Ledger yoksa None."""
    from . import post_break as pbk
    from . import report_faz8 as r8

    d = Path(golden_dir) if golden_dir is not None else pbk.GOLDEN_DIR
    if not pbk.golden_available(d):
        return None
    rows = r8.load_faz8(d)[0]
    near = pbk.compute_cells(rows)["near"]
    k1 = r8.k1(near)["holds"]

    def cell(key: str) -> Optional[dict[str, Any]]:
        c = near.get(key)
        return None if c is None else {"diff": c["mean"], "ci95": c["ci95"], "n": c["n"], "n_months": c["n_months"]}

    return {"scale": pbk.SCALE, "subset": f"first_trading_date >= {pbk.NEAR_ERA_START}", "F1_product": cell("F1_product"),
            "F1_zero": cell("F1_zero"), "k1": k1, "label": BREAK_BACKTEST_PASS if k1 else BREAK_BACKTEST_NEUTRAL}


def break_promotion(n_scored: int, n_machine: int, n_live: int, cells: Sequence[Mapping[str, Any]],
                    backtest: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    """§8 öne çıkan kuralı (önceden yazılı). Aşama 1 (canlı n_scored < 30): k1 (backtest) varsa öne çıkar, etiket "ön eleme (…);
    canlı n = k"; yoksa "basit kuraldan ayırt edilemiyor (backtest)". Aşama 2 (n_scored ≥ 30): yalnız canlı hücreler (k2: birincil ve
    `@ZERO` aralıklarının üst uçları < 0) — "geçiyor" ancak ikisi de n ≥ 30 ve aralık 0'ın altında; backtest yalnız bilgi."""
    by = {(c["model_id"], c["horizon_or_k"], c["rule_id"]): c for c in cells}
    prim, zero = by.get((BREAK_MODEL_ID, "F1", BREAK_PRODUCT)), by.get((BREAK_MODEL_ID, "F1", BREAK_ZERO_ID))
    if n_scored < MIN_N_FULL:
        k1 = bool(backtest and backtest.get("k1"))
        return {"stage": 1, "basis": "backtest_k1 (yakın dönem; tasarıma maruz)", "promoted": k1, "live_verdict": None,
                "label": BREAK_PROMOTION_STAGE1.format(n=n_scored) if k1 else BREAK_BACKTEST_NEUTRAL}
    verdicts = [None if c is None else c.get("verdict") for c in (prim, zero)]
    k2 = all(v == V_PASS for v in verdicts)
    live_verdict = V_PASS if k2 else (V_FAIL if V_FAIL in verdicts else V_NEUTRAL)
    return {"stage": 2, "basis": "live_k2", "promoted": k2, "live_verdict": live_verdict,
            "label": BREAK_PROMOTION_STAGE2.format(n=n_scored, n_machine=n_machine, n_live=n_live) if k2 else live_verdict}


def break_card(ctx: BreakContext, entry: Mapping[str, Any], model_ev: Mapping[str, Any], block: Mapping[str, Any],
               backtest: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    params = ctx.params[BREAK_MODEL_ID]
    nv, nr = _n_variants_same_data(entry["data_version_sha256"], BREAK_MODEL_ID)
    return {"training_n_F1": entry["training_n"], "training_n_F2": entry.get("training_n_F2"),
            "training_last_label_date": entry["training_cutoff_date"],
            "training_last_label_date_meaning": "eğitim etiketlerinin son seansı (JSON alanı training.cutoff_date; kesim değil, "
                                                "SPEC_DEVIATIONS N22)",
            "spec_training_cutoff": OUTCOME_CUTOFF, "params_sha256_8": entry["sha256"][:8], "frozen_at": entry["frozen_at"],
            "model_commit": model_ev["commit"], "model_push_proof_created_at": model_ev["push_proof_created_at"],
            "n_variants_same_data": nv, "n_runs_same_data": nr,
            "comparators_frozen": {"zero": dict(params["comparators"]["zero"]),
                                   "by_type_F1": {k: v["rate"] for k, v in sorted(params["comparators"]["by_type_F1"].items())}},
            "regime_warning": dict(params.get("regime_warning") or {}),
            "backtest_info": None if backtest is None else dict(backtest),
            "promotion": break_promotion(block["n_scored"], block["n_machine"], block["n_live"], block["cells"], backtest)}


def _break_ref_day(rows: Sequence[Mapping[str, str]], st: Mapping[str, Any]) -> tuple[Optional[str], int]:
    """Sınıfın sonuç günü (§9.3): b biliniyorsa (1..10) D_b ve h ≥ b + 1; L = 10 ise D_10 ve h ≥ 11 (B10 ile aynı hesap); seri
    belirsizse (bekliyor, NA, 15 seans) None — HEAD'e karşı (SPEC_DEVIATIONS N)."""
    if st["b"] is not None:
        return rows[st["b"] - 1]["session_date"], st["b"] + 1
    if st["state"] == fz.NOT_APPLICABLE_NO_BREAK:
        return rows[oc.N_SESSIONS - 1]["session_date"], oc.N_SESSIONS + 1
    return None, 0


def break_block(ctx: BreakContext) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """(live_break bloğu, RETRO bilgi satırları). Payda: ipos.csv'de FROZEN her arz için bir satır, `BREAK_DENOMINATOR_ORDER`
    sırasıyla. Kırılma akşamı olan her arzda kayıt bugünkü kodla bellekte yeniden üretilir: "kayıt yazılmaz" nedenleri (bülten, girdi,
    takvim) ondan, parite birincil kayıtla (K-LB-3)."""
    entry = next(e for e in ctx.entries if e["model_id"] == BREAK_MODEL_ID)
    params = ctx.params[BREAK_MODEL_ID]
    model_ev = model_evidence(ctx.git, entry["file"], ctx.proofs)
    rows, denom, retro = [], [], []
    n = dict.fromkeys(BREAK_STAGE_COUNTERS.values(), 0)
    for ipo in ctx.ipos:
        t = ipo["ticker"]
        orows = _break_outcome_rows(ctx, t)
        st = fz.break_streak(orows)
        d1 = orows[0]["session_date"] if orows and orows[0]["status"] in (oc.STATUS_OK, oc.STATUS_NA_LIMIT) else None
        day, h_min = _break_ref_day(orows, st)
        ingest = outcome_ingest_commit_after(ctx.git, t, day, h_min) if day else None
        d_b = orows[st["b"] - 1]["session_date"] if st["b"] is not None else None
        d_row: dict[str, Any] = {"ticker": t, "d1": d1, "listed_first_trading_date": ipo["first_trading_date"],
                                 "streak_state": st["state"], "L": st["L"], "b": st["b"], "break_date": d_b, "stage_status": None,
                                 "class": None, "record_id": None}
        denom.append(d_row)
        fresh, unavailable, primary, parity = None, None, None, None
        if st["state"] == fz.BREAK_STATE:
            try:
                fresh = fz.build_post_break_machine_record(t, calendar=ctx.calendar, proofs=ctx.proofs, **ctx.dirs)
            except fz.BreakNotAvailable as exc:
                unavailable = exc.code
            if fresh is not None:
                primary = select_primary_break(ctx, t, fresh)
                if primary is None:
                    raise ScoringError(f"{t}: kırılma akşamı var ama birincil makine kaydı yok; önce `python -m borsai.scoring --break` "
                                       "kayıt adımı (registry/post_break/)")
                parity = break_record_parity(primary[1], fresh)
                d_row["record_id"] = primary[0].name
        if not model_prospective_break(ctx.git, model_ev, ingest):
            n["n_retro"] += 1
            d_row.update(stage_status=STAGE_RETRO, **{"class": pbrk.CLASS_RETRO})
            info = {"model_id": BREAK_MODEL_ID, "ticker": t, "d1": d1, "streak_state": st["state"], "L": st["L"], "b": st["b"],
                    "break_date": d_b, "record_id": None}
            if primary is not None:
                info.update(break_record_summary(primary[0], primary[1], params, d1), parity=parity)
            info["class_evidence"] = {
                "model_prospective": False, "model_commit": model_ev["commit"],
                "model_push_proof_created_at": model_ev["push_proof_created_at"], "model_frozen_at": entry["frozen_at"],
                "model_params_sha256": entry["sha256"], "outcome_ingest_commit": ingest, "checked_against": ingest or ctx.git.head(),
                "outcome_ingest_basis": "COMMITTED" if ingest else "UNCOMMITTED_CHECKED_AGAINST_HEAD", "outcome_day": day,
                "basis": "MODEL_FROZEN_AFTER_BREAK_OUTCOME: model, D_b'den sonraki ilk sonuç verisi (tarihi > D_b bülten ya da h ≥ b + 1 "
                         "satırı) repoya girdikten sonra donduruldu ya da push kanıtı yok (SPEC_BREAK_V0 §9.3). Yalnız bilgi: hiçbir "
                         "n'e girmez."}
            retro.append(info)
            continue
        if st["state"] != fz.BREAK_STATE or unavailable is not None:
            code = st["state"] if st["state"] != fz.BREAK_STATE else unavailable
            n[BREAK_STAGE_COUNTERS[code]] += 1
            d_row["stage_status"] = code
            continue
        path, rec = primary
        pit = inputs_pit_problems_break(rec, d1, root=ctx.root, manifest=ctx.manifest)
        cls, ev = class_break_evidence(ctx.git, model_ev, ingest, not pit, d_b, reg.parse_instant(rec["t_open"]))
        d_row["class"] = cls
        if cls == pbrk.CLASS_RETRO:
            n["n_retro"] += 1
            d_row["stage_status"] = STAGE_RETRO
            retro.append({"model_id": BREAK_MODEL_ID, "ticker": t, "d1": d1, "streak_state": st["state"],
                          **break_record_summary(path, rec, params, d1), "parity": parity, "class_evidence": ev,
                          "inputs_pit_problems": pit})
            continue
        d_row["stage_status"] = BREAK_STAGE_RECORD
        rows.append(break_row(t, d1, cls, ev, path, rec, params, break_labels(ctx, t, orows, st["b"]), pit, parity))
    count = {name: sum(r["status"] == st_ for r in rows) for st_, name in BREAK_ROW_COUNTERS.items()}
    scored = [r for r in rows if r["status"] == ROW_SCORED]
    cells = break_cells(scored) if len(scored) >= MIN_N_METRIC else []
    block = {
        "title": BREAK_TITLE, "scale": SCALE_LIVE_BREAK,
        "definition": "SPEC_BREAK_V0 §2, §5, §9: kırılma akşamı (b = L + 1 ∈ 1..9) donmuş modelin p_floor'u; F1 = D_{b+1} taban kapanışı, "
                      "F2 = D_{b+1} ve D_{b+2} taban (b ≤ 8); Brier kırpmasız, model − karşılaştırılan; hiçbir ölçekle birleşmez",
        "class_definition": BREAK_CLASS_DEFINITION, "primary_cell": BREAK_PRIMARY,
        "comparators": [BREAK_PRODUCT, BREAK_ZERO_ID, BREAK_BY_TYPE],
        **count, **n, "n_rows": len(rows),
        "n_live": sum(r["class"] == CLASS_LIVE for r in scored), "n_machine": sum(r["class"] == CLASS_MACHINE for r in scored),
        "rows": rows, "cells": cells, "descriptive": break_descriptive(scored), "denominator": denom,
    }
    return block, retro


def break_denominator_problems(block: Mapping[str, Any]) -> list[str]:
    """§13-12 payda özdeşliği: payda satırı sayısı = Σ aşama sayaçları + satır sayısı; satır sayısı = Σ satır durumu sayaçları;
    n_scored = n_live + n_machine; her payda satırının durumu sayacıyla tutarlı."""
    out = []
    stage = sum(block[c] for c in BREAK_STAGE_COUNTERS.values())
    if len(block["denominator"]) != stage + block["n_rows"]:
        out.append(f"payda {len(block['denominator'])} ≠ aşama sayaçları {stage} + satır {block['n_rows']}")
    if block["n_rows"] != len(block["rows"]) or len(block["rows"]) != sum(block[c] for c in BREAK_ROW_COUNTERS.values()):
        out.append("satır sayısı satır durumu sayaçlarının toplamı değil")
    if block["n_scored"] != block["n_live"] + block["n_machine"]:
        out.append("n_scored ≠ n_live + n_machine")
    by = {s: sum(d["stage_status"] == s for d in block["denominator"]) for s in BREAK_DENOMINATOR_ORDER}
    for s, c in BREAK_STAGE_COUNTERS.items():
        if by[s] != block[c]:
            out.append(f"{s}: payda {by[s]} ≠ {c} {block[c]}")
    if by[BREAK_STAGE_RECORD] != len(block["rows"]):
        out.append("RECORD payda satırı sayısı satır sayısı değil")
    return out


def build_break_scores(*, root: Path = ROOT, now: Optional[datetime] = None, calendar: Any = None,
                       backtest: Optional[Mapping[str, Any]] = None, backtest_dir: Optional[Path] = None) -> dict[str, Any]:
    """`scores/scores_break.json` içeriği (yazmaz). `backtest`: §8 aşama 1 bilgi satırı (verilmezse docs/faz8/backtest/'ten)."""
    root = Path(root)
    ctx = load_break_context(root, calendar=calendar)
    if not ctx.entries:
        raise ScoringError(f"models/{fz.INDEX_POST_BREAK_NAME} yok: POST_BREAK modeli dondurulmamış")
    backtest = break_backtest_info(backtest_dir) if backtest is None else backtest
    entry = next(e for e in ctx.entries if e["model_id"] == BREAK_MODEL_ID)
    model_ev = model_evidence(ctx.git, entry["file"], ctx.proofs)
    block, retro = break_block(ctx)
    problems = break_denominator_problems(block)
    if problems:
        raise ScoringError("payda özdeşliği: " + "; ".join(problems))
    state = git_state(root)
    post_files = sorted((root / "registry" / "post_break").rglob("*.json"))
    outcome_files = sorted((root / "data" / "outcomes").glob("*.csv"))
    manifest_path = root / "data" / "raw" / "bist" / oc.MANIFEST_NAME
    return {
        "schema_version": BREAK_SCHEMA,
        "generated_at_utc": (now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
        .isoformat().replace("+00:00", "Z"),
        "scale": SCALE_LIVE_BREAK,
        "code": {"git_head": state["commit"], "borsai_source_sha256": source_tree_sha256(root / "borsai")["tree_sha256"]
                 if (root / "borsai").exists() else None, "borsai_dirty": state["borsai_dirty"]},
        "inputs": {"post_break_records_sha256": _tree_sha(post_files, root) if post_files else None,
                   "models_index_post_break_sha256": ctx.index_sha256,
                   "outcomes_sha256": _tree_sha(outcome_files, root) if outcome_files else None,
                   "manifest_sha256": sha256_file(manifest_path) if manifest_path.exists() else None,
                   "calendar_sha256": getattr(ctx.calendar, "sha256", None),
                   "unannounced_closures": list(getattr(ctx.calendar, "closures", ()))},
        "definitions": {"scale": SCALE_LIVE_BREAK, "class": BREAK_CLASS_DEFINITION,
                        "t_open": "D_b'yi izleyen ilk resmi seans (ilan dışı kapanışlar düşülmüş) 09:40:00+03:00 (bilgi; v0'da insan kaydı yok)",
                        "targets": {"F1": pbrk.TARGET_DEFINITION["F1"], "F2": pbrk.TARGET_DEFINITION["F2"],
                                    "label": "Decimal(kapanış) == Decimal(alt limit), resmi THB kapanışı ve pinli THM alt limiti; F1 = 0 ise "
                                             "F2 = 0; b = 9'da F2 tanımsız"},
                        "comparators": {BREAK_PRODUCT: "arzın birincil listeleme öncesi kaydındaki ceiling_path_v0 (yoksa @INF) çıktısı ve "
                                                       "donmuş hücreleriyle (§5.1); kayıtta yoksa NOT_AVAILABLE",
                                        BREAK_ZERO_ID: "donmuş @ZERO JSON'unun eğitim oranı (kayıttaki çıktısı)",
                                        BREAK_BY_TYPE: "donmuş comparators.by_type_F1 sınıf oranı (yalnız F1)"},
                        "cells": [{"model_id": m, "horizon_or_k": h, "rule_id": r, "label": lab} for m, h, r, lab in BREAK_CELL_SPECS],
                        "primary_record": "INDEX_POST_BREAK sha'sı ve D_1..D_b bülten sha'ları bugünküyle eşit en erken makine kaydı; "
                                          "tahmin bellekte yeniden üretilir, |Δ| > 1e-12 ScoringError (K-LB-3)",
                        "denominator_order": list(BREAK_DENOMINATOR_ORDER),
                        "small_n": {"row_table_only_below": MIN_N_METRIC, "insufficient_below": MIN_N_FULL, "min_blocks": MIN_BLOCKS},
                        "bootstrap_live": {"B": BOOTSTRAP_B, "generator": "numpy PCG64", "seed": BOOTSTRAP_SEED,
                                           "block": "gerçekleşen D_1'in takvim ayı", "percentiles": [2.5, 97.5]},
                        "diff": "model − karşılaştırılan; negatif = model iyi", "brier_clip": None},
        "models": [{"model_id": BREAK_MODEL_ID, "kind": fz.model_kind(ctx.params[BREAK_MODEL_ID]), "stage": entry.get("stage"),
                    "rule_rows": [BREAK_ZERO_ID], "card": break_card(ctx, entry, model_ev, block, backtest),
                    "primary_cell": BREAK_PRIMARY, "live_break": block}],
        "retro_info": retro,
    }


def write_break_scores(scores: Mapping[str, Any], path: Path = BREAK_SCORES_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pretty_json_bytes(scores))
    return path


def ensure_post_break_records(root: Path = ROOT, *, now: Optional[datetime] = None, calendar: Any = None) -> dict[str, Any]:
    """`--break` adım (i): ipos.csv'de FROZEN her arz için eksik makine kaydını yazar (kırılma akşamı b ∈ 1..9 olan, bültenleri pinli,
    girdisi ve takvimi olan arzlar; sınıftan bağımsız: RETRO arzın kaydı da yazılır, bilgi satırı ondan okunur). Mükerrer anahtarlı
    kayıt varsa yazmaz (K-LB-3). Dönen: {written, existing, not_written: {arz: kod}}."""
    root = Path(root)
    _, ipos = reg.read_ipos(root / "registry" / "ipos.csv")
    calendar = calendar if calendar is not None else oc.load_calendar(bist_dir=root / "data" / "raw" / "bist")
    proofs = pp.load_proofs(root / "registry" / "push_proofs")
    dirs = {"models_dir": root / "models", "records_dir": root / "registry" / "records", "inputs_dir": root / "registry" / "inputs",
            "bist_dir": root / "data" / "raw" / "bist", "outcomes_dir": root / "data" / "outcomes", "root": root}
    written, existing, not_written = [], [], {}
    for r in ipos:
        if r["status"] != "FROZEN":
            continue
        t = r["ticker"]
        try:
            path = fz.write_post_break_machine_record(t, now=now, post_dir=root / "registry" / "post_break", calendar=calendar,
                                                      proofs=proofs, **dirs)
            written.append(_rel(path, root))
        except fz.DuplicateRecord:
            existing.append(t)
        except fz.BreakNotAvailable as exc:
            not_written[t] = exc.code
    return {"written": written, "existing": existing, "not_written": not_written}


def main_break(root: Path = ROOT, *, now: Optional[datetime] = None) -> int:
    """K-LB-1: `python -m borsai.scoring --break` — (i) eksik makine kayıtları (registry/post_break/), (ii) scores/scores_break.json,
    (iii) yazılmış JSON'dan docs/SCORES_BREAK.md. scores.json, scores_post_d1.json, scores_oot.json, SCORES.md ve SCORES_OOT.md'ye
    dokunulmaz."""
    root = Path(root)
    now = now or datetime.now(timezone.utc)
    calendar = oc.load_calendar(bist_dir=root / "data" / "raw" / "bist")
    print(json.dumps(ensure_post_break_records(root, now=now, calendar=calendar), ensure_ascii=False, indent=2))
    out = write_break_scores(build_break_scores(root=root, now=now, calendar=calendar), root / "scores" / "scores_break.json")
    print(out)
    print(write_break_doc(json.loads(out.read_text(encoding="utf-8")), root / "docs" / "SCORES_BREAK.md"))
    return 0


# ---- docs/SCORES_BREAK.md (yalnız scores_break.json'dan; sıra sabitlerden ve listelerden)

BREAK_STAGE_TEXT = {STAGE_RETRO: "RETRO (model bu arz için prospektif değil; yalnız bilgi)",
                    fz.STREAK_PENDING: "seri sürüyor / kırılma günü bekleniyor", fz.STREAK_TARGET_UNAVAILABLE: "seri bozulmadan 15 seans "
                    "sınırı doldu", fz.NOT_SCORABLE_STREAK_NA: "seride üst limit NA (L belirsiz)",
                    fz.NOT_APPLICABLE_NO_BREAK: "L = 10 (kırılma yok)", fz.NOT_APPLICABLE_B10: "b = 10 (D_{b+1} yok)",
                    fz.BULLETIN_NOT_PINNED: "D_1..D_b bülteni pinli değil", fz.INPUTS_NOT_AVAILABLE: "girdi dosyası yok",
                    reg.CALENDAR_NOT_AVAILABLE: "takvim yok (T_open hesaplanamıyor)", BREAK_STAGE_RECORD: "satır (makine kaydı; sınıf)"}
BREAK_CELL_TEXT = {(BREAK_MODEL_ID, "F1", BREAK_PRODUCT): "F1 Brier: model − ürün (BİRİNCİL)",
                   (BREAK_MODEL_ID, "F1", BREAK_ZERO_ID): "F1 Brier: model − `@ZERO`",
                   (BREAK_MODEL_ID, "F2", BREAK_PRODUCT): "F2 Brier: model − ürün",
                   (BREAK_MODEL_ID, "F2", BREAK_ZERO_ID): "F2 Brier: model − `@ZERO`",
                   (BREAK_MODEL_ID, "F1", BREAK_BY_TYPE): "F1 Brier: model − kırılma türü oranı",
                   (BREAK_PRODUCT, "F1", BREAK_ZERO_ID): "bilgi: ürün − `@ZERO` (F1)"}


def _break_verdict(c: Mapping[str, Any]) -> str:
    """SPEC_SCORING §8 dili; bilgi hücresinde hüküm yazılmaz."""
    if c.get("diff") is None:
        return f"metrik yok (n < {MIN_N_METRIC})"
    if c["label"] == LABEL_INFO:
        return "— (bilgi)"
    return str(c["verdict"])


def _y(lab: Mapping[str, Any]) -> str:
    return str(lab["y"]) if lab["status"] == oc.STATUS_OK else lab["status"]


def render_break_doc(scores: Mapping[str, Any]) -> str:
    """docs/SCORES_BREAK.md: yalnız `scores/scores_break.json`'dan (dördüncü ölçek `live_break`). Backtest, canlı listeleme öncesi,
    POST_D1 ya da zaman-dışı sayısıyla toplam/ortalama yoktur; backtest yalnız §8 bilgi satırıdır. Bülten adı yazılmaz."""
    L: list[str] = []
    w = L.append
    m = scores["models"][0]
    b = m["live_break"]
    card = m["card"]
    d = scores["definitions"]
    bs = d["bootstrap_live"]
    code = scores["code"]
    w(f"# {BREAK_TITLE}")
    w("")
    w("Bu sayfa `python -m borsai.scoring --break` ile `scores/scores_break.json`'dan üretilir; elle düzenlenmez. Tanımlar: "
      "`docs/specs_faz8/SPEC_BREAK_V0.md` (§2 hedefler, §5 karşılaştırıcılar, §8 öne çıkan kuralı, §9 canlı aşama `POST_BREAK`), "
      "`docs/specs/SPEC_SCORING.md` §7–§8; yorum kararları `docs/SPEC_DEVIATIONS.md` bölüm N. Kod: `borsai/scoring.py` (skor), "
      "`borsai/freeze.py` (makine kaydı), `borsai/registry.py` (kayıt bekçisi).")
    w("")
    w(f"- **Dördüncü ölçek (`{scores['scale']}`), asla toplanmaz.** Geçmiş veri testi (backtest, `docs/MODELS.md` Faz 8), canlı "
      "listeleme öncesi ve POST_D1 sicili (`docs/SCORES.md`) ve zaman-dışı terazi (`docs/SCORES_OOT.md`) ayrıdır; aralarında toplam "
      "ya da ortalama yoktur (CLAUDE.md kural 3).")
    w("- **Makine sıralı kayıt:** tahmin, donmuş model JSON'u, D_1..D_b'nin sha-pinli resmi bültenleri ve listeleme öncesi girdi "
      "dosyasından skorlama anında deterministik üretilir ve `registry/post_break/` altına append-only yazılır; insan değer girmez.")
    w(f"- Sınıf koddan hesaplanır, elle etiket yok: {d['class']} RETRO arz hiçbir n'e girmez (yalnız §6 bilgi tablosu).")
    w(f"- Hedefler: F1 = `{d['targets']['F1']}`, F2 = `{d['targets']['F2']}`; {d['targets']['label']}.")
    w(f"- Fark = {d['diff']}; Brier kırpmasız. Aralık: ay-blok bootstrap (blok = {bs['block']}), B = {bs['B']}, {bs['generator']} "
      f"tohum {bs['seed']}, yüzdelik [{bs['percentiles'][0]}, {bs['percentiles'][1]}]; koşul n ≥ {d['small_n']['row_table_only_below']} "
      f"ve ≥ {d['small_n']['min_blocks']} blok.")
    w(f"- Dil (SPEC_SCORING §8, SPEC_BREAK_V0 §6 e): n < {MIN_N_METRIC} → yalnız satır tablosu; {MIN_N_METRIC} ≤ n < {MIN_N_FULL} → "
      f"\"{V_SMALL}\"; \"{V_PASS}\" yalnız n ≥ {MIN_N_FULL} ve aralık tamamen 0'ın altındaysa; tamamen üstündeyse \"{V_FAIL}\", 0'ı "
      f"içeriyorsa \"{V_NEUTRAL}\". Model ancak birincil ve `@ZERO` hücrelerinin ikisi de \"{V_PASS}\" ise canlıda geçer.")
    w(f"- Üretim {scores['generated_at_utc']}; HEAD `{code['git_head']}`; borsai kaynak sha256 `{(code['borsai_source_sha256'] or '—')[:12]}`; "
      f"borsai kirli: {'evet' if code['borsai_dirty'] else 'hayır'}; INDEX_POST_BREAK sha256 "
      f"`{(scores['inputs']['models_index_post_break_sha256'] or '—')[:12]}`.")
    w("")
    w(f"## 1. Kart: `{m['model_id']}` (kural satırı `{BREAK_ZERO_ID}`)")
    w("")
    promo = card["promotion"]
    bt = card["backtest_info"]
    zero, by_type = card["comparators_frozen"]["zero"], card["comparators_frozen"]["by_type_F1"]
    w("| Alan | Değer |")
    w("|---|---|")
    w(f"| Dondurma | {card['frozen_at']} (yerel saat, kanıt değil); commit `{(card['model_commit'] or '—')[:12]}`; push kanıtı "
      f"{card['model_push_proof_created_at'] or 'yok'} |")
    w(f"| Eğitim | F1 n = {card['training_n_F1']}, F2 n = {card['training_n_F2']}; etiketlerin son seansı "
      f"{card['training_last_label_date']}; şartname kesimi {card['spec_training_cutoff']}; parametre sha256 `{card['params_sha256_8']}` |")
    w(f"| Donmuş karşılaştırıcılar | `@ZERO` F1 {_p(zero['F1'])}, F2 {_p(zero['F2'])}; kırılma türü oranı (F1) b_floor = 0: "
      f"{_p(by_type['0'])}, b_floor = 1: {_p(by_type['1'])} |")
    w(f"| Öne çıkan durum (§8 aşama {promo['stage']}) | {'öne çıkar' if promo['promoted'] else 'ikincil satır'}; etiket: "
      f"\"{promo['label']}\" |")
    if bt is None:
        w("| Backtest bilgi satırı | yok (docs/faz8/backtest/ bulunamadı) |")
    else:
        w(f"| Backtest bilgi satırı ({bt['scale']}, {bt['subset']}; toplanmaz) | F1 − ürün {_s(bt['F1_product']['diff'])} "
          f"[{_s(bt['F1_product']['ci95'][0])}, {_s(bt['F1_product']['ci95'][1])}] n {bt['F1_product']['n']}; F1 − `@ZERO` "
          f"{_s(bt['F1_zero']['diff'])} [{_s(bt['F1_zero']['ci95'][0])}, {_s(bt['F1_zero']['ci95'][1])}] n {bt['F1_zero']['n']}; "
          f"\"{bt['label']}\" |")
    rw = card["regime_warning"]
    w(f"| Rejim uyarısı | `{rw.get('tag')}` (D_1 ≥ {rw.get('start_d1')}, bitiş {rw.get('end_d1') or 'açık'}); model girdisi değil, n'den "
      "düşülmez |")
    w(f"| Varyant sayacı (aynı veri) | {card['n_variants_same_data']} model varyantı / {card['n_runs_same_data']} koşu |")
    w("")
    w("## 2. Payda (ipos.csv'de FROZEN her arz; ilk tutan durum)")
    w("")
    w("| Durum | Anlam | Arz |")
    w("|---|---|---|")
    for s in BREAK_DENOMINATOR_ORDER:
        k = b["n_rows"] if s == BREAK_STAGE_RECORD else b[BREAK_STAGE_COUNTERS[s]]
        w(f"| `{s}` | {BREAK_STAGE_TEXT[s]} | {k} |")
    w("")
    w(f"Özdeşlik: payda {len(b['denominator'])} = aşama sayaçları + satır ({b['n_rows']}); satırlar: skorlanan {b['n_scored']} "
      f"(makine sıralı {b['n_machine']} / LIVE {b['n_live']}), ret {b['n_refused']}, hedef bekleniyor {b['n_pending']}, hedef oluşmadı "
      f"{b['n_target_unavailable']}, etiket NA {b['n_target_label_na']}.")
    w("")
    w("| Arz | D_1 | seri | L | b | D_b | durum | sınıf | makine kaydı |")
    w("|---|---|---|---|---|---|---|---|---|")
    for r in b["denominator"]:
        w(f"| {r['ticker']} | {r['d1'] or '—'} | `{r['streak_state']}` | {'—' if r['L'] is None else r['L']} | "
          f"{'—' if r['b'] is None else r['b']} | {r['break_date'] or '—'} | `{r['stage_status']}` | {r['class'] or '—'} | "
          f"{r['record_id'] or '—'} |")
    w("")
    w(f"## 3. Satır tablosu (canlı satırlar; n_scored < {MIN_N_METRIC} iken yalnız bu tablo)")
    w("")
    if not b["rows"]:
        w("Canlı satır yok (bütün arzlar ya RETRO ya da payda durumunda).")
    else:
        w("| Arz | D_1 | b | tür (b_floor) | p_F1 | gerçekleşen F1 | `@ZERO` F1 | ürün F1 | tür oranı | p_F2 | gerçekleşen F2 | sınıf | durum |")
        w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for r in b["rows"]:
            c = r["comparators"]
            w(f"| {r['ticker']} | {r['d1']} | {r['b']} | {'—' if r['b_floor'] is None else r['b_floor']} | {_p(r['p']['F1'])} | "
              f"{_y(r['realized']['F1'])} | {_p(c[BREAK_ZERO_ID]['F1'])} | {_p(c[BREAK_PRODUCT]['F1'])} "
              f"({c[BREAK_PRODUCT]['status']}) | {_p(c[BREAK_BY_TYPE]['F1'])} | {_p(r['p']['F2'])} | {_y(r['realized']['F2'])} | "
              f"{r['class']} | {r['status']} |")
    w("")
    w("## 4. Hücreler (§5.2; satır başına eşleşik)")
    w("")
    if not b["cells"]:
        w(f"n_scored = {b['n_scored']} < {MIN_N_METRIC}: hücre yok, hüküm yok (yalnız satır tablosu).")
    else:
        w("| Hücre | etiket | n (blok) | makine / LIVE | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |")
        w("|---|---|---|---|---|---|---|---|---|---|")
        for c in b["cells"]:
            ci = "—" if c["ci95"] is None else f"[{_s(c['ci95'][0])}, {_s(c['ci95'][1])}]"
            wlt = "—" if c["wins"] is None else f"{c['wins']} / {c['losses']} / {c['ties']}"
            w(f"| {BREAK_CELL_TEXT[(c['model_id'], c['horizon_or_k'], c['rule_id'])]} | {c['label']} | {c['n']} ({c['n_blocks']}) | "
              f"{c['n_machine']} / {c['n_live']} | {_p(c['model_value'])} | {_p(c['rule_value'])} | {_s(c['diff'])} | {ci} | {wlt} | "
              f"{_break_verdict(c)} |")
    w("")
    w("## 5. Kalibrasyon ve rejim kırılımı (betimsel; aralık ve hüküm yok)")
    w("")
    if not b["descriptive"]:
        w(f"n_scored = {b['n_scored']} < {MIN_N_METRIC}: yok.")
    else:
        w("| Alt küme | n | ort(p_F1) | gözlenen F1 | fark | not |")
        w("|---|---|---|---|---|---|")
        for x in b["descriptive"]:
            note = x.get("note") or x.get("label") or "—"
            w(f"| {x['subset']} | {x['n']} | {_p(x['model_value'])} | {_p(x['observed'])} | {_s(x['diff'])} | {note} |")
    w("")
    w("## 6. RETRO bilgi satırları (hiçbir n'e girmez)")
    w("")
    retro = scores["retro_info"]
    if not retro:
        w("Yok.")
    else:
        w("| Arz | D_1 | L | b | D_b | b_floor | p_F1 | p_F2 | `@ZERO` F1 / F2 | tür oranı | ürün | rejim | uyarılar | makine kaydı | neden |")
        w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for r in retro:
            c = r.get("comparators")
            p = r.get("p") or {"F1": None, "F2": None}
            zero_txt = "—" if c is None else f"{_p(c[BREAK_ZERO_ID]['F1'])} / {_p(c[BREAK_ZERO_ID]['F2'])}"
            w(f"| {r['ticker']} | {r['d1'] or '—'} | {'—' if r['L'] is None else r['L']} | {'—' if r['b'] is None else r['b']} | "
              f"{r['break_date'] or '—'} | {'—' if r.get('b_floor') is None else r['b_floor']} | {_p(p['F1'])} | {_p(p['F2'])} | "
              f"{zero_txt} | {'—' if c is None else _p(c[BREAK_BY_TYPE]['F1'])} | {'—' if c is None else c[BREAK_PRODUCT]['status']} | "
              f"{', '.join(r.get('regime_tags') or []) or '—'} | {', '.join(r.get('warnings') or []) or '—'} | {r['record_id'] or '—'} | "
              f"{r['class_evidence']['basis'].split(':')[0] if 'basis' in r['class_evidence'] else 'RETRO (girdi/kayıt PIT değil)'} |")
    w("")
    return "\n".join(L)


def write_break_doc(scores: Mapping[str, Any], path: Path = BREAK_DOC_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_break_doc(scores), encoding="utf-8")
    return path


# ============================================================ bütün çıktı

def _n_variants_same_data(data_version: Optional[str], model_id: str, log_path: Path = LOG_PATH) -> tuple[int, int]:
    """(aynı veri sürümünde denenen farklı varyant sayısı, bu modelin o verideki koşu sayısı). Varyant: `kind: backtest`
    satırlarının farklı (model_id, spec_sha256) çiftleri + `kind: exploration` satırları (keşif varyantı başına bir; kaynak dosya
    sha'sı ve varyant kimliğiyle; SPEC_C_V0 §8, KARARLAR_C "Çokluk", SPEC_DEVIATIONS K). Duyarlılık ve koşullu değerlendirme
    satırları sayılmaz."""
    variants, runs = set(), 0
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get("data_version_sha256") != data_version:
                continue
            if e.get("kind") == "backtest":
                variants.add((e["model_id"], e["spec_sha256"]))
                runs += e["model_id"] == model_id
            elif e.get("kind") == "exploration":
                variants.add(("exploration", e["source_sha256"], e["variant_id"]))
    return len(variants), runs


def family_exploration_card(log_path: Optional[Path] = None) -> dict[str, Any]:
    """(C) kartlarının aile keşif sayacı (Fable Faz 7C denetimi F3, §3 K10; orkestratör kararı; SPEC_DEVIATIONS L): günlükteki
    `kind: exploration` satırı sayısı, kaynak `denenenler.csv` sha'sıyla (`report_faz7c.exploration_count`, MODELS.md ile tek tanım).
    Var olan `n_variants_same_data` değişmez; ikisi yan yana gösterilir, toplanmaz."""
    from . import report_faz7c as r7c
    from .specs import FAZ7C_EXPLORATION

    return {"n_exploration_family": r7c.exploration_count(Path(log_path) if log_path is not None else LOG_PATH),
            "exploration_family_source": {"path": FAZ7C_EXPLORATION["path"], "sha256": FAZ7C_EXPLORATION["sha256"],
                                          "kind": "exploration"}}


def _tree_sha(paths: Iterable[Path], root: Path) -> str:
    items = sorted(f"{p.relative_to(root).as_posix()}\t{sha256_file(p)}" for p in paths)
    return identity_hash(items)


def build_scores(*, root: Path = ROOT, outcomes_dir: Path = oc.OUTCOMES_DIR, now: Optional[datetime] = None,
                 runs: Optional[Mapping[str, list]] = None, runs4: Optional[Mapping[str, list]] = None) -> dict[str, Any]:
    ctx = load_context(root=root, outcomes_dir=outcomes_dir)
    models_out, retro_all = [], []
    all_params = {e["model_id"]: json.loads((root / "models" / e["file"]).read_text(encoding="utf-8")) for e in ctx.index["models"]}
    new_ids = [e["model_id"] for e in ctx.index["models"] if e["model_id"] in NEW_MODEL_COMPARATORS]
    near = near_era_blocks() if new_ids else {}
    for e in ctx.index["models"]:
        m = e["model_id"]
        kind = fz.model_kind(all_params[m])
        live, retro = live_block(ctx, m)
        retro_all += retro
        nv, nr = _n_variants_same_data(e["data_version_sha256"], m)
        block = {
            "model_id": m, "kind": kind,
            "card": {"training_n": e["training_n"], "training_cutoff": e["training_cutoff_date"],
                     "params_sha256_8": e["sha256"][:8], "n_variants_same_data": nv, "n_runs_same_data": nr,
                     **(family_exploration_card() if m in FAZ7C_CANDIDATES + (FAZ7C_RULE_ROW,) else {})},
            "primary_cell": primary_cell_of(m),
            "backtest": {"title": BACKTEST_TITLE, "scale": SCALE_BACKTEST, "cells": backtest_cells(m, runs, runs4),
                         **({"near_era": near.get(m)} if m in new_ids else {})},
            "live": {**live, "scale": SCALE_LIVE},
        }
        if kind in CONDITIONAL_KINDS:   # G2: S vektörü olan her tür; S'siz modelde blok yok
            block["conditional"] = conditional_block(m, conditional_units(ctx, m, live, retro), all_params)
        models_out.append(block)
    separate = separate_models(ctx)
    state = git_state(root)
    _, all_ipos = reg.read_ipos()
    outcome_files = sorted(Path(outcomes_dir).glob("*.csv"))
    record_files = sorted((root / "registry" / "records").rglob("*.json"))
    return {
        "schema_version": SCHEMA,
        "generated_at_utc": (now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
        .isoformat().replace("+00:00", "Z"),
        "as_of_session": oc.as_of_session(),
        "code": {"git_head": state["commit"], "borsai_source_sha256": source_tree_sha256(root / "borsai")["tree_sha256"],
                 "borsai_dirty": state["borsai_dirty"]},
        "inputs": {"outcomes_sha256": _tree_sha(outcome_files, root) if outcome_files else None,
                   "records_sha256": _tree_sha(record_files, root),
                   "models_index_sha256": sha256_file(root / "models" / "INDEX.json")},
        "definitions": {"small_n": {"row_table_only_below": MIN_N_METRIC, "insufficient_below": MIN_N_FULL,
                                    "min_blocks": MIN_BLOCKS},
                        "bootstrap_live": {"B": BOOTSTRAP_B, "generator": "numpy PCG64", "seed": BOOTSTRAP_SEED,
                                           "block": "gerçekleşen D_1'in takvim ayı", "percentiles": [2.5, 97.5]},
                        "diff": "model − kural; negatif = model iyi", "logloss_clip": LOGLOSS_CLIP,
                        "live_brier_clip": None},
        "outcomes": [{"ticker": r["ticker"], "status": r["status"], "listed_first_trading_date": r["first_trading_date"],
                      "ipo_price": oc.ipo_price_of(r["ticker"]),
                      "realized": ctx.realized[r["ticker"]].as_json() if ctx.realized.get(r["ticker"]) else None}
                     for r in ctx.ipos],
        "models": models_out,
        "separate_models": separate,
        "skipped": [dict(r) for r in all_ipos if r["status"] in ("SKIPPED", "OUT_OF_SCOPE")],
        "retro_info": retro_all,
        **({"faz7c_near_era": faz7c_near_era_block()}
           if any(e["model_id"] in FAZ7C_CANDIDATES for e in ctx.index["models"]) else {}),
    }


def separate_models(ctx: Context) -> list[dict[str, Any]]:
    """Legacy kayıtlardan INDEX'te olmayan ayrı modeller (TKNKA v1_5_full20; SPEC_SCORING §6): tek satırlık
    kendi listesi, metrik yok."""
    out: dict[str, dict[str, Any]] = {}
    for e in ctx.legacy["records"]:
        if e["role"] != "PRIMARY_SEPARATE_MODEL":
            continue
        t = e["ticker"]
        realized = ctx.realized.get(t)
        ipo = next((r for r in ctx.ipos if r["ticker"] == t), None)
        d1 = realized.d1 if realized and realized.d1 else (ipo or {}).get("first_trading_date")
        pred = legacy_prediction(e, root=ctx.root)
        needs = _needs("linear", realized)
        row = {"ticker": t, "d1": d1, "class": CLASS_LEGACY_SELF if e["time_proof"] == "SELF_REPORTED" else None,
               "record_id": e["record"], "prediction": pred, "realized": realized.as_json() if realized else None,
               "status": _row_status(pred, needs), "targets": dict(zip(_need_names("linear"), needs)),
               "note": "AYRI model (n = 20/20/20/19 eğitim); v1_5_h99 sütununa yazılmaz; metrik yok (SPEC_SCORING §6)"}
        out.setdefault(e["model_id"], {"model_id": e["model_id"], "in_models_index": e["model_id"] in ctx.models,
                                       "rows": [], "cells": []})["rows"].append(row)
    return list(out.values())


def write_scores(scores: Mapping[str, Any], path: Path = SCORES_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pretty_json_bytes(scores))
    return path


# ============================================================ docs/SCORES.md

def _p(x: Optional[float], nd: int = 4) -> str:
    return "—" if x is None else f"{x:.{nd}f}"


def _s(x: Optional[float], nd: int = 4) -> str:
    return "—" if x is None else f"{x:+.{nd}f}"


def _rv(rules: Mapping[str, Any], rid: str, h: str, key: str) -> str:
    v = rules.get(rid, {}).get("values", {})
    if "refused" in v:
        return "ret"
    return _p((v.get(h) or {}).get(key), 4 if key == "return" else 3)


def render_doc(scores: Mapping[str, Any], post: Optional[Mapping[str, Any]] = None) -> str:
    """docs/SCORES.md. `post`: scores/scores_post_d1.json (varsa §7 bölümü; SPEC_DEVIATIONS H28)."""
    L: list[str] = []
    w = L.append
    w("# Skorlar: canlı sicil ve backtest")
    w("")
    w("Bu sayfa `python -m borsai.scoring` ile `scores/scores.json`'dan üretilir; elle düzenlenmez. Tanımlar: "
      "`docs/specs/SPEC_SCORING.md`; kod: `borsai/outcomes.py` (sonuç), `borsai/scoring.py` (sınıf, birincil kayıt, metrik).")
    w("")
    w(f"- Skora giren en son THB: **{scores['as_of_session']}**. Sonuç yalnız resmi BIST THB/THM'den (`data/raw/bist/`, "
      "`data/outcomes/`).")
    w(f"- Kod: HEAD `{scores['code']['git_head']}` (üretim anı); borsai kaynak sha256 "
      f"`{scores['code']['borsai_source_sha256'][:12]}`.")
    w("- **İki terazi asla toplanmaz.** Canlı sicil (prospektif) ile geçmiş veri testi (retrospektif walk-forward, H99) "
      "ayrı bölümlerdedir; aralarında ortalama ya da toplam yoktur (CLAUDE.md kural 3).")
    n_max = max((m["live"]["n_scored"] for m in scores["models"]), default=0)
    small = n_max < MIN_N_METRIC
    w(f"- **Küçük n (SPEC_SCORING §8):** modellerin canlı skorlanan arz sayısı en çok n = {n_max}"
      + (f" < {MIN_N_METRIC}. Canlı tarafta YALNIZ satır tablosu vardır: metrik, ortalama, fark, aralık ya da hüküm "
         "üretilmez." if small else f"; n ≥ {MIN_N_METRIC} olan modellerde hücreler `scores/scores.json`'dadır."))
    w("")
    w("## 1. Sonuçlar (arz × ufuk)")
    w("")
    w("D_h = payın işlem gördüğü h'inci resmi seans (yarım gün sayılır, tam gün durdurma sayılmaz). Tavan = kapanış = "
      "o seansın THM üst limiti (Decimal eşitliği). R_h = kapanış / arz fiyatı − 1; Y_h = 1[kapanış > arz fiyatı]. "
      "PENDING = seans henüz oluşmadı.")
    w("")
    w("| Arz | Arz fiyatı | D_1 (THB) | D_1 (duyuru) | D_3 | D_5 | D_10 | R_D1 | R_D3 | R_D5 | R_D10 | Y 1/3/5/10 | "
      "Tavan D1…D10 | L | Satır durumu |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for o in scores["outcomes"]:
        J = o["realized"]
        if J is None:
            w(f"| {o['ticker']} | {o['ipo_price'] or '—'} | — | {o['listed_first_trading_date']} | " + " | ".join(["—"] * 10)
              + " | sonuç dosyası yok |")
            continue
        dates = J["sessions"]
        rs = [(_p(float(J["R"][h])) if J["R"][h] else J["row_status"][int(h[1:]) - 1]) for h in HORIZONS]
        ys = "/".join("·" if J["Y"][h] is None else str(J["Y"][h]) for h in HORIZONS)
        cc = "".join("·" if st == oc.STATUS_PENDING else ("?" if c is None else str(c))
                     for c, st in zip(J["ceiling_close"], J["row_status"]))
        same = J["d1"] == o["listed_first_trading_date"]
        L_txt = str(J["L"]) if J["L"] is not None else f"— ({J['L_status']})"
        counts = ", ".join(f"{s} {J['row_status'].count(s)}" for s in oc.ROW_STATUSES if s in J["row_status"])
        w(f"| {o['ticker']} | {o['ipo_price']} | {J['d1'] or '—'} | {o['listed_first_trading_date']}{'' if same else ' (FARKLI)'} | "
          + " | ".join(dates[h - 1] or J["row_status"][h - 1] for h in (3, 5, 10)) + " | " + " | ".join(rs)
          + f" | {ys} | {cc} | {L_txt} | {counts} |")
    w("")
    w("Tavan sütunu: 1 = tavan kapanışı, 0 = değil, ? = NA (üst limit yok), · = PENDING. Satır durumu: 10 ufuk satırının "
      "`data/outcomes/<T>.csv` durumları.")
    extra = [(o["ticker"], h + 1, key) for o in scores["outcomes"] if o["realized"]
             for key in ("half_day", "halt_flag", "shifted_by_suspension") for h, v in enumerate(o["realized"][key]) if v]
    w("")
    w("Yarım gün / gün içi durdurma / tam gün durdurma kayması: "
      + (", ".join(f"{t} D{h} {k}" for t, h, k in extra) if extra else "yok") + ".")
    w("")
    w("## 2. Sınıf ve birincil kayıt (arz × model)")
    w("")
    w("Sınıf koddan hesaplanır (SPEC_SCORING §5): model JSON'unu ekleyen commit sonuç commit'inin atası mı ve push kanıtı "
      "var mı; kaydın push kanıtı D_1'den önce mi; inputs_pit_ok. Birincil kayıt §6 kuralıyla (`registry.select_primary`). "
      "Sonuç dosyaları henüz commit edilmemişken üretilen skorda sınıf HEAD'e karşı denetlenir (`class_evidence`).")
    w("")
    tickers = [o["ticker"] for o in scores["outcomes"]]
    w("| Model | " + " | ".join(tickers) + " |")
    w("|---|" + "---|" * len(tickers))
    for m in scores["models"]:
        cells = []
        for t in tickers:
            r = next((x for x in m["live"]["rows"] if x["ticker"] == t), None)
            sr = next((x for x in m["live"]["self_reported_rows"] if x["ticker"] == t), None)
            rt = next((x for x in scores["retro_info"] if x["model_id"] == m["model_id"] and x["ticker"] == t), None)
            txt = "—"
            if r is not None:
                txt = r["class"] + (" (ret)" if r["status"] == ROW_REFUSED else "")
                if r["record_source"] == "LEGACY":
                    txt += f" legacy `{r['record_id']}`"
            elif rt is not None:
                txt = "RETRO"
            if sr is not None:
                txt += f"; + {sr['class']} `{sr['record_id']}`"
            cells.append(txt)
        w(f"| `{m['model_id']}` | " + " | ".join(cells) + " |")
    w("")
    regs = sorted({(r["ticker"], r["record_id"], r["class_evidence"]["record_commit"],
                    r["class_evidence"]["record_push_proof_created_at"]) for m in scores["models"] for r in m["live"]["rows"]
                   if r["record_source"] == "REGISTRY"})
    w("Sicil kayıtları (kayıt → ekleyen commit, push kanıtı):")
    w("")
    for t, rid, c, at in regs:
        w(f"- {t}: `{rid}` → `{(c or '—')[:7]}`, kanıt {at or 'yok'}")
    legs = sorted({(r["ticker"], r["record_id"], r["class"], r["class_evidence"]["record_push_proof_created_at"])
                   for m in scores["models"] for r in m["live"]["rows"] + m["live"]["self_reported_rows"]
                   if r["record_source"] == "LEGACY"})
    for t, rid, cls, at in legs:
        w(f"- {t}: legacy `{rid}` → {cls}; kanıt {at or 'yok (yalnız beyan)'}")
    w("")
    for m in scores["models"]:
        _render_model_rows(w, m)
    w("## 4. Ayrı modeller, geçersiz kullanım, atlananlar, RETRO")
    w("")
    for s in scores["separate_models"]:
        w(f"### `{s['model_id']}` (INDEX'te değil; tek satırlık kendi listesi)")
        w("")
        w("| Arz | Sınıf | Kayıt | R̂ D1/D3/D5/D10 | p̂ D1/D3/D5/D10 | R D1/D3/D5/D10 | Durum |")
        w("|---|---|---|---|---|---|---|")
        for r in s["rows"]:
            J = r["realized"] or {"R": {h: None for h in HORIZONS}, "row_status": [oc.STATUS_PENDING] * 10}
            w(f"| {r['ticker']} | {r['class']} | `{r['record_id']}` | "
              + " / ".join(_p(r["prediction"][h]["return"]) for h in HORIZONS) + " | "
              + " / ".join(_p(r["prediction"][h]["p_up"], 3) for h in HORIZONS) + " | "
              + " / ".join(_p(float(J["R"][h])) if J["R"][h] else J["row_status"][int(h[1:]) - 1] for h in HORIZONS)
              + f" | {r['status']} |")
        w("")
        if s["rows"]:
            w(s["rows"][0]["note"] + ".")
            w("")
    inv = [(m["model_id"], r) for m in scores["models"] for r in m["live"]["invalid_use_rows"]]
    if inv:
        w("### Geçersiz kullanım (gri; hiçbir metriğe ve n'e girmez)")
        w("")
        w("| Model | Arz | Kayıt | R̂ D1/D3/D5/D10 | Not |")
        w("|---|---|---|---|---|")
        for mid, r in inv:
            w(f"| `{mid}` | {r['ticker']} | `{r['record_id']}` | "
              + " / ".join(_p(r["prediction"][h]["return"]) for h in HORIZONS) + f" | {r['note']} |")
        w("")
    canc = [(m["model_id"], r) for m in scores["models"] for r in m["live"]["cancelled_records"]]
    w(f"İptal edilmiş kayıt: {len(canc)}.")
    w("")
    w("### Payda (`registry/ipos.csv`)")
    w("")
    n_skip = sum(1 for r in scores["skipped"] if r["status"] == "SKIPPED")
    w(f"Kapsam içi atlanan (SKIPPED) arz: {n_skip}. Kapsam dışı (OUT_OF_SCOPE) satırlar:")
    w("")
    w("| Satır | KAP | Durum ve neden |")
    w("|---|---|---|")
    for r in scores["skipped"]:
        w(f"| {r['ticker']} | {r['listing_source_id']} | {r['status']}: {r['skip_reason']} |")
    w("")
    w(f"RETRO (yalnız bilgi, hiçbir teraziye girmez): {len(scores['retro_info'])} (model, arz) çifti"
      + (": " + ", ".join(f"`{x['model_id']}`/{x['ticker']}" for x in scores["retro_info"]) if scores["retro_info"] else "")
      + ".")
    w("")
    w("## 5. Geçmiş veri testi (retrospektif, tasarıma maruz): önceden ilan edilen birincil hücreler")
    w("")
    w("Canlı sicilden AYRI terazi. Kaynak: fold ledger'ları; tam tablolar `docs/MODELS.md`'de (aralık `random.Random`, "
      "SPEC_DEVIATIONS C7). Bütün backtest hücreleri `scores/scores.json` → `models[].backtest.cells`.")
    w("")
    w("| Model | Hücre | Karşılaştırılan | n (ay) | model | karşılaştırılan | fark | %95 aralık | hüküm (§8) |")
    w("|---|---|---|---|---|---|---|---|---|")
    for m in scores["models"]:
        for c in m["backtest"]["cells"]:
            if c["label"] != "birincil":
                continue
            ci = "—" if c["ci95"] is None else f"[{_s(c['ci95'][0])}, {_s(c['ci95'][1])}]"
            hk = "" if c["horizon_or_k"] is None else f" {c['horizon_or_k']}"
            w(f"| `{m['model_id']}` | {c['output']}{hk} {c['metric']} | `{c['rule_id']}` | {c['n']} ({c['n_blocks']}) | "
              f"{_p(c['model_value'])} | {_p(c['rule_value'])} | {_s(c['diff'])} | {ci} | {c['verdict']} |")
    if scores.get("faz7c_near_era"):       # SPEC_C_V0 §5.1; yalnız (C) adayları INDEX'teyken (SPEC_DEVIATIONS K)
        w(render_faz7c_panel_row(scores["faz7c_near_era"]))
    w("")
    _render_near_era_and_family(w, scores)
    _render_conditional(w, scores)
    if post is not None:
        _render_post_d1(w, post)
    return "\n".join(L)


def _render_near_era_and_family(w: Callable[[str], None], scores: Mapping[str, Any]) -> None:
    """§5'in ekleri (SPEC_DEVIATIONS L): `models[].backtest.near_era` blokları (SPEC_APP_EK3 §5.5; SPEC_HAZARD_V1 §8 "yakın dönem
    etiketleri SCORES.md backtest panelinde ayrı satır") ve (C) kartlarının aile keşif sayacı (`n_exploration_family`, yanında
    `n_variants_same_data`; toplanmaz). Bloklar yoksa (Faz 7/7C kartsız skor dosyası) hiçbir şey yazmaz. Sıra `models` listesinden."""
    near = [(m["model_id"], m["backtest"]["near_era"]) for m in scores["models"] if m["backtest"].get("near_era")]
    if near:
        w("### 5.1 Yakın dönem blokları (backtest, H99, ilk işlem ≥ 2024-01-01; `models[].backtest.near_era`)")
        w("")
        w("Etiket kuralı önceden yazılı (SPEC_HAZARD_V1 §5.1, SPEC_C_V0 §5.1): %95 aralığın alt ucu > 0 → bozuyor; üst ucu ≤ tolerans "
          "→ tolerans içinde; diğer → belirsiz. (C)'de birincil hücreyi yalnız `fall_d10_v0_pooled` taşır; öteki (C) satırları §5.5 "
          "k3'ün \"yakın dönem − `base_rate`\" hücresidir. Hüküm sözcüğü değil etikettir.")
        w("")
        w("| Model | Karşılaştırılan | Metrik | n (ay) | fark | %95 aralık | tolerans | Etiket |")
        w("|---|---|---|---|---|---|---|---|")
        for mid, b in near:
            ci = "—" if b["ci95"] is None else f"[{_s(b['ci95'][0])}, {_s(b['ci95'][1])}]"
            w(f"| `{mid}` | `{b['comparator']}` | {b['metric']} | {b['n']} ({b['n_blocks']}) | {_s(b['diff'])} | {ci} | "
              f"{b['tolerance']:+.3f} | {b['label']} |")
        w("")
    fam = [(m["model_id"], m["card"]) for m in scores["models"] if "n_exploration_family" in m["card"]]
    if fam:
        src = fam[0][1]["exploration_family_source"]
        w("### 5.2 (C) kart sayaçları: varyant sayacı ve aile keşif sayacı (yan yana, toplanmaz)")
        w("")
        w(f"Aile keşif sayacı: `experiments/log.jsonl`'daki `kind: exploration` satırları (kaynak `{src['path']}`, sha256 "
          f"`{src['sha256'][:12]}…`; SPEC_C_V0 §10, KARARLAR_C \"Çokluk\"). Varyant sayacı: aynı veri sürümündeki farklı backtest "
          "varyantları + keşif satırları (kart `n_variants_same_data`, değişmedi).")
        w("")
        w("| Model | Varyant (aynı veri sürümü) | Aile keşif sayacı |")
        w("|---|---|---|")
        for mid, card in fam:
            w(f"| `{mid}` | {card['n_variants_same_data']} | {card['n_exploration_family']} |")
        w("")


def _render_post_d1(w: Callable[[str], None], post: Mapping[str, Any]) -> None:
    """§7: POST_D1 aşaması (ayrı terazi `live_post_d1`). Yalnız sayımlar, payda ve satır tabloları; hücreler
    scores/scores_post_d1.json'da (n ≥ 10)."""
    w("## 7. D1 sonrası güncelleme (canlı POST_D1, j = 1; SPEC_POST_D1_V0 §7)")
    w("")
    w("Kaynak `scores/scores_post_d1.json` (şema `borsai.scores_post_d1/1`). D1'i resmi THM üst limitinde kapatan arzda D_1 "
      "bülteninden yazılan POST_D1 kaydının (`registry/post_d1/`) S vektöründen S_k / S_1, k = 2..10; D1 hedefi skorlanmaz. "
      "Sınıf tarihlerden: model dosyası D_1'den sonraki ilk sonuç verisinin atası ve push kanıtlı mı; kaydın push kanıtı "
      "T_open'dan (D_1'i izleyen ilk resmi seans 09:40:00+03:00) önce mi; inputs_pit_ok_post_d1. Yorum kararları "
      "`docs/SPEC_DEVIATIONS.md` H28–H47.")
    w("")
    w("- **Ayrı ölçek** (`live_post_d1`): koşulsuz canlı sicil (§3), koşullu bloklar (§6) ve geçmiş veri testi (§5) ile "
      "toplanmaz.")
    w(f"- **n < {MIN_N_METRIC}: metrik hesaplanmaz**, yalnız satır tablosu; {MIN_N_METRIC} ≤ n < {MIN_N_FULL}: \"yetersiz örnek\".")
    w("")
    for m in post["models"]:
        b, card = m["conditional_j1"], m["card"]
        w(f"### `{m['model_id']}`")
        w("")
        w(f"Kart: eğitim n = {card['training_n']}; δ eğitim arzlarının son seans tarihi {card['training_last_session_date']} "
          f"(kesim değil; şartname eğitim kesimi {card['spec_training_cutoff']}); param sha `{card['params_sha256_8']}`; aynı veri "
          f"sürümünde denenen varyant {card['n_variants_same_data']}. Önceden ilan edilen birincil hücre: RPS_1, "
          + " / ".join(f"`{x}`" for x in b["primary_cell"]["rule_ids"]) + " koşullu karşısında. Karşılaştırılanlar: "
          + ", ".join(f"`{x}`" for x in b["comparators"]["S_cond"]) + "; path ikincili "
          + ", ".join(f"`{x}`" for x in b["comparators"]["path"]) + ".")
        w("")
        w("| skorlanan (LIVE / LATE) | ret | atlanan | kapsam dışı (D1 tavan değil) | D1 etiketi NA | hedef oluşmadı | bekleyen | "
          "S_1 = 0 | RETRO | D1 bekleniyor | hücre |")
        w("|---|---|---|---|---|---|---|---|---|---|---|")
        cells = f"— (n < {MIN_N_METRIC})" if b["n_scored"] < MIN_N_METRIC else str(len(b["cells"]))
        w(f"| {b['n_scored']} ({b['n_live']} / {b['n_late']}) | {b['n_refused']} | {b['n_skipped']} | {b['n_not_applicable']} | "
          f"{b['n_d1_label_na']} | {b['n_target_unavailable']} | {b['n_pending']} | {b['n_undefined']} | {b['n_retro']} | "
          f"{b['n_undetermined']} | {cells} |")
        w("")
        w("Payda (`registry/ipos.csv`'de FROZEN her arz, §7.5):")
        w("")
        w("| Arz | D_1 | D1 tavan | Aşama durumu | Kayıt | Sınıf |")
        w("|---|---|---|---|---|---|")
        for d in b["denominator"]:
            st = d["stage_status"] + (f": {d['skip_reason']}" if d["skip_reason"] else "")
            lab = "—" if d["ceiling_close_D1"] is None else str(d["ceiling_close_D1"])
            w(f"| {d['ticker']} | {d['d1'] or '—'} | {lab} | {st} | {('`' + d['record_id'] + '`') if d['record_id'] else '—'} | "
              f"{d['class'] or '—'} |")
        w("")
        if b["rows"]:
            head = ["Arz", "Sınıf", "Kayıt", "T_open", "L", "model S_2/S_1 · S_10/S_1"] + [f"`{x}`" for x in b["comparators"]["S_cond"]] \
                + ["Durum"]
            w("| " + " | ".join(head) + " |")
            w("|" + "---|" * len(head))
            for r in b["rows"]:
                L_txt = str(r["L"]) if r["L"] is not None else f"≥ {r['L_at_least']}"
                cells_ = [r["ticker"], r["class"], f"`{r['record_id']}`", r["t_open"], L_txt, _cond_pair(r, POST_D1_J)]
                cells_ += [_cond_pair(r["rules"][x], POST_D1_J) for x in b["comparators"]["S_cond"]]
                cells_.append(r["status"])
                w("| " + " | ".join(cells_) + " |")
            w("")
    rt = post["retro_info"]
    w(f"RETRO (yalnız bilgi, hiçbir n'e girmez): {len(rt)} (model, arz) çifti"
      + (": " + ", ".join(f"`{x['model_id']}`/{x['ticker']}" for x in rt) if rt else "") + ".")
    w("")


def _cond_pair(v: Mapping[str, Any], j: int) -> str:
    """Satır tablosu hücresi: S_{j+1}/S_j · S_10/S_j (tahmin; kayıp değil)."""
    if "refused" in v:
        return f"ret ({v['refused']['code']})"
    sc_ = v.get("S_cond")
    if sc_ is None:
        return f"tanımsız (S_{j} = 0)"
    return f"{_p(sc_[str(j + 1)], 3)} · {_p(sc_[str(sv.DAYS)], 3)}"


def _render_conditional(w: Callable[[str], None], scores: Mapping[str, Any]) -> None:
    """§6: koşullu canlı skorlar. Yalnız sayımlar ve satır tabloları (tahmin, gerçekleşen); hücreler scores.json'da."""
    blocks = [(m["model_id"], m["conditional"]) for m in scores["models"] if m.get("conditional")]
    if not blocks:
        return
    w("## 6. Koşullu tavan skorları (canlı, j başına; SPEC_CEILING_PATH_V0 §7)")
    w("")
    w("Seri j. günde sürüyorken (D_1..D_j resmi THM'de tavan) dondurulmuş kaydın S vektöründen P(L ≥ k | L ≥ j) = S_k / S_j. "
      "Skorlanan çift (arz, j): L ≥ j biliniyor ve D_{j+1}..D_10 sonuçlarının hepsi girmiş; eksik ufuk bütün modellerde aynı "
      "anda düşer. Sınıf, dayandığı kaydın sınıfıdır (j'ye göre yeniden sınıflanmaz). Metrikler `borsai/predict_path.py`'nin "
      "ortak fonksiyonlarından (`conditional_rps`, `conditional_brier`, `conditional`); yorum kararları "
      "`docs/SPEC_DEVIATIONS.md` bölüm G.")
    w("")
    w("- **Farklı j'ler ve koşulsuz tablolar toplanmaz**: aynı arz birden çok j'de bulunur (bağımlı). Bu bölüm canlı sicilden "
      "(§3) ve geçmiş veri testinden (§5) ayrı bir ölçektir (`live_conditional`).")
    n_max = max((b["n_scored"] for _, c in blocks for b in c["by_j"]), default=0)
    w(f"- **j başına n < {MIN_N_METRIC}: metrik hesaplanmaz**; yalnız satır tablosu (tahmin ve gerçekleşen). "
      f"{MIN_N_METRIC} ≤ n < {MIN_N_FULL}: \"yetersiz örnek\". Bugün en büyük n = {n_max}"
      + (": hiçbir j'de koşullu hücre ya da hüküm yoktur." if n_max < MIN_N_METRIC else
         "; hücreler `scores/scores.json` → `models[].conditional.by_j[].cells`.")
      + " Satır kayıpları (RPS_j, Brier) `scores/scores.json` → `models[].conditional.by_j[].rows`.")
    w("")
    for mid, c in blocks:
        comps = c["comparators"]
        # sözlük sırası bellek ile yazılmış dosya (sıralı anahtar) arasında farklıdır; belge sabit sırayla yazılır
        refs = [comps["unconditional_reference"][k] for k in CONDITIONAL_UNCONDITIONAL_REFS if k in comps["unconditional_reference"]]
        w(f"### `{mid}`")
        w("")
        cmp_txt = ", ".join(f"`{x}`" for x in comps["S_cond"]) or "yok (yalnız satır; koşulsuz blokta da karşılaştırıcısı yok)"
        w(f"Karşılaştırılanlar, S_k / S_j: {cmp_txt}."
          + (f" Önceden ilan edilen birincil hücre (j başına ayrı): RPS_j, "
             + " / ".join(f"`{x}`" for x in c["primary_cell"]["rule_ids"]) + " karşısında." if c["primary_cell"] else "")
          + (" Getiri/p_up ikincilleri (h ∈ {3, 5, 10}, h > j): koşullu "
             + (", ".join(f"`{x}`" for x in comps["path"]) or "—") + "; koşulsuz referans "
             + ", ".join(f"`{x}`" for x in refs) + "." if comps["path"] or refs else ""))
        w("")
        w("| j | skorlanan (LIVE / LATE) | ret | bekleyen | hedef oluşmadı | S_j = 0 | atlanan | RETRO | kayıt yok | "
          "L ≥ j henüz belirsiz | hücre |")
        w("|---|---|---|---|---|---|---|---|---|---|---|")
        for b in c["by_j"]:
            cells = f"— (n < {MIN_N_METRIC})" if b["n_scored"] < MIN_N_METRIC else str(len(b["cells"]))
            w(f"| {b['j']} | {b['n_scored']} ({b['n_live']} / {b['n_late']}) | {b['n_refused']} | {b['n_pending']} | "
              f"{b['n_target_unavailable']} | {b['n_undefined']} | {b['n_skipped']} | {b['n_retro']} | {b['n_no_record']} | "
              f"{b['n_undetermined']} | {cells} |")
        w("")
        for b in c["by_j"]:
            if not b["rows"]:
                continue
            j = b["j"]
            head = ["Arz", "Sınıf", "Kayıt", "L", f"model S_{j + 1}/S_{j} · S_10/S_{j}"] + [f"`{x}`" for x in comps["S_cond"]]
            hs = [h for h in CONDITIONAL_PATH_HS if h > j]
            if comps["path"] or comps["unconditional_reference"]:
                head += [f"koşullu R̂ / p̂ D{'/'.join(map(str, hs))}", f"R D{'/'.join(map(str, hs))}", "limit yolu farkı"]
            head.append("Durum")
            w(f"j = {j} (skorlanan n = {b['n_scored']}):")
            w("")
            w("| " + " | ".join(head) + " |")
            w("|" + "---|" * len(head))
            for r in b["rows"]:
                L_txt = str(r["L"]) if r["L"] is not None else f"≥ {r['L_at_least']}"
                cells = [r["ticker"], r["class"], f"`{r['record_id']}`", L_txt, _cond_pair(r, j)]
                cells += [_cond_pair(r["rules"][x], j) for x in comps["S_cond"]]
                if comps["path"] or comps["unconditional_reference"]:
                    p = r.get("path") or {}
                    cells.append(" / ".join(f"{_p((p.get(f'D{h}') or {}).get('return'))} · "
                                            f"{_p((p.get(f'D{h}') or {}).get('p_up'), 3)}" for h in hs))
                    cells.append(" / ".join(_p(float(p[f"D{h}"]["R"])) if (p.get(f"D{h}") or {}).get("R") else "—" for h in hs))
                    cells.append("—" if not p else str(p["limit_path_mismatch"]))
                cells.append(r["status"])
                w("| " + " | ".join(cells) + " |")
            w("")


def _render_model_rows(w: Callable[[str], None], m: Mapping[str, Any]) -> None:
    live = m["live"]
    rows = live["rows"]
    sr = live["self_reported_rows"]
    if not rows and not sr:
        return
    kind = m["kind"]
    w(f"## 3. `{m['model_id']}` — Canlı sicil (prospektif, n = {live['n_scored']}; atlanan = {live['n_skipped']})")
    w("")
    w(f"n_live = {live['n_live']} (LIVE), n_late = {live['n_late']} (LATE_RECORD); ret = {live['n_refused']}; hedef "
      f"oluşmadı = {live['n_target_unavailable']}; bekleyen = {live['n_pending']} (skorlanan ama bazı ufukları bekleyen: "
      f"{live['n_partial_pending']}). "
      + (f"n < {MIN_N_METRIC}: metrik yok, yalnız satırlar." if not live["cells"] else
         f"Hücreler ({len(live['cells'])}) `scores/scores.json` → `live.cells`."))
    w("")
    groups = [("", rows)] + ([("Self-reported (ikincil; kanıtlı n'e girmez)", sr)] if sr else [])
    for title, rs in groups:
        if title:
            w(f"{title}:")
            w("")
        if kind in ("hazard", "km"):
            comps = comparators(m["model_id"], kind)
            head = ["Arz", "Sınıf", "Kayıt", "model S_1/S_3/S_5/S_10"] + [f"`{c}` S_1/3/5/10" for c in comps if c != P_UP_AS_CEILING]
            head += ["model P_close 1/3/5/10"] + ([f"`{P_UP_AS_CEILING}` 1/3/5/10"] if P_UP_AS_CEILING in comps else [])
            head += ["L", "tavan 1/3/5/10", "Durum"]
            w("| " + " | ".join(head) + " |")
            w("|" + "---|" * len(head))
            for r in rs:
                pred = r["prediction"]
                J = r["realized"] or {}

                def curve(v):
                    if "refused" in v:
                        return f"ret ({v['refused']['code']})"
                    return " / ".join(_p(v["S"][k - 1], 3) for k in KS)
                cells = [r["ticker"], r["class"], f"`{r['record_id']}`", curve(pred)]
                cells += [curve(r["rules"][c]["values"]) for c in comps if c != P_UP_AS_CEILING]
                cells.append("ret" if "refused" in pred else " / ".join(_p(pred["P_close_ceiling"][k - 1], 3) for k in KS))
                if P_UP_AS_CEILING in comps:
                    v = r["rules"][P_UP_AS_CEILING]["values"]
                    cells.append("ret" if "refused" in v else " / ".join(_p(v["P_close_ceiling_k"][str(k)], 3) for k in KS))
                cc = J.get("ceiling_close") or [None] * sv.DAYS
                st = J.get("row_status") or [oc.STATUS_PENDING] * sv.DAYS
                cells.append("—" if J.get("L") is None else str(J["L"]))
                cells.append(" / ".join("·" if st[k - 1] == oc.STATUS_PENDING else ("?" if cc[k - 1] is None else str(cc[k - 1]))
                                        for k in KS))
                cells.append(r["status"])
                w("| " + " | ".join(cells) + " |")
        else:
            comps = comparators(m["model_id"], kind)
            fall = kind == "fall"            # (C): yalnız D5/D10 p_up; getiri başlığı yok (SPEC_DEVIATIONS L)
            ret_c = [] if fall else [c for c in comps if c in RETURN_RULES or c == V15]
            p_c = [c for c in comps if c in PROB_RULES or c == V15 or (fall and c in NEW_MODEL_COMPARATORS)]
            head = ["Arz", "Ufuk", "Sınıf", "Kayıt", "model R̂", "model p̂"] + [f"`{c}` R̂" for c in ret_c] + \
                   [f"`{c}` p̂" for c in p_c] + ["R", "Y", "Durum"]
            w("| " + " | ".join(head) + " |")
            w("|" + "---|" * len(head))
            for r in rs:
                pred = r["prediction"]
                J = r["realized"] or {"R": {}, "Y": {}, "row_status": [oc.STATUS_PENDING] * 10}
                for h in (pf.FALL_HORIZONS if fall else HORIZONS):
                    if "refused" in pred:
                        mr = mp = f"ret ({pred['refused']['code']})"
                    else:
                        mr, mp = _p(pred[h]["return"]), _p(pred[h]["p_up"], 3)
                    cells = [r["ticker"], h, r["class"], f"`{r['record_id']}`", mr, mp]
                    cells += [_rv(r["rules"], c, h, "return") for c in ret_c]
                    cells += [_rv(r["rules"], c, h, "p_up") for c in p_c]
                    Rv = J["R"].get(h)
                    st = J["row_status"][int(h[1:]) - 1]
                    cells += [_p(float(Rv)) if Rv else st, "—" if J["Y"].get(h) is None else str(J["Y"][h]),
                              r["status"] if "refused" in pred else ("OK" if Rv else st)]
                    w("| " + " | ".join(cells) + " |")
        w("")
    w("")


def write_doc(scores: Mapping[str, Any], path: Path = DOC_PATH, post: Optional[Mapping[str, Any]] = None) -> Path:
    path.write_text(render_doc(scores, post), encoding="utf-8")
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Canlı sicil ve backtest skorları: scores/scores.json, "
                                                 "scores/scores_post_d1.json ve docs/SCORES.md.")
    parser.add_argument("--oot", action="store_true",
                        help="yalnız zaman-dışı eski kohort (üçüncü terazi): scores/scores_oot.json ve docs/SCORES_OOT.md; "
                             "öbür skor dosyaları yazılmaz")
    parser.add_argument("--break", dest="brk", action="store_true",
                        help="yalnız kırılma akşamı (ölçek live_break; makine sıralı): eksik makine kayıtları (registry/post_break/), "
                             "scores/scores_break.json ve docs/SCORES_BREAK.md; öbür skor dosyaları yazılmaz")
    args = parser.parse_args(argv)
    if args.oot and args.brk:
        parser.error("--oot ve --break birlikte kullanılmaz")
    if args.oot:
        return main_oot()
    if args.brk:
        return main_break()
    scores = build_scores()
    post = build_post_d1_scores(scores)
    print(write_scores(scores))
    print(write_post_d1_scores(post))
    # belge yazılmış dosyalardan (sıralı anahtar) üretilir: commit denetimiyle aynı yol (memory: render sırası)
    print(write_doc(json.loads(pretty_json_bytes(scores)), post=json.loads(pretty_json_bytes(post))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Dondurma: (1) modelleri models/ altına, (2) tahmin kayıtlarını registry/records/ altına.

(1) Model dondurma — H99'un 99 arzıyla fit edip models/<model_id>.json + models/INDEX.json.
  Faz 7 `ceiling_hazard_v1_*` kimlikleri (specs.FAZ7_MODEL_SPECS) `backtest.final_fit_v1` ile fit edilir (nihai fit
  önizlemesiyle aynı kod yolu; pooled ve @INF training_table_v2'nin 165 arzıyla); `fit.fit` bu kimlikleri bilmez.
  Faz 7C `fall_d10_v0_*` kimlikleri (specs.FAZ7C_MODEL_SPECS) aynı kalıpla `backtest.final_fit_fall` ile (h99 H99'un 94 arzı;
  pooled, @ZERO ve addsale training_table_v2'den 161 / 161 / 165 arz; SPEC_C_V0 §2.3, SPEC_DEVIATIONS K16).
  Faz 8 kırılma akşamı kimlikleri (`break_floor_v0`, kural satırı `break_floor_v0@ZERO`; specs.POST_BREAK_MODEL_SPECS) yalnız
  birlikte `freeze_post_break` ile `post_break.final_fit`'ten (önizlemeyle aynı kod yolu) models/INDEX_POST_BREAK.json'a
  (SPEC_BREAK_V0 §4.4, §7.3; SPEC_DEVIATIONS N21–N23); INDEX.json ve INDEX_POST_D1.json'a girmez.
- Dondurulmuş dosyanın ya da INDEX kaydının üzerine yazılmaz (CLAUDE.md kural 1);
  model değişirse yeni model_id ile eklenir (kural 5).
- frozen_at yerel saattir; zaman kanıtı değildir. Kanıt, dosyaları içeren
  commit'in uzak depoya push edilme zamanıdır.
- fit/veri modülleri (numpy, scikit-learn) yalnız bu yolda yüklenir.

(2) Tahmin kaydı (CLAUDE.md kural 1; SPEC_SCORING §5-§6) — girdi JSON'u -> kayıt dosyası:
    registry/inputs/<TICKER>.json  ->  registry/records/<TICKER>/<UTC-zaman>_<kısa-sha>.json
  Kayıt: girdi belgesinin tamamı + input_sha256; models/INDEX.json'daki kayıtlı BÜTÜN modellerin
  çıktısı (ret edenler için ret kodu ve nedeni); her modelin parametre dosyası sha256'sı;
  f6 (XU100) hesabı; kayıt zamanı, git HEAD, borsai kaynak sha'sı, schema_version.
  INDEX'te deflatörlü model (SPEC_HAZARD_V1 §3.2; JSON'da `deflator`) varsa `tufe` bloğu (market20 kalıbı) ve
  model_inputs["tufe_index"] (`tufe.index_for(T)`: T'nin ayı − 2, release_date < T bekçisi, model pinleri). Ön koşul
  (§9): o ay dosyada yoksa kayıt YAZILMAZ (TufeMissing; ileti eksik ayı ve aylık ekleme komutunu söyler). Canlı kayıtta
  model_inputs["alloc_regime"] anahtarı yoktur (rejimli model r = regime.live_value = 0; SPEC_DEVIATIONS J6); anahtar
  yalnız eski kohort (OOT_PRE_LISTING) kayıtlarındadır ve orada rejimli model varken zorunludur (B7 bekçisi).
  Faz 7C düşen arz modelleri (`fall` türü, `predict_fall.predict`) ek girdi istemez: `additional_sale_shares` V1.5 alanıdır
  (model_inputs'ta zaten var); h99 ve pooled deflatörlüdür, `tufe` bloğu ve ön koşul v1'le ortaktır (SPEC_DEVIATIONS K16).
  <kısa-sha> = kayıt dosyası baytlarının sha256'sının ilk 12 hanesi (içerik adresli).
- Yalnız stdlib (masaüstü uygulamasının "dondur" düğmesi aynı fonksiyonu çağırır).
- Dosya yeniden yazılmaz ('xb'). Aynı arz için birden çok etkin kayıt olabilir (ör. önce talep öncesi PB
  kaydı, sonra talep katlı kayıt); hangisinin skorlandığına SPEC_SCORING §6 karar verir
  (`registry.select_primary`). Etkin bir kayıtla aynı `input_sha256` ve aynı models/INDEX.json sha256'sını
  taşıyan ikinci kayıt reddedilir (DUPLICATE_RECORD). Hatalı kayda açık iptal kaydı (record_type =
  CANCELLATION) düşülür; iptal ilk işlem gününden (Istanbul tarihi) itibaren yapılamaz (SPEC_SCORING §6).
- Girdi belgesi yapısal denetimi ve inputs_pit_ok'un girdi kısmı geçmezse kayıt yazılmaz.
- f6 ref_date: kayıt Istanbul tarihi < ilk işlem günü ise tahmin tarihi (canlı, kural 5 dahil);
  değilse ilk işlem günü (geç kayıt; SPEC_MARKET20_V0 §4-e).
- Sınıf (LIVE / LATE_RECORD / RETRO) kayda YAZILMAZ; Faz 2B'de tarihlerden hesaplanır.

(3) POST_D1 kaydı (SPEC_POST_D1_V0 §7.4) — D_1 bülteni -> registry/post_d1/<TICKER>/<UTC-zaman>_<kısa-sha>.json:
  base_record (ceiling_hazard_v0'ın SPEC_SCORING §6 birincil kaydı; f1–f3 onun `model_inputs`'u), D_1 tarihli THB+THM
  (pinli sha256) ve ham alanlar, models/INDEX_POST_D1.json'daki her modelin çıktısı, karşılaştırıcıların koşullu kopyası.
  Zaman sınırı T_open = D_1'i izleyen ilk resmi seans 09:40:00+03:00; zaman kanıtı push kanıtıdır.

Kullanım:
  .venv/bin/python -m borsai.freeze registry/inputs/<TICKER>.json          # tahmin kaydı
  .venv/bin/python -m borsai.freeze --post-d1 <TICKER>                      # POST_D1 kaydı (D_1 akşamı)
  .venv/bin/python -m borsai.freeze --cancel <kayıt.json> --reason "<neden>" # iptal kaydı (POST_D1: T_open'dan önce)
  .venv/bin/python -m borsai.freeze --models <model_id> ...                  # model dondurma
  .venv/bin/python -m borsai.freeze --models break_floor_v0 break_floor_v0@ZERO   # POST_BREAK dondurma (INDEX_POST_BREAK.json)
  .venv/bin/python -m borsai.freeze --oot registry/oot/cohort_pre_h99.csv    # eski kohort toplu kaydı (S2, tek koşu)
  .venv/bin/python -m borsai.freeze --oot registry/oot/cohort_pre_h99.csv --only-missing-models   # ek kayıt (yalnız eksik modeller)
  .venv/bin/python -m borsai.freeze --oot-post-d1 <TICKER>                   # eski kohort POST_D1 kaydı (S3, d1_rows'tan)

(4) Eski kohort (Faz 6; SPEC_OOT_PRE_H99_V0 §5, KARARLAR D6): registry/oot/records/<T>/ (borsai.oot_record/1) ve
  registry/oot/post_d1/<T>/ (borsai.oot_post_d1_record/1, exposure_class = MACHINE_SEQUENCED). Ayrıntı bölüm (4)'te.

(5) POST_BREAK makine kaydı (SPEC_BREAK_V0 §9.2): registry/post_break/<T>/machine_<UTC>_<kısa-sha>.json
  (borsai.post_break_machine_record/1, exposure_class = MACHINE_SEQUENCED, append-only). CLI'si yoktur: skorlama anında
  `python -m borsai.scoring --break` yazar (`write_post_break_machine_record`). Ayrıntı bölüm (5)'te.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Optional, Sequence

from . import market20 as m20
from . import outcomes as oc
from . import predict as pr
from . import predict_break as pbrk
from . import predict_fall as pf
from . import predict_hazard as ph
from . import predict_market20 as pm
from . import predict_path as pth
from . import predict_pb as ppb
from . import predict_post_d1 as pd1
from . import registry as reg
from .provenance import (ISTANBUL, ROOT, canonical_sha256, git_state, pretty_json_bytes, sha256_bytes, sha256_file,
                         source_tree_sha256)

if TYPE_CHECKING:
    from .data import Dataset

MODELS_DIR = ROOT / "models"
INDEX_PATH = MODELS_DIR / "INDEX.json"
# POST_D1 aşamasının modelleri ayrı dizinde (proje sahibi kararı 4, SPEC_DEVIATIONS H): listeleme öncesi kayıt
# (`build_record`) yalnız INDEX.json'u okur; POST_D1 modelleri INDEX.json'a asla girmez.
INDEX_POST_D1_NAME = "INDEX_POST_D1.json"
INDEX_POST_D1_PATH = MODELS_DIR / INDEX_POST_D1_NAME
# POST_BREAK (kırılma akşamı) aşamasının modelleri de ayrı dizinde (SPEC_BREAK_V0 §7.3, §9.2): INDEX.json'a ve INDEX_POST_D1.json'a
# asla girmez; listeleme öncesi kayıt ve POST_D1 kaydı onları okumaz.
INDEX_POST_BREAK_NAME = "INDEX_POST_BREAK.json"
INDEX_POST_BREAK_PATH = MODELS_DIR / INDEX_POST_BREAK_NAME
INDEX_SCHEMA = "borsai.model_index/1"
FROZEN_AT_BASIS = "LOCAL_CLOCK_SELF_REPORTED: zaman kanıtı bu dosyayı içeren commit'in push'udur (CLAUDE.md kural 1)"

RECORD_SCHEMA = "borsai.record/1"
RECORDED_AT_BASIS = ("LOCAL_CLOCK_SELF_REPORTED: zaman kanıtı bu kaydı içeren commit'in push kanıtıdır "
                     "(registry/push_proofs, SPEC_SCORING §5)")
RECORD_PREDICTION = "PREDICTION"
RECORD_CANCELLATION = "CANCELLATION"
STATUS_PREDICTED = "PREDICTED"
STATUS_REFUSED = "REFUSED"
STATUS_ERROR = "ERROR"


class FreezeError(RuntimeError):
    pass


class DuplicateRecord(FreezeError):
    code = "DUPLICATE_RECORD"


# ============================================================ (1) model dondurma

def load_index(path: Path = INDEX_PATH) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"schema_version": INDEX_SCHEMA, "models": []}


def index_entry(params: dict[str, Any], file_name: str, file_sha256: str) -> dict[str, Any]:
    tr = params["training"]
    return {
        "model_id": params["model_id"],
        "file": file_name,
        "sha256": file_sha256,
        "algorithm": params["algorithm"],
        "schema_version": params["schema_version"],
        "spec_sha256": params["spec_sha256"],
        "training_n": tr["n"],
        "training_cutoff_date": tr["cutoff_date"],
        "training_tickers_sha256": tr["tickers_sha256"],
        "data_version_sha256": tr["data_version_sha256"],
        "frozen_at": params["created_at"],
        "frozen_at_basis": FROZEN_AT_BASIS,
        "status": "FROZEN",
    }


def freeze(model_ids: Sequence[str], dataset: "Dataset", *, models_dir: Path = MODELS_DIR) -> dict[str, Any]:
    from .fit import fit
    from .specs import FAZ7_MODEL_SPECS, FAZ7C_MODEL_SPECS, MODEL_SPECS, POST_BREAK_MODEL_SPECS, POST_D1_MODEL_SPECS

    if any(m in POST_BREAK_MODEL_SPECS for m in model_ids):     # yalnız iki Faz 8 kimliği birlikte (freeze_post_break denetler)
        return freeze_post_break(model_ids, dataset, models_dir=models_dir)
    post = [m for m in model_ids if m in POST_D1_MODEL_SPECS]
    if post:
        if len(post) != len(model_ids):
            raise FreezeError("listeleme öncesi ve POST_D1 modelleri aynı çağrıda dondurulmaz (ayrı dizinler)")
        return freeze_post_d1(post, dataset, models_dir=models_dir)
    index_path = models_dir / "INDEX.json"
    index = load_index(index_path)
    known = {e["model_id"] for e in index["models"]}
    rows = list(dataset.rows)
    for model_id in model_ids:
        path = models_dir / f"{model_id}.json"
        if model_id in known or path.exists():
            raise FreezeError(f"{model_id} zaten dondurulmuş; üzerine yazılmaz (yeni model_id gerekir)")
        if model_id in FAZ7_MODEL_SPECS:
            params = fit_v1(model_id)
        elif model_id in FAZ7C_MODEL_SPECS:
            params = fit_fall(model_id)
        else:
            params = fit(MODEL_SPECS[model_id], rows, dataset_version=dataset.data_version_sha256)
        payload = pretty_json_bytes(params)
        path.write_bytes(payload)
        index["models"].append(index_entry(params, path.name, sha256_bytes(payload)))
        known.add(model_id)
    index_path.write_bytes(pretty_json_bytes(index))
    return index


def fit_v1(model_id: str) -> dict[str, Any]:
    """Faz 7 `ceiling_hazard_v1_*`: `backtest.final_fit_v1` (kendi veri kümesi: clip/real H99, pooled/@INF training_table_v2;
    şartnamedeki eğitim n'i ve veri sürümü sha'sı denetlenir). Nihai fit önizlemesiyle (tests/reference/macos_golden_faz7/)
    `created_at`, `code_version`, `runtime` dışında bit-eşit olmalıdır (tests/test_faz7_golden.py)."""
    from .backtest import final_fit_v1

    return final_fit_v1(model_id)[0]


def fit_fall(model_id: str) -> dict[str, Any]:
    """Faz 7C `fall_d10_v0_*`: `backtest.final_fit_fall` (kendi veri kümesi: h99 H99, ötekiler training_table_v2; ek satış
    `data.additional_sale_shares`; şartnamedeki eğitim n'i ve veri sürümü sha'sı denetlenir). Nihai fit önizlemesiyle
    (tests/reference/macos_golden_faz7c/) `created_at`, `code_version`, `runtime` dışında bit-eşit olmalıdır
    (tests/test_faz7c_golden.py; SPEC_DEVIATIONS K13, K16)."""
    from .backtest import final_fit_fall

    return final_fit_fall(model_id)[0]


def _parent_ok(ref: Mapping[str, str], index: Mapping[str, Any], models_dir: Path) -> None:
    entry = next((e for e in index["models"] if e["model_id"] == ref["model_id"]), None)
    if entry is None or entry["file"] != ref["file"]:
        raise FreezeError(f"{ref['model_id']} INDEX.json'da yok ya da dosya adı farklı")
    sha = sha256_file(Path(models_dir) / entry["file"])
    if not sha == entry["sha256"] == ref["sha256"]:
        raise FreezeError(f"{ref['model_id']}: dosya sha256 {sha} INDEX.json/şartname ile aynı değil ({entry['sha256']}, {ref['sha256']})")


def freeze_post_d1(model_ids: Sequence[str], dataset: "Dataset", *, models_dir: Path = MODELS_DIR) -> dict[str, Any]:
    """POST_D1 modelleri (SPEC_POST_D1_V0 §6.2; proje sahibi kararı 4): models/<id>.json + models/INDEX_POST_D1.json
    (yoksa oluşturulur, şema borsai.model_index/1). models/INDEX.json'a hiçbir zaman yazılmaz. Ön koşul: parent
    (ceiling_hazard_v0) ve path_conditional kaynağı (ceiling_path_v0) dosyalarının sha256'sı INDEX.json ile eşit."""
    from . import post_d1
    from .specs import POST_D1_MODEL_SPECS

    models_dir = Path(models_dir)
    index = load_index(models_dir / "INDEX.json")
    post_path = models_dir / INDEX_POST_D1_NAME
    post_index = load_index(post_path)
    known = {e["model_id"] for e in index["models"]} | {e["model_id"] for e in post_index["models"]}
    for model_id in model_ids:
        spec = POST_D1_MODEL_SPECS[model_id]
        _parent_ok(spec["parent"], index, models_dir)
        _parent_ok(spec["path_secondary"], index, models_dir)
        path = models_dir / f"{model_id}.json"
        if model_id in known or path.exists():
            raise FreezeError(f"{model_id} zaten dondurulmuş; üzerine yazılmaz (yeni model_id gerekir)")
        params = post_d1.fit_params(dataset, models_dir=models_dir)
        payload = pretty_json_bytes(params)
        path.write_bytes(payload)
        post_index["models"].append({**index_entry(params, path.name, sha256_bytes(payload)), "stage": params["stage"],
                                     "parent_model_id": params["parent"]["model_id"], "parent_sha256": params["parent"]["sha256"]})
        known.add(model_id)
    post_path.write_bytes(pretty_json_bytes(post_index))
    return post_index


def post_break_index_entry(params: dict[str, Any], file_name: str, file_sha256: str) -> dict[str, Any]:
    """models/INDEX_POST_BREAK.json girişi (SPEC_DEVIATIONS N22): `index_entry`'nin alanları — kırılma JSON'unun `training`'inde tek
    `n` yoktur, `training_n` = F1 başlığının eğitim n'i (`n_F1`; `training_tickers_sha256` de F1 kümesinin) — ve ek olarak `stage`,
    `training_n_F2`, `training_tickers_sha256_F2`, `sessions_file_sha256`. `index_entry`'nin kendisi değişmez."""
    tr = params["training"]
    entry = index_entry({**params, "training": {**tr, "n": tr["n_F1"]}}, file_name, file_sha256)
    entry.update(stage=params["stage"], training_n_F2=tr["n_F2"], training_tickers_sha256_F2=tr["tickers_sha256_F2"],
                 sessions_file_sha256=tr["sessions_file_sha256"])
    return entry


def freeze_post_break(model_ids: Sequence[str], dataset: "Dataset", *, models_dir: Path = MODELS_DIR) -> dict[str, Any]:
    """POST_BREAK modelleri (SPEC_BREAK_V0 §4.4, §7.3, §9.2; SPEC_DEVIATIONS N21–N23): `break_floor_v0` ve kural satırı
    `break_floor_v0@ZERO` yalnız birlikte ve `FAZ8_MODEL_IDS` sırasıyla dondurulur (tek kimlik, başka sıra ya da başka modellerle
    karışık çağrı FreezeError). Parametreler nihai fit önizlemesiyle aynı kod yolundan: `post_break.final_fit` (şartnamedeki eğitim
    n'leri, veri sürümü ve SESSIONS sha'sı denetlenir) -> models/<id>.json; giriş `post_break_index_entry` ->
    models/INDEX_POST_BREAK.json (yeni dosya, şema borsai.model_index/1). models/INDEX.json ve INDEX_POST_D1.json'a hiçbir zaman
    yazılmaz. Kimlik üç dizinin birinde ya da diskte varsa hiçbir şey yazılmadan FreezeError (üzerine yazılmaz; kural 1)."""
    from . import post_break
    from .specs import FAZ8_MODEL_IDS

    if tuple(model_ids) != FAZ8_MODEL_IDS:
        raise FreezeError(f"POST_BREAK modelleri yalnız birlikte ve {list(FAZ8_MODEL_IDS)} sırasıyla dondurulur; verilen {list(model_ids)}")
    models_dir = Path(models_dir)
    brk_path = models_dir / INDEX_POST_BREAK_NAME
    known = {e["model_id"] for name in ("INDEX.json", INDEX_POST_D1_NAME, INDEX_POST_BREAK_NAME)
             for e in load_index(models_dir / name)["models"]}
    for model_id in model_ids:
        if model_id in known or (models_dir / f"{model_id}.json").exists():
            raise FreezeError(f"{model_id} zaten dondurulmuş; üzerine yazılmaz (yeni model_id gerekir)")
    brk_index = load_index(brk_path)
    for model_id in model_ids:
        params = post_break.final_fit(model_id, dataset)[0]
        payload = pretty_json_bytes(params)
        path = models_dir / f"{model_id}.json"
        path.write_bytes(payload)
        brk_index["models"].append(post_break_index_entry(params, path.name, sha256_bytes(payload)))
    brk_path.write_bytes(pretty_json_bytes(brk_index))
    return brk_index


# ============================================================ (2) tahmin kaydı

def model_kind(params: Mapping[str, Any]) -> str:
    """Parametre dosyasından tahmin yolu: hazard | km | ceiling_path | post_d1 | post_break | fall | market20 | pb | linear | rule.
    `specs.model_kind` ile aynı sınıflama (fall: Faz 7C düşen arz ailesi, `@ZERO` kural satırı dahil; post_break: Faz 8 kırılma
    akşamı, `@ZERO` dahil; testli). post_break algoritma adını (`l2_logit_v1_6_grid`) fall ile paylaşır: aşama ve aile algoritmadan
    ÖNCE denetlenir (SPEC_DEVIATIONS N23)."""
    algorithm = params.get("algorithm")
    features = list(params.get("features") or [])
    if params.get("stage") == pbrk.STAGE and params.get("family") == pbrk.FAMILY:
        return "post_break"
    if algorithm == pd1.ALGORITHM:
        return "post_d1"
    if algorithm == pf.FALL_ALGORITHM:
        return "fall"
    if algorithm == ph.HAZARD_ALGORITHM:
        return "hazard"
    if algorithm == pth.ALGORITHM:
        return "ceiling_path"
    if algorithm in ph.KM_ALGORITHMS:
        return "km"
    if algorithm == "V1_5_RIDGE_LOGIT":
        if "f6" in features:
            return "market20"
        if any(str(f).startswith("pb") for f in features):
            return "pb"
        return "linear"
    return "rule"


def run_model(params: Mapping[str, Any], inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Tek model: {status, refusal, output}. Girdi reddi etiketli REFUSED; parametre dosyası
    hatası ERROR (kayıt yazılmaz, çağıran karar verir)."""
    kind = model_kind(params)
    if kind == "post_d1":   # D1 bülteni ister; listeleme öncesi kayıtta çalışmaz (models/INDEX_POST_D1.json, ayrı akış)
        return {"kind": kind, "status": STATUS_ERROR, "output": None,
                "refusal": {"code": "PARAMS_INVALID", "field": None, "reason": "POST_D1 modeli listeleme öncesi kayıtta çalışmaz"}}
    if kind == "post_break":   # D_b bülteni ister; listeleme öncesi kayıtta çalışmaz (models/INDEX_POST_BREAK.json, makine sıralı)
        return {"kind": kind, "status": STATUS_ERROR, "output": None,
                "refusal": {"code": "PARAMS_INVALID", "field": None,
                            "reason": "POST_BREAK modeli listeleme öncesi kayıtta çalışmaz"}}
    try:
        if kind in ("hazard", "km"):
            out = ph.predict(params, inputs)
        elif kind == "ceiling_path":
            out = pth.predict(params, inputs)
        elif kind == "market20":
            out = pm.predict(params, inputs)
        elif kind == "pb":
            out = ppb.predict(params, inputs)
        elif kind == "fall":
            out = pf.predict(params, inputs)
        else:
            out = pr.predict(params, inputs)
    except pr.PredictError as exc:
        return {"kind": kind, "status": STATUS_ERROR, "refusal": {"code": exc.code, "field": None, "reason": str(exc)}, "output": None}
    refused = out.get("refused")
    return {"kind": kind, "status": STATUS_REFUSED if refused else STATUS_PREDICTED, "refusal": refused, "output": out}


def market20_for_record(t: Optional[str], recorded_local_date: str) -> dict[str, Any]:
    """f6 bloğu (SPEC_MARKET20_V0 §2-§4). Canlı: ref_date = kayıt tarihi; geç: ref_date = T."""
    if t is None:
        return {"ref_date": recorded_local_date, "ref_date_rule": "T_UNKNOWN", "f6": None,
                "refusal": m20.PREDICTION_TOO_EARLY,
                "note": "ilk işlem günü bilinmiyor; kural 5 (T − tahmin tarihi ≤ 12) denetlenemez"}
    calendar, records, xu_sha = m20.load_live_sources()
    live = recorded_local_date < t
    ref = recorded_local_date if live else t
    res = m20.market20(ref, calendar, records, xu100_sha256=xu_sha, live=live, first_trading_date=t)
    block = res.as_record()
    block.update(ref_date_rule="LIVE_PREDICTION_DATE" if live else "LATE_RECORD_T_SPEC_MARKET20_V0_4E",
                 calendar=calendar.name, xu100_file=str(m20.XU100_PINNED[-1][0].relative_to(ROOT)))
    return block


class TufeMissing(FreezeError):
    """SPEC_HAZARD_V1 §9 kayıt ön koşulu: deflatörlü model varken T'nin ayı − 2'nin TÜFE'si dosyada yok; kayıt yazılmaz."""

    code = "TUFE_MISSING"

    def __init__(self, month: str, t: str) -> None:
        from . import tufe

        self.month = month
        super().__init__(f"TUFE_MISSING: TÜFE {month} ayı {tufe.TUFE_REL} dosyasında yok (T = {t}, kural T'nin ayı − 2); kayıt "
                         f"yazılmadı. Önce ayı ekleyin (bülten yayımlandıktan sonra): {tufe.append_command(month)}")


def deflator_pins(models: Sequence[tuple[Mapping[str, Any], Mapping[str, Any], str]]) -> dict[str, dict[str, str]]:
    """INDEX'teki deflatörlü modellerin TÜFE pinleri: model_id -> {through_month, prefix_sha256} (J4 önek pini)."""
    return {e["model_id"]: {"through_month": p["deflator"]["through_month"], "prefix_sha256": p["deflator"]["file_sha256"]}
            for e, p, _ in models if isinstance(p.get("deflator"), Mapping)}


def tufe_for_record(t: Optional[str], pins: Mapping[str, Mapping[str, str]]) -> dict[str, Any]:
    """Kaydın `tufe` bloğu (SPEC_HAZARD_V1 §3.2; market20 kalıbı): {month, index, release_date, bulletin_id, file,
    file_sha256, rule, pins, refusal}. `tufe.index_for(T)` (T'nin ayı − 2; release_date < T bekçisi) ve her modelin önek pini
    (`tufe.verify_pin`). Ay dosyada yoksa TufeMissing (kayıt ön koşulu). Pin tutmuyorsa refusal = TUFE_FILE_MISMATCH, yayım
    T'den önce değilse TUFE_NOT_PIT (kural gereği olamaz): o modeller RET verir (§9), kayıt yazılır. T bilinmiyorsa ay
    belirlenemez: refusal = TUFE_MISSING (f6'daki T_UNKNOWN kalıbı), deflatörlü modeller RET."""
    from . import tufe

    table = tufe.load()
    block: dict[str, Any] = {"series": tufe.SERIES, "rule": tufe.MONTH_RULE, "file": tufe.TUFE_REL, "file_sha256": table.file_sha256,
                             "pins": {m: dict(v) for m, v in pins.items()}, "month": None, "index": None, "release_date": None,
                             "bulletin_id": None, "refusal": None, "reason": None}
    if t is None:
        block.update(refusal=tufe.TUFE_MISSING, reason="T_UNKNOWN: ilk işlem günü bilinmiyor; T'nin ayı − 2 belirlenemez")
        return block
    try:
        got = tufe.index_for(t, table)
    except tufe.TufeRefusal as exc:
        if exc.code == tufe.TUFE_MISSING:
            raise TufeMissing(exc.month, t) from exc
        block.update(month=exc.month, refusal=exc.code, reason=str(exc))
        return block
    block.update({k: got[k] for k in ("month", "index", "release_date", "bulletin_id")})
    for m, pin in pins.items():
        try:
            tufe.verify_pin(table, pin)
        except tufe.TufeRefusal as exc:
            block.update(index=None, refusal=exc.code, reason=f"{m}: {exc}")
            break
    return block


def regime_input_problems(record_stage: Optional[str], models: Sequence[tuple[Mapping[str, Any], Mapping[str, Any], str]],
                          inputs: Mapping[str, Any]) -> list[str]:
    """SPEC_HAZARD_V1 §3.3, §9; SPEC_DEVIATIONS J6 (Fable denetimi B7). Rejimli model (JSON'da `regime`): canlı (listeleme öncesi)
    kayıtta `alloc_regime` anahtarı OLMAZ (r = live_value); eski kohort kaydında (OOT_PRE_LISTING) anahtar ZORUNLUDUR —
    unutulursa tahmin sessizce canlı sayılırdı (r = 0)."""
    regime_models = [e["model_id"] for e, p, _ in models if p.get("regime") is not None]
    if record_stage == OOT_STAGE:
        if regime_models and "alloc_regime" not in inputs:
            return [f"eski kohort kaydında rejimli model(ler) {regime_models} var ama model_inputs['alloc_regime'] yok "
                    "(kohort satırının ALLOC_REGIME etiketi verilmeli; J6, B7)"]
        return []
    if "alloc_regime" in inputs:
        return ["canlı kayıtta model_inputs['alloc_regime'] olamaz (rejimli modelde r = regime.live_value; J6)"]
    return []


def v1_record_inputs(record_stage: Optional[str], t: Optional[str], models: Sequence[tuple[Mapping[str, Any], Mapping[str, Any], str]],
                     inputs: dict[str, Any], alloc_regime: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Faz 7 modellerinin kayıt girdileri (INDEX'te o tür model yoksa hiçbir şey eklenmez; eski kayıtların biçimi aynen):
    deflatörlü model -> `tufe` bloğu + model_inputs tufe_index / tufe_refusal (ay yoksa TufeMissing, kayıt yazılmaz);
    rejimli model + eski kohort kaydı -> model_inputs["alloc_regime"] = kohort satırının ALLOC_REGIME etiketi (SPEC_DEVIATIONS
    J2, J6). Sonra B7 bekçisi (`regime_input_problems`). Dönen: `tufe` bloğu ya da None."""
    pins = deflator_pins(models)
    block = tufe_for_record(t, pins) if pins else None
    if block is not None:
        inputs["tufe_index"] = block["index"]
        inputs["tufe_refusal"] = block["refusal"]
    if record_stage == OOT_STAGE and alloc_regime is not None and any(p.get("regime") is not None for _, p, _ in models):
        inputs["alloc_regime"] = alloc_regime
    problems = regime_input_problems(record_stage, models, inputs)
    if problems:
        raise FreezeError("; ".join(problems))
    return block


def _index_models(models_dir: Path) -> tuple[dict[str, Any], str, list[tuple[dict[str, Any], dict[str, Any], str]]]:
    index_path = models_dir / "INDEX.json"
    index_bytes = index_path.read_bytes()
    index = json.loads(index_bytes)
    models = []
    for e in index["models"]:
        raw = (models_dir / e["file"]).read_bytes()
        sha = sha256_bytes(raw)
        if sha != e["sha256"]:
            raise FreezeError(f"{e['model_id']}: parametre dosyası sha256 INDEX ile uyuşmuyor ({sha} != {e['sha256']})")
        models.append((e, json.loads(raw), sha))
    return index, sha256_bytes(index_bytes), models


def _code_block(root: Path) -> dict[str, Any]:
    state = git_state(root)
    tree = source_tree_sha256(root / "borsai")
    return {"git_head": state["commit"], "borsai_dirty": state["borsai_dirty"],
            "borsai_source_sha256": tree["tree_sha256"], "borsai_files_sha256": tree["files"]}


def _now_pair(now: Optional[datetime]) -> tuple[datetime, str, str]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
    return now, now.isoformat().replace("+00:00", "Z"), now.astimezone(ISTANBUL).isoformat()


def _rel(path: Path, root: Path) -> str:
    try:
        return Path(path).resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def build_record(inputs_path: Path, *, now: Optional[datetime] = None, models_dir: Path = MODELS_DIR,
                 root: Path = ROOT, legacy_roles: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    doc, raw = reg.load_inputs(inputs_path)
    now_utc, recorded_utc, recorded_ist = _now_pair(now)
    problems = reg.inputs_pit_problems(doc, root=root, as_of=recorded_ist)
    if problems:
        raise FreezeError("girdi belgesi geçmedi: " + "; ".join(problems))
    ticker = doc["ticker"]
    t = doc["fields"]["first_trading_date"]["value"]
    local_date = recorded_ist[:10]
    m20_block = market20_for_record(t, local_date)
    inputs = reg.model_inputs(doc)
    inputs["f6_market20"] = m20_block.get("f6")
    inputs["f6_market20_refusal"] = m20_block.get("refusal")
    index, index_sha, models = _index_models(models_dir)
    tufe_block = v1_record_inputs(None, t, models, inputs)          # ön koşul: ay yoksa TufeMissing (kayıt yazılmaz)
    cells = []
    for entry, params, sha in models:
        result = run_model(params, inputs)
        if result["status"] == STATUS_ERROR:
            raise FreezeError(f"{entry['model_id']}: {result['refusal']['reason']}")
        cells.append({"model_id": entry["model_id"], "file": f"models/{entry['file']}", "params_sha256": sha,
                      "spec_sha256": entry["spec_sha256"], "algorithm": entry["algorithm"], **result})
    links = reg.legacy_links(ticker, legacy_roles)
    record = {
        "schema_version": RECORD_SCHEMA,
        "record_type": RECORD_PREDICTION,
        "ticker": ticker,
        "recorded_at_utc": recorded_utc,
        "recorded_at_istanbul": recorded_ist,
        "recorded_at_basis": RECORDED_AT_BASIS,
        "code": _code_block(root),
        "input_sha256": sha256_bytes(raw),
        "inputs": {"path": _rel(inputs_path, root), "sha256": sha256_bytes(raw), "document": doc},
        "model_inputs": inputs,
        "market20": m20_block,
        "models_index": {"path": _rel(models_dir / "INDEX.json", root), "sha256": index_sha,
                         "model_ids": [e["model_id"] for e, _, _ in models]},
        "models": cells,
        "summary": {"n_models": len(cells),
                    "n_predicted": sum(c["status"] == STATUS_PREDICTED for c in cells),
                    "n_refused": sum(c["status"] == STATUS_REFUSED for c in cells),
                    "refusals": {c["model_id"]: c["refusal"]["code"] for c in cells if c["status"] == STATUS_REFUSED}},
        "legacy_links": [{k: e[k] for k in ("record", "model_id", "role", "time_proof", "has_official_f3")} for e in links],
        "legacy_roles_sha256": sha256_file(reg.LEGACY_ROLES_PATH) if legacy_roles is None else canonical_sha256(legacy_roles),
    }
    if tufe_block is not None:
        record["tufe"] = tufe_block
    return record


def record_filename(payload: bytes, recorded_at_utc: str) -> str:
    stamp = recorded_at_utc.replace("-", "").replace(":", "")
    return f"{stamp}_{sha256_bytes(payload)[:12]}.json"


def list_records(ticker: str, records_dir: Path = reg.RECORDS_DIR) -> list[tuple[Path, dict[str, Any]]]:
    d = Path(records_dir) / ticker
    return [(p, json.loads(p.read_text(encoding="utf-8"))) for p in sorted(d.glob("*.json"))] if d.exists() else []


def active_records(ticker: str, records_dir: Path = reg.RECORDS_DIR) -> list[tuple[Path, dict[str, Any]]]:
    """İptal kaydı düşülmemiş tahmin kayıtları."""
    recs = list_records(ticker, records_dir)
    cancelled = {r["cancels"]["file"] for _, r in recs if r.get("record_type") == RECORD_CANCELLATION}
    return [(p, r) for p, r in recs if r.get("record_type") == RECORD_PREDICTION and p.name not in cancelled]


def _write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as fh:  # var olan dosya asla yeniden yazılmaz
        fh.write(payload)


def write_record(inputs_path: Path, *, now: Optional[datetime] = None, records_dir: Path = reg.RECORDS_DIR,
                 models_dir: Path = MODELS_DIR, root: Path = ROOT,
                 legacy_roles: Optional[Mapping[str, Any]] = None) -> Path:
    doc, raw = reg.load_inputs(inputs_path)
    index_sha = sha256_file(Path(models_dir) / "INDEX.json")
    for path, rec in active_records(doc["ticker"], records_dir):
        if rec["input_sha256"] == sha256_bytes(raw) and rec["models_index"]["sha256"] == index_sha:
            raise DuplicateRecord(f"DUPLICATE_RECORD: {doc['ticker']} için aynı girdi ve aynı model dizinli etkin kayıt var "
                                  f"({path.name})")
    record = build_record(inputs_path, now=now, models_dir=models_dir, root=root, legacy_roles=legacy_roles)
    payload = pretty_json_bytes(record)
    path = Path(records_dir) / record["ticker"] / record_filename(payload, record["recorded_at_utc"])
    _write_new(path, payload)
    return path


def cancel_record(record_path: Path, reason: str, *, now: Optional[datetime] = None,
                  records_dir: Path = reg.RECORDS_DIR, root: Path = ROOT) -> Path:
    """Açık iptal kaydı. İptal edilen dosya değişmez; skorlanmaz, nedeni ve zamanı görünür."""
    record_path = Path(record_path)
    if not reason or not reason.strip():
        raise FreezeError("iptal nedeni boş olamaz")
    target = json.loads(record_path.read_text(encoding="utf-8"))
    if target.get("record_type") != RECORD_PREDICTION:
        raise FreezeError("yalnız tahmin kaydı iptal edilebilir")
    ticker = target["ticker"]
    if record_path.name not in {p.name for p, _ in active_records(ticker, records_dir)}:
        raise FreezeError(f"{record_path.name} etkin bir kayıt değil (yok ya da zaten iptal)")
    _, recorded_utc, recorded_ist = _now_pair(now)
    t = target["inputs"]["document"]["fields"]["first_trading_date"]["value"]
    if t is not None and recorded_ist[:10] >= t:
        raise FreezeError(f"iptal ilk işlem gününden ({t}) itibaren yapılamaz (SPEC_SCORING §6)")
    cancellation = {
        "schema_version": RECORD_SCHEMA,
        "record_type": RECORD_CANCELLATION,
        "ticker": ticker,
        "recorded_at_utc": recorded_utc,
        "recorded_at_istanbul": recorded_ist,
        "recorded_at_basis": RECORDED_AT_BASIS,
        "code": _code_block(root),
        "cancels": {"file": record_path.name, "sha256": sha256_file(record_path)},
        "reason": reason.strip(),
    }
    payload = pretty_json_bytes(cancellation)
    path = Path(records_dir) / ticker / record_filename(payload, recorded_utc)
    _write_new(path, payload)
    return path


# ============================================================ (3) POST_D1 kaydı (SPEC_POST_D1_V0 §7.4)

POST_D1_RECORD_SCHEMA = reg.POST_D1_RECORD_SCHEMA
POST_D1_STAGE = pd1.STAGE
POST_D1_RECORDED_AT_BASIS = ("LOCAL_CLOCK_SELF_REPORTED: zaman kanıtı bu kaydı içeren commit'in push kanıtıdır; sınır T_open = D_1'i "
                             "izleyen ilk resmi seans 09:40:00+03:00 (SPEC_POST_D1_V0 §7.3)")
BASE_RECORD_RULE = "SPEC_SCORING_6_PRIMARY_ceiling_hazard_v0_AT_POST_D1_TIME"
BASE_MODEL_ID = pd1.PARENT_MODEL_ID
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"
# §7.4 comparators_conditional: dördü base_record'daki hücrenin kopyası; her-zaman-tavan tanım gereği S ≡ 1 (SPEC_DEVIATIONS
# C4; base_record'da S'i yok, H39).
POST_D1_COMPARATORS = ("ceiling_hazard_v0", "ceiling_hazard_v0@INF", "base_km_expanding", "base_km_last10", "base_always_ceiling")
ALWAYS_CEILING_SOURCE = "SPEC_DEVIATIONS_C4"
SKIPPED_NO_PRE_LISTING_RECORD = "SKIPPED_POST_D1: NO_PRE_LISTING_RECORD"


class NoBaseRecord(FreezeError):
    """§7.4: uygun listeleme öncesi kayıt yok -> POST_D1 kaydı yazılmaz; payda satırı SKIPPED_POST_D1."""

    code = SKIPPED_NO_PRE_LISTING_RECORD


class D1NotAvailable(FreezeError):
    """D_1 henüz oluşmadı (sonuç dosyasında h = 1 dolu değil) ya da D_1 bülteni yerelde yok: kayıt yazılmaz (§9 D1_NOT_TRADED)."""

    code = pd1.D1_NOT_TRADED


def _index_sha_checked(models_dir: Path, name: str) -> tuple[dict[str, Any], str, list[tuple[dict[str, Any], dict[str, Any], str]]]:
    raw = (Path(models_dir) / name).read_bytes()
    index = json.loads(raw)
    models = []
    for e in index["models"]:
        data = (Path(models_dir) / e["file"]).read_bytes()
        sha = sha256_bytes(data)
        if sha != e["sha256"]:
            raise FreezeError(f"{e['model_id']}: parametre dosyası sha256 {name} ile uyuşmuyor ({sha} != {e['sha256']})")
        models.append((e, json.loads(data), sha))
    return index, sha256_bytes(raw), models


def _frozen_ref(models_dir: Path, ref: Mapping[str, Any]) -> dict[str, Any]:
    """POST_D1 modelinin parent/path kaynağı: models/INDEX.json kaydı, dosya sha256'sı ve JSON'daki kopya sha aynı olmalı."""
    index = load_index(Path(models_dir) / "INDEX.json")
    entry = next((e for e in index["models"] if e["model_id"] == ref["model_id"]), None)
    if entry is None or entry["file"] != ref["file"]:
        raise FreezeError(f"{ref['model_id']} INDEX.json'da yok ya da dosya adı farklı (PARAMS_INVALID)")
    raw = (Path(models_dir) / entry["file"]).read_bytes()
    if not sha256_bytes(raw) == entry["sha256"] == ref["sha256"]:
        raise FreezeError(f"{ref['model_id']}: dosya sha256 INDEX.json/POST_D1 JSON'undaki kopya ile aynı değil (PARAMS_INVALID)")
    return json.loads(raw)


def d1_session(ticker: str, outcomes_dir: Path = oc.OUTCOMES_DIR) -> dict[str, str]:
    """Gerçekleşen D_1: data/outcomes/<T>.csv'nin h = 1 satırı (SPEC_SCORING §2; `outcomes update --through <D_1>`)."""
    path = oc.outcome_path(ticker, outcomes_dir)
    if not path.exists():
        raise D1NotAvailable(f"{pd1.D1_NOT_TRADED}: {ticker} sonuç dosyası yok; önce `python -m borsai.outcomes update --through <D_1>`")
    row = oc.read_outcome(path)[0]
    if row["status"] not in (oc.STATUS_OK, oc.STATUS_NA_LIMIT) or not row["session_date"]:
        raise D1NotAvailable(f"{pd1.D1_NOT_TRADED}: {ticker} D_1 henüz oluşmadı (h = 1 satırı {row['status']})")
    return row


def d1_block(ticker: str, d1: str, calendar: "oc.SessionCalendar", *, bist_dir: Path = oc.BIST_DIR, root: Path = ROOT,
             outcome_row: Optional[Mapping[str, str]] = None) -> dict[str, Any]:
    """§7.4 `d1` bloğu: D_1 tarihli resmi THB ve THM (pinli sha256, MANIFEST satırı) ve `<T>.E` satırının ham alanları."""
    manifest = {(r["date"], r["kind"]): r for r in oc.read_manifest(bist_dir)}
    bulletins, refs = {}, {}
    for kind in oc.KINDS:
        b = oc.local_bulletin(d1, kind, bist_dir)
        m = manifest.get((d1, kind))
        if b is None or m is None:
            raise D1NotAvailable(f"{pd1.D1_NOT_TRADED}: D_1 {d1} {kind.upper()} bülteni yerelde yok (MANIFEST)")
        bulletins[kind] = b
        refs[kind] = {"file": _rel(oc.local_path(d1, kind, bist_dir), root), "sha256": m["sha256"], "url": m["url"],
                      "http_last_modified": m["http_last_modified"], "downloaded_at": m["downloaded_at"],
                      "internal_filename": m["internal_filename"]}
    if outcome_row is not None and (outcome_row["thb_sha256"], outcome_row["thm_sha256"]) != (refs["thb"]["sha256"], refs["thm"]["sha256"]):
        raise FreezeError(f"{ticker}: sonuç dosyasının D_1 bülten sha'ları yerel bültenlerle aynı değil")
    code = oc.equity_code(ticker)
    row, lim = bulletins["thb"].get(code), bulletins["thm"].get(code)
    if row is None or not oc.traded(row):
        raise D1NotAvailable(f"{pd1.D1_NOT_TRADED}: {code} D_1 {d1} THB'sinde işlem görmemiş")
    fields = {"open": row.open, "high": row.high, "low": row.low, "close": row.close, "volume": row.volume,
              "turnover": row.turnover, "aof": row.aof, "trade_count": row.trade_count, "halt": row.halt,
              "special_trade_volume": row.special_volume, "special_trade_turnover": row.special_turnover,
              "reference_price": lim.reference if lim else "", "upper_limit": lim.upper if lim else "",
              "lower_limit": lim.lower if lim else ""}
    assert tuple(fields) == reg.POST_D1_FIELDS_RAW
    upper, close = oc.dec(fields["upper_limit"]), oc.dec(fields["close"])
    label = None if upper is None or upper <= 0 else int(close == upper)
    at_u = lambda name: None if label is None else (oc.dec(fields[name]) == upper)  # noqa: E731
    return {"session_date": d1, "session_h": 1, "half_day": int(calendar.is_half(d1)),
            "halt_flag": oc._halt_flag(ticker, d1, row), "thb": refs["thb"], "thm": refs["thm"], "fields_raw": fields,
            "ceiling_close_D1": label,
            "lock_consistency": {"open_at_U": at_u("open"), "high_at_U": at_u("high"), "close_at_U": at_u("close")}}


def select_base_record(ticker: str, d1: str, *, records_dir: Path = reg.RECORDS_DIR, root: Path = ROOT,
                       proofs: Optional[Sequence[Mapping[str, Any]]] = None) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    """§7.4 `base_record`: `ceiling_hazard_v0` için SPEC_SCORING §6 birincil kaydı (D_1'den önce push kanıtlı f3'lü en son;
    yoksa en erken LATE adayı) — skorlamayla aynı kural ve aynı aday kurucusu (`registry.select_primary`,
    `scoring.registry_candidates`). Yoksa NoBaseRecord."""
    from . import push_proof as pp
    from . import scoring as sc

    proofs = list(pp.load_proofs(Path(root) / "registry" / "push_proofs")) if proofs is None else list(proofs)
    recs = list_records(ticker, records_dir)
    cancelled = {r["cancels"]["file"] for _, r in recs if r.get("record_type") == RECORD_CANCELLATION}
    preds = [(p, r) for p, r in recs if r.get("record_type") == RECORD_PREDICTION]
    cands = sc.registry_candidates(sc.Git(root), preds, cancelled, BASE_MODEL_ID, d1, proofs, root)
    sel = reg.select_primary(BASE_MODEL_ID, [c for c, _ in cands], d1)["proven"]
    if sel["record_id"] is None:
        raise NoBaseRecord(f"{SKIPPED_NO_PRE_LISTING_RECORD}: {ticker} için {BASE_MODEL_ID} birincil listeleme öncesi kaydı yok "
                           f"({sel['rule']}); POST_D1 kaydı yazılmaz")
    path, rec = next((p, r) for p, r in preds if p.name == sel["record_id"])
    return path, rec, sel


def run_post_d1_model(params: Mapping[str, Any], models_dir: Path, inputs: Mapping[str, Any], d1: Mapping[str, Any],
                      base_cells: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Tek POST_D1 modeli: {status ∈ PREDICTED/REFUSED/NOT_APPLICABLE, refusal, output}. Parametre/parent hatası ve
    D1_NOT_TRADED -> FreezeError (kayıt yazılmaz, §9). path_conditional yalnız base_record'da ceiling_path_v0 çıktısı varsa;
    o çıktı bugünkü kodla yeniden üretilip kayıttakiyle `==` denetlenir (tek tanım, sessiz sapma yok)."""
    parent = _frozen_ref(models_dir, params["parent"])
    sec = params.get("path_secondary") or {}
    path_params, path_cell = None, base_cells.get(sec.get("model_id"))
    if path_cell is not None and path_cell["status"] == STATUS_PREDICTED:
        path_params = _frozen_ref(models_dir, sec)
        if pth.predict(path_params, inputs) != path_cell["output"]:
            raise FreezeError(f"{sec['model_id']}: base_record çıktısı bugünkü kodla yeniden üretilemedi (parite)")
    try:
        out = pd1.predict_post_d1(params, parent, inputs, d1, path_params=path_params)
    except pr.PredictError as exc:
        raise FreezeError(f"{params.get('model_id')}: {exc.code}: {exc}") from exc
    status = STATUS_REFUSED if out["refused"] else (STATUS_NOT_APPLICABLE if out["not_applicable"] else STATUS_PREDICTED)
    return {"kind": "post_d1", "status": status, "refusal": out["refused"] or out["not_applicable"], "output": out}


def comparators_conditional(base_cells: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """§7.4: base_record hücrelerinin S kopyası ve S_cond = conditional_weights(S, 1) (Faz 2C ile tek tanım)."""
    out: dict[str, Any] = {}
    for rid in POST_D1_COMPARATORS:
        if rid == "base_always_ceiling":
            S = [1.0] * 10
            cell_sha, source = None, ALWAYS_CEILING_SOURCE
        else:
            cell = base_cells.get(rid)
            cell_sha = canonical_sha256(cell) if cell is not None else None
            S = list(cell["output"]["S"]) if cell is not None and cell["status"] == STATUS_PREDICTED else None
            source = "base_record"
        s_cond = None
        if S is not None:
            try:
                s_cond = {str(k): v for k, v in pth.conditional_weights(S, pd1.CONDITION_J)[0].items()}
            except ValueError:
                s_cond = None           # S_1 = 0: koşul tanımsız (G6)
        out[rid] = {"record_cell_sha256": cell_sha, "S": S, "S_cond": s_cond, "source": source}
    return out


def _d1_features(cells: Sequence[Mapping[str, Any]], d1: Mapping[str, Any], shares_offered: Any) -> dict[str, Any]:
    """§7.4 `d1_features`: iki özellik (tek tanım `predict_post_d1.evaluate_d1`) ve D_1 uyarıları; kırpma ve z ilk tahmin
    veren modelin ön işlemesinden (modele bağlı)."""
    block: dict[str, Any] = {"d1_lock": None, "d1_turnover_ratio": None, "d1_turnover_ln": None, "clipped": None, "z": None,
                             "warnings": []}
    try:
        v = pd1.evaluate_d1(d1, shares_offered)
    except (pd1.D1Refusal, pd1.D1NotApplicable):
        return block
    block.update(d1_lock=v.lock, d1_turnover_ratio=str(v.turnover_ratio), d1_turnover_ln=v.turnover_ln, warnings=list(v.warnings))
    first = next((c for c in cells if c["status"] == STATUS_PREDICTED), None)
    if first is not None:
        f = first["output"]["d1_features"]
        block.update(clipped=f["clipped"], z=f["z"])
        block["warnings"] += [w for w in first["output"]["warnings"] if w.get("code") == pd1.WARN_D1_TURNOVER_CLIPPED]
    return block


def build_post_d1_record(ticker: str, *, now: Optional[datetime] = None, models_dir: Path = MODELS_DIR,
                         records_dir: Path = reg.RECORDS_DIR, bist_dir: Path = oc.BIST_DIR,
                         outcomes_dir: Path = oc.OUTCOMES_DIR, root: Path = ROOT,
                         calendar: Optional["oc.SessionCalendar"] = None,
                         proofs: Optional[Sequence[Mapping[str, Any]]] = None) -> dict[str, Any]:
    """§7.4 kaydı (şema borsai.post_d1_record/1). Girdi belgesi yeniden okunmaz: f1–f3 base_record'un `model_inputs`'u."""
    _, recorded_utc, recorded_ist = _now_pair(now)
    calendar = calendar or oc.load_calendar(bist_dir=bist_dir)
    orow = d1_session(ticker, outcomes_dir)
    d1 = orow["session_date"]
    reg.t_open(d1, calendar)                     # takvim dışı D_1: CALENDAR_NOT_AVAILABLE, kayıt yazılmaz (L6)
    base_path, base, _ = select_base_record(ticker, d1, records_dir=records_dir, root=root, proofs=proofs)
    block = d1_block(ticker, d1, calendar, bist_dir=bist_dir, root=root, outcome_row=orow)
    inputs = base["model_inputs"]
    base_cells = {c["model_id"]: c for c in base["models"]}
    index, index_sha, models = _index_sha_checked(Path(models_dir), INDEX_POST_D1_NAME)
    d1_input = {k: block[k] for k in ("fields_raw", "half_day", "halt_flag")}
    cells = []
    for entry, params, sha in models:
        result = run_post_d1_model(params, Path(models_dir), inputs, d1_input, base_cells)
        cells.append({"model_id": entry["model_id"], "stage": entry["stage"], "file": f"models/{entry['file']}",
                      "params_sha256": sha, "spec_sha256": entry["spec_sha256"], "algorithm": entry["algorithm"], **result})
    state = git_state(root)
    return {
        "schema_version": POST_D1_RECORD_SCHEMA,
        "record_type": RECORD_PREDICTION,
        "record_stage": POST_D1_STAGE,
        "ticker": ticker,
        "recorded_at_utc": recorded_utc,
        "recorded_at_istanbul": recorded_ist,
        "recorded_at_basis": POST_D1_RECORDED_AT_BASIS,
        "code": {"git_head": state["commit"], "borsai_dirty": state["borsai_dirty"],
                 "borsai_source_sha256": source_tree_sha256(root / "borsai")["tree_sha256"]},
        "base_record": {"file": _rel(base_path, root), "sha256": sha256_file(base_path),
                        "model_inputs_sha256": canonical_sha256(inputs), "selected_by": BASE_RECORD_RULE},
        "d1": block,
        "d1_features": _d1_features(cells, d1_input, inputs.get("shares_offered")),
        "models_index": {"path": _rel(Path(models_dir) / INDEX_POST_D1_NAME, root), "sha256": index_sha,
                         "model_ids": [e["model_id"] for e, _, _ in models]},
        "models": cells,
        "comparators_conditional": comparators_conditional(base_cells),
        "summary": {"n_models": len(cells), "n_predicted": sum(c["status"] == STATUS_PREDICTED for c in cells),
                    "n_refused": sum(c["status"] == STATUS_REFUSED for c in cells),
                    "n_not_applicable": sum(c["status"] == STATUS_NOT_APPLICABLE for c in cells)},
    }


def list_post_d1_records(ticker: str, post_dir: Path = reg.POST_D1_DIR) -> list[tuple[Path, dict[str, Any]]]:
    return list_records(ticker, post_dir)


def active_post_d1_records(ticker: str, post_dir: Path = reg.POST_D1_DIR) -> list[tuple[Path, dict[str, Any]]]:
    return active_records(ticker, post_dir)


def write_post_d1_record(ticker: str, *, now: Optional[datetime] = None, post_dir: Path = reg.POST_D1_DIR,
                         **kw: Any) -> Path:
    """Kayıt dosyası ('xb', içerik adresli ad). Etkin bir kayıtla aynı base_record sha + aynı iki bülten sha + aynı
    INDEX_POST_D1 sha -> DUPLICATE_RECORD (§7.4)."""
    record = build_post_d1_record(ticker, now=now, **kw)
    key = lambda r: (r["base_record"]["sha256"], r["d1"]["thb"]["sha256"], r["d1"]["thm"]["sha256"],  # noqa: E731
                     r["models_index"]["sha256"])
    for path, rec in active_post_d1_records(ticker, post_dir):
        if key(rec) == key(record):
            raise DuplicateRecord(f"DUPLICATE_RECORD: {ticker} için aynı base_record, aynı D_1 bültenleri ve aynı POST_D1 model "
                                  f"dizinli etkin kayıt var ({path.name})")
    payload = pretty_json_bytes(record)
    path = Path(post_dir) / ticker / record_filename(payload, record["recorded_at_utc"])
    _write_new(path, payload)
    return path


def cancel_post_d1_record(record_path: Path, reason: str, *, now: Optional[datetime] = None,
                          post_dir: Path = reg.POST_D1_DIR, root: Path = ROOT, bist_dir: Path = oc.BIST_DIR,
                          calendar: Optional["oc.SessionCalendar"] = None) -> Path:
    """POST_D1 iptal kaydı (aynı dizinde). T_open'dan itibaren iptal yapılamaz (§7.4; SPEC_SCORING §6'nın aşama karşılığı)."""
    record_path = Path(record_path)
    if not reason or not reason.strip():
        raise FreezeError("iptal nedeni boş olamaz")
    target = json.loads(record_path.read_text(encoding="utf-8"))
    if target.get("record_type") != RECORD_PREDICTION or target.get("record_stage") != POST_D1_STAGE:
        raise FreezeError("yalnız POST_D1 tahmin kaydı iptal edilebilir")
    ticker = target["ticker"]
    if record_path.name not in {p.name for p, _ in active_post_d1_records(ticker, post_dir)}:
        raise FreezeError(f"{record_path.name} etkin bir POST_D1 kaydı değil (yok ya da zaten iptal)")
    now_utc, recorded_utc, recorded_ist = _now_pair(now)
    calendar = calendar or oc.load_calendar(bist_dir=bist_dir)
    t_open_at = reg.t_open(target["d1"]["session_date"], calendar)
    if not now_utc < t_open_at:
        raise FreezeError(f"POST_D1 iptali T_open'dan ({t_open_at.isoformat()}) itibaren yapılamaz (SPEC_POST_D1_V0 §7.4)")
    cancellation = {
        "schema_version": POST_D1_RECORD_SCHEMA,
        "record_type": RECORD_CANCELLATION,
        "record_stage": POST_D1_STAGE,
        "ticker": ticker,
        "recorded_at_utc": recorded_utc,
        "recorded_at_istanbul": recorded_ist,
        "recorded_at_basis": POST_D1_RECORDED_AT_BASIS,
        "code": {k: v for k, v in _code_block(root).items() if k != "borsai_files_sha256"},
        "cancels": {"file": record_path.name, "sha256": sha256_file(record_path)},
        "reason": reason.strip(),
    }
    payload = pretty_json_bytes(cancellation)
    path = Path(post_dir) / ticker / record_filename(payload, recorded_utc)
    _write_new(path, payload)
    return path


# ============================================================ (4) eski kohort (Faz 6; SPEC_OOT_PRE_H99_V0 §5; KARARLAR D6)
#
# registry/oot/cohort_pre_h99.csv'nin her MEMBER satırı için tek toplu koşu -> registry/oot/records/<T>/<UTC>_<sha>.json
# (şema borsai.oot_record/1; registry/records/ DEĞİL). models/INDEX.json'daki bütün modeller (ret hücreleri dahil); rejim
# yüzünden uygulanamayan hücre NOT_APPLICABLE_REGIME + neden (şartname §7; `registry.regime_not_applicable`). Kural değerleri
# (karşılaştırıcılar) H99'da donmuş değerlerdir; last10 kuralları kronolojik değildir (comparator_note). f6: Takvim C,
# ref_date = first_trading_date (SPEC_MARKET20_V0 §4-e). Ön koşul: kohort dosyası, girdiler, kaynak belgeler ve modeller
# commit'li (temiz ağaç). Sınıf (OOT_BLIND / OOT_RETRO) kayda yazılmaz; `scoring.class_oot` hesaplar.
# Faz 7 (INDEX'te v1 varken): `tufe` bloğu ve model_inputs tufe_index (canlıyla aynı yol) ve model_inputs["alloc_regime"] =
# kohort satırının ALLOC_REGIME etiketi (J2, J6); rejimli model varken anahtar yoksa kayıt kurulmaz (B7).
# Ek kayıt (`--oot <kohort> --only-missing-models`; SPEC_HAZARD_V1 §7.1-3, SPEC_C_V0 §7.1-3; SPEC_DEVIATIONS L): üye başına
# yalnız o üyenin hiçbir etkin kaydında bulunmayan INDEX modellerini içeren kayıt (`record_scope = ONLY_MISSING_MODELS`,
# `delta_of` = üyenin ilk etkin kaydının dosya adı); girdiler, kohort satırı, f6 bloğu ve model_inputs ilk kayıtla bayt-eşit
# olmalıdır (değilse DUR: FreezeError), yalnız v1/(C) girdileri (`tufe_index`, `tufe_refusal`, `alloc_regime`) eklenir. Hijyen
# (görev kuralı: hangi kodun kasada olduğu hiçbir dosyaya yazılmaz): ek kayıt `vault` alanını ve kohort satırının `vault` sütununu
# TAŞIMAZ (ilk kayıt ve kohort dosyası taşır; skorlama kasa ayrımını kohort dosyasından okur). Tam üyede kayıt yazılmaz (yeniden
# koşu güvenli). Birincil kayıt kuralı (eski kohort): (model, üye) için o modeli içeren EN ERKEN etkin kayıt
# (`oot_primary_record`; SPEC_HAZARD_V1 §7.3); skorlama ve indirme kapısı aynı fonksiyonu çağırır.

OOT_RECORD_SCHEMA = "borsai.oot_record/1"
OOT_STAGE = "OOT_PRE_LISTING"
OOT_POST_D1_RECORD_SCHEMA = "borsai.oot_post_d1_record/1"
OOT_POST_D1_STAGE = "OOT_POST_D1"
STATUS_NOT_APPLICABLE_REGIME = "NOT_APPLICABLE_REGIME"
OOT_RECORDED_AT_BASIS = ("LOCAL_CLOCK_SELF_REPORTED: zaman kanıtı bu kaydı içeren commit'in push kanıtıdır; kayıt, kohortun "
                         "sonucu repoya girmeden push edilir (KARARLAR D3, D6)")
OOT_COMPARATOR_RULES = ("base_train_median", "base_train_mean", "base_zero", "base_always_ceiling", "base_rate",
                        "base_last10_rate", "base_km_expanding", "base_km_last10")
OOT_LAST10_RULES = ("base_last10_rate", "base_km_last10")
COMPARATOR_NOTE_LAST10 = "FROZEN_H99_LAST10_NOT_CHRONOLOGICAL"
COMPARATOR_NOTE_FROZEN = "FROZEN_H99"
OOT_GUARDED_PATHS = ("registry/oot/cohort_pre_h99.csv", "registry/oot/inputs", "registry/oot/source_docs", "models")
EXPOSURE_MACHINE_SEQUENCED = "MACHINE_SEQUENCED"


class OotPreconditionError(FreezeError):
    """Kohort dosyası, girdiler, kaynak belgeler ya da modeller commit'li değil / kohort doğrulayıcıdan geçmiyor."""


def _git_out(root: Path, *args: str) -> str:
    import subprocess

    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout


def oot_precondition_problems(root: Path, input_rels: Sequence[str]) -> list[str]:
    """Temiz ağaç: kohort dosyası ve verilen girdi dosyaları izleniyor; kohort, girdi, kaynak belge ve model yollarında
    commit'lenmemiş değişiklik ya da izlenmeyen dosya yok."""
    tracked = set(_git_out(root, "ls-files", "--", *OOT_GUARDED_PATHS).splitlines())
    out = [f"commit'li değil: {p}" for p in [OOT_GUARDED_PATHS[0], *input_rels] if p not in tracked]
    dirty = _git_out(root, "status", "--porcelain", "--untracked-files=all", "--", *OOT_GUARDED_PATHS).strip()
    if dirty:
        out.append(f"temiz değil: {dirty[:300]}")
    return out


def _oot_cell(entry: Mapping[str, Any], params: Mapping[str, Any], sha: str, inputs: Mapping[str, Any],
              na: Optional[Mapping[str, str]]) -> dict[str, Any]:
    result = run_model(params, inputs)
    if result["status"] == STATUS_ERROR:
        raise FreezeError(f"{entry['model_id']}: {result['refusal']['reason']}")
    cell = {"model_id": entry["model_id"], "file": f"models/{entry['file']}", "params_sha256": sha,
            "spec_sha256": entry["spec_sha256"], "algorithm": entry["algorithm"], **result, "not_applicable": None}
    if na is not None:     # şartname §7: o arzda uygulanamaz; modelin kendi durumu ve çıktısı görünür kalır
        cell.update(status=STATUS_NOT_APPLICABLE_REGIME, not_applicable=dict(na), model_status=result["status"])
    return cell


def build_oot_record(row: Mapping[str, str], *, cohort_sha256: str, inputs_path: Path, now: Optional[datetime] = None,
                     models_dir: Path = MODELS_DIR, root: Path = ROOT, code_root: Path = ROOT,
                     m20_sources: Optional[tuple[Any, Any, Any]] = None,
                     index_models: Optional[tuple[dict[str, Any], str, list[tuple[dict[str, Any], dict[str, Any], str]]]] = None
                     ) -> dict[str, Any]:
    """Bir MEMBER satırı için §5 kaydı (yazmaz). `root`: kohort ve girdilerin (ve belge sha denetiminin) kökü; `code_root`:
    `code` bloğunun git/borsai kökü."""
    doc, raw = reg.load_inputs(inputs_path)
    _, recorded_utc, recorded_ist = _now_pair(now)
    t = row["ticker"]
    if doc.get("ticker") != t or doc["fields"]["first_trading_date"]["value"] != row["first_trading_date"]:
        raise FreezeError(f"{t}: girdi belgesi kohort satırıyla aynı arz değil (ticker/first_trading_date)")
    problems = reg.inputs_pit_problems(doc, root=root, as_of=recorded_ist)
    if problems:
        raise FreezeError(f"{t}: girdi belgesi geçmedi: " + "; ".join(problems))
    tags = reg.parse_regime_tags(row["regime_tags"])
    res = m20.oot_market20(row["first_trading_date"], m20_sources)
    m20_block = {**res.as_record(), "ref_date_rule": "OOT_FIRST_TRADING_DATE_SPEC_MARKET20_V0_4E", "calendar": "C",
                 "calendar_file": _rel(m20.CALENDAR_C_PATH, ROOT), "xu100_file": _rel(m20.XU100_PINNED[-1][0], ROOT)}
    inputs = reg.model_inputs(doc)
    inputs["f6_market20"] = m20_block["f6"]
    inputs["f6_market20_refusal"] = m20_block["refusal"]
    index, index_sha, models = index_models or _index_models(Path(models_dir))
    try:
        tufe_block = v1_record_inputs(OOT_STAGE, row["first_trading_date"], models, inputs, alloc_regime=tags["ALLOC_REGIME"])
    except FreezeError as exc:
        raise FreezeError(f"{t}: {exc}") from exc
    na = reg.regime_not_applicable(tags)
    cells = [_oot_cell(e, p, sha, inputs, na.get(e["model_id"])) for e, p, sha in models]
    by_id = {c["model_id"]: c for c in cells}
    comparators = {rid: {"params_sha256": by_id[rid]["params_sha256"], "status": by_id[rid]["status"],
                         "output": by_id[rid]["output"], "not_applicable": by_id[rid]["not_applicable"],
                         "comparator_note": COMPARATOR_NOTE_LAST10 if rid in OOT_LAST10_RULES else COMPARATOR_NOTE_FROZEN}
                   for rid in OOT_COMPARATOR_RULES if rid in by_id}
    state = git_state(code_root)
    record = {
        "schema_version": OOT_RECORD_SCHEMA,
        "record_type": RECORD_PREDICTION,
        "record_stage": OOT_STAGE,
        "scale": reg.OOT_SCALE,
        "ticker": t,
        "first_trading_date": row["first_trading_date"],
        "recorded_at_utc": recorded_utc,
        "recorded_at_istanbul": recorded_ist,
        "recorded_at_basis": OOT_RECORDED_AT_BASIS,
        "code": {"git_head": state["commit"], "borsai_dirty": state["borsai_dirty"],
                 "borsai_source_sha256": source_tree_sha256(Path(code_root) / "borsai")["tree_sha256"]},
        "cohort_file_sha256": cohort_sha256,
        "cohort_row": dict(row),
        "vault": row["vault"],
        "regime_tags": tags,
        "inputs_sha256": sha256_bytes(raw),
        "inputs": {"path": _rel(inputs_path, root), "sha256": sha256_bytes(raw)},
        "model_inputs": inputs,
        "market20": m20_block,
        "models_index": {"path": "models/INDEX.json", "sha256": index_sha, "model_ids": [e["model_id"] for e, _, _ in models]},
        "models": cells,
        "comparators": comparators,
        "summary": {"n_models": len(cells),
                    "n_predicted": sum(c["status"] == STATUS_PREDICTED for c in cells),
                    "n_refused": sum(c["status"] == STATUS_REFUSED for c in cells),
                    "n_not_applicable_regime": sum(c["status"] == STATUS_NOT_APPLICABLE_REGIME for c in cells),
                    "refusals": {c["model_id"]: c["refusal"]["code"] for c in cells if c["status"] == STATUS_REFUSED},
                    "not_applicable": {c["model_id"]: c["not_applicable"]["code"] for c in cells
                                       if c["status"] == STATUS_NOT_APPLICABLE_REGIME}},
    }
    if tufe_block is not None:
        record["tufe"] = tufe_block
    return record


def active_oot_records(ticker: str, records_dir: Path = reg.OOT_RECORDS_DIR) -> list[tuple[Path, dict[str, Any]]]:
    return active_records(ticker, records_dir)


def build_oot_records(cohort_path: Path = reg.COHORT_PATH, *, now: Optional[datetime] = None,
                      records_dir: Path = reg.OOT_RECORDS_DIR, models_dir: Path = MODELS_DIR, root: Path = ROOT,
                      code_root: Path = ROOT, require_clean: bool = True) -> dict[str, Any]:
    """Toplu koşunun bellekteki sonucu (yazmaz): {"records": [(ticker, kayıt)], "skipped": [...], "duplicates": [...]}.
    Bir üyede hata varsa hiçbiri yazılmaz (FreezeError). Girdi dosyası olmayan üye kayıtsızdır (SKIPPED:
    INPUTS_NOT_AVAILABLE, §1); aynı girdi sha'lı, aynı model dizinli ve aynı kohort satırlı etkin kaydı olan üye yinelenmez."""
    cohort_path = Path(cohort_path)
    header, rows = reg.read_cohort(cohort_path)
    problems = reg.validate_cohort(header, rows)
    if problems:
        raise OotPreconditionError("kohort dosyası geçmedi: " + "; ".join(problems[:5]))
    members = reg.cohort_members(rows)
    inputs_dir = cohort_path.parent / "inputs"
    rels = [_rel(inputs_dir / f"{r['ticker']}.json", root) for r in members if (inputs_dir / f"{r['ticker']}.json").exists()]
    if require_clean:
        problems = oot_precondition_problems(Path(root), rels)
        if problems:
            raise OotPreconditionError("ön koşul (temiz ağaç) tutmuyor: " + "; ".join(problems[:5]))
    cohort_sha = sha256_file(cohort_path)
    sources = m20.load_oot_sources()
    index_models = _index_models(Path(models_dir))
    out: dict[str, Any] = {"records": [], "skipped": [], "duplicates": [], "cohort_file_sha256": cohort_sha}
    for r in members:
        p = inputs_dir / f"{r['ticker']}.json"
        if not p.exists():
            out["skipped"].append({"ticker": r["ticker"], "status": "SKIPPED", "skip_reason": "INPUTS_NOT_AVAILABLE"})
            continue
        rec = build_oot_record(r, cohort_sha256=cohort_sha, inputs_path=p, now=now, models_dir=models_dir, root=root,
                               code_root=code_root, m20_sources=sources, index_models=index_models)
        key = (rec["inputs_sha256"], rec["models_index"]["sha256"], canonical_sha256(rec["cohort_row"]))
        if any((a["inputs_sha256"], a["models_index"]["sha256"], canonical_sha256(a["cohort_row"])) == key
               for _, a in active_oot_records(r["ticker"], records_dir)):
            out["duplicates"].append(r["ticker"])
            continue
        out["records"].append((r["ticker"], rec))
    return out


def write_oot_records(cohort_path: Path = reg.COHORT_PATH, *, now: Optional[datetime] = None,
                      records_dir: Path = reg.OOT_RECORDS_DIR, **kw: Any) -> dict[str, Any]:
    """§5 tek toplu koşu: önce bütün kayıtlar bellekte kurulur, sonra her biri 'xb' ile yazılır (içerik adresli ad)."""
    built = build_oot_records(cohort_path, now=now, records_dir=records_dir, **kw)
    paths = []
    for ticker, rec in built["records"]:
        payload = pretty_json_bytes(rec)
        path = Path(records_dir) / ticker / record_filename(payload, rec["recorded_at_utc"])
        _write_new(path, payload)
        paths.append(str(path))
    return {"written": paths, "skipped": built["skipped"], "duplicates": built["duplicates"],
            "cohort_file_sha256": built["cohort_file_sha256"]}


def oot_outcome_present(ticker: str, root: Path = ROOT) -> list[str]:
    """Arzın eski kohort sonucu (ya da D_1 satırı) repoda mı: iptal ancak sonuçtan önce (SPEC_SCORING §6'nın karşılığı)."""
    paths = [f"data/outcomes_oot/{ticker}.csv", f"data/outcomes_oot/raw/{ticker}.json", f"registry/oot/d1_rows/{ticker}.json"]
    return [p for p in paths if (Path(root) / p).exists()]


def cancel_oot_record(record_path: Path, reason: str, *, now: Optional[datetime] = None,
                      records_dir: Path = reg.OOT_RECORDS_DIR, root: Path = ROOT) -> Path:
    """Eski kohort iptal kaydı (aynı dizinde); iptal edilen dosya değişmez. Arzın D_1 satırı ya da sonucu repoya girdiyse
    iptal yapılamaz."""
    record_path = Path(record_path)
    if not reason or not reason.strip():
        raise FreezeError("iptal nedeni boş olamaz")
    target = json.loads(record_path.read_text(encoding="utf-8"))
    if target.get("record_type") != RECORD_PREDICTION or target.get("record_stage") != OOT_STAGE:
        raise FreezeError("yalnız eski kohort tahmin kaydı iptal edilebilir")
    ticker = target["ticker"]
    if record_path.name not in {p.name for p, _ in active_oot_records(ticker, records_dir)}:
        raise FreezeError(f"{record_path.name} etkin bir kayıt değil (yok ya da zaten iptal)")
    present = oot_outcome_present(ticker, root)
    if present:
        raise FreezeError(f"{ticker}: sonuç ya da D_1 satırı repoda ({present}); iptal yapılamaz")
    _, recorded_utc, recorded_ist = _now_pair(now)
    cancellation = {"schema_version": OOT_RECORD_SCHEMA, "record_type": RECORD_CANCELLATION, "record_stage": OOT_STAGE,
                    "scale": reg.OOT_SCALE, "ticker": ticker, "recorded_at_utc": recorded_utc,
                    "recorded_at_istanbul": recorded_ist, "recorded_at_basis": OOT_RECORDED_AT_BASIS,
                    "cancels": {"file": record_path.name, "sha256": sha256_file(record_path)}, "reason": reason.strip()}
    payload = pretty_json_bytes(cancellation)
    path = Path(records_dir) / ticker / record_filename(payload, recorded_utc)
    _write_new(path, payload)
    return path


def oot_base_record(ticker: str, records_dir: Path = reg.OOT_RECORDS_DIR) -> tuple[Path, dict[str, Any]]:
    """Eski kohort birincil kaydı: en erken etkin kayıt (toplu koşu tek kayıt yazar; sonradan eklenen üye kendi koşusunda).
    Sonuç görülmeden, önceden ilan (SPEC_DEVIATIONS I12)."""
    recs = active_oot_records(ticker, records_dir)
    if not recs:
        raise NoBaseRecord(f"{SKIPPED_NO_PRE_LISTING_RECORD}: {ticker} için eski kohort kaydı yok")
    return min(recs, key=lambda x: (x[1]["recorded_at_utc"], x[0].name))


def oot_primary_of(recs: Sequence[tuple[Path, Mapping[str, Any]]], model_id: str) -> Optional[tuple[Path, Mapping[str, Any]]]:
    """SPEC_HAZARD_V1 §7.3 (SPEC_DEVIATIONS L): (model, üye) için birincil kayıt = o modeli içeren EN ERKEN etkin kayıt (sıra
    `oot_base_record` ile aynı: recorded_at_utc, dosya adı). `recs`: üyenin etkin kayıtları. Modeli içeren kayıt yoksa None. Eski 19
    model için bu, S2 kaydıdır (I12 ile aynı seçim)."""
    have = [(p, r) for p, r in recs if any(c["model_id"] == model_id for c in r["models"])]
    return min(have, key=lambda x: (x[1]["recorded_at_utc"], x[0].name)) if have else None


def oot_primary_record(ticker: str, model_id: str, records_dir: Path = reg.OOT_RECORDS_DIR
                       ) -> Optional[tuple[Path, Mapping[str, Any]]]:
    return oot_primary_of(active_oot_records(ticker, records_dir), model_id)


# Ek kaydın ilk kayda eklediği model_inputs anahtarları (v1 ve (C) girdileri; J26, K16). Başka her anahtar ilk kayıtla bayt-eşittir.
OOT_DELTA_INPUT_KEYS = frozenset({"tufe_index", "tufe_refusal", "alloc_regime"})
OOT_DELTA_SCOPE = "ONLY_MISSING_MODELS"
# Ek kayıtla ilk kaydın aynı olması gereken bloklar (girdiler ve listeleme öncesi bağlam; SPEC_HAZARD_V1 §7.1-3 "bayt-eşit").
# `cohort_row` `vault` sütunu dışında karşılaştırılır: ek kayıt kasa ayrımını yazmaz (OOT_DELTA_OMITTED; SPEC_DEVIATIONS L3).
OOT_DELTA_SAME_KEYS = ("ticker", "first_trading_date", "record_stage", "scale", "cohort_row", "regime_tags", "inputs_sha256",
                       "inputs", "market20")
OOT_DELTA_OMITTED = "vault"


def _sans_vault(x: Any) -> Any:
    return {k: v for k, v in x.items() if k != OOT_DELTA_OMITTED} if isinstance(x, Mapping) else x


def oot_delta_problems(first: Mapping[str, Any], delta: Mapping[str, Any]) -> list[str]:
    """Ek kaydın girdileri ilk kayıtla bayt-eşit mi: `OOT_DELTA_SAME_KEYS` blokları kanonik JSON olarak aynı (`cohort_row` `vault`
    sütunu dışında); ek kayıt `vault` alanı ya da kohort satırında `vault` sütunu taşımaz; model_inputs'un ilk kayıttaki her anahtarı
    aynı değer, yeni anahtarlar yalnız `OOT_DELTA_INPUT_KEYS` ve ilk kaydın model_inputs'u, ek kaydınkinden yeni anahtarlar çıkarılınca
    bayt-eşit (`pretty_json_bytes`). Boş liste = aynı. İleti yalnız alan adı taşır."""
    norm = lambda rec, k: _sans_vault(rec.get(k)) if k == "cohort_row" else rec.get(k)  # noqa: E731
    out = [f"{k} ilk kayıttan farklı" for k in OOT_DELTA_SAME_KEYS
           if pretty_json_bytes(norm(first, k)) != pretty_json_bytes(norm(delta, k))]
    if OOT_DELTA_OMITTED in delta or OOT_DELTA_OMITTED in (delta.get("cohort_row") or {}):
        out.append("ek kayıt kasa alanını (vault) taşıyor")
    a, b = first["model_inputs"], delta["model_inputs"]
    extra = sorted(set(b) - set(a))
    out += [f"model_inputs'ta beklenmeyen yeni anahtar {k}" for k in extra if k not in OOT_DELTA_INPUT_KEYS]
    out += [f"model_inputs'ta ilk kayıttaki {k} yok" for k in sorted(set(a) - set(b))]
    if pretty_json_bytes({k: v for k, v in b.items() if k in a}) != pretty_json_bytes(a):
        out.append("model_inputs ilk kayıtla bayt-eşit değil")
    return out


def build_oot_delta_records(cohort_path: Path = reg.COHORT_PATH, *, now: Optional[datetime] = None,
                            records_dir: Path = reg.OOT_RECORDS_DIR, models_dir: Path = MODELS_DIR, root: Path = ROOT,
                            code_root: Path = ROOT, require_clean: bool = True) -> dict[str, Any]:
    """`--oot --only-missing-models` toplu koşusunun bellekteki sonucu (yazmaz): {"records": [(ticker, kayıt)], "complete",
    "skipped", "cohort_file_sha256"}. Ön koşullar `build_oot_records` ile aynı (kohort doğrulayıcı, temiz ağaç). Üye başına: etkin
    kaydı yoksa SKIPPED (NO_BASE_RECORD: ilk kayıt `--oot` ile yazılır); INDEX'in bütün modelleri etkin kayıtlarında varsa
    `complete` (kayıt yazılmaz); yoksa yalnız eksik modellerle `build_oot_record` (aynı üretici; kasa üyeleri için de yalnız listeleme
    öncesi girdiler) + `record_scope`, `delta_of`, `delta_of_sha256`; `models_index.model_ids` bütün INDEX'tir, kaydın modelleri
    `models` hücreleridir; `vault` alanı ve kohort satırının `vault` sütunu yazılmaz (hijyen). Girdiler ilk kayıtla bayt-eşit değilse
    hiçbiri yazılmaz (FreezeError, DUR)."""
    cohort_path = Path(cohort_path)
    header, rows = reg.read_cohort(cohort_path)
    problems = reg.validate_cohort(header, rows)
    if problems:
        raise OotPreconditionError("kohort dosyası geçmedi: " + "; ".join(problems[:5]))
    members = reg.cohort_members(rows)
    inputs_dir = cohort_path.parent / "inputs"
    rels = [_rel(inputs_dir / f"{r['ticker']}.json", root) for r in members if (inputs_dir / f"{r['ticker']}.json").exists()]
    if require_clean:
        problems = oot_precondition_problems(Path(root), rels)
        if problems:
            raise OotPreconditionError("ön koşul (temiz ağaç) tutmuyor: " + "; ".join(problems[:5]))
    cohort_sha = sha256_file(cohort_path)
    sources = m20.load_oot_sources()
    index, index_sha, models = _index_models(Path(models_dir))
    index_ids = [e["model_id"] for e, _, _ in models]
    out: dict[str, Any] = {"records": [], "complete": [], "skipped": [], "cohort_file_sha256": cohort_sha}
    for r in members:
        t = r["ticker"]
        p = inputs_dir / f"{t}.json"
        if not p.exists():
            out["skipped"].append({"ticker": t, "status": "SKIPPED", "skip_reason": "INPUTS_NOT_AVAILABLE"})
            continue
        active = active_oot_records(t, records_dir)
        if not active:
            out["skipped"].append({"ticker": t, "status": "SKIPPED", "skip_reason": "NO_BASE_RECORD"})
            continue
        have = {c["model_id"] for _, rec in active for c in rec["models"]}
        missing = [x for x in models if x[0]["model_id"] not in have]
        if not missing:
            out["complete"].append(t)
            continue
        first_path, first = min(active, key=lambda x: (x[1]["recorded_at_utc"], x[0].name))
        rec = build_oot_record(r, cohort_sha256=cohort_sha, inputs_path=p, now=now, models_dir=models_dir, root=root,
                               code_root=code_root, m20_sources=sources, index_models=(index, index_sha, missing))
        rec["models_index"]["model_ids"] = index_ids
        rec.pop(OOT_DELTA_OMITTED)                       # hijyen: kasa ayrımı ek kayda yazılmaz (ilk kayıt ve kohort dosyası taşır)
        rec["cohort_row"] = _sans_vault(rec["cohort_row"])
        rec.update(record_scope=OOT_DELTA_SCOPE, delta_of=first_path.name, delta_of_sha256=sha256_file(first_path))
        bad = oot_delta_problems(first, rec)
        if bad:
            raise FreezeError(f"{t}: ek kaydın girdileri ilk kayıtla ({first_path.name}) aynı değil: " + "; ".join(bad))
        out["records"].append((t, rec))
    return out


def write_oot_delta_records(cohort_path: Path = reg.COHORT_PATH, *, now: Optional[datetime] = None,
                            records_dir: Path = reg.OOT_RECORDS_DIR, **kw: Any) -> dict[str, Any]:
    """Tek toplu koşu: önce bütün ek kayıtlar bellekte kurulur ve denetlenir, sonra her biri 'xb' ile yazılır (içerik adresli ad).
    Dönen değer yalnız sayılar ve yollardır; CLI yalnız sayıları basar (kasa kodu hiçbir çıktıya yazılmaz)."""
    built = build_oot_delta_records(cohort_path, now=now, records_dir=records_dir, **kw)
    paths = []
    for ticker, rec in built["records"]:
        payload = pretty_json_bytes(rec)
        path = Path(records_dir) / ticker / record_filename(payload, rec["recorded_at_utc"])
        _write_new(path, payload)
        paths.append(str(path))
    return {"written": paths, "complete": built["complete"], "skipped": built["skipped"],
            "cohort_file_sha256": built["cohort_file_sha256"]}


def delta_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    """`--only-missing-models` CLI çıktısı: yalnız sayılar (hijyen: kod yok)."""
    reasons: dict[str, int] = {}
    for s in result["skipped"]:
        reasons[s["skip_reason"]] = reasons.get(s["skip_reason"], 0) + 1
    return {"written": len(result["written"]), "complete": len(result["complete"]), "skipped": len(result["skipped"]),
            "skip_reasons": reasons, "cohort_file_sha256": result["cohort_file_sha256"]}


def build_oot_post_d1_record(ticker: str, d1_doc: Mapping[str, Any], *, now: Optional[datetime] = None,
                             models_dir: Path = MODELS_DIR, records_dir: Path = reg.OOT_RECORDS_DIR, root: Path = ROOT,
                             code_root: Path = ROOT) -> dict[str, Any]:
    """S3 (şartname §2; KARARLAR D5): registry/oot/d1_rows/<T>.json'daki D_1 satırı + eski kohort S2 kaydı (ceiling_hazard_v0
    hücresi ve model_inputs) -> models/INDEX_POST_D1.json'daki her modelin çıktısı. Canlı POST_D1 kaydıyla aynı üretici
    (`run_post_d1_model`, `comparators_conditional`); `exposure_class = MACHINE_SEQUENCED` (makine bütün zip'i gördü, insan
    görmedi)."""
    _, recorded_utc, recorded_ist = _now_pair(now)
    d1 = d1_doc["d1"]
    if d1_doc.get("ticker") != ticker or d1.get("session_h") != 1:
        raise FreezeError(f"{ticker}: D_1 satırı dosyası bu arzın D_1'i değil")
    base_path, base = oot_base_record(ticker, records_dir)
    inputs = base["model_inputs"]
    base_cells = {c["model_id"]: c for c in base["models"] if c["status"] != STATUS_NOT_APPLICABLE_REGIME}
    index, index_sha, models = _index_sha_checked(Path(models_dir), INDEX_POST_D1_NAME)
    d1_input = {k: d1[k] for k in ("fields_raw", "half_day", "halt_flag")}
    cells = []
    for entry, params, sha in models:
        result = run_post_d1_model(params, Path(models_dir), inputs, d1_input, base_cells)
        cells.append({"model_id": entry["model_id"], "stage": entry["stage"], "file": f"models/{entry['file']}",
                      "params_sha256": sha, "spec_sha256": entry["spec_sha256"], "algorithm": entry["algorithm"], **result})
    state = git_state(code_root)
    return {
        "schema_version": OOT_POST_D1_RECORD_SCHEMA,
        "record_type": RECORD_PREDICTION,
        "record_stage": OOT_POST_D1_STAGE,
        "scale": reg.OOT_SCALE,
        "exposure_class": EXPOSURE_MACHINE_SEQUENCED,
        "ticker": ticker,
        "recorded_at_utc": recorded_utc,
        "recorded_at_istanbul": recorded_ist,
        "recorded_at_basis": OOT_RECORDED_AT_BASIS,
        "code": {"git_head": state["commit"], "borsai_dirty": state["borsai_dirty"],
                 "borsai_source_sha256": source_tree_sha256(Path(code_root) / "borsai")["tree_sha256"]},
        "base_record": {"file": _rel(base_path, root), "sha256": sha256_file(base_path),
                        "model_inputs_sha256": canonical_sha256(inputs), "selected_by": "OOT_EARLIEST_ACTIVE_RECORD"},
        "d1_rows": {"file": f"registry/oot/d1_rows/{ticker}.json", "sha256": canonical_sha256(d1_doc)},
        "d1": dict(d1),
        "d1_features": _d1_features(cells, d1_input, inputs.get("shares_offered")),
        "models_index": {"path": f"models/{INDEX_POST_D1_NAME}", "sha256": index_sha,
                         "model_ids": [e["model_id"] for e, _, _ in models]},
        "models": cells,
        "comparators_conditional": comparators_conditional(base_cells),
        "summary": {"n_models": len(cells), "n_predicted": sum(c["status"] == STATUS_PREDICTED for c in cells),
                    "n_refused": sum(c["status"] == STATUS_REFUSED for c in cells),
                    "n_not_applicable": sum(c["status"] == STATUS_NOT_APPLICABLE for c in cells)},
    }


def write_oot_post_d1_record(ticker: str, *, now: Optional[datetime] = None, post_dir: Path = reg.OOT_POST_D1_DIR,
                             d1_rows_dir: Path = reg.OOT_D1_ROWS_DIR, **kw: Any) -> Path:
    d1_doc = json.loads((Path(d1_rows_dir) / f"{ticker}.json").read_text(encoding="utf-8"))
    record = build_oot_post_d1_record(ticker, d1_doc, now=now, **kw)
    key = lambda r: (r["base_record"]["sha256"], r["d1"]["thb"]["sha256"], r["d1"]["thm"]["sha256"],  # noqa: E731
                     r["models_index"]["sha256"])
    for path, rec in active_records(ticker, post_dir):
        if key(rec) == key(record):
            raise DuplicateRecord(f"DUPLICATE_RECORD: {ticker} için aynı eski kohort POST_D1 kaydı var ({path.name})")
    payload = pretty_json_bytes(record)
    path = Path(post_dir) / ticker / record_filename(payload, record["recorded_at_utc"])
    _write_new(path, payload)
    return path


# ============================================================ (5) POST_BREAK makine kaydı (SPEC_BREAK_V0 §9.2, §11; K-LB-2, K-LB-3)
#
# Kayıt skorlama anında yazılır (`python -m borsai.scoring --break`, adım i); girdiler yalnız D_1..D_b'nin sha-pinli resmi bültenleri
# (data/raw/bist/ + MANIFEST; tarih kuralıyla seçilir), data/outcomes/<T>.csv (seans tarihleri, tavan etiketleri, half_day, halt_flag;
# satırlar pinli bültenle denetlenir) ve registry/inputs/<T>.json (shares_offered, ipo_price_tl). İnsan değer girmez; sınıf kayda
# yazılmaz (`scoring` hesaplar). Kayıt b ∈ 1..9 için yazılır; değilse etiketli `BreakNotAvailable` (§11 "kayıt yazılmaz" kodları).
# Mükerrer yok (K-LB-3): INDEX_POST_BREAK sha'sı, D_1..D_b bülten sha'ları ve girdi dosyası sha'sı aynı bir kayıt varsa yeni kayıt
# yazılmaz (DUPLICATE_RECORD); kod değişince de yazılmaz, parite skorlamada bellekte denetlenir.

POST_BREAK_RECORD_SCHEMA = reg.POST_BREAK_RECORD_SCHEMA
RECORD_MACHINE = reg.POST_BREAK_RECORD_TYPE
POST_BREAK_STAGE = reg.POST_BREAK_STAGE
# §5.1: ürün karşılaştırıcısı arzın birincil listeleme öncesi kaydındaki tavan yolu çıktısından (ceiling_path_v0, yoksa @INF)
POST_BREAK_PRODUCT_SOURCES = ("ceiling_path_v0", "ceiling_path_v0@INF")
PRODUCT_NOT_AVAILABLE = "NOT_AVAILABLE"
# Seri durumu (sonuç dosyasından) ve kayıt yazılmayan hâller (§9.3 payda sırası; §11)
BREAK_STATE = "BREAK"                                         # b = L + 1 ∈ 1..9: kırılma akşamı var
STREAK_PENDING = "STREAK_PENDING"                             # h = L + 1 seansı henüz yok
STREAK_TARGET_UNAVAILABLE = "STREAK_TARGET_UNAVAILABLE"       # seri bozulmadan 15 seans sınırı doldu (SPEC_DEVIATIONS N)
NOT_SCORABLE_STREAK_NA = "NOT_SCORABLE_STREAK_NA"             # bozulmadan önce bir seansta üst limit NA: L belirsiz
NOT_APPLICABLE_NO_BREAK = "NOT_APPLICABLE_NO_BREAK"           # L = 10
NOT_APPLICABLE_B10 = "NOT_APPLICABLE_B10"                     # b = 10
BULLETIN_NOT_PINNED = "BULLETIN_NOT_PINNED"                   # D_1..D_b bülteni yerelde / MANIFEST'te yok
INPUTS_NOT_AVAILABLE = "INPUTS_NOT_AVAILABLE"                 # registry/inputs/<T>.json yok
POST_BREAK_RECORD_KEYS = frozenset({"schema_version", "record_type", "record_stage", "exposure_class", "ticker", "produced_at_utc",
                                    "code", "inputs_ref", "streak", "break_day", "features", "models_index", "models", "comparators",
                                    "structural_zero_D10", "t_open", "summary"})


class BreakNotAvailable(FreezeError):
    """Makine kaydı yazılmaz (§11): `code` ∈ {STREAK_PENDING, STREAK_TARGET_UNAVAILABLE, NOT_SCORABLE_STREAK_NA, NOT_APPLICABLE_NO_BREAK,
    NOT_APPLICABLE_B10, BULLETIN_NOT_PINNED, INPUTS_NOT_AVAILABLE, CALENDAR_NOT_AVAILABLE}; skorlamada payda satırının durumu."""

    def __init__(self, code: str, reason: str) -> None:
        self.code = code
        super().__init__(f"{code}: {reason}")


def break_streak(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    """Sonuç dosyasının h = 1..10 satırlarından seri durumu (SPEC_BREAK_V0 §1.2; tavan etiketi SPEC_SCORING §3, `ceiling_close`):
    {"state", "L", "b"}. BREAK (b = L + 1 ∈ 1..9) | NOT_APPLICABLE_B10 (b = 10) | NOT_APPLICABLE_NO_BREAK (L = 10) |
    NOT_SCORABLE_STREAK_NA (bozulmadan önce etiket NA) | STREAK_PENDING (h = L + 1 satırı PENDING ya da dosya yok) |
    STREAK_TARGET_UNAVAILABLE (h = L + 1 satırı TARGET_UNAVAILABLE)."""
    L = 0
    for r in list(rows)[:oc.N_SESSIONS]:
        if r["status"] == oc.STATUS_TARGET_UNAVAILABLE:
            return {"state": STREAK_TARGET_UNAVAILABLE, "L": None, "b": None}
        if r["status"] not in (oc.STATUS_OK, oc.STATUS_NA_LIMIT):
            return {"state": STREAK_PENDING, "L": None, "b": None}
        if r["ceiling_close"] not in ("0", "1"):
            return {"state": NOT_SCORABLE_STREAK_NA, "L": None, "b": None}
        if r["ceiling_close"] == "0":
            b = L + 1
            return {"state": NOT_APPLICABLE_B10 if b == oc.N_SESSIONS else BREAK_STATE, "L": L, "b": b}
        L += 1
    if L == oc.N_SESSIONS:
        return {"state": NOT_APPLICABLE_NO_BREAK, "L": L, "b": None}
    return {"state": STREAK_PENDING, "L": None, "b": None}


def _path_params_checked(models_dir: Path, cell: Mapping[str, Any]) -> dict[str, Any]:
    """Listeleme öncesi kayıttaki tavan yolu hücresinin parametre dosyası: models/INDEX.json kaydı, dosya sha256'sı ve hücredeki
    `params_sha256` aynı olmalı (PARAMS_INVALID)."""
    name = Path(str(cell["file"])).name
    entry = next((e for e in load_index(Path(models_dir) / "INDEX.json")["models"] if e["model_id"] == cell["model_id"]), None)
    if entry is None or entry["file"] != name:
        raise FreezeError(f"{cell['model_id']} INDEX.json'da yok ya da dosya adı farklı (PARAMS_INVALID)")
    raw = (Path(models_dir) / name).read_bytes()
    if not sha256_bytes(raw) == entry["sha256"] == cell["params_sha256"]:
        raise FreezeError(f"{cell['model_id']}: dosya sha256 INDEX.json / kayıt hücresi ile aynı değil (PARAMS_INVALID)")
    return json.loads(raw)


def post_break_product(ticker: str, d1: str, L: int, closes: Sequence[str], *, records_dir: Path = reg.RECORDS_DIR,
                       models_dir: Path = MODELS_DIR, root: Path = ROOT,
                       proofs: Optional[Sequence[Mapping[str, Any]]] = None) -> dict[str, Any]:
    """§5.1 / K-LB-7 `PRODUCT_BREAK_FLOOR` (canlı): arzın birincil listeleme öncesi kaydındaki (SPEC_SCORING §6, skorlamayla aynı kural
    ve aday kurucusu) `ceiling_path_v0` çıktısı, yoksa `ceiling_path_v0@INF`'inki, ve dondurulmuş hücreleriyle
    `predict_break.product_break_floor`; çıktı bugünkü kodla yeniden üretilip kayıttakiyle `==` denetlenir. Kayıt yoksa
    NOT_AVAILABLE. Dönen: {source_record, source_model_id, F1, F2, status}."""
    from . import push_proof as pp
    from . import scoring as sc

    recs = list_records(ticker, records_dir)
    cancelled = {r["cancels"]["file"] for _, r in recs if r.get("record_type") == RECORD_CANCELLATION}
    preds = [(p, r) for p, r in recs if r.get("record_type") == RECORD_PREDICTION]
    if preds:
        proofs = list(pp.load_proofs(Path(root) / "registry" / "push_proofs")) if proofs is None else list(proofs)
        git = sc.Git(root)
        for mid in POST_BREAK_PRODUCT_SOURCES:
            cands = sc.registry_candidates(git, preds, cancelled, mid, d1, proofs, root)
            sel = reg.select_primary(mid, [c for c, _ in cands], d1)["proven"]
            if sel["record_id"] is None:
                continue
            info = next(x for c, x in cands if c.record_id == sel["record_id"])
            cell = info["cell"]
            if cell["status"] != STATUS_PREDICTED:
                continue
            path_params = _path_params_checked(models_dir, cell)
            rec = next(r for p, r in preds if p.name == sel["record_id"])
            if pth.predict(path_params, rec["model_inputs"]) != cell["output"]:
                raise FreezeError(f"{ticker} {mid}: listeleme öncesi kayıt çıktısı bugünkü kodla yeniden üretilemedi (parite)")
            res = pbrk.product_break_floor(path_params, cell["output"], L, closes)
            return {"source_record": info["path"], "source_model_id": mid, "F1": res["F1"], "F2": res["F2"], "status": res["status"]}
    return {"source_record": None, "source_model_id": None, "F1": None, "F2": None, "status": PRODUCT_NOT_AVAILABLE}


def build_post_break_machine_record(ticker: str, *, now: Optional[datetime] = None, models_dir: Path = MODELS_DIR,
                                    records_dir: Path = reg.RECORDS_DIR, inputs_dir: Path = reg.INPUTS_DIR,
                                    bist_dir: Path = oc.BIST_DIR, outcomes_dir: Path = oc.OUTCOMES_DIR, root: Path = ROOT,
                                    code_root: Path = ROOT, calendar: Optional["oc.SessionCalendar"] = None,
                                    proofs: Optional[Sequence[Mapping[str, Any]]] = None) -> dict[str, Any]:
    """§9.2 makine kaydı (şema borsai.post_break_machine_record/1; alan kümeleri şartnamedeki gibi). Yükseltir: BreakNotAvailable
    (kayıt yazılmaz; §11), FreezeError (parametre, parite ya da sonuç dosyası ↔ bülten uyuşmazlığı)."""
    _, produced_utc, _ = _now_pair(now)
    opath = oc.outcome_path(ticker, outcomes_dir)
    rows = oc.read_outcome(opath) if opath.exists() else []
    st = break_streak(rows)
    if st["state"] != BREAK_STATE:
        raise BreakNotAvailable(st["state"], f"{ticker}: b ∈ 1..9 kırılma akşamı yok ya da henüz oluşmadı")
    L, b = st["L"], st["b"]
    d1, db = rows[0]["session_date"], rows[b - 1]["session_date"]
    manifest = {(r["date"], r["kind"]): r for r in oc.read_manifest(bist_dir)}
    code = oc.equity_code(ticker)
    sessions, bulletins = [], {}
    for h in range(1, b + 1):
        r = rows[h - 1]
        day = r["session_date"]
        refs = {}
        for kind in oc.KINDS:
            m = manifest.get((day, kind))
            bt = oc.local_bulletin(day, kind, bist_dir) if m is not None else None
            if bt is None:
                raise BreakNotAvailable(BULLETIN_NOT_PINNED, f"{ticker} D_{h} {day} {kind.upper()} bülteni yerelde ya da MANIFEST'te yok")
            if r[f"{kind}_sha256"] != m["sha256"]:
                raise FreezeError(f"{ticker} D_{h} {day}: sonuç dosyasının {kind} sha256'sı MANIFEST'teki pinli değerle aynı değil")
            bulletins[(day, kind)] = bt
            refs[kind] = {"file": _rel(oc.local_path(day, kind, bist_dir), root), "sha256": m["sha256"]}
        row, lim = bulletins[(day, "thb")].get(code), bulletins[(day, "thm")].get(code)
        if row is None or row.close != r["close_raw"] or (lim.upper if lim else "") != r["upper_limit_raw"]:
            raise FreezeError(f"{ticker} D_{h} {day}: sonuç dosyası satırı pinli bültenin satırıyla aynı değil")
        sessions.append({"h": h, "date": day, "thb": refs["thb"], "thm": refs["thm"], "close_raw": r["close_raw"],
                         "upper_limit_raw": r["upper_limit_raw"], "ceiling_close": int(r["ceiling_close"])})
    ipath = Path(inputs_dir) / f"{ticker}.json"
    if not ipath.exists():
        raise BreakNotAvailable(INPUTS_NOT_AVAILABLE, f"{ticker}: registry/inputs/{ticker}.json yok")
    doc, raw = reg.load_inputs(ipath)
    so = doc["fields"]["shares_offered"]
    price = doc["fields"]["ipo_price_tl"]["value"]
    calendar = calendar or oc.load_calendar(bist_dir=bist_dir)
    try:
        t_open_at = reg.t_open(db, calendar)
    except reg.CalendarNotAvailable as exc:
        raise BreakNotAvailable(reg.CALENDAR_NOT_AVAILABLE, str(exc)) from exc
    trow, tlim = bulletins[(db, "thb")].get(code), bulletins[(db, "thm")].get(code)
    fields = {"open": trow.open, "high": trow.high, "low": trow.low, "close": trow.close, "volume": trow.volume,
              "turnover": trow.turnover, "aof": trow.aof, "trade_count": trow.trade_count, "halt": trow.halt,
              "special_trade_volume": trow.special_volume, "special_trade_turnover": trow.special_turnover,
              "reference_price": tlim.reference if tlim else "", "upper_limit": tlim.upper if tlim else "",
              "lower_limit": tlim.lower if tlim else ""}
    assert tuple(fields) == reg.POST_D1_FIELDS_RAW
    rb = rows[b - 1]
    day_input = {"fields_raw": fields, "half_day": int(rb["half_day"] or 0), "halt_flag": int(rb["halt_flag"] or 0)}
    index, index_sha, models = _index_sha_checked(Path(models_dir), INDEX_POST_BREAK_NAME)
    cells, first = [], None
    for entry, params, sha in models:
        if model_kind(params) != "post_break":
            raise FreezeError(f"{entry['model_id']}: {INDEX_POST_BREAK_NAME}'de POST_BREAK modeli değil (PARAMS_INVALID)")
        try:
            out = pbrk.predict_break(params, day_input, so.get("value"), b=b, first_trading_date=d1)
        except pr.PredictError as exc:
            raise FreezeError(f"{entry['model_id']}: {exc.code}: {exc}") from exc
        status = STATUS_REFUSED if out["refused"] else (STATUS_NOT_APPLICABLE if out["not_applicable"] else STATUS_PREDICTED)
        cells.append({"model_id": entry["model_id"], "file": f"models/{entry['file']}", "params_sha256": sha,
                      "spec_sha256": entry["spec_sha256"], "status": status, "refused": out["refused"],
                      "not_applicable": out["not_applicable"], "output": {"F1": out["F1"], "F2": out["F2"], "warnings": out["warnings"]}})
        if first is None and status == STATUS_PREDICTED and out["features"] is not None:
            first = out
    try:
        v = pbrk.evaluate_break_day(day_input, so.get("value"))
    except pbrk.BreakRefusal:
        v = None
    features = {"b_floor": None, "b_turnover_ratio": None, "b_turnover_ln": None, "clipped": None, "z": None}
    if v is not None:
        features.update(b_floor=v.b_floor, b_turnover_ratio=str(v.turnover_ratio), b_turnover_ln=v.turnover_ln)
        if first is not None:
            features.update(clipped=first["features"]["clipped"], z=first["features"]["z"])
    rl, ru, band_ok = pbrk.band_ratios(fields)
    try:
        sz = pbrk.structural_zero_d10(fields["close"], b, price)
        structural = {k: sz[k] for k in ("min10", "P", "impossible", "k_b", "r_b")} | {"band_rule_ok": band_ok}
    except (ValueError, ArithmeticError):
        structural = None
    pit = reg.post_break_inputs_pit_problems(doc, d1, root=root)
    product = post_break_product(ticker, d1, L, [s["close_raw"] for s in sessions], records_dir=records_dir, models_dir=models_dir,
                                 root=root, proofs=proofs)
    state = git_state(code_root)
    return {
        "schema_version": POST_BREAK_RECORD_SCHEMA,
        "record_type": RECORD_MACHINE,
        "record_stage": POST_BREAK_STAGE,
        "exposure_class": EXPOSURE_MACHINE_SEQUENCED,
        "ticker": ticker,
        "produced_at_utc": produced_utc,
        "code": {"git_head": state["commit"], "borsai_dirty": state["borsai_dirty"],
                 "borsai_source_sha256": source_tree_sha256(Path(code_root) / "borsai")["tree_sha256"],
                 "predict_break_sha256": sha256_file(Path(code_root) / "borsai" / "predict_break.py")},
        "inputs_ref": {"file": _rel(ipath, root), "sha256": sha256_bytes(raw),
                       "shares_offered": {"value": so.get("value"), "source_published_at": so.get("source_published_at")},
                       "ipo_price_tl": price, "inputs_pit_ok": not pit},
        "streak": {"L": L, "b": b, "break_date": db, "sessions": sessions},
        "break_day": {"h": b, "session_date": db, "half_day": day_input["half_day"], "halt_flag": day_input["halt_flag"],
                      "fields_raw": fields, "b_floor": None if v is None else v.b_floor,
                      "band_ratio": {"lower_over_reference": None if rl is None else str(rl),
                                     "upper_over_reference": None if ru is None else str(ru), "rule_ok": band_ok},
                      "warnings": [] if v is None else list(v.warnings)},
        "features": features,
        "models_index": {"path": _rel(Path(models_dir) / INDEX_POST_BREAK_NAME, root), "sha256": index_sha,
                         "model_ids": [e["model_id"] for e, _, _ in models]},
        "models": cells,
        "comparators": {pbrk.PRODUCT_COMPARATOR: product, "base_floor_by_type": None},
        "structural_zero_D10": structural,
        "t_open": t_open_at.isoformat(),
        "summary": {"n_models": len(cells), "n_predicted": sum(c["status"] == STATUS_PREDICTED for c in cells),
                    "n_refused": sum(c["status"] == STATUS_REFUSED for c in cells),
                    "n_not_applicable": sum(c["status"] == STATUS_NOT_APPLICABLE for c in cells)},
    }


def machine_record_filename(payload: bytes, produced_at_utc: str) -> str:
    """§9.2 `machine_<UTC>_<kısa-sha>.json` (içerik adresli: kısa-sha = dosya baytlarının sha256'sının ilk 12 hanesi)."""
    return f"machine_{produced_at_utc.replace('-', '').replace(':', '')}_{sha256_bytes(payload)[:12]}.json"


def post_break_record_key(rec: Mapping[str, Any]) -> tuple[Any, ...]:
    """K-LB-3 mükerrer anahtarı: (INDEX_POST_BREAK sha'sı, D_1..D_b bülten sha'ları, girdi dosyası sha'sı)."""
    return (rec["models_index"]["sha256"], tuple((s["thb"]["sha256"], s["thm"]["sha256"]) for s in rec["streak"]["sessions"]),
            rec["inputs_ref"]["sha256"])


def list_post_break_records(ticker: str, post_dir: Path = reg.POST_BREAK_DIR) -> list[tuple[Path, dict[str, Any]]]:
    d = Path(post_dir) / ticker
    return [(p, json.loads(p.read_text(encoding="utf-8"))) for p in sorted(d.glob("machine_*.json"))] if d.exists() else []


def write_post_break_machine_record(ticker: str, *, now: Optional[datetime] = None, post_dir: Path = reg.POST_BREAK_DIR,
                                    **kw: Any) -> Path:
    """Makine kaydı dosyası ('xb', içerik adresli ad; append-only). Aynı mükerrer anahtarlı bir kayıt varsa DUPLICATE_RECORD (yeni
    kayıt yazılmaz; K-LB-3)."""
    record = build_post_break_machine_record(ticker, now=now, **kw)
    key = post_break_record_key(record)
    for path, rec in list_post_break_records(ticker, post_dir):
        if post_break_record_key(rec) == key:
            raise DuplicateRecord(f"DUPLICATE_RECORD: {ticker} için aynı POST_BREAK model dizini, aynı D_1..D_b bültenleri ve aynı girdi "
                                  f"dosyalı makine kaydı var ({path.name})")
    payload = pretty_json_bytes(record)
    path = Path(post_dir) / ticker / machine_record_filename(payload, record["produced_at_utc"])
    _write_new(path, payload)
    return path


# ============================================================ CLI

def _record_stage(path: Path) -> Optional[str]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")).get("record_stage")
    except (OSError, ValueError):
        return None


def _is_post_d1(path: Path) -> bool:
    return _record_stage(path) == POST_D1_STAGE


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Tahmin kaydı (girdi JSON -> kayıt), POST_D1 kaydı, iptal kaydı ya da model dondurma.")
    parser.add_argument("inputs", nargs="?", type=Path, help="registry/inputs/<TICKER>.json: tahmin kaydı yazar")
    parser.add_argument("--post-d1", metavar="TICKER", help="D_1 bülteninden POST_D1 kaydı (registry/post_d1/<TICKER>/)")
    parser.add_argument("--cancel", type=Path, help="iptal edilecek kayıt dosyası (listeleme öncesi ya da POST_D1)")
    parser.add_argument("--reason", help="iptal nedeni (--cancel ile zorunlu)")
    parser.add_argument("--models", nargs="*", help="model dondurma (fit gerekir; numpy/scikit-learn)")
    parser.add_argument("--oot", type=Path, metavar="COHORT_CSV",
                        help="eski kohort toplu kaydı: registry/oot/cohort_pre_h99.csv'nin her MEMBER satırı (registry/oot/records/)")
    parser.add_argument("--only-missing-models", action="store_true",
                        help="--oot ile: üye başına yalnız etkin kayıtlarında bulunmayan INDEX modellerini içeren ek kayıt "
                             "(SPEC_HAZARD_V1 §7.1-3); çıktı yalnız sayılar")
    parser.add_argument("--oot-post-d1", metavar="TICKER", help="eski kohort D_1 satırından POST_D1 kaydı (registry/oot/post_d1/)")
    args = parser.parse_args(argv)
    if args.only_missing_models and args.oot is None:
        parser.error("--only-missing-models yalnız --oot ile kullanılır")
    if args.oot is not None and args.only_missing_models:
        print(json.dumps(delta_summary(write_oot_delta_records(args.oot)), ensure_ascii=False, indent=2))
        return 0
    if args.oot is not None:
        print(json.dumps(write_oot_records(args.oot), ensure_ascii=False, indent=2))
        return 0
    if args.oot_post_d1 is not None:
        print(write_oot_post_d1_record(args.oot_post_d1))
        return 0
    if args.cancel is not None:
        stage = _record_stage(args.cancel)
        print(cancel_post_d1_record(args.cancel, args.reason or "") if stage == POST_D1_STAGE
              else cancel_oot_record(args.cancel, args.reason or "") if stage == OOT_STAGE
              else cancel_record(args.cancel, args.reason or ""))
        return 0
    if args.post_d1 is not None:
        now = datetime.now(timezone.utc)
        path = write_post_d1_record(args.post_d1, now=now)
        rec = json.loads(path.read_text(encoding="utf-8"))
        t_open_at = reg.t_open(rec["d1"]["session_date"], oc.load_calendar())
        print(json.dumps({"path": str(path), "d1": rec["d1"]["session_date"], "ceiling_close_D1": rec["d1"]["ceiling_close_D1"],
                          "summary": rec["summary"], "T_open": t_open_at.isoformat(),
                          "note": ("T_open'dan ÖNCE: commit + push + push_proof (proje sahibi)" if now < t_open_at else
                                   "T_open GEÇTİ (yerel saat): kayıt en iyi ihtimalle LATE_RECORD olur")},
                         ensure_ascii=False, indent=2))
        return 0
    if args.inputs is not None:
        print(write_record(args.inputs))
        return 0
    from .data import load_dataset
    from .specs import FAZ7_MODEL_SPECS, FAZ7C_MODEL_SPECS, MODEL_SPECS, POST_BREAK_MODEL_SPECS, POST_D1_MODEL_SPECS

    ids = args.models if args.models else list(MODEL_SPECS)
    unknown = [m for m in ids if m not in MODEL_SPECS and m not in POST_D1_MODEL_SPECS and m not in FAZ7_MODEL_SPECS
               and m not in FAZ7C_MODEL_SPECS and m not in POST_BREAK_MODEL_SPECS]
    if unknown:
        parser.error(f"bilinmeyen model_id: {unknown}")
    print(json.dumps(freeze(ids, load_dataset()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

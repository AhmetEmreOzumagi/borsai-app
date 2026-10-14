"""Faz 8 (kırılma akşamı) için var olan testlerin sınırlı istisnası (SPEC_DEVIATIONS N19; proje sahibi kararı 2026-10-01; Faz 7/7C J16/K10
kalıbı). `scores/` bu görevde yeniden üretilmez; `break_floor_v0`'ın H99 veri sürümündeki `kind: backtest` satırı kart varyant sayacını
(E16) artırır. İstisna yalnız skor dosyaları Faz 8'den önceki halleriyle (87434ff) bayt-eşitken ve fark tam olarak günlükteki Faz 8
varyant sayısı kadarken geçerlidir; yeniden üretilen her skor dosyası tam karşılaştırılır (istisna kendiliğinden devre dışı kalır)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from borsai.provenance import ROOT

FAZ8_SCORES_BASE_COMMIT = "87434ff"      # scores/scores.json ve scores_post_d1.json'ı Faz 8'den önce son yazan commit (BORSAI_LIVE_SCORES)


def faz8_variants(data_version: str, log_path: Path = ROOT / "experiments" / "log.jsonl") -> int:
    """Aynı veri sürümünde günlüğe düşmüş Faz 8 modeli (model_id, spec_sha256) varyant sayısı (H99 sürümünde resmi koşudan sonra 1;
    duyarlılık satırları sayılmaz)."""
    from borsai.specs import POST_BREAK_MODEL_SPECS

    seen = set()
    for line in Path(log_path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            if e.get("kind") == "backtest" and e.get("data_version_sha256") == data_version and e.get("model_id") in POST_BREAK_MODEL_SPECS:
                seen.add((e["model_id"], e["spec_sha256"]))
    return len(seen)


def faz8_sensitivity_lines(log_path: Path = ROOT / "experiments" / "log.jsonl") -> list[dict]:
    """Günlükteki Faz 8 duyarlılık satırları (`kind: sensitivity`, temel model Faz 8 sözlüğünde)."""
    from borsai.specs import POST_BREAK_MODEL_SPECS

    out = []
    for line in Path(log_path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            if e.get("kind") == "sensitivity" and e.get("base_model_id") in POST_BREAK_MODEL_SPECS:
                out.append(e)
    return out


def _git_bytes(rev: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, check=True, capture_output=True).stdout


def scores_json_is_pre_faz8() -> bool:
    return (ROOT / "scores" / "scores.json").read_bytes() == _git_bytes(FAZ8_SCORES_BASE_COMMIT, "scores/scores.json")


def scores_post_d1_is_pre_faz8() -> bool:
    return (ROOT / "scores" / "scores_post_d1.json").read_bytes() == _git_bytes(FAZ8_SCORES_BASE_COMMIT, "scores/scores_post_d1.json")


# ---------------------------------------------------------------- dondurma (BORSAI_FAZ8_FREEZE_20261002; K-PIN, SPEC_DEVIATIONS N25)

def frozen_post_break_files() -> list[str]:
    """models/'e Faz 8 dondurmasıyla eklenen dosya adları (`faz7_support.frozen_tail_ids` kalıbı). İzinli durumlar yalnız şunlardır:
    dondurmadan önce `[]` (üç dosyanın hiçbiri yok) ya da dondurmadan sonra tam olarak `[INDEX_POST_BREAK.json, break_floor_v0.json,
    break_floor_v0@ZERO.json]`: dizin şeması `borsai.model_index/1`, girişler tam olarak `FAZ8_MODEL_IDS` sırasıyla, dosya adı
    `<model_id>.json`, sha256'lar diskteki dosyalarla eşit. Başka her durum (eksik dosya, fazla giriş, sha farkı) durur. Dondurma öncesi
    durumu sabitleyen testler (models/ dosya listesi, `git diff` boş, INDEX_POST_BREAK yok) bunu kullanır; eski bayt-eşitlik ayakları
    (INDEX.json, INDEX_POST_D1.json, 28 model dosyası) testlerde aynen kalır."""
    from borsai.freeze import INDEX_POST_BREAK_NAME, INDEX_SCHEMA
    from borsai.provenance import sha256_file
    from borsai.specs import FAZ8_MODEL_IDS

    d = ROOT / "models"
    names = [INDEX_POST_BREAK_NAME] + [f"{m}.json" for m in FAZ8_MODEL_IDS]
    present = [n for n in names if (d / n).exists()]
    if not present:
        return []
    assert present == names, f"Faz 8 dondurma dosyaları eksik: {present}"
    index = json.loads((d / INDEX_POST_BREAK_NAME).read_text(encoding="utf-8"))
    assert index["schema_version"] == INDEX_SCHEMA and [e["model_id"] for e in index["models"]] == list(FAZ8_MODEL_IDS), index
    for e in index["models"]:
        assert e["file"] == f"{e['model_id']}.json" and e["sha256"] == sha256_file(d / e["file"]), e["model_id"]
    return names

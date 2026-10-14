"""Faz 7 test yardımcıları: sentetik v1 veri kümesi (gerçek sonuç görmeden hata ayıklama ve A testleri) ve varyant sayacı istisnası
(SPEC_DEVIATIONS J; Faz 5 H22 kalıbı, proje sahibi kararı 2026-09-25)."""
from __future__ import annotations

import json
import random
import subprocess
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from borsai import tufe
from borsai.data import Dataset, IPORowV2, alloc_regime
from borsai.provenance import ROOT

# ---------------------------------------------------------------- sentetik veri (gerçek arz yok; kod adı yok)


def _business_days(start: date, n: int) -> list[str]:
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def synthetic_dataset(*, n_oot: int = 16, n_h99: int = 30, seed: int = 20260925, n_filtered: int = 2,
                      oot_unfiltered_share: float = 0.6, tag: str = "synthetic") -> Dataset:
    """IPORowV2 satırları: `n_oot` eski kohort benzeri arz (2021-01 … 2023-06; rejim talep toplama gününden) ve `n_h99` H99 benzeri
    arz (2023-09-25 sonrası; r = 0). Eski kohortun f3 filtre durumları çoğunlukla UNFILTERED ve `n_filtered` tanesi FILTERED:
    erken havuz fold'larında mod UNFILTERED olur ve f3 filtre dışlaması çalışır. TÜFE değerleri gerçek dosyadan (tufe.index_for)."""
    rng = random.Random(seed)
    tt = tufe.load()
    rows = []
    oot_days = sorted(rng.sample(range(0, 880), n_oot))                 # 2021-01-04 + gün
    h99_days = sorted(rng.sample(range(0, 980), n_h99))                 # 2023-09-25 + gün
    starts = [date(2021, 1, 4) + timedelta(days=d) for d in oot_days] + [date(2023, 9, 25) + timedelta(days=d) for d in h99_days]
    for i, start in enumerate(starts):
        while start.weekday() >= 5:
            start += timedelta(days=1)
        ftd = start.isoformat()
        cohort = "OOT_OPEN" if i < n_oot else "H99"
        price = Decimal(rng.choice(["8.8", "10.5", "17.25", "22.4", "31.2", "45", "64.5"]))
        shares = rng.randint(4, 90) * 1_000_000
        post = shares * rng.randint(3, 9)
        f3 = None if rng.random() < 0.05 else f"{rng.uniform(1.1, 40.0):.2f}"
        L = rng.choice(range(0, 11))
        closes = [1] * L + ([0] + [rng.choice([0, 0, 1]) for _ in range(9 - L)] if L < 10 else [])
        if cohort == "OOT_OPEN":
            status = "FILTERED" if i < n_filtered else ("UNFILTERED" if rng.random() < oot_unfiltered_share else "NOT_SPECIFIED")
        else:
            status = "NOT_SPECIFIED" if rng.random() < 0.6 else "UNFILTERED"
        regime_date = (start - timedelta(days=7)).isoformat()
        t = tufe.index_for(ftd, tt)
        rows.append(IPORowV2(
            ticker=f"SYN{i:02d}", first_trading_date=ftd, point_in_time_status="PASS",
            inputs={"ipo_price_tl": str(price), "shares_offered": str(shares), "post_ipo_share_capital": str(post),
                    "capital_increase_shares": str(shares // 2), "total_demand_multiple": f3, "ipo_size_tl": None},
            total_demand_filter_status=status if f3 is not None else None, targets={},
            session_dates=tuple(_business_days(start, 10)), ceiling_close=tuple(closes), ceiling_streak=L, cohort=cohort,
            alloc_regime=alloc_regime(regime_date), alloc_regime_date=regime_date, tufe_month=t["month"], tufe_index=t["index"],
        ))
    rows.sort(key=lambda r: (r.first_trading_date, r.ticker))
    return Dataset(rows=tuple(rows), data_version_sha256=tag, table_sha256=tag,
                   outcome_sessions_through=max(d for r in rows for d in r.session_dates))


def synthetic_spec(model_id: str, dataset: Dataset) -> dict:
    """Şartname kopyası; yalnız eğitim n'i ve veri sürümü sentetik veriye göre (nihai fit fonksiyonunu sentetikte koşmak için)."""
    from borsai.specs import FAZ7_MODEL_SPECS

    spec = json.loads(json.dumps(FAZ7_MODEL_SPECS[model_id]))
    n = sum(1 for r in dataset.rows if r.inputs["total_demand_multiple"] is not None)
    spec["training"].update(n=n, data_version_sha256=dataset.data_version_sha256)
    return spec


# ---------------------------------------------------------------- varyant sayacı istisnası (SPEC_DEVIATIONS J)

FAZ7_SCORES_BASE_COMMIT = "8e3a623"      # scores/scores.json'ı Faz 7'den önce son yazan commit (BORSAI_FAZ5_LIVE_B)


def faz7_variants(data_version: str, log_path: Path = ROOT / "experiments" / "log.jsonl") -> int:
    """Aynı veri sürümünde günlüğe düşmüş Faz 7 modeli (model_id, spec_sha256) varyant sayısı. scores.json Faz 7 görevinde yeniden
    üretilmediği için kartlardaki veri geneli sayaç tam olarak bu kadar geride kalır (v1_clip ve v1_real H99 veri sürümünde: 2)."""
    from borsai.specs import FAZ7_MODEL_SPECS

    seen = set()
    for line in Path(log_path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            if e.get("kind") == "backtest" and e.get("data_version_sha256") == data_version and e.get("model_id") in FAZ7_MODEL_SPECS:
                seen.add((e["model_id"], e["spec_sha256"]))
    return len(seen)


def scores_json_is_pre_faz7() -> bool:
    old = subprocess.run(["git", "show", f"{FAZ7_SCORES_BASE_COMMIT}:scores/scores.json"], cwd=ROOT, check=True,
                         capture_output=True).stdout
    return (ROOT / "scores" / "scores.json").read_bytes() == old


def scores_post_d1_is_pre_faz7() -> bool:
    """scores/scores_post_d1.json 8e3a623'teki haliyle bayt-eşit mi (aynı istisnanın POST_D1 dosyası için koşulu)."""
    old = subprocess.run(["git", "show", f"{FAZ7_SCORES_BASE_COMMIT}:scores/scores_post_d1.json"], cwd=ROOT, check=True,
                         capture_output=True).stdout
    return (ROOT / "scores" / "scores_post_d1.json").read_bytes() == old


# ---------------------------------------------------------------- dondurma (BORSAI_FAZ7_FREEZE; SPEC_DEVIATIONS J)

PRE_FAZ7_INDEX_COMMIT = "a0df5b7"        # models/INDEX.json'u Faz 7'den önce son yazan commit (BORSAI_FAZ4_FREEZE; 19 giriş)
N_PRE_FAZ7 = 19


def _git_bytes(rev: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, check=True, capture_output=True).stdout


def pre_faz7_index_bytes() -> bytes:
    return _git_bytes(PRE_FAZ7_INDEX_COMMIT, "models/INDEX.json")


def frozen_tail_ids() -> list[str]:
    """models/INDEX.json'un Faz 7 öncesi 19 girişinden (a0df5b7, metin olarak aynı) sonraki dondurulmuş kimlikler. İzinli durumlar
    yalnız şunlardır: boş (Faz 7 dondurmasından önce), `FAZ7_MODEL_IDS` (Faz 7 dondurması, 23 giriş) ya da `FAZ7_MODEL_IDS` +
    `FAZ7C_MODEL_IDS` (Faz 7C dondurması, 27 giriş; SPEC_DEVIATIONS K19). "19 + dondurulmuş Faz 7/7C" sayan testler bunu kullanır."""
    from borsai.specs import FAZ7_MODEL_IDS, FAZ7C_MODEL_IDS

    entries = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]
    base = json.loads(pre_faz7_index_bytes())["models"]
    assert len(base) == N_PRE_FAZ7 and entries[:N_PRE_FAZ7] == base, "INDEX'in ilk 19 girişi Faz 7 öncesiyle aynı değil"
    tail = [e["model_id"] for e in entries[N_PRE_FAZ7:]]
    assert tail in ([], list(FAZ7_MODEL_IDS), list(FAZ7_MODEL_IDS) + list(FAZ7C_MODEL_IDS)), tail
    return tail


def frozen_faz7_ids() -> list[str]:
    """models/INDEX.json'da dondurulmuş Faz 7 modelleri (dondurmadan önce boş liste, sonra FAZ7_MODEL_IDS sırasıyla). INDEX her
    durumda Faz 7 öncesi 19 girişle (a0df5b7) metin olarak aynı başlar; ardından bu dört giriş ve (Faz 7C dondurmasından sonra)
    dört Faz 7C girişi gelir (`frozen_tail_ids`)."""
    from borsai.specs import FAZ7_MODEL_SPECS

    return [m for m in frozen_tail_ids() if m in FAZ7_MODEL_SPECS]


def frozen_faz7c_ids() -> list[str]:
    """models/INDEX.json'da dondurulmuş Faz 7C modelleri (Faz 7C dondurmasından önce boş, sonra FAZ7C_MODEL_IDS sırasıyla)."""
    from borsai.specs import FAZ7C_MODEL_SPECS

    return [m for m in frozen_tail_ids() if m in FAZ7C_MODEL_SPECS]


def strip_frozen_faz7(doc: dict) -> dict:
    """Commit'li bir skor dosyası (scores.json ya da scores_post_d1.json) Faz 7 dondurmasından önce yazıldıysa, yeniden hesabı
    onunla karşılaştırmak için yeniden hesaptan YALNIZ dondurulmuş Faz 7 modellerinin izlerini çıkarır: `models` ve `retro_info`
    listelerindeki o model_id'li girdiler ve `inputs.models_index_sha256` (yeniden hesapta bugünkü INDEX'in sha'sı; burada Faz 7
    öncesi INDEX'inkiyle değiştirilir, bugünkü INDEX'in ilk 19 girişi onunla aynı olmak koşuluyla). Başka hiçbir alan dokunulmaz;
    dondurmadan önce (INDEX'te Faz 7 modeli yokken) kopyayı aynen döndürür. Yalnız `scores_json_is_pre_faz7()` iken kullanılır
    (J16 kalıbı; skorlar yeniden üretilince kendiliğinden devre dışı). Faz 7C dondurmasından sonra aynı koşullarla dört Faz 7C
    kimliğini de çıkarır (sekiz kart; orkestratör kararı, SPEC_DEVIATIONS K19): `frozen_tail_ids`; ve yeniden hesabın (C) INDEX'teyken
    yazdığı üst düzey `faz7c_near_era` bloğunu (SPEC_DEVIATIONS K11; yakın dönem bloğu sıradaki skorlama görevinde yazılır)."""
    from borsai.provenance import sha256_bytes, sha256_file

    ids = set(frozen_tail_ids())
    out = json.loads(json.dumps(doc))
    if not ids:
        return out
    for key in ("models", "retro_info"):
        if key in out:
            out[key] = [x for x in out[key] if x.get("model_id") not in ids]
    if frozen_faz7c_ids():
        out.pop("faz7c_near_era", None)
    if "inputs" in out and "models_index_sha256" in out["inputs"]:
        assert out["inputs"]["models_index_sha256"] == sha256_file(ROOT / "models" / "INDEX.json")
        out["inputs"]["models_index_sha256"] = sha256_bytes(pre_faz7_index_bytes())
    return out


# ---------------------------------------------------------------- B1 yeniden üretimi (BORSAI_FAZ7_FREEZE, K1; SPEC_DEVIATIONS J23)

B1_CONTEXT = "faz7_golden_b1"
B1_PARENT_COMMIT = "eda9732f73832d928e2e60431a797198650a27dc"   # B1 koşusunun HEAD'i (kod ve altın dosyalar sonraki commit K'da)
PRE_B1_GOLDEN_COMMIT = "70b67d1"                                # Faz 7 altın dizinini ilk yazan commit (BORSAI_FAZ7_B)


def borsai_tree_sha256_at(rev: str) -> str:
    """`provenance.source_tree_sha256` (borsai/*.py) bir commit'teki dosyalardan."""
    import hashlib

    names = subprocess.run(["git", "ls-tree", "--name-only", rev, "borsai/"], cwd=ROOT, check=True, capture_output=True,
                           text=True).stdout.split()
    files = sorted(n for n in names if n.endswith(".py") and n.count("/") == 1)
    lines = [f"{Path(n).name}\t{hashlib.sha256(_git_bytes(rev, n)).hexdigest()}" for n in files]
    return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()


def introducing_commit(path: str, needle: str) -> str | None:
    """`path`'e `needle` metnini ilk getiren commit (git pickaxe); henüz commit'lenmediyse None."""
    out = subprocess.run(["git", "log", "--format=%H", "-S", needle, "--", path], cwd=ROOT, check=True, capture_output=True,
                         text=True).stdout.split()
    return out[-1] if out else None


def code_sha_matches_introducing_commit(borsai_source_sha256: str, path: str, needle: str) -> bool:
    """Kod ve çıktısı aynı commit'e girdiğinde (borsai_dirty = true) çıktının `borsai_source_sha256`'sı o commit'in borsai/
    ağacıdır; commit'lenmeden önce çalışma ağacınınkidir."""
    from borsai.provenance import source_tree_sha256

    c = introducing_commit(path, needle)
    return borsai_source_sha256 == (source_tree_sha256()["tree_sha256"] if c is None else borsai_tree_sha256_at(c))

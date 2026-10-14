"""Faz 7C test yardımcıları: sentetik düşen arz veri kümesi (gerçek sonuç görmeden hata ayıklama ve commit A testleri) ve varyant
sayacı istisnası (SPEC_DEVIATIONS K; J16/J30 kalıbı)."""
from __future__ import annotations

import json
import math
import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from borsai import tufe
from borsai.data import Dataset, IPORowV2, Target, alloc_regime
from borsai.provenance import ROOT

# ---------------------------------------------------------------- sentetik veri (gerçek arz yok; kod adı yok)


def _business_days(start: date, n: int) -> list[str]:
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def synthetic_fall_dataset(*, n_oot: int = 24, n_h99: int = 40, seed: int = 20260927, n_filtered: int = 2,
                           oot_unfiltered_share: float = 0.7, tag: str = "synthetic_fall", h99_only: bool = False,
                           n_as_missing: int = 2, n_f3_missing: int = 2) -> tuple[Dataset, dict[str, str | None]]:
    """(Dataset, ticker -> additional_sale_shares metni). `n_oot` eski kohort benzeri arz (2021-01 … 2023-06) ve `n_h99` H99 benzeri
    arz (2023-09-25 sonrası). Hedefler (D1, D3, D5, D10) f1r, f3 ve ek satıştan türeyen gizli bir lojistikle üretilir (Y_h = 1 ⇔
    R_h > 0). Eski kohortun f3 filtre durumları çoğunlukla UNFILTERED ve `n_filtered` tanesi FILTERED: erken havuz fold'larında mod
    UNFILTERED olur ve f3 filtre dışlaması (J10 kuralı) çalışır. Ek satış alanı `n_as_missing` arzda boş, f3 `n_f3_missing` arzda
    boş (kümeler bunları dışarıda bırakır). TÜFE gerçek dosyadan (`tufe.index_for`)."""
    rng = random.Random(seed)
    tt = tufe.load()
    rows, add_sale = [], {}
    n_oot_eff = 0 if h99_only else n_oot
    oot_days = sorted(rng.sample(range(0, 880), n_oot_eff))
    h99_days = sorted(rng.sample(range(0, 980), n_h99))
    starts = [date(2021, 1, 4) + timedelta(days=d) for d in oot_days] + [date(2023, 9, 25) + timedelta(days=d) for d in h99_days]
    for i, start in enumerate(starts):
        while start.weekday() >= 5:
            start += timedelta(days=1)
        ftd = start.isoformat()
        cohort = "OOT_OPEN" if i < n_oot_eff else "H99"
        price = Decimal(rng.choice(["8.8", "10.5", "17.25", "22.4", "31.2", "45", "64.5"]))
        shares = rng.randint(4, 90) * 1_000_000
        post = shares * rng.randint(3, 9)
        f3v = rng.uniform(1.1, 40.0)
        f3 = f"{f3v:.2f}"
        flag = rng.random() < 0.2
        a = str(rng.randint(1, 30) * 500_000) if flag else "0"
        if cohort == "OOT_OPEN":
            status = "FILTERED" if i < n_filtered else ("UNFILTERED" if rng.random() < oot_unfiltered_share else "NOT_SPECIFIED")
        else:
            status = "NOT_SPECIFIED" if rng.random() < 0.6 else "UNFILTERED"
        t = tufe.index_for(ftd, tt)
        real = float(price * shares) / (float(t["index"]) / 100)
        eta = 1.2 - 0.9 * (math.log(real) - 21.0) + 0.8 * (math.log(f3v) - 2.0) - 1.1 * flag + rng.gauss(0.0, 0.8)
        sessions = _business_days(start, 10)
        targets = {}
        for h, k in (("D1", 1), ("D3", 3), ("D5", 5), ("D10", 10)):
            up = 1 if rng.random() < 1.0 / (1.0 + math.exp(-(eta - 0.05 * k))) else 0
            R = Decimal(rng.randint(1, 900)) / Decimal(1000) if up else -Decimal(rng.randint(0, 400)) / Decimal(1000)
            close = str((price * (1 + R)).quantize(Decimal("0.01")))
            targets[h] = Target(R=str(R), Y=up, session_date=sessions[k - 1], close=close)
        L = rng.choice(range(0, 11))
        closes = [1] * L + ([0] * (10 - L))
        regime_date = (start - timedelta(days=7)).isoformat()
        tk = f"SYF{i:02d}"
        rows.append(IPORowV2(
            ticker=tk, first_trading_date=ftd, point_in_time_status="PASS",
            inputs={"ipo_price_tl": str(price), "shares_offered": str(shares), "post_ipo_share_capital": str(post),
                    "capital_increase_shares": str(shares // 2), "total_demand_multiple": f3, "ipo_size_tl": None},
            total_demand_filter_status=status, targets=targets, session_dates=tuple(sessions), ceiling_close=tuple(closes),
            ceiling_streak=L, cohort=cohort, alloc_regime=alloc_regime(regime_date), alloc_regime_date=regime_date,
            tufe_month=t["month"], tufe_index=t["index"],
        ))
        add_sale[tk] = a
    rows.sort(key=lambda r: (r.first_trading_date, r.ticker))
    h99_rows = [r for r in rows if r.cohort == "H99"]
    for r in rng.sample(h99_rows, n_as_missing):
        add_sale[r.ticker] = None
    for r in rng.sample([r for r in h99_rows if add_sale[r.ticker] is not None], n_f3_missing):
        idx = rows.index(r)
        rows[idx] = IPORowV2(**{**{k: getattr(r, k) for k in IPORowV2.__dataclass_fields__},
                                "inputs": {**r.inputs, "total_demand_multiple": None}, "total_demand_filter_status": None})
    ds = Dataset(rows=tuple(rows), data_version_sha256=tag, table_sha256=tag,
                 outcome_sessions_through=max(d for r in rows for d in r.session_dates))
    return ds, {r.ticker: add_sale[r.ticker] for r in rows}


def synthetic_spec(model_id: str, dataset: Dataset, add_sale: dict) -> dict:
    """Şartname kopyası; yalnız eğitim n'i, olay/kohort sayıları ve veri sürümü sentetik veriye göre (nihai fit ve koşuları sentetikte
    koşmak için)."""
    from borsai.data import select_fall_training_rows
    from borsai.specs import FAZ7C_MODEL_SPECS

    spec = json.loads(json.dumps(FAZ7C_MODEL_SPECS[model_id]))
    rows = select_fall_training_rows(dataset, spec["training"]["set"], add_sale)
    spec["training"].update(
        n=len(rows), data_version_sha256=dataset.data_version_sha256,
        events_D5=sum(1 for r in rows if r.targets["D5"].Y == 0), events_D10=sum(1 for r in rows if r.targets["D10"].Y == 0),
        cohort_counts={c: sum(1 for r in rows if r.cohort == c) for c in ("H99", "OOT_OPEN")})
    return spec


# ---------------------------------------------------------------- varyant sayacı istisnası (SPEC_DEVIATIONS K; J16/J30 kalıbı)

def faz7c_variants(data_version: str, log_path: Path = ROOT / "experiments" / "log.jsonl") -> int:
    """Aynı veri sürümünde günlüğe düşmüş Faz 7C varyant sayısı: Faz 7C modellerinin (model_id, spec_sha256) backtest satırları +
    keşif (`kind: exploration`) satırları. scores/ bu görevde yeniden üretilmediği için kartlardaki veri geneli sayaç tam olarak bu
    kadar geride kalır (H99 veri sürümünde 1: fall_d10_v0_h99; v2'de 3 + 2 054)."""
    from borsai.specs import FAZ7C_MODEL_SPECS

    seen = set()
    for line in Path(log_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        if e.get("data_version_sha256") != data_version:
            continue
        if e.get("kind") == "backtest" and e.get("model_id") in FAZ7C_MODEL_SPECS:
            seen.add((e["model_id"], e["spec_sha256"]))
        elif e.get("kind") == "exploration":
            seen.add(("exploration", e["source_sha256"], e["variant_id"]))
    return len(seen)


def h99_subset(dataset: Dataset, additional_sale: dict, tag: str = "synthetic_fall_h99") -> tuple[Dataset, dict[str, str | None]]:
    """Sentetik havuzun H99 satırları ayrı bir veri kümesi olarak (gerçekte training_table.csv = v2'nin H99 satırları): h99 ve havuz
    ledger'ları aynı test arzlarını taşır."""
    rows = tuple(r for r in dataset.rows if r.cohort == "H99")
    ds = Dataset(rows=rows, data_version_sha256=tag, table_sha256=tag,
                 outcome_sessions_through=max(d for r in rows for d in r.session_dates))
    return ds, {r.ticker: additional_sale[r.ticker] for r in rows}

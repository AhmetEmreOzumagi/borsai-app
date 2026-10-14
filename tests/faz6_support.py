"""Faz 6 (eski kohort altyapısı, BORSAI_FAZ6_OOT_INFRA) test yardımcıları: sentetik girdi belgeleri, kohort satırları, geçici
git deposu, push kanıtı ve sentetik THB/THM zip'leri. Gerçek repoya hiçbir şey yazılmaz; gerçek bülten indirilmez. Sentetik
kodlar gerçek kohort kodlarıyla çakışmaz (SYN*, ZZZZ)."""
from __future__ import annotations

import copy
import io
import json
import shutil
import subprocess
import zipfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

from borsai import outcomes as oc
from borsai import outcomes_oot as oo
from borsai import registry as reg
from borsai.provenance import ROOT, pretty_json_bytes, sha256_bytes

TEMPLATE = ROOT / "registry" / "inputs" / "CITAS.json"
SRC_BYTES = b"%PDF-1.4 synthetic faz6 source document\n"
ADDED_AT = "2026-09-24T23:00:00+03:00"
FILLER = "ZZZZ.E"                     # başka bir pay: bültende hep var, hiçbir çıktıya girmemeli
HEAD_THB = ["TARIH", "ISLEM  KODU", "BULTEN ADI", "PAZAR", "ENSTRUMAN GRUBU", "GECICI DURDURMA", "KAPANIS FIYATI",
            "TOPLAM SOZLESME SAYISI", *oc.THB_D1_COLUMNS.values()]
HEAD_THM = ["TARIH", "ISLEM  KODU", "REFERANS FIYATI", "UST LIMIT FIYATI", "ALT LIMIT FIYATI"]


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


def commit(root: Path, message: str, *paths: str) -> str:
    git(root, "add", "--", *paths)
    git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")


def iso(d: str, days: int) -> str:
    return (date.fromisoformat(d) + timedelta(days=days)).isoformat()


def inputs_doc(ticker: str, ftd: str, *, price: str = "10.5", f3: Optional[str] = "7.83", price_try: Optional[str] = None,
               published: Optional[str] = None) -> dict[str, Any]:
    """CITAS belgesinden türetilmiş sentetik eski kohort girdisi: bütün dolu alanlar tek sentetik kaynağa (ilk işlem gününden
    5 gün önce yayımlanmış) bağlı; tarih ve fiyat alanları verilen değerlerle."""
    doc = copy.deepcopy(json.loads(TEMPLATE.read_text(encoding="utf-8")))
    sid, path = "KAP_1", f"registry/oot/source_docs/{ticker}/KAP_1_bildirim.pdf"
    pub = published or f"{iso(ftd, -5)}T18:00:00+03:00"
    sha = sha256_bytes(SRC_BYTES)
    doc.update(ticker=ticker, company=f"{ticker} Sentetik A.Ş.", first_trading_date_source=sid,
               sources={sid: {"kind": "KAP_NOTIFICATION_PDF", "document_id": "KAP 1", "published_at": pub, "sha256": sha,
                              "path": path}})
    values = {"first_trading_date": ftd, "bookbuilding_start": iso(ftd, -9), "bookbuilding_end": iso(ftd, -7),
              "ipo_price_tl": price, "ipo_price_try": price_try or price, "total_demand_multiple": f3}
    for name, f in doc["fields"].items():
        if name in values:
            f["value"] = values[name]
        if f.get("value") is None:
            f.update(missing_reason="SENTETIK_TEST")
            for k in reg.FIELD_SOURCE_KEYS:
                f.pop(k, None)
            continue
        f.update(source_id=sid, source_document="KAP 1", source_published_at=pub, source_sha256=sha, source_path=path)
    return doc


def cohort_row(doc: Mapping[str, Any], *, sessions: Sequence[str], market: str = "YILDIZ",
               sale_method: str = reg.SALE_OFF_EXCHANGE, vault: str = reg.VAULT_OPEN, kap_id: int = 1) -> dict[str, str]:
    f = doc["fields"]
    ftd = f["first_trading_date"]["value"]
    tags = reg.compute_regime_tags(first_trading_date=ftd, market=market, sale_method=sale_method,
                                   ipo_price_tl=f["ipo_price_tl"]["value"], ipo_price_try=f["ipo_price_try"]["value"],
                                   bookbuilding_start=f["bookbuilding_start"]["value"], sessions=sessions, vault=vault)
    return {"ticker": doc["ticker"], "company": doc["company"], "first_trading_date": ftd, "listing_source_id": f"KAP_{kap_id}",
            "listing_source_sha256": "a" * 64, "sale_method": sale_method, "market": market, "year": ftd[:4],
            "status": reg.COHORT_MEMBER, "reason": "", "vault": vault, "regime_tags": reg.format_regime_tags(tags),
            "added_at": ADDED_AT}


OOS_ROW = {"ticker": "SYNOS", "company": "Kapsam Dışı A.Ş.", "first_trading_date": "2021-03-01", "listing_source_id": "KAP_9",
           "listing_source_sha256": "b" * 64, "sale_method": reg.SALE_METHOD_NONE, "market": "ALT", "year": "2021",
           "status": reg.COHORT_OUT_OF_SCOPE, "reason": "HALKA_ARZSIZ_KOTASYON (sentetik)", "vault": "", "regime_tags": "",
           "added_at": ADDED_AT}


def write_members(root: Path, members: Sequence[Mapping[str, Any]], *, sessions: Sequence[str],
                  with_oos: bool = True) -> list[dict[str, str]]:
    """members: {ticker, ftd, [price, f3, price_try, market, sale_method, vault, published]} -> kohort + girdi + belge dosyaları."""
    rows = []
    for i, m in enumerate(members, start=1):
        doc = inputs_doc(m["ticker"], m["ftd"], price=m.get("price", "10.5"), f3=m.get("f3", "7.83"),
                         price_try=m.get("price_try"), published=m.get("published"))
        d = root / "registry" / "oot"
        (d / "inputs").mkdir(parents=True, exist_ok=True)
        (d / "inputs" / f"{m['ticker']}.json").write_bytes(pretty_json_bytes(doc))
        (d / "source_docs" / m["ticker"]).mkdir(parents=True, exist_ok=True)
        (d / "source_docs" / m["ticker"] / "KAP_1_bildirim.pdf").write_bytes(SRC_BYTES)
        rows.append(cohort_row(doc, sessions=sessions, market=m.get("market", "YILDIZ"),
                               sale_method=m.get("sale_method", reg.SALE_OFF_EXCHANGE), vault=m.get("vault", reg.VAULT_OPEN),
                               kap_id=i))
    if with_oos:
        rows.append(dict(OOS_ROW))
    (root / "registry" / "oot" / "cohort_pre_h99.csv").write_bytes(reg.cohort_bytes(rows))
    return rows


def init_repo(tmp_path: Path, *, with_models: bool = False) -> Path:
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    git(root, "init", "-q")
    # Arka plan otomatik bakımı (gc/repack) kapalı: modül fixture'ı depoyu shutil.copytree ile klonlarken nesneleri taşır ve
    # kopya "No such file or directory" ile kırılır (yük altında ~%8; sıralı koşuda da görüldü).
    git(root, "config", "gc.auto", "0")
    git(root, "config", "maintenance.auto", "false")
    if with_models:
        shutil.copytree(ROOT / "models", root / "models")
        commit(root, "models", "models")
    return root


def make_proof(root: Path, sha: str, created_at: str) -> Path:
    """Biçimi `push_proof.validate_proof`'tan geçen sentetik kanıt (ağ yok)."""
    doc = {"schema_version": "borsai.push_proof/1", "proven_commit_sha": sha, "repo_slug": "t/t",
           "method": "GITHUB_COMMIT_STATUS_CREATED_AT", "created_at": created_at, "auth": "test",
           "github_response": {"created_at": created_at, "url": f"https://api.github.com/repos/t/t/statuses/{sha}"}}
    p = root / "registry" / "push_proofs" / f"{sha}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(pretty_json_bytes(doc))
    return p


# ---------------------------------------------------------------- sentetik bültenler

def make_zip(day: str, kind: str, rows: Iterable[Sequence[str]]) -> bytes:
    head = HEAD_THB if kind == "thb" else HEAD_THM
    lines = [head, [h.lower() for h in head]] + [[day] + list(r) for r in rows]
    text = "\n".join(";".join(r) for r in lines) + "\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(oc.internal_name(day, kind), text.encode("cp1254"))
    return buf.getvalue()


def thb_row(code: str, close: str, trades: str = "10", halt: str = "0", name: str = "SENTETIK") -> list[str]:
    # BULTEN ADI, PAZAR, ENSTRUMAN GRUBU, GECICI DURDURMA, KAPANIS, SOZLESME + D1 alanları (açılış, en yüksek, en düşük, adet,
    # hacim, AOF, özel adet, özel hacim)
    return [code, name, "Y", "EQT", halt, close, trades, close, close, close, "1000", "10000", close, "0", "0"]


def thm_row(code: str, ref: str, upper: str, lower: str) -> list[str]:
    return [code, ref, upper, lower]


def market(sessions: Sequence[str], paths: Mapping[str, Mapping[str, tuple[str, str, str]]]) -> dict[str, bytes]:
    """URL -> zip baytları. paths: ticker -> {gün: (kapanış, sözleşme, üst limit)}; her bültende FILLER da var."""
    files = {}
    for s in sessions:
        thb = [thb_row(FILLER, "5.00")]
        thm = [thm_row(FILLER, "5.00", "5.50", "4.50")]
        for t, days in paths.items():
            if s in days:
                close, trades, upper = days[s]
                thb.append(thb_row(oc.equity_code(t), close, trades))
                thm.append(thm_row(oc.equity_code(t), close, upper, "1.00"))
        files[oc.source_url(s, "thb")] = make_zip(s, "thb", thb)
        files[oc.source_url(s, "thm")] = make_zip(s, "thm", thm)
    return files


class FakeDownloader:
    def __init__(self, files: Mapping[str, bytes]):
        self.files, self.calls = dict(files), []

    def __call__(self, url: str) -> tuple[bytes, str]:
        self.calls.append(url)
        if url not in self.files:
            raise oc.NotPublished(url)
        return self.files[url], "Tue, 22 Sep 2020 15:00:00 GMT"


def ceiling_path(sessions: Sequence[str], start: str, closes: Sequence[str], uppers: Optional[Sequence[str]] = None
                 ) -> dict[str, tuple[str, str, str]]:
    """start'tan itibaren ardışık seanslarda (kapanış, sözleşme = 10, üst limit)."""
    days = [s for s in sessions if s >= start][:len(closes)]
    uppers = uppers or closes
    return {d: (c, "10", u) for d, c, u in zip(days, closes, uppers)}


def oot_calendar() -> oc.SessionCalendar:
    return oo.load_calendar_oot()

"""Eski kohort (Faz 6) sonuç verisi: karantina ve ayıklama. KARARLAR D6 (şartname §2 S3/S5 ve G5'in yerine); tanımlar
SPEC_SCORING §2–§3 ve `borsai/outcomes.py` ile aynı. Yalnız stdlib. Gerçek veriyle yalnız CLI üzerinden çağrılır
(`python -m borsai.outcomes_oot {probe|calendar-evidence|s3|s3-post-d1|s5}`, BORSAI_FAZ6_S3_S5_EXTRACT ve EK1;
SPEC_DEVIATIONS I28–I38).

Kurallar:
1. Kohort penceresindeki (2020-01-01…2023-09-21 ve D_10'ları) THB/THM zip'leri repoya GİRMEZ. Repo dışındaki karantina
   dizinine indirilir (`quarantine_dir`; varsayılan ~/Desktop/BorsAi_quarantine, `BORSAI_QUARANTINE_DIR` ile değişir; repo
   içinde bir yol reddedilir). Karantinanın kendi MANIFEST'i (karantina/MANIFEST.csv) repo dışındadır.
2. İndirme kapısı (`download_gate`), model başına (SPEC_HAZARD_V1 §7.3): models/INDEX.json'daki her model ve kohortun her
   MEMBER'ı için o modeli içeren birincil kayıt (registry/oot/records/<T>/; en erken etkin kayıt) commit'li, çalışma kopyasında
   değişmemiş VE kayıt commit'ini kapsayan bir push kanıtı var. Değilse hiçbir bülten indirilmez (`GateError`). Kirlilik
   denetimi S3 çıktılarını (`registry/oot/d1_rows/`, `registry/oot/post_d1/`) ve kasa işaret dosyasını (`VAULT_MARKER_REL`)
   saymaz: yarım kalan bir S3 ya da `vault-d1` koşusu kapıyı kapatmaz; bekçileri ayrıdır (G1/G3, `d1_rows_problems`, M-E).
3. Ayıklayıcı yalnız AÇIK kümenin (OPEN ∪ EXPOSED_*) kodlarının `<T>.E` satırlarını ve yalnız o üyenin D_1…D_10 penceresindeki
   seansları okur (bülten satırları taranır, yalnız hedef kodun satırı tutulur; başka satır hiçbir dosyaya, günlüğe ya da
   ekrana yazılmaz). SEALED bir kod istenirse bülten açılmadan `SealedAccessError` (kasa açılışı hariç: `open_vault`).
   Savunma (`assert_window_bound`): çözümlenen seans sayısı ≤ N_SESSIONS ve pencere dolduysa D_10'dan sonraki hiçbir seansın
   bülteni okunmamış; aksi halde ham kopya ve sonuç yazılmaz.
4. Çıktılar (repoda): `data/outcomes_oot/<T>.csv` (sütunlar `outcomes.OUTCOME_COLUMNS` + `outcome_basis`; anlam aynen,
   `outcome_basis = MACHINE_EXTRACTED`: makine gördü, insan görmedi), `data/outcomes_oot/raw/<T>.json` (ham alan kopyaları, yalnız
   `<T>.E`), `data/raw/bist/MANIFEST_OOT.csv` (her zip'in tarih, tür, URL, sha256, bayt, Last-Modified, indirme zamanı).
   S3: `registry/oot/d1_rows/<T>.json` (yalnız D_1 satırı).
5. D_1 (şartname §1): KAP bildirimindeki ilk işlem gününden (first_trading_date) ÖNCE olmayan, `<T>.E` satırında sözleşme > 0
   ve kapanış > 0 olan ilk resmi seans (`outcomes.resolve_sessions`, start = first_trading_date; 15 seans sınırı ilk görünüşten).
6. Sonuç takvimi (EK1): Takvim C (2020-01-01…2023-09-21) ∪ bülten kanıtında TRADING_SESSION olan kapanış günleri ∪ H99
   takvimi (2023-09-22…) ∪ Faz 2A uzatması; ilan dışı kapanışlar düşülmüş. Takvim C dosyası f6'nındır, değişmez. Kanıt
   dosyası (`calendar-evidence`) Takvim C'nin her hafta içi kapanışı için HEAD ve bülten toplam sayılarını pinler; indirmeden
   önce prob (`check_calendar_closures`) her kapanışı kanıta karşı denetler (kanıt yoksa 5 XU100-boşluk günü; yayımlanmışsa
   DUR). Uyuşmazlık -> `CalendarConflict`.
7. Kasa açılışı (`open_vault`): ön-kayıtlı belgeler (SPEC_HAZARD_V1, KARARLAR, SPEC_C_V0, KARARLAR_C) commit'li, değişmemiş
   ve push kanıtlı olmalı; model başına indirme kapısı açık olmalı (kural 2); MANIFEST_OOT'taki her zip yeniden indirilir ve pinli
   sha256'yla eşleşmelidir; sonra SEALED satırlar ayıklanabilir.
8. Sıra (SPEC_DEVIATIONS I10, I13): S3a (d1_rows + pinler) -> S3b (eski kohort POST_D1 kayıtları) -> push + kanıt -> S5. S5
   kapısı (`s3_gate_problems`): açık kümenin her üyesinin D_1 satırı dosyası ve POST_D1 kaydı commit'li, değişmemiş ve push
   kanıtlı; değilse S5'te hiçbir bülten indirilmez. `extract_d1_rows` yeniden koşuya dayanıklıdır (aynı bayt -> UNCHANGED).
9. Kasanın tek seferlik açılışı (BORSAI_FAZ7_VAULT_OPEN; SPEC_DEVIATIONS M): `vault-d1` (M-B kapısı -> takvim probu -> `open_vault`
   -> kasa üyelerinin yalnız D_1'e kadar ayıklanması -> d1_rows + pinler -> işaret dosyası registry/oot/VAULT_OPEN.json, en son)
   -> `vault-post-d1` (kasa üyelerinin POST_D1 kayıtları) -> push + kanıt -> `vault-s5` (B kapısı `vault_s3_gate_problems` ->
   D_1…D_10). Kasa ayıklamasında okunan her zip o koşuda resmi kaynaktan indirilir (`VaultFetcher`); SEALED satır ancak
   `VaultUnsealed` yetkisiyle okunur (`open_vault` ya da commit'li ve push kanıtlı işaret dosyası). Kasa kodları çıktıya yazılmaz.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

from . import market20 as m20
from . import outcomes as oc
from . import registry as reg
from .provenance import ISTANBUL, ROOT, git_state, pretty_json_bytes, sha256_bytes, sha256_file, source_tree_sha256

QUARANTINE_ENV = "BORSAI_QUARANTINE_DIR"
DEFAULT_QUARANTINE = Path.home() / "Desktop" / "BorsAi_quarantine"
OUTCOMES_OOT_DIR = ROOT / "data" / "outcomes_oot"
RAW_COPIES_NAME = "raw"
MANIFEST_OOT_PATH = ROOT / "data" / "raw" / "bist" / "MANIFEST_OOT.csv"
MANIFEST_OOT_COLUMNS = ("date", "kind", "url", "sha256", "bytes", "http_last_modified", "downloaded_at", "internal_filename")
OUTCOME_BASIS = "MACHINE_EXTRACTED"
OOT_OUTCOME_COLUMNS = oc.OUTCOME_COLUMNS + ("outcome_basis",)
D1_ROW_SCHEMA = "borsai.oot_d1_row/1"
EXPOSURE_MACHINE_SEQUENCED = "MACHINE_SEQUENCED"
MAX_APPEARANCE_WAIT = oc.MAX_SEEN     # ilk işlem gününden sonra kod bu kadar seansta görünmezse DUR (D_1 bulunamadı)
S3_OUTPUT_DIRS = ("registry/oot/d1_rows", "registry/oot/post_d1")        # S5 kapısının denetlediği S3 çıktıları
VAULT_MARKER_REL = "registry/oot/VAULT_OPEN.json"                           # kasa işaret dosyası (M-D); bekçileri ayrı (M-E)
S2_GATE_DIRT_EXCLUDED = S3_OUTPUT_DIRS + (VAULT_MARKER_REL,)               # kapının kirlilik denetimi dışında (S3 ve kasa çıktıları)
MANIFEST_OOT_REL = "data/raw/bist/MANIFEST_OOT.csv"


class OotOutcomeError(RuntimeError):
    pass


class QuarantineError(OotOutcomeError):
    pass


class GateError(OotOutcomeError):
    """İndirme kapısı kapalı: kohortun S2 kayıtları commit'li ve push kanıtlı değil (KARARLAR D6-5)."""


class SealedAccessError(OotOutcomeError):
    """Kasadaki (SEALED) bir kodun satırı istendi (KARARLAR D6-3)."""


class CalendarConflict(OotOutcomeError):
    """Takvim C'de kapanış sayılan bir günün bülteni yayımlanmış (XU100-boşluk kapanışı yanlış)."""


# ============================================================ karantina ve takvim

def quarantine_dir(path: Optional[Path] = None, *, repo_root: Path = ROOT) -> Path:
    """Karantina dizini: argüman > BORSAI_QUARANTINE_DIR > ~/Desktop/BorsAi_quarantine. Repo içinde olamaz."""
    q = Path(path or os.environ.get(QUARANTINE_ENV) or DEFAULT_QUARANTINE).expanduser().resolve()
    root = Path(repo_root).resolve()
    if q == root or root in q.parents:
        raise QuarantineError(f"karantina dizini repo içinde olamaz: {q}")
    return q


def load_calendar_oot(*, bist_dir: Path = oc.BIST_DIR, evidence_path: Optional[Path] = None) -> oc.SessionCalendar:
    """Sonuç takvimi (EK1 K2; SPEC_DEVIATIONS I34): Takvim C seansları ∪ bülten kanıtında TRADING_SESSION olan günler ∪ H99
    takvimi ∪ Faz 2A uzatması (ardışık; ilan dışı kapanışlar düşülmüş; yarım günler değişmez). Takvim C dosyası ve market20
    sabitleri f6'nın takvimidir ve değişmez (K1). Kanıt dosyası (varsayılan `bist_dir`'in üst dizininde) yoksa sonuç takvimi
    Takvim C'dir. sha'lar pinli değerlerle; kanıt dosyasının sha'sı takvim sha'sına girer."""
    c = m20.load_calendar_c()
    rest = oc.load_calendar(bist_dir=bist_dir, apply_closures=False)
    if date.fromisoformat(rest.first_day) - date.fromisoformat(c.last_date) != timedelta(days=1):
        raise OotOutcomeError(f"Takvim C ({c.last_date}) ile H99 takvimi ({rest.first_day}) ardışık değil")
    path = Path(evidence_path) if evidence_path is not None else Path(bist_dir).parent / CAL_EVIDENCE_NAME
    trading: list[str] = []
    shas = [c.sha256]
    if path.exists():
        closures = {d for d, _ in calendar_c_weekday_closures(c)}
        trading = [r["date"] for r in read_calendar_evidence(path) if r["decision"] == EV_TRADING_SESSION]
        stray = [d for d in trading if d not in closures]
        if stray:
            raise OotOutcomeError(f"kanıtta TRADING_SESSION olan gün Takvim C'nin hafta içi kapanışı değil: {stray}")
        shas.append(sha256_file(path))
    sessions = tuple(sorted(set(c.sessions) | set(trading)))
    cal = oc.SessionCalendar(sessions + rest.sessions, m20.half_days_c() | rest.half_days, c.days[0], rest.last_day,
                             sha256="+".join(shas + [rest.sha256]))
    return cal.without(r["date"] for r in oc.read_closures(bist_dir))


# ============================================================ Takvim C kapanışları için bülten kanıtı (EK1; I34–I38)
#
# Yayımlanmış bülten işlem olduğunu göstermez: kapalı bir günde işlemsiz bülten yayımlanabilir. Ölçüt o gün işlem yapılıp
# yapılmadığıdır; bülten açılır, yalnız TOPLAM sayılar tutulur (satır, kod, fiyat tutulmaz, yazılmaz, basılmaz).

CAL_EVIDENCE_NAME = "pay_calendar_c_bulletin_evidence_20200101_20230921.csv"
CAL_EVIDENCE_REL = f"data/raw/{CAL_EVIDENCE_NAME}"
CAL_EVIDENCE_COLUMNS = ("date", "source", "thb_head_status", "thb_sha256", "thb_bytes", "n_rows", "n_equity_rows",
                        "n_equity_rows_traded", "decision", "checked_at_istanbul")
CAL_EVIDENCE_COUNTS = ("n_rows", "n_equity_rows", "n_equity_rows_traded")
SOURCE_HOLIDAY_TABLE, SOURCE_XU100_GAP = "HOLIDAY_TABLE", "XU100_GAP"
EV_NOT_PUBLISHED, EV_PUBLISHED_NO_TRADING, EV_TRADING_SESSION = "NOT_PUBLISHED", "PUBLISHED_NO_TRADING", "TRADING_SESSION"
EV_DECISIONS = (EV_NOT_PUBLISHED, EV_PUBLISHED_NO_TRADING, EV_TRADING_SESSION)
TRADING_SESSION_MIN_TRADED = 50          # K4: ≥ 50 işlemli pay satırı -> seans; 1–49 -> DUR


def calendar_c_weekday_closures(c: Optional[m20.Calendar] = None) -> list[tuple[str, str]]:
    """Takvim C'nin hafta içi bütün tam kapanışları, (gün, kaynak) artan: tatil tablosu ya da XU100 boşluğu (K3)."""
    c = c or m20.load_calendar_c()
    sessions = set(c.sessions)
    table = {d for t in m20.HOLIDAY_TABLES_2020_2023.values() for d in t["full"]}
    gaps = set(m20.XU100_GAP_CLOSURES)
    out = []
    for d in c.days:
        if date.fromisoformat(d).weekday() >= 5 or d in sessions:
            continue
        source = SOURCE_XU100_GAP if d in gaps else SOURCE_HOLIDAY_TABLE if d in table else None
        if source is None:
            raise OotOutcomeError(f"{d}: Takvim C kapanışının kaynağı (tatil tablosu ya da XU100 boşluğu) yok")
        out.append((d, source))
    return out


def bulletin_trade_counts(data: bytes, market_date: str) -> dict[str, int]:
    """K3 sayıları: toplam veri satırı, `.E` satırı, TOPLAM SOZLESME SAYISI > 0 olan `.E` satırı. Hiçbir satır, kod ya da fiyat
    tutulmaz. Bülten geçerliliği `outcomes.parse_bulletin` ile aynı: tek iç dosya (beklenen ad), iki başlık satırı aynı
    genişlikte, her veri satırı başlık genişliğinde ve TARIH'i bülten günü; aksi halde OotOutcomeError (DUR)."""
    expected = oc.internal_name(market_date, "thb")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if archive.namelist() != [expected]:
            raise OotOutcomeError(f"THB {market_date}: ZIP iç dosya adı beklenen değil")
        text = archive.read(expected).decode("cp1254")
    reader = csv.reader(io.StringIO(text.lstrip("﻿")), delimiter=";")
    headers, english = next(reader, None), next(reader, None)
    if headers is None or english is None or len(headers) != len(english):
        raise OotOutcomeError(f"THB {market_date}: iki başlık satırı yok ya da genişlikleri farklı")
    missing = sorted({"ISLEM  KODU", "TARIH", "TOPLAM SOZLESME SAYISI"} - set(headers))
    if missing:
        raise OotOutcomeError(f"THB {market_date}: zorunlu sütunlar yok: {missing}")
    i_code, i_date, i_tc = headers.index("ISLEM  KODU"), headers.index("TARIH"), headers.index("TOPLAM SOZLESME SAYISI")
    n = n_eq = n_traded = 0
    for r in reader:
        if not any(cell != "" for cell in r):
            continue
        if len(r) != len(headers) or r[i_date] != market_date:
            raise OotOutcomeError(f"THB {market_date}: bir veri satırının genişliği ya da TARIH'i bültenle tutarsız (DUR)")
        n += 1
        if r[i_code].endswith(".E"):
            n_eq += 1
            tc = oc.dec(r[i_tc])
            n_traded += int(tc is not None and tc > 0)
    return {"n_rows": n, "n_equity_rows": n_eq, "n_equity_rows_traded": n_traded}


def evidence_decision(head_status: int, n_equity_rows_traded: Optional[int]) -> str:
    """K4 (önceden yazılmış, tek tanım): HEAD 404 -> NOT_PUBLISHED; 200 ve 0 işlemli pay satırı -> PUBLISHED_NO_TRADING;
    200 ve ≥ 50 -> TRADING_SESSION; 1–49 ya da başka HEAD kodu -> OotOutcomeError (DUR)."""
    if head_status == 404:
        return EV_NOT_PUBLISHED
    if head_status != 200:
        raise OotOutcomeError(f"HEAD {head_status} (200 ya da 404 değil; DUR)")
    if n_equity_rows_traded == 0:
        return EV_PUBLISHED_NO_TRADING
    if n_equity_rows_traded is not None and n_equity_rows_traded >= TRADING_SESSION_MIN_TRADED:
        return EV_TRADING_SESSION
    raise OotOutcomeError(f"işlemli pay satırı {n_equity_rows_traded} (1–{TRADING_SESSION_MIN_TRADED - 1}): K4 karar "
                          f"kuralının dışında, DUR")


def evidence_problems(rows: Sequence[Mapping[str, str]]) -> list[str]:
    """Kanıt satırlarının biçimi ve kararların K4'le (`evidence_decision`) tutarlılığı."""
    out: list[str] = []
    dates = [r["date"] for r in rows]
    if dates != sorted(set(dates)):
        out.append("günler artan ve tekil değil")
    for r in rows:
        d = r["date"]
        if r["source"] not in (SOURCE_HOLIDAY_TABLE, SOURCE_XU100_GAP) or not r["checked_at_istanbul"]:
            out.append(f"{d}: kaynak ya da checked_at")
        filled = [r[k] for k in ("thb_sha256", "thb_bytes", *CAL_EVIDENCE_COUNTS)]
        if r["thb_head_status"] == "404":
            if any(filled) or r["decision"] != EV_NOT_PUBLISHED:
                out.append(f"{d}: 404 satırında sha/bayt/sayı dolu ya da karar NOT_PUBLISHED değil")
            continue
        if r["thb_head_status"] != "200" or len(r["thb_sha256"]) != 64 or not all(v.isdigit() for v in filled[1:]):
            out.append(f"{d}: HEAD durumu, sha256, bayt ya da sayılar geçersiz")
            continue
        n, n_eq, n_traded = (int(r[k]) for k in CAL_EVIDENCE_COUNTS)
        if not n_traded <= n_eq <= n:
            out.append(f"{d}: sayılar tutarsız")
        try:
            decision = evidence_decision(200, n_traded)
        except OotOutcomeError as exc:
            decision = f"DUR ({exc})"
        if r["decision"] != decision:
            out.append(f"{d}: karar {r['decision']} K4 kuralıyla ({decision}) aynı değil")
    return out


def evidence_bytes(rows: Sequence[Mapping[str, str]]) -> bytes:
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=CAL_EVIDENCE_COLUMNS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r[k] for k in CAL_EVIDENCE_COLUMNS})
    return buf.getvalue().encode("utf-8")


def read_calendar_evidence(path: Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != CAL_EVIDENCE_COLUMNS:
            raise OotOutcomeError(f"{Path(path).name}: sütunlar {reader.fieldnames}")
        rows = list(reader)
    problems = evidence_problems(rows)
    if problems:
        raise OotOutcomeError(f"{Path(path).name} geçmedi: " + "; ".join(problems[:5]))
    return rows


def calendar_evidence_rows(*, qdir: Path, downloader: Optional[Downloader] = None, head: Optional[Head] = None,
                           now: Optional[datetime] = None) -> list[dict[str, str]]:
    """K3: Takvim C'nin her hafta içi tam kapanışı için THB HEAD; 200 dönen günün zip'i karantinaya (`fetch_quarantine`,
    önbellek) ve yalnız toplam sayılar. Kapı ÇAĞIRANIN işidir (`calendar-evidence` komutu önce `download_gate` koşar)."""
    head = head or head_status
    rows = []
    for d, source in calendar_c_weekday_closures():
        r = dict(head(oc.source_url(d, "thb")))
        status = int(r["status"])
        if status not in (200, 404):
            raise OotOutcomeError(f"{d}: HEAD {status} (200 ya da 404 değil; GET denenmez, DUR): Content-Type "
                                  f"{r.get('content_type', '')!r}, Content-Length {r.get('content_length', '')!r}")
        row = {k: "" for k in CAL_EVIDENCE_COLUMNS}
        row.update(date=d, source=source, thb_head_status=str(status), checked_at_istanbul=oc._now_istanbul(now))
        traded = None
        if status == 200:
            data, pin = fetch_quarantine(d, "thb", qdir=qdir, downloader=downloader, now=now)
            counts = bulletin_trade_counts(data, d)
            row.update(thb_sha256=pin.sha256, thb_bytes=str(pin.bytes), **{k: str(v) for k, v in counts.items()})
            traded = counts["n_equity_rows_traded"]
        row["decision"] = evidence_decision(status, traded)
        rows.append(row)
    return rows


def write_calendar_evidence(rows: Sequence[Mapping[str, str]], path: Path) -> str:
    """CREATED ('xb') | UNCHANGED. Var olan dosya checked_at dışında yeni ölçümle aynıysa dokunulmaz (ilk yazım korunur);
    farklıysa OotOutcomeError (DUR; dosya elle düzenlenmez, üzerine yazılmaz)."""
    problems = evidence_problems(rows)
    if problems:
        raise OotOutcomeError("kanıt satırları geçmedi: " + "; ".join(problems[:5]))
    path = Path(path)
    if path.exists():
        strip = lambda rs: [{k: r[k] for k in CAL_EVIDENCE_COLUMNS if k != "checked_at_istanbul"} for r in rs]  # noqa: E731
        if strip(read_calendar_evidence(path)) == strip(rows):
            return "UNCHANGED"
        raise OotOutcomeError(f"{path.name}: var olan kanıt dosyası (checked_at hariç) yeni ölçümle aynı değil (DUR)")
    oc._write_new(path, evidence_bytes(rows))
    return "CREATED"


# ============================================================ indirme kapısı (KARARLAR D6-5)

def _git(root: Path, *args: str) -> str:
    import subprocess

    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout


def s2_gate_problems(*, root: Path = ROOT, proofs: Optional[Sequence[Mapping[str, Any]]] = None) -> list[str]:
    """Boş liste = kapı açık. Model başına kapı (SPEC_HAZARD_V1 §7.3; SPEC_C_V0 §7.1-4; SPEC_DEVIATIONS L): models/INDEX.json'daki
    HER model m ve kohortun HER MEMBER'ı a için m'yi içeren birincil kayıt (`freeze.oot_primary_of`: m'yi içeren en erken etkin
    kayıt; skorlamanın seçtiği kayıt) var, commit'li ve değişmemiş, onu ekleyen commit'i kapsayan push kanıtı var. İndirme ingest'ten
    önce olduğundan ingest kanıtı kayıt kanıtından sonra gelir; skorlamadaki eşi `scoring.cohort_gate_ok` (ata + kanıt sırası).
    Etkin kaydı hiç olmayan üye "S2 kaydı yok"; kaydı olan ama bir modeli içeren kaydı olmayan üye tek satırda sayıyla yazılır."""
    from . import push_proof as pp
    from . import scoring as sc

    root = Path(root)
    proofs = list(pp.load_proofs(root / "registry" / "push_proofs")) if proofs is None else list(proofs)
    header, rows = reg.read_cohort(root / "registry" / "oot" / "cohort_pre_h99.csv")
    problems = [f"kohort: {p}" for p in reg.validate_cohort(header, rows)]
    index_ids = [e["model_id"] for e in json.loads((root / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]]
    git = sc.Git(root)
    tracked = set(_git(root, "ls-files", "--", "registry/oot/records").splitlines())
    dirty = _git(root, "status", "--porcelain", "--untracked-files=all", "--", "registry/oot",
                 *(f":(exclude){p}" for p in S2_GATE_DIRT_EXCLUDED)).strip()
    if dirty:
        problems.append(f"registry/oot temiz değil: {dirty[:200]}")
    from . import freeze as fz

    for r in reg.cohort_members(rows):
        recs = fz.active_records(r["ticker"], root / "registry" / "oot" / "records")
        if not recs:
            problems.append(f"{r['ticker']}: S2 kaydı yok")
            continue
        primaries: dict[Path, None] = {}
        missing = []
        for m in index_ids:
            prim = fz.oot_primary_of(recs, m)
            if prim is None:
                missing.append(m)
            else:
                primaries.setdefault(prim[0], None)
        if missing:
            problems.append(f"{r['ticker']}: {len(missing)} model için etkin kayıt yok ({', '.join(missing[:3])}"
                            + (" …)" if len(missing) > 3 else ")"))
        for p in primaries:
            rel = p.relative_to(root).as_posix()
            if rel not in tracked:
                problems.append(f"{rel}: commit'li değil")
                continue
            if sc.proof_time(git, git.added_commit(rel), proofs) is None:
                problems.append(f"{rel}: push kanıtı yok")
    return problems


def download_gate(*, root: Path = ROOT, proofs: Optional[Sequence[Mapping[str, Any]]] = None) -> None:
    problems = s2_gate_problems(root=root, proofs=proofs)
    if problems:
        raise GateError("karantina indirmesi başlamaz (KARARLAR D6-5): " + "; ".join(problems[:5])
                        + (f" … (+{len(problems) - 5})" if len(problems) > 5 else ""))


# ============================================================ S5 kapısı (SPEC_DEVIATIONS I30)

def oot_post_d1_primary(ticker: str, post_dir: Path) -> Optional[tuple[Path, dict[str, Any]]]:
    """Skorlamanın kullandığı eski kohort POST_D1 kaydı: en erken etkin kayıt (`scoring.oot_post_d1_block` ile aynı kural)."""
    from . import freeze as fz

    recs = fz.active_records(ticker, Path(post_dir))
    return min(recs, key=lambda x: (x[1]["recorded_at_utc"], x[0].name)) if recs else None


def _cup_problem(rel: str, committed: set[str], changed: set[str], git: Any, proofs: Sequence[Mapping[str, Any]]) -> Optional[str]:
    """commit'li / değişmemiş / push kanıtlı denetiminin sorun türü (yol yazmadan) ya da None."""
    from . import scoring as sc

    if rel not in committed:
        return "commit'li değil"
    if rel in changed:
        return "commit'ten sonra değişmiş"
    if sc.proof_time(git, git.added_commit(rel), proofs) is None:
        return "push kanıtı yok"
    return None


def _committed_unchanged_proven(rel: str, committed: set[str], changed: set[str], git: Any,
                                proofs: Sequence[Mapping[str, Any]]) -> list[str]:
    """`committed`: HEAD ağacındaki yollar (sahnelenmiş ama commit'lenmemiş dosya commit'li sayılmaz)."""
    kind = _cup_problem(rel, committed, changed, git, proofs)
    return [] if kind is None else [f"{rel}: {kind}"]


def s3_gate_problems(*, root: Path = ROOT, proofs: Optional[Sequence[Mapping[str, Any]]] = None) -> list[str]:
    """Boş liste = S5 başlayabilir. Açık kümenin (OPEN ∪ EXPOSED_*) her üyesi için:
    (a) registry/oot/d1_rows/<T>.json commit'li, değişmemiş, onu ekleyen commit'i kapsayan push kanıtı var ve `d1_rows_problems`
        HEAD'deki (commit'li) MANIFEST_OOT'a karşı boş;
    (b) registry/oot/post_d1/<T>/ altında etkin bir kayıt var; skorlamanın seçeceği kayıt (`oot_post_d1_primary`) commit'li,
        değişmemiş, push kanıtlı ve D_1 satırı dosyasının kanonik sha'sını taşıyor.
    Neden: POST_D1 kaydı D_2+ sonuçtan önce push kanıtlı değilse `scoring.class_oot` onu OOT_RETRO sayar (I13). S3 çıktı
    dizinlerindeki izlenmeyen dosyalar ve açık küme dışındaki adlar yalnız SAYI olarak yazılır (kasadaki bir kodu göstermez)."""
    import subprocess

    from . import push_proof as pp
    from . import scoring as sc
    from .provenance import canonical_sha256

    root = Path(root)
    proofs = list(pp.load_proofs(root / "registry" / "push_proofs")) if proofs is None else list(proofs)
    git = sc.Git(root)
    open_members = [t for t, v in _vault_map(root).items() if reg.is_open(v)]
    d1_dir, post_dir = root / S3_OUTPUT_DIRS[0], root / S3_OUTPUT_DIRS[1]
    committed = set(_git(root, "ls-tree", "-r", "--name-only", "HEAD", "--", *S3_OUTPUT_DIRS).splitlines())
    status = _git(root, "status", "--porcelain", "--untracked-files=all", "--", *S3_OUTPUT_DIRS).splitlines()
    changed = {line[3:] for line in status if line and not line.startswith("??")}
    problems: list[str] = []
    n_untracked = sum(line.startswith("??") for line in status)
    if n_untracked:
        problems.append(f"S3 çıktı dizinlerinde izlenmeyen {n_untracked} dosya")
    names = [p.stem for p in d1_dir.glob("*.json")]
    names += [p.name for p in post_dir.iterdir() if p.is_dir()] if post_dir.exists() else []
    outside = sum(n not in set(open_members) for n in names)
    if outside:
        problems.append(f"S3 çıktı dizinlerinde açık küme dışında {outside} ad")
    try:
        manifest = list(csv.DictReader(io.StringIO(_git(root, "show", f"HEAD:{MANIFEST_OOT_REL}"))))
    except subprocess.CalledProcessError:
        manifest = []
        problems.append(f"{MANIFEST_OOT_REL}: HEAD'de yok (D_1 pinleri commit'li değil)")
    for t in open_members:
        rel = f"{S3_OUTPUT_DIRS[0]}/{t}.json"
        doc = None
        if not (root / rel).exists():
            problems.append(f"{t}: D_1 satırı dosyası yok")
        else:
            doc = json.loads((root / rel).read_text(encoding="utf-8"))
            bad = d1_rows_problems(doc, manifest)
            if bad:
                problems.append(f"{rel}: d1_rows bekçisi {len(bad)} sorun (commit'li MANIFEST_OOT'a karşı)")
            problems += _committed_unchanged_proven(rel, committed, changed, git, proofs)
        primary = oot_post_d1_primary(t, post_dir)
        if primary is None:
            problems.append(f"{t}: etkin eski kohort POST_D1 kaydı yok")
            continue
        rpath, rec = primary
        rrel = rpath.relative_to(root).as_posix()
        problems += _committed_unchanged_proven(rrel, committed, changed, git, proofs)
        if doc is not None and (rec.get("d1_rows") or {}).get("sha256") != canonical_sha256(doc):
            problems.append(f"{rrel}: d1_rows sha256'sı D_1 satırı dosyasının kanonik sha'sı değil")
    return problems


# ============================================================ karantinaya indirme

Downloader = Callable[[str], tuple[bytes, str]]
Prober = Callable[[str], bool]


def head_published(url: str) -> bool:
    """THB HEAD probu (gövde okunmaz): 200 -> True, 404 -> False."""
    if urllib.parse.urlparse(url).hostname != oc.SOURCE_HOST:
        raise OotOutcomeError(f"izinli kaynak dışı: {url}")
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": oc.USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        raise


def check_xu100_gap_closures(prober: Optional[Prober] = None) -> list[str]:
    """Takvim C'nin XU100-boşluk kapanışları için THB yayımlanmış mı (HEAD). Biri yayımlanmışsa CalendarConflict."""
    prober = prober or head_published
    published = [d for d in m20.XU100_GAP_CLOSURES if prober(oc.source_url(d, "thb"))]
    if published:
        raise CalendarConflict(f"Takvim C kapanış sayıyor ama THB yayımlanmış: {published} (takvim düzeltilmeden DUR)")
    return list(m20.XU100_GAP_CLOSURES)


def check_calendar_closures(prober: Optional[Prober] = None, *, qdir: Path, evidence_path: Path) -> list[str]:
    """Prob (EK1 K5; I37). Kanıt dosyası yoksa `check_xu100_gap_closures` (5 gün; yayımlanmışsa DUR). Varsa Takvim C'nin HER
    hafta içi tam kapanışı kanıta karşı denetlenir; CalendarConflict: kanıtta satırı yok (ya da kanıtta kapanış olmayan gün
    var); NOT_PUBLISHED ama HEAD 200; PUBLISHED_NO_TRADING / TRADING_SESSION ama HEAD 404; karantinadaki zip yok ya da sha'sı
    kanıttaki pinle eşit değil. Dönen: denetlenen günler."""
    prober = prober or head_published
    path = Path(evidence_path)
    if not path.exists():
        return check_xu100_gap_closures(prober)
    evidence = {r["date"]: r for r in read_calendar_evidence(path)}
    closures = calendar_c_weekday_closures()
    problems = [f"{d}: kanıtta var ama Takvim C'nin hafta içi kapanışı değil"
                for d in sorted(set(evidence) - {d for d, _ in closures})]
    for d, source in closures:
        r = evidence.get(d)
        if r is None or r["source"] != source:
            problems.append(f"{d}: kanıtta satırı yok (ya da kaynağı farklı)")
            continue
        published = prober(oc.source_url(d, "thb"))
        if r["decision"] == EV_NOT_PUBLISHED:
            if published:
                problems.append(f"{d}: kanıt NOT_PUBLISHED ama HEAD 200")
            continue
        if not published:
            problems.append(f"{d}: kanıt {r['decision']} ama HEAD 404")
        q = oc.local_path(d, "thb", qdir)
        if not q.exists():
            problems.append(f"{d}: karantinada zip yok; kanıt pini denetlenemedi")
        elif sha256_file(q) != r["thb_sha256"]:
            problems.append(f"{d}: karantinadaki zip'in sha256'sı kanıttaki pinle eşit değil")
    if problems:
        raise CalendarConflict("Takvim C kapanışları bülten kanıtıyla çelişiyor (DUR): " + "; ".join(problems[:8])
                               + (f" … (+{len(problems) - 8})" if len(problems) > 8 else ""))
    return [d for d, _ in closures]


def _q_path(qdir: Path, market_date: str, kind: str) -> Path:
    return oc.local_path(market_date, kind, qdir)


def _q_manifest(qdir: Path) -> dict[tuple[str, str], dict[str, str]]:
    return {(r["date"], r["kind"]): r for r in oc.read_manifest(qdir)}


@dataclass(frozen=True)
class Pin:
    date: str
    kind: str
    url: str
    sha256: str
    bytes: int
    http_last_modified: str
    downloaded_at: str
    internal_filename: str

    def as_row(self) -> dict[str, str]:
        return {k: str(getattr(self, k)) for k in MANIFEST_OOT_COLUMNS}


def fetch_quarantine(market_date: str, kind: str, *, qdir: Path, downloader: Optional[Downloader] = None,
                     now: Optional[datetime] = None) -> tuple[bytes, Pin]:
    """Karantinadaki zip (manifest sha256'sıyla denetlenir) ya da resmi kaynaktan indirip karantinaya yazar ('xb').
    Kapı ÇAĞIRANIN işidir (`extract_open_members`, `extract_d1_rows` önce `download_gate` koşar)."""
    path = _q_path(qdir, market_date, kind)
    man = _q_manifest(qdir)
    if path.exists():
        data = path.read_bytes()
        m = man.get((market_date, kind))
        if m is None or m["sha256"] != sha256_bytes(data):
            raise QuarantineError(f"karantina {path.name}: manifest satırı yok ya da sha256 uyuşmuyor")
        return data, Pin(market_date, kind, m["url"], m["sha256"], int(m["bytes"]), m["http_last_modified"],
                         m["downloaded_at"], m["internal_filename"])
    url = oc.source_url(market_date, kind)
    data, last_modified = (downloader or oc.download_bytes)(url)
    with zipfile.ZipFile(io.BytesIO(data)) as z:          # yazmadan önce biçim: tek iç dosya, beklenen ad
        if z.namelist() != [oc.internal_name(market_date, kind)]:
            raise QuarantineError(f"{kind.upper()} {market_date}: ZIP iç dosya adı {z.namelist()}")
    oc._write_new(path, data)
    pin = Pin(market_date, kind, url, sha256_bytes(data), len(data), last_modified, oc._now_istanbul(now),
              oc.internal_name(market_date, kind))
    oc._append_csv(Path(qdir) / oc.MANIFEST_NAME, oc.MANIFEST_COLUMNS, {
        "date": market_date, "kind": kind, "url": url, "sha256": pin.sha256, "bytes": pin.bytes,
        "internal_filename": pin.internal_filename, "downloaded_at": pin.downloaded_at, "http_last_modified": last_modified})
    return data, pin


# ============================================================ ayıklama (yalnız hedef kodun satırı)

THB_FIELDS = dict(oc.THB_COLUMNS)
THM_FIELDS = dict(oc.THM_COLUMNS)

# TARIH biçimi (SPEC_DEVIATIONS M14; proje sahibi kararı 2026-09-29): bültenlerin TARIH alanı ISO'dur; tek istisna olarak
# d.mm.yyyy / dd.mm.yyyy kabul edilir. Böyle bir bültende ("noktalı bülten") her veri satırının TARIH'i bülten gününe çevrilmeli
# ve sayısal alanlar diğer bültenlerin biçiminde olmalıdır (yalnız rakam ve tek noktalı ondalık; sözleşme sayısı tam sayı; boş
# serbest); değilse tahmin edilmez, DUR (yalnız sayı). ISO bültenlerin yolu değişmedi.
DOTTED_DAY = re.compile(r"(\d{1,2})\.(\d{2})\.(\d{4})")
_DEC_TEXT = re.compile(r"\d+(\.\d+)?")
_INT_TEXT = re.compile(r"\d+")
NUMERIC_FORMAT_COLUMNS = {"thb": {"KAPANIS FIYATI": _DEC_TEXT, "TOPLAM SOZLESME SAYISI": _INT_TEXT},
                          "thm": {"REFERANS FIYATI": _DEC_TEXT, "UST LIMIT FIYATI": _DEC_TEXT, "ALT LIMIT FIYATI": _DEC_TEXT}}
TARIH_ISO, TARIH_DOTTED = "ISO", "DOTTED"


def dotted_day(value: str) -> Optional[str]:
    """d.mm.yyyy ya da dd.mm.yyyy -> ISO gün; başka her biçim (ya da geçersiz tarih) None."""
    m = DOTTED_DAY.fullmatch(value)
    if m is None:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
    except ValueError:
        return None


def _bulletin_rows(data: bytes, market_date: str, kind: str) -> tuple[list[str], list[list[str]]]:
    expected = oc.internal_name(market_date, kind)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if archive.namelist() != [expected]:
            raise OotOutcomeError(f"ZIP iç dosya adı: beklenen {expected}, bulunan {archive.namelist()}")
        text = archive.read(expected).decode("cp1254")
    reader = csv.reader(io.StringIO(text.lstrip("﻿")), delimiter=";")
    headers = next(reader)
    english = next(reader)
    if len(headers) != len(english):
        raise OotOutcomeError("iki başlık satırının genişliği farklı")
    return headers, list(reader)


def tarih_style(headers: Sequence[str], rows: Iterable[Sequence[str]]) -> str:
    """Bültenin TARIH biçimi: bir veri satırında bile d.mm.yyyy / dd.mm.yyyy varsa DOTTED, yoksa ISO (bugünkü yol)."""
    i = list(headers).index("TARIH")
    return TARIH_DOTTED if any(len(r) > i and DOTTED_DAY.fullmatch(r[i]) for r in rows) else TARIH_ISO


def bulletin_tarih_style(data: bytes, market_date: str, kind: str) -> str:
    return tarih_style(*_bulletin_rows(data, market_date, kind))


def dotted_bulletin_problems(headers: Sequence[str], rows: Iterable[Sequence[str]], market_date: str, kind: str) -> list[str]:
    """Noktalı bülten (M14): her veri satırının TARIH'i bülten gününe çevrilir; sayısal alanlar (kapanış, sözleşme sayısı, referans,
    üst ve alt limit) kanonik biçimde. Dönen sorunlar yalnız sayı taşır (kod, satır, değer yok)."""
    h = {name: i for i, name in enumerate(headers)}
    i_date = h["TARIH"]
    data_rows = [r for r in rows if any(cell != "" for cell in r)]
    bad_day = sum(len(r) <= i_date or dotted_day(r[i_date]) != market_date for r in data_rows)
    bad_num = sum(1 for r in data_rows for col, pat in NUMERIC_FORMAT_COLUMNS[kind].items()
                  if col in h and len(r) > h[col] and r[h[col]] != "" and not pat.fullmatch(r[h[col]]))
    out = []
    if bad_day:
        out.append(f"{bad_day} satırın TARIH'i bülten gününe (d.mm.yyyy / dd.mm.yyyy) çevrilmiyor")
    if bad_num:
        out.append(f"{bad_num} sayısal değer diğer bültenlerin biçiminde değil (ondalık/binlik ayırıcı)")
    return out


def extract_code_row(data: bytes, market_date: str, kind: str, code: str) -> Optional[Any]:
    """Bültenden YALNIZ `code` satırı (oc.ThbRow / oc.ThmRow) ya da None. Diğer satırlar taranır ama tutulmaz. Kod iki kez
    geçerse SOURCE_CONFLICT (outcomes.Bulletin ile aynı kural). TARIH: ISO bültende kod satırının TARIH'i bülten günü (bugünkü
    kural); noktalı bültende (M14) önce `dotted_bulletin_problems` boş olmalı, kod satırının TARIH'i bülten gününe çevrilmeli."""
    headers, rows = _bulletin_rows(data, market_date, kind)
    missing = sorted(set(oc.REQUIRED[kind]) - set(headers))
    if missing:
        raise OotOutcomeError(f"{kind.upper()} ad tabanlı zorunlu sütunlar yok: {missing}")
    h = {name: i for i, name in enumerate(headers)}
    i_code, i_date = h["ISLEM  KODU"], h["TARIH"]
    if tarih_style(headers, rows) == TARIH_DOTTED:
        problems = dotted_bulletin_problems(headers, rows, market_date, kind)
        if problems:
            raise OotOutcomeError(f"{kind.upper()} {market_date}: TARIH d.mm.yyyy biçiminde ve " + "; ".join(problems) + " (DUR)")
        same_day = lambda v: dotted_day(v) == market_date  # noqa: E731
    else:
        same_day = lambda v: v == market_date  # noqa: E731
    found = None
    for r in rows:
        if not any(cell != "" for cell in r) or len(r) <= i_code or r[i_code] != code:
            continue
        if len(r) != len(headers):
            raise OotOutcomeError(f"{kind.upper()} {market_date}: {code} satırının genişliği başlıktan farklı")
        if not same_day(r[i_date]):
            raise OotOutcomeError(f"{kind.upper()} {market_date}: {code} satır tarihi {r[i_date]!r}")
        if found is not None:
            raise OotOutcomeError(f"{kind.upper()} {market_date}: {code} iki kez geçiyor (SOURCE_CONFLICT)")
        opt = lambda col: r[h[col]] if col in h else ""  # noqa: E731
        if kind == "thb":
            found = oc.ThbRow(code, r[h["KAPANIS FIYATI"]], r[h["TOPLAM SOZLESME SAYISI"]], r[h["GECICI DURDURMA"]],
                              opt("BULTEN ADI"), opt("ENSTRUMAN GRUBU"), opt("PAZAR"),
                              **{name: r[h[col]] for name, col in oc.THB_D1_COLUMNS.items()})
        else:
            found = oc.ThmRow(code, r[h["REFERANS FIYATI"]], r[h["UST LIMIT FIYATI"]], r[h["ALT LIMIT FIYATI"]])
    return found


UNSEALED_BY_OPEN_VAULT = "OPEN_VAULT"                     # Bölüm A: M-B kapısı + pinli yeniden indirme (`open_vault`)
UNSEALED_BY_MARKER = "MARKER_COMMITTED_AND_PUSHED"        # Bölüm B: işaret dosyası commit'li, değişmemiş, push kanıtlı


class VaultUnsealed(frozenset):
    """Kasa açılış yetkisi (SPEC_DEVIATIONS M-E (d)): SEALED kodlar ve dayanağı. Yalnız iki yerde üretilir: `open_vault` (Bölüm A)
    ve `vault_marker_unsealed` (Bölüm B). `assert_extractable` düz bir kümeyi (ya da başka bir dayanağı) yetki saymaz."""

    basis: str

    def __new__(cls, codes: Iterable[str], basis: str) -> "VaultUnsealed":
        if basis not in (UNSEALED_BY_OPEN_VAULT, UNSEALED_BY_MARKER):
            raise ValueError(f"kasa açılış dayanağı tanımsız: {basis!r}")
        obj = super().__new__(cls, codes)
        obj.basis = basis
        return obj


def assert_extractable(ticker: str, vault: Mapping[str, str], unsealed: Iterable[str] = ()) -> None:
    """Yalnız açık küme (OPEN ∪ EXPOSED_*) ya da kasası açılmış kod; aksi halde bülten AÇILMADAN hata. Kasa kodu yalnız
    `VaultUnsealed` yetkisiyle açılır (M-E (d): `open_vault` sonucu ya da commit'li ve push kanıtlı işaret dosyası)."""
    v = vault.get(ticker)
    if v is None:
        raise SealedAccessError(f"{ticker}: kohortun MEMBER'ı değil; satırı okunmaz")
    if not reg.is_open(v) and not (isinstance(unsealed, VaultUnsealed) and ticker in unsealed):
        raise SealedAccessError(f"{ticker}: kasada (SEALED); satırı okunmaz (KARARLAR D6-3; kasa yalnız `open_vault` ya da "
                                f"commit'li ve push kanıtlı işaret dosyasıyla açılır)")


@dataclass
class MemberExtraction:
    ticker: str
    first_trading_date: str
    thb: dict[str, oc.Bulletin]
    thm: dict[str, oc.Bulletin]
    pins: list[Pin]
    resolution: oc.Resolution


def _one_code_bulletin(market_date: str, kind: str, data: bytes, code: str) -> oc.Bulletin:
    row = extract_code_row(data, market_date, kind, code)
    return oc.Bulletin(market_date, kind, sha256_bytes(data), rows={code: row} if row is not None else {})


def resolve_member(ticker: str, first_trading_date: str, calendar: oc.SessionCalendar, vault: Mapping[str, str], *,
                   fetch: Callable[[str, str], tuple[bytes, Pin]], unsealed: Iterable[str] = (),
                   d1_only: bool = False) -> MemberExtraction:
    """D_1…D_10 (ya da `d1_only`: yalnız D_1'e kadar) seanslarını sırayla karantinadan (gerekirse indirerek) okur; her
    bültenden yalnız `<T>.E` satırı. Durma: 10 işlem günü, 15 seans sınırı ya da (d1_only) ilk işlem günü."""
    assert_extractable(ticker, vault, unsealed)
    code = oc.equity_code(ticker)
    thb: dict[str, oc.Bulletin] = {}
    thm: dict[str, oc.Bulletin] = {}
    pins: list[Pin] = []
    res = None
    for i, s in enumerate(calendar.sessions_from(first_trading_date)):
        data, pin = fetch(s, "thb")
        thb[s] = _one_code_bulletin(s, "thb", data, code)
        pins.append(pin)
        data, pin = fetch(s, "thm")
        thm[s] = _one_code_bulletin(s, "thm", data, code)
        pins.append(pin)
        res = oc.resolve_sessions(ticker, calendar, thb, start=first_trading_date)
        if res.first_appearance is None and i + 1 >= MAX_APPEARANCE_WAIT:
            raise OotOutcomeError(f"{code}: ilk işlem gününden ({first_trading_date}) sonra {i + 1} seansta görünmedi")
        if (d1_only and res.sessions) or len(res.sessions) == oc.N_SESSIONS or res.exhausted:
            break
    if res is None:
        raise OotOutcomeError(f"{ticker}: takvimde {first_trading_date}'ten sonra seans yok")
    return MemberExtraction(ticker, first_trading_date, thb, thm, pins, res)


def assert_window_bound(ext: MemberExtraction) -> None:
    """D6-2 savunması: çözümlenen seans sayısı ≤ N_SESSIONS; pencere dolduysa (D_10 bulundu) okunan hiçbir bülten D_10'dan
    sonra değil. Aşılırsa hata (ham kopya ya da sonuç yazılmadan)."""
    sessions = ext.resolution.sessions
    if len(sessions) > oc.N_SESSIONS:
        raise OotOutcomeError(f"{ext.ticker}: {len(sessions)} seans çözümlendi (> {oc.N_SESSIONS})")
    if len(sessions) == oc.N_SESSIONS:
        late = sorted(s for s in set(ext.thb) | set(ext.thm) if s > sessions[-1].date)
        if late:
            raise OotOutcomeError(f"{ext.ticker}: D_10'dan ({sessions[-1].date}) sonra {len(late)} seansın bülteni okunmuş")


def outcome_rows_oot(ext: MemberExtraction, ipo_price: str, calendar: oc.SessionCalendar) -> list[dict[str, str]]:
    rows = oc.outcome_rows(ext.ticker, ipo_price, calendar, ext.thb, ext.thm, start=ext.first_trading_date)
    return [{**r, "outcome_basis": OUTCOME_BASIS} for r in rows]


def raw_copies(ext: MemberExtraction) -> dict[str, Any]:
    """Ham alan kopyaları: okunan her seansın yalnız `<T>.E` THB/THM satırı (ham metin) ve bülten sha256'sı."""
    assert_window_bound(ext)
    code = oc.equity_code(ext.ticker)
    out = []
    for s in sorted(ext.thb):
        b, m = ext.thb[s].get(code), ext.thm[s].get(code)
        out.append({"session_date": s, "thb_sha256": ext.thb[s].sha256, "thm_sha256": ext.thm[s].sha256,
                     "thb_row": None if b is None else {k: getattr(b, k) for k in b.__dataclass_fields__ if k != "code"},
                     "thm_row": None if m is None else {k: getattr(m, k) for k in m.__dataclass_fields__ if k != "code"}})
    return {"schema_version": "borsai.oot_raw_rows/1", "ticker": ext.ticker, "code": code, "outcome_basis": OUTCOME_BASIS,
            "first_trading_date": ext.first_trading_date, "first_appearance": ext.resolution.first_appearance,
            "sessions": out}


def outcome_path(ticker: str, outcomes_dir: Path = OUTCOMES_OOT_DIR) -> Path:
    return Path(outcomes_dir) / f"{ticker}.csv"


def read_outcome_oot(path: Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != OOT_OUTCOME_COLUMNS:
            raise OotOutcomeError(f"{path}: sütunlar {reader.fieldnames}")
        rows = list(reader)
    if any(r["outcome_basis"] != OUTCOME_BASIS for r in rows):
        raise OotOutcomeError(f"{path}: outcome_basis {OUTCOME_BASIS} değil")
    return rows


def _rows_bytes(rows: Sequence[Mapping[str, str]]) -> bytes:
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=OOT_OUTCOME_COLUMNS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r[k] for k in OOT_OUTCOME_COLUMNS})
    return buf.getvalue().encode("utf-8")


def write_outcome_oot(ticker: str, rows: Sequence[Mapping[str, str]], outcomes_dir: Path = OUTCOMES_OOT_DIR) -> str:
    """CREATED | UPDATED | UNCHANGED; var olan dosyada yalnız PENDING satırlar değişebilir (outcomes.write_outcome kuralı)."""
    path = outcome_path(ticker, outcomes_dir)
    payload = _rows_bytes(rows)
    if path.exists():
        for a, b in zip(read_outcome_oot(path), rows):
            if a["status"] != oc.STATUS_PENDING and dict(a) != {k: b[k] for k in OOT_OUTCOME_COLUMNS}:
                raise oc.OutcomeConflict(f"{ticker} h={a['h']}: dolu satır değişiyor; resmi veri değişmiş olabilir")
        if path.read_bytes() == payload:
            return "UNCHANGED"
        path.write_bytes(payload)
        return "UPDATED"
    oc._write_new(path, payload)
    return "CREATED"


def read_manifest_oot(path: Path = MANIFEST_OOT_PATH) -> list[dict[str, str]]:
    return oc._read_csv(path) if Path(path).exists() else []


def append_manifest_oot(pins: Iterable[Pin], path: Path = MANIFEST_OOT_PATH) -> int:
    """Her (tarih, tür) bir kez; aynı anahtar farklı sha256'yla gelirse SourceChanged. Dönen: eklenen satır sayısı."""
    have = {(r["date"], r["kind"]): r for r in read_manifest_oot(path)}
    added = 0
    for p in pins:
        old = have.get((p.date, p.kind))
        if old is not None:
            if old["sha256"] != p.sha256:
                raise oc.SourceChanged(f"{p.kind.upper()} {p.date}: pinli sha256 {old['sha256']} != {p.sha256}")
            continue
        oc._append_csv(Path(path), MANIFEST_OOT_COLUMNS, p.as_row())
        have[(p.date, p.kind)] = p.as_row()
        added += 1
    return added


def _vault_map(root: Path) -> dict[str, str]:
    _, rows = reg.read_cohort(Path(root) / "registry" / "oot" / "cohort_pre_h99.csv")
    return {r["ticker"]: r["vault"] for r in reg.cohort_members(rows)}


def _ipo_price(ticker: str, root: Path) -> str:
    doc = reg.load_inputs(Path(root) / "registry" / "oot" / "inputs" / f"{ticker}.json")[0]
    return doc["fields"]["ipo_price_tl"]["value"]


def extract_open_members(*, root: Path = ROOT, qdir: Optional[Path] = None, downloader: Optional[Downloader] = None,
                         prober: Optional[Prober] = None, proofs: Optional[Sequence[Mapping[str, Any]]] = None,
                         now: Optional[datetime] = None, calendar: Optional[oc.SessionCalendar] = None,
                         outcomes_dir: Optional[Path] = None, manifest_path: Optional[Path] = None) -> dict[str, Any]:
    """S5 (KARARLAR D6): kapı -> takvim kapanışı probu (`check_calendar_closures`) -> açık kümenin her üyesi için D_1…D_10
    ayıklama (sonuç takvimi `load_calendar_oot`) -> çıktılar. SEALED üyeler hiç açılmaz."""
    root = Path(root)
    download_gate(root=root, proofs=proofs)
    qdir = quarantine_dir(qdir, repo_root=root)
    check_calendar_closures(prober, qdir=qdir, evidence_path=root / CAL_EVIDENCE_REL)
    calendar = calendar or load_calendar_oot(bist_dir=root / "data" / "raw" / "bist")
    outcomes_dir = Path(outcomes_dir or root / "data" / "outcomes_oot")
    manifest_path = Path(manifest_path or root / "data" / "raw" / "bist" / "MANIFEST_OOT.csv")
    vault = _vault_map(root)
    _, rows = reg.read_cohort(root / "registry" / "oot" / "cohort_pre_h99.csv")
    fetch = lambda s, k: fetch_quarantine(s, k, qdir=qdir, downloader=downloader, now=now)  # noqa: E731
    out: dict[str, Any] = {"extracted": {}, "sealed_not_opened": 0}
    for r in reg.cohort_members(rows):
        t = r["ticker"]
        if not reg.is_open(vault[t]):
            out["sealed_not_opened"] += 1
            continue
        ext = resolve_member(t, r["first_trading_date"], calendar, vault, fetch=fetch)
        assert_window_bound(ext)
        action = write_outcome_oot(t, outcome_rows_oot(ext, _ipo_price(t, root), calendar), outcomes_dir)
        raw_path = outcomes_dir / RAW_COPIES_NAME / f"{t}.json"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(pretty_json_bytes(raw_copies(ext)))
        append_manifest_oot(ext.pins, manifest_path)
        out["extracted"][t] = {"action": action, "d1": ext.resolution.d1, "n_sessions": len(ext.resolution.sessions)}
    return out


# ============================================================ S3: yalnız D_1 satırı

def d1_row_doc(ext: MemberExtraction, calendar: oc.SessionCalendar) -> dict[str, Any]:
    """registry/oot/d1_rows/<T>.json: yalnız D_1 tarihli `<T>.E` THB+THM alanları (POST_D1 kaydının `d1` bloğuyla aynı
    şema; bülten atıfları karantina yoluyla ve MANIFEST_OOT pinleriyle)."""
    res = ext.resolution
    if not res.sessions:
        raise OotOutcomeError(f"{ext.ticker}: D_1 bulunamadı")
    d1 = res.sessions[0].date
    code = oc.equity_code(ext.ticker)
    row, lim = ext.thb[d1].get(code), ext.thm[d1].get(code)
    pins = {p.kind: p for p in ext.pins if p.date == d1}
    refs = {kind: {"file": f"quarantine/{kind}/{d1[:4]}/{oc.internal_name(d1, kind)[:-4]}.zip", "sha256": pins[kind].sha256,
                   "url": pins[kind].url, "http_last_modified": pins[kind].http_last_modified,
                   "downloaded_at": pins[kind].downloaded_at, "internal_filename": pins[kind].internal_filename}
            for kind in oc.KINDS}
    fields = {"open": row.open, "high": row.high, "low": row.low, "close": row.close, "volume": row.volume,
              "turnover": row.turnover, "aof": row.aof, "trade_count": row.trade_count, "halt": row.halt,
              "special_trade_volume": row.special_volume, "special_trade_turnover": row.special_turnover,
              "reference_price": lim.reference if lim else "", "upper_limit": lim.upper if lim else "",
              "lower_limit": lim.lower if lim else ""}
    upper, close = oc.dec(fields["upper_limit"]), oc.dec(fields["close"])
    label = None if upper is None or upper <= 0 else int(close == upper)
    at_u = lambda name: None if label is None else (oc.dec(fields[name]) == upper)  # noqa: E731
    return {"schema_version": D1_ROW_SCHEMA, "ticker": ext.ticker, "exposure_class": EXPOSURE_MACHINE_SEQUENCED,
            "outcome_basis": OUTCOME_BASIS, "first_trading_date": ext.first_trading_date,
            "d1": {"session_date": d1, "session_h": 1, "half_day": int(calendar.is_half(d1)),
                   "halt_flag": oc._halt_flag(ext.ticker, d1, row), "thb": refs["thb"], "thm": refs["thm"],
                   "fields_raw": fields, "ceiling_close_D1": label,
                   "lock_consistency": {"open_at_U": at_u("open"), "high_at_U": at_u("high"), "close_at_U": at_u("close")}}}


def d1_rows_problems(doc: Mapping[str, Any], manifest_rows: Sequence[Mapping[str, str]]) -> list[str]:
    """G1/G3 (şartname §2 S3): yalnız D_1 alanları, yalnız `d1` bloğunda; bülten atıfları tam D_1 ve MANIFEST_OOT pinine eşit
    (canlı POST_D1 bekçisiyle tek tanım: `registry.post_d1_record_problems`)."""
    manifest = {(r["date"], r["kind"]): r for r in manifest_rows}
    out = reg.post_d1_record_problems({"record_type": "PREDICTION", "d1": doc.get("d1")}, manifest)
    extra = set(doc) - {"schema_version", "ticker", "exposure_class", "outcome_basis", "first_trading_date", "d1"}
    if extra:
        out.append(f"üst düzey fazladan alan: {sorted(extra)}")
    if doc.get("schema_version") != D1_ROW_SCHEMA or doc.get("exposure_class") != EXPOSURE_MACHINE_SEQUENCED:
        out.append("şema ya da exposure_class")
    return out


def d1_row_action(path: Path, payload: bytes) -> str:
    """registry/oot/d1_rows/<T>.json yeniden koşuda (F6 kalıntısı; SPEC_DEVIATIONS I28): dosya yoksa CREATED; varsa ve baytları
    yeni belgeyle aynıysa UNCHANGED (dokunulmaz); farklıysa OotOutcomeError (DUR: resmi veri ya da kod değişmiş olabilir;
    ayıklanmış dosya elle düzenlenmez, üzerine yazılmaz). Hiçbir şey yazmaz."""
    path = Path(path)
    if not path.exists():
        return "CREATED"
    if path.read_bytes() == payload:
        return "UNCHANGED"
    raise OotOutcomeError(f"{path.name}: var olan D_1 satırı dosyası yeni ayıklamayla bayt-eşit değil (DUR)")


def extract_d1_rows(*, root: Path = ROOT, qdir: Optional[Path] = None, downloader: Optional[Downloader] = None,
                    prober: Optional[Prober] = None, proofs: Optional[Sequence[Mapping[str, Any]]] = None,
                    now: Optional[datetime] = None, calendar: Optional[oc.SessionCalendar] = None,
                    d1_rows_dir: Optional[Path] = None, manifest_path: Optional[Path] = None) -> dict[str, Any]:
    """S3 (şartname §2; KARARLAR D5): kapı -> açık kümenin her üyesi için yalnız D_1'e kadar okuma -> d1_rows/<T>.json ve
    MANIFEST_OOT pinleri. SEALED üyeler hiç açılmaz. Yeniden koşuya dayanıklı (`d1_row_action`): karantina önbellektir, var
    olan aynı dosya UNCHANGED sayılır. Dönen: {"written", "unchanged", "d1_after_first_trading_date"} (ticker listeleri)."""
    root = Path(root)
    download_gate(root=root, proofs=proofs)
    qdir = quarantine_dir(qdir, repo_root=root)
    check_calendar_closures(prober, qdir=qdir, evidence_path=root / CAL_EVIDENCE_REL)
    calendar = calendar or load_calendar_oot(bist_dir=root / "data" / "raw" / "bist")
    d1_rows_dir = Path(d1_rows_dir or root / "registry" / "oot" / "d1_rows")
    manifest_path = Path(manifest_path or root / "data" / "raw" / "bist" / "MANIFEST_OOT.csv")
    vault = _vault_map(root)
    _, rows = reg.read_cohort(root / "registry" / "oot" / "cohort_pre_h99.csv")
    fetch = lambda s, k: fetch_quarantine(s, k, qdir=qdir, downloader=downloader, now=now)  # noqa: E731
    out: dict[str, list[str]] = {"written": [], "unchanged": [], "d1_after_first_trading_date": []}
    for r in reg.cohort_members(rows):
        t = r["ticker"]
        if not reg.is_open(vault[t]):
            continue
        ext = resolve_member(t, r["first_trading_date"], calendar, vault, fetch=fetch, d1_only=True)
        doc = d1_row_doc(ext, calendar)
        d1 = doc["d1"]["session_date"]
        path, payload = d1_rows_dir / f"{t}.json", pretty_json_bytes(doc)
        action = d1_row_action(path, payload)            # farklı içerik: DUR, bu üye için hiçbir şey yazılmadan
        append_manifest_oot([p for p in ext.pins if p.date == d1], manifest_path)
        if action == "CREATED":
            oc._write_new(path, payload)
        out["written" if action == "CREATED" else "unchanged"].append(t)
        if d1 != r["first_trading_date"]:
            out["d1_after_first_trading_date"].append(t)
    return out


# ============================================================ kasa açılışı (BORSAI_FAZ7_VAULT_OPEN; SPEC_DEVIATIONS M)
#
# Tek seferlik ve geri alınamaz. Sıra (M-A): C -> VA1 (`vault-d1`: yeniden indirme + D_1 satırları + işaret dosyası) -> VA2
# (`vault-post-d1`) -> push + kanıt -> VB (`vault-s5`: D_1…D_10). Kasa kodları hiçbir çıktıya, iletiye ya da işaret dosyasına
# yazılmaz (yalnız sayı; DUR iletisi dışında kod adı yok).

VAULT_OPENING_DOCS = ("docs/specs_faz7/SPEC_HAZARD_V1.md", "docs/specs_faz7/KARARLAR.md", "docs/specs_faz7_c/SPEC_C_V0.md",
                      "docs/specs_faz7_c/KARARLAR_C.md")                   # M-B: açılıştan önce commit'li ve push kanıtlı
VAULT_MARKER_SCHEMA = "borsai.vault_open/1"
VAULT_MARKER_TIME_KEYS = ("opened_at_utc", "opened_at_istanbul")          # yeniden koşuda karşılaştırma dışı
VAULT_MARKER_KEYS = frozenset({"schema_version", *VAULT_MARKER_TIME_KEYS, "opened_at_basis", "rule", "documents", "download_gate",
                               "manifest_oot_before", "redownload", "cohort", "n_sealed", "code"})
VAULT_OPENED_AT_BASIS = ("LOCAL_CLOCK_SELF_REPORTED: zaman kanıtı bu dosyayı ekleyen commit'in push kanıtıdır (CLAUDE.md kural 1); "
                         "işaret dosyası bütün indirme ve ayıklamadan sonra yazılır")
VAULT_RULE = ("SPEC_DEVIATIONS M-A…M-D; KARARLAR D6-4: kasa bir kez açılır; MANIFEST_OOT'un her zip'i yeniden indirildi ve pinli "
              "sha256'ya eşit; SEALED üyelerin satırları yalnız o koşuda resmi kaynaktan indirilmiş baytlardan ayıklanır")
COHORT_REL = "registry/oot/cohort_pre_h99.csv"
VAULT_SHARED_FILES = ("scores/scores_oot.json", "docs/SCORES_OOT.md")      # M-E (a): kasa kodu taşıyabilen ortak çıktılar


def _sealed_codes(root: Path) -> list[str]:
    return sorted(t for t, v in _vault_map(root).items() if v == reg.VAULT_SEALED)


def _load_proofs(root: Path, proofs: Optional[Sequence[Mapping[str, Any]]]) -> list[Mapping[str, Any]]:
    from . import push_proof as pp

    d = Path(root) / "registry" / "push_proofs"
    return (list(pp.load_proofs(d)) if d.exists() else []) if proofs is None else list(proofs)


def _git_bytes(root: Path, spec: str) -> Optional[bytes]:
    """`git show <spec>` baytları; yoksa None."""
    r = subprocess.run(["git", "-C", str(root), "show", spec], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def _now_utc(now: Optional[datetime]) -> str:
    from datetime import timezone

    return (now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def vault_docs_evidence(root: Path = ROOT, docs: Sequence[str] = VAULT_OPENING_DOCS,
                        proofs: Optional[Sequence[Mapping[str, Any]]] = None) -> tuple[list[dict[str, Any]], list[str]]:
    """M-B: her belge HEAD ağacında (sahnelenmiş sayılmaz), çalışma kopyasında değişmemiş ve onu en son değiştiren commit'i
    kapsayan bir push kanıtı var (kanıt commit'i ve bütün atalarını kapsar). Dönen: (kanıt satırları, sorunlar)."""
    from . import scoring as sc

    root = Path(root)
    proofs = _load_proofs(root, proofs)
    git = sc.Git(root)
    committed = set(_git(root, "ls-tree", "-r", "--name-only", "HEAD", "--", *docs).splitlines())
    changed = {line[3:] for line in _git(root, "status", "--porcelain", "--untracked-files=all", "--", *docs).splitlines() if line}
    evidence, problems = [], []
    for d in docs:
        if d not in committed:
            problems.append(f"{d}: commit'li değil")
            continue
        if d in changed:
            problems.append(f"{d}: commit'ten sonra değişmiş")
            continue
        added, last = git.added_commit(d), git.run("log", "-1", "--format=%H", "--", d)
        p_added, p_last = sc.proof_time(git, added, proofs), sc.proof_time(git, last, proofs)
        if p_last is None:
            problems.append(f"{d}: push kanıtı yok")
            continue
        evidence.append({"path": d, "added_commit": added, "added_commit_push_proof_created_at": p_added,
                         "last_commit": last, "last_commit_push_proof_created_at": p_last})
    return evidence, problems


def vault_gate_problems(*, root: Path = ROOT, proofs: Optional[Sequence[Mapping[str, Any]]] = None,
                        docs: Sequence[str] = VAULT_OPENING_DOCS) -> list[str]:
    """M-B açılış kapısı: belgeler (`vault_docs_evidence`) + model başına indirme kapısı (`s2_gate_problems`). Boş = açık."""
    proofs = _load_proofs(Path(root), proofs)
    return vault_docs_evidence(root, docs, proofs)[1] + s2_gate_problems(root=root, proofs=proofs)


def open_vault(*, feature_spec: Optional[str] = None, feature_specs: Sequence[str] = VAULT_OPENING_DOCS, root: Path = ROOT,
               qdir: Optional[Path] = None, downloader: Optional[Downloader] = None,
               proofs: Optional[Sequence[Mapping[str, Any]]] = None, manifest_path: Optional[Path] = None,
               manifest_rows: Optional[Sequence[Mapping[str, str]]] = None,
               fresh: Optional[dict[tuple[str, str], tuple[bytes, str]]] = None,
               stats: Optional[dict[str, int]] = None) -> VaultUnsealed:
    """KARARLAR D6-4 ve M-B/M-C: (1) ön-kayıtlı belgeler (`feature_specs`; eski tek-belge çağrısı `feature_spec`) commit'li,
    değişmemiş ve push kanıtlı; (2) model başına indirme kapısı (`download_gate`) açık — biri eksikse HİÇBİR zip indirilmez; (3)
    MANIFEST_OOT'taki (ya da verilen `manifest_rows`'taki) her zip resmi kaynaktan yeniden indirilir (`downloader`; CLI'de
    tempolu) ve pinli sha256'ya eşit olmalıdır, tek uyuşmazlık SourceChanged (DUR; hiçbir kasa dosyası yazılmaz); taze baytlar
    `fresh`'e (aynı koşunun `VaultFetcher` önbelleği), sayılar `stats`'a. Dönen: SEALED kodlar (`VaultUnsealed`, dayanak
    OPEN_VAULT); `resolve_member(..., unsealed=...)` kasa kodunu yalnız bununla açar."""
    root = Path(root)
    proofs = _load_proofs(root, proofs)
    docs = (feature_spec,) if feature_spec is not None else tuple(feature_specs)
    problems = vault_docs_evidence(root, docs, proofs)[1]
    if problems:
        raise GateError("kasa açılmaz (M-B: ön-kayıtlı belgeler commit'li, değişmemiş ve push kanıtlı değil): " + "; ".join(problems))
    download_gate(root=root, proofs=proofs)          # kapı kapalıysa hiçbir zip indirilmez
    rows = list(manifest_rows) if manifest_rows is not None else read_manifest_oot(Path(manifest_path or root / MANIFEST_OOT_REL))
    if not rows:
        raise GateError("kasa açılmaz: MANIFEST_OOT boş (açık kümenin bültenleri henüz pinlenmedi)")
    quarantine_dir(qdir, repo_root=root)
    get = downloader or oc.download_bytes
    n_equal = 0
    for r in rows:
        if r["url"] != oc.source_url(r["date"], r["kind"]):
            raise OotOutcomeError(f"{r['kind'].upper()} {r['date']}: MANIFEST_OOT URL'si resmi bülten URL'si değil (DUR)")
        data, last_modified = get(r["url"])
        if sha256_bytes(data) != r["sha256"]:
            raise oc.SourceChanged(f"{r['kind'].upper()} {r['date']}: yeniden indirilen zip pinli sha256'ya eşit değil")
        n_equal += 1
        if fresh is not None:
            fresh[(r["date"], r["kind"])] = (data, last_modified)
    if stats is not None:
        stats.update(n_manifest_rows=len(rows), n_redownloaded=len(rows), n_sha_equal=n_equal, n_mismatch=len(rows) - n_equal)
    return VaultUnsealed(_sealed_codes(root), UNSEALED_BY_OPEN_VAULT)


class VaultFetcher:
    """M-C: kasa ayıklamasında okunan her zip o koşuda resmi kaynaktan indirilmiş baytlardır (aynı koşuda `open_vault`'un taze
    indirmesi önbellektir: `fresh`; yoksa indirilir). Baytlar (a) karantinada kopyası varsa onunla (ve karantina manifestiyle),
    (b) MANIFEST_OOT'ta pini varsa onunla, (c) Takvim C bülten kanıtında THB pini varsa onunla sha256-eşit olmalıdır; biri
    tutmazsa SourceChanged (DUR; hiçbir şey yazılmadan). Karantinada yoksa zip karantinaya ('xb') ve karantina manifestine yazılır.
    Dönen pin karantina manifestinin satırıdır (yeniden koşu bayt-eşit belge üretir; I28). Kapı ÇAĞIRANIN işidir."""

    def __init__(self, *, qdir: Path, downloader: Optional[Downloader] = None,
                 manifest_rows: Iterable[Mapping[str, str]] = (), evidence_path: Optional[Path] = None,
                 fresh: Optional[dict[tuple[str, str], tuple[bytes, str]]] = None, now: Optional[datetime] = None):
        self.qdir = Path(qdir)
        self.get = downloader or oc.download_bytes
        self.pins = {(r["date"], r["kind"]): r["sha256"] for r in manifest_rows}
        ev = Path(evidence_path) if evidence_path is not None else None
        self.evidence = ({r["date"]: r["thb_sha256"] for r in read_calendar_evidence(ev) if r["thb_sha256"]}
                         if ev is not None and ev.exists() else {})
        self.fresh = {} if fresh is None else fresh
        self.now = now
        self.qman = _q_manifest(self.qdir)
        self.n_network = self.n_from_fresh = self.n_quarantined = 0
        self.keys: set[tuple[str, str]] = set()

    def __call__(self, market_date: str, kind: str) -> tuple[bytes, Pin]:
        key = (market_date, kind)
        url = oc.source_url(market_date, kind)
        if key in self.fresh:
            data, last_modified = self.fresh[key]
            self.n_from_fresh += 1
        else:
            data, last_modified = self.get(url)
            self.fresh[key] = (data, last_modified)
            self.n_network += 1
        self.keys.add(key)
        with zipfile.ZipFile(io.BytesIO(data)) as z:        # biçim: tek iç dosya, beklenen ad
            if z.namelist() != [oc.internal_name(market_date, kind)]:
                raise QuarantineError(f"{kind.upper()} {market_date}: ZIP iç dosya adı {z.namelist()}")
        sha = sha256_bytes(data)
        path = _q_path(self.qdir, market_date, kind)
        m = self.qman.get(key)
        if path.exists():
            if sha256_file(path) != sha or m is None or m["sha256"] != sha:
                raise oc.SourceChanged(f"{kind.upper()} {market_date}: taze indirme karantina kopyasıyla (ya da karantina "
                                       f"manifestiyle) sha256-eşit değil (DUR)")
        elif m is not None:
            raise QuarantineError(f"karantina {path.name}: manifest satırı var ama dosya yok (DUR)")
        if key in self.pins and self.pins[key] != sha:
            raise oc.SourceChanged(f"{kind.upper()} {market_date}: taze indirme MANIFEST_OOT pinine eşit değil (DUR)")
        if kind == "thb" and market_date in self.evidence and self.evidence[market_date] != sha:
            raise oc.SourceChanged(f"THB {market_date}: taze indirme Takvim C bülten kanıtındaki pine eşit değil (DUR)")
        if m is None:
            oc._write_new(path, data)
            m = {"date": market_date, "kind": kind, "url": url, "sha256": sha, "bytes": str(len(data)),
                 "internal_filename": oc.internal_name(market_date, kind), "downloaded_at": oc._now_istanbul(self.now),
                 "http_last_modified": last_modified}
            oc._append_csv(self.qdir / oc.MANIFEST_NAME, oc.MANIFEST_COLUMNS, m)
            self.qman[key] = {k: str(v) for k, v in m.items()}
            self.n_quarantined += 1
        return data, Pin(market_date, kind, m["url"], m["sha256"], int(m["bytes"]), m["http_last_modified"], m["downloaded_at"],
                         m["internal_filename"])

    def n_dotted(self) -> int:
        """Bu koşuda okunan zip'lerden TARIH'i ISO olmayan (noktalı; M14) bülten sayısı."""
        return sum(bulletin_tarih_style(self.fresh[k][0], k[0], k[1]) == TARIH_DOTTED for k in self.keys)


# ---------------------------------------------------------------- işaret dosyası (M-D) ve kasa durumu (M-E)

@dataclass(frozen=True)
class MarkerState:
    """İşaret dosyasının git durumu: çalışma kopyasında var mı, HEAD ağacında mı, commit'ten sonra değişmiş mi, onu ekleyen commit
    ve o commit'i kapsayan en erken push kanıtı."""
    present: bool
    committed: bool
    unchanged: bool
    added_commit: Optional[str]
    proof: Optional[str]

    @property
    def open_mode(self) -> bool:
        """Kasa açık kipi: işaret çalışma kopyasında ya da HEAD'de (commit'siz işaret aynı bekleyen commit'e girer; M-E yorumu)."""
        return self.present or self.committed


def vault_marker_state(root: Path = ROOT, proofs: Optional[Sequence[Mapping[str, Any]]] = None) -> MarkerState:
    from . import scoring as sc

    root = Path(root)
    present = (root / VAULT_MARKER_REL).is_file()
    committed = bool(_git(root, "ls-tree", "--name-only", "HEAD", "--", VAULT_MARKER_REL).strip())
    unchanged = committed and not _git(root, "status", "--porcelain", "--", VAULT_MARKER_REL).strip()
    added = proof = None
    if committed:
        git = sc.Git(root)
        added = git.added_commit(VAULT_MARKER_REL)
        proof = sc.proof_time(git, added, _load_proofs(root, proofs))
    return MarkerState(present, committed, unchanged, added, proof)


def vault_marker_problems(doc: Mapping[str, Any], sealed: Iterable[str] = ()) -> list[str]:
    """İşaret dosyası şeması (M-D): anahtarlar, dört belge kanıtı, açık indirme kapısı, uyuşmazlıksız yeniden indirme, n_sealed;
    kasa kodu YOK (yalnız sayı döner)."""
    out: list[str] = []
    if set(doc) != VAULT_MARKER_KEYS:
        out.append(f"anahtarlar şemayla aynı değil ({len(set(doc) ^ VAULT_MARKER_KEYS)} fark)")
    if doc.get("schema_version") != VAULT_MARKER_SCHEMA:
        out.append("schema_version")
    docs = doc.get("documents") or []
    if [d.get("path") for d in docs] != list(VAULT_OPENING_DOCS) or not all(
            d.get("added_commit") and d.get("last_commit") and d.get("last_commit_push_proof_created_at") for d in docs):
        out.append("documents: dört belge, commit'leri ve kanıt zamanları")
    if (doc.get("download_gate") or {}).get("result") != "OPEN":
        out.append("download_gate OPEN değil")
    rd = doc.get("redownload") or {}
    if not rd.get("n_manifest_rows") or rd.get("n_sha_equal") != rd.get("n_manifest_rows") or rd.get("n_mismatch") != 0:
        out.append("redownload: her pin yeniden indirilip eşleşmemiş")
    if not isinstance(doc.get("n_sealed"), int) or doc.get("n_sealed") <= 0:
        out.append("n_sealed")
    codes = sorted(set(sealed))
    if codes:
        text = json.dumps(doc, ensure_ascii=False)
        n = len(set(re.findall(r"\b(" + "|".join(map(re.escape, codes)) + r")\b", text)))
        if n:
            out.append(f"işaret dosyasında kasa kodu ({n} farklı)")
        if doc.get("n_sealed") != len(codes):
            out.append("n_sealed kohortun kasa üye sayısına eşit değil")
    return out


def build_vault_marker(*, root: Path, docs_evidence: Sequence[Mapping[str, Any]], redownload: Mapping[str, int],
                       manifest_before: Mapping[str, Any], now: Optional[datetime] = None, code_root: Path = ROOT) -> dict[str, Any]:
    root = Path(root)
    _, rows = reg.read_cohort(root / COHORT_REL)
    members = reg.cohort_members(rows)
    state = git_state(code_root)
    return {
        "schema_version": VAULT_MARKER_SCHEMA,
        "opened_at_utc": _now_utc(now),
        "opened_at_istanbul": oc._now_istanbul(now),
        "opened_at_basis": VAULT_OPENED_AT_BASIS,
        "rule": VAULT_RULE,
        "documents": [dict(d) for d in docs_evidence],
        "download_gate": {"result": "OPEN", "n_problems": 0},
        "manifest_oot_before": dict(manifest_before),
        "redownload": {k: int(redownload[k]) for k in ("n_manifest_rows", "n_redownloaded", "n_sha_equal", "n_mismatch")},
        "cohort": {"path": COHORT_REL, "sha256": sha256_file(root / COHORT_REL), "n_member": len(members),
                   "n_open": sum(reg.is_open(r["vault"]) for r in members)},
        "n_sealed": sum(r["vault"] == reg.VAULT_SEALED for r in members),
        "code": {"git_head": state["commit"], "borsai_dirty": state["borsai_dirty"],
                 "borsai_source_sha256": source_tree_sha256(Path(code_root) / "borsai")["tree_sha256"]},
    }


def write_vault_marker(doc: Mapping[str, Any], path: Path, sealed: Iterable[str] = ()) -> str:
    """CREATED ('xb') | UNCHANGED. Var olan işaret dosyası zaman alanları dışında aynıysa dokunulmaz; farklıysa OotOutcomeError
    (DUR; üzerine yazılmaz, elle düzenlenmez)."""
    problems = vault_marker_problems(doc, sealed)
    if problems:
        raise OotOutcomeError("işaret dosyası şemadan geçmedi: " + "; ".join(problems))
    path = Path(path)
    if path.exists():
        strip = lambda d: {k: v for k, v in d.items() if k not in VAULT_MARKER_TIME_KEYS}  # noqa: E731
        if strip(json.loads(path.read_text(encoding="utf-8"))) == strip(doc):
            return "UNCHANGED"
        raise OotOutcomeError(f"{path.name}: var olan işaret dosyası (zaman alanları hariç) yeni açılışla aynı değil (DUR)")
    oc._write_new(path, pretty_json_bytes(doc))
    return "CREATED"


def vault_marker_unsealed(root: Path = ROOT, proofs: Optional[Sequence[Mapping[str, Any]]] = None) -> VaultUnsealed:
    """Bölüm B yetkisi (M-E (d)): işaret dosyası HEAD'de, değişmemiş, onu ekleyen commit'i kapsayan push kanıtı var ve şemadan
    geçiyor; değilse GateError (bülten açılmaz)."""
    root = Path(root)
    state = vault_marker_state(root, proofs)
    if not (state.committed and state.unchanged and state.proof is not None):
        raise GateError("kasa satırları açılmaz: işaret dosyası commit'li, değişmemiş ve push kanıtlı değil")
    sealed = _sealed_codes(root)
    problems = vault_marker_problems(json.loads((root / VAULT_MARKER_REL).read_text(encoding="utf-8")), sealed)
    if problems:
        raise GateError("kasa satırları açılmaz: işaret dosyası şemadan geçmedi: " + "; ".join(problems))
    return VaultUnsealed(sealed, UNSEALED_BY_MARKER)


def vault_member_of(rel: str) -> Optional[str]:
    """M-E (a): üye başına kasa yolunun üyesi — registry/oot/d1_rows/<T>.json, registry/oot/post_d1/<T>/<dosya>,
    data/outcomes_oot/<T>.csv, data/outcomes_oot/raw/<T>.json; başka yol None."""
    parts = rel.split("/")
    if len(parts) == 4 and rel.startswith("registry/oot/d1_rows/") and rel.endswith(".json"):
        return parts[3][:-5]
    if len(parts) == 5 and rel.startswith("registry/oot/post_d1/"):
        return parts[3]
    if len(parts) == 4 and rel.startswith("data/outcomes_oot/raw/") and rel.endswith(".json"):
        return parts[3][:-5]
    if len(parts) == 3 and rel.startswith("data/outcomes_oot/") and rel.endswith(".csv"):
        return parts[2][:-4]
    return None


def vault_scope_files(root: Path = ROOT) -> list[str]:
    """Kasa bekçisinin taradığı yollar (repo-göreli): ayıklanmış dosyalar (data/outcomes_oot/**, registry/oot/d1_rows/**),
    registry/oot/post_d1/**, MANIFEST_OOT, ortak skor çıktıları ve işaret dosyası."""
    root = Path(root)
    out = set()
    for d in ("data/outcomes_oot", "registry/oot/d1_rows", "registry/oot/post_d1"):
        if (root / d).exists():
            out |= {p.relative_to(root).as_posix() for p in (root / d).rglob("*") if p.is_file()}
    out |= {rel for rel in (MANIFEST_OOT_REL, *VAULT_SHARED_FILES, VAULT_MARKER_REL) if (root / rel).is_file()}
    return sorted(out)


def vault_hygiene_problems(root: Path = ROOT, *, sealed: Optional[Sequence[str]] = None,
                           proofs: Optional[Sequence[Mapping[str, Any]]] = None) -> list[str]:
    """M-E bekçisi, iki kip (kasa durumu elle bayrakla değil işaret dosyasıyla belirlenir; iletiler yalnız sayı):
    - İşaret yokken (kapalı kip): taranan hiçbir yolda (`vault_scope_files`) kasa kodu yok (bugünkü iddia).
    - İşaret varken (açık kip): (a) kasa kodu yalnız üye başına kasa yollarında (`vault_member_of`; dosya yalnız KENDİ üyesinin
      kodunu taşır) ve ortak skor çıktılarında (`VAULT_SHARED_FILES`); MANIFEST_OOT ve işaret dosyası kasa kodu taşımaz; (b) kasa
      kodu taşıyan her dosya işaret dosyasını ekleyen commit'te ya da torununda girmiştir (ortak çıktılarda: işaret commit'inin
      atası olan hiçbir sürümde kasa kodu yok). Commit'lenmemiş dosya bekleyen commit'e girer (HEAD'in torunu; E15 kalıbı); işaret
      commit'siz ise commit'li hiçbir kasa dosyası olamaz. İşaret dosyası şemadan geçer, commit'liyse değişmemiştir."""
    from . import scoring as sc

    root = Path(root)
    sealed = _sealed_codes(root) if sealed is None else sorted(set(sealed))
    if not sealed:
        return []
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, sealed)) + r")\b")
    state = vault_marker_state(root, proofs)
    tally: Counter[str] = Counter()
    hits: dict[str, set[str]] = {}
    for rel in vault_scope_files(root):
        codes = set(pattern.findall(rel)) | set(pattern.findall((root / rel).read_text(encoding="utf-8", errors="replace")))
        if codes:
            hits[rel] = codes
    if not state.open_mode:
        if hits:
            tally["kasa kodu, işaret dosyası yokken (kasa kapalı)"] += len(hits)
        return [f"{k}: {n} dosya" for k, n in sorted(tally.items())]
    if state.committed and not state.present:
        tally["işaret dosyası HEAD'de var ama çalışma kopyasında yok"] += 1
    elif state.committed and not state.unchanged:
        tally["işaret dosyası commit'ten sonra değişmiş"] += 1
    if state.present:
        tally.update(f"işaret dosyası: {p}" for p in
                     vault_marker_problems(json.loads((root / VAULT_MARKER_REL).read_text(encoding="utf-8")), sealed))
    git = sc.Git(root)
    added = {}
    for prefix in ("registry/oot/d1_rows", "registry/oot/post_d1", "data/outcomes_oot"):
        added.update(git.added_under(prefix))
    after_marker = lambda c: state.committed and state.added_commit is not None and (  # noqa: E731
        c == state.added_commit or git.is_ancestor(state.added_commit, c))
    for rel, codes in hits.items():
        member = vault_member_of(rel)
        if rel in (MANIFEST_OOT_REL, VAULT_MARKER_REL):
            tally["kasa kodu MANIFEST_OOT'ta ya da işaret dosyasında"] += 1
            continue
        if member is not None:
            if member not in sealed or codes != {member}:
                tally["kasa kodu izinli yol dışında (üye yolu başka bir kodu taşıyor)"] += 1
                continue
            c = added.get(rel) or git.added_commit(rel)
            if c is not None and not after_marker(c):
                tally["kasa dosyası işaret dosyasını ekleyen commit'ten önce (ya da işaret commit'siz iken) commit'lenmiş"] += 1
            continue
        if rel not in VAULT_SHARED_FILES:
            tally["kasa kodu izinli yol dışında"] += 1
            continue
        for c in git.history(rel):
            if after_marker(c):
                continue
            old = _git_bytes(root, f"{c}:{rel}")
            if old and pattern.search(old.decode("utf-8", errors="replace")):
                tally["ortak çıktının işaret commit'inden önceki bir sürümünde kasa kodu"] += 1
                break
    return [f"{k}: {n}" for k, n in sorted(tally.items())]


# ---------------------------------------------------------------- B kapısı (M-I)

def vault_s3_gate_problems(*, root: Path = ROOT, proofs: Optional[Sequence[Mapping[str, Any]]] = None) -> list[str]:
    """M-I (`s3_gate_problems`'ın kasa karşılığı). Boş liste = `vault-s5` bülten açabilir:
    (1) `s2_gate_problems()` boş; (2) M-B belgeleri kanıtlı; (3) işaret dosyası commit'li, değişmemiş, push kanıtlı ve şemadan
    geçiyor; (4) her kasa üyesinin registry/oot/d1_rows/<T>.json'u commit'li, değişmemiş, push kanıtlı ve `d1_rows_problems` HEAD'deki
    MANIFEST_OOT'a karşı boş; skorlamanın seçeceği POST_D1 kaydı (`oot_post_d1_primary`) commit'li, değişmemiş, push kanıtlı ve
    d1_rows'un kanonik sha'sını taşıyor. S3 çıktı dizinlerinde izlenmeyen dosya ya da kohort dışı ad yok. Neden: POST_D1 kaydı D_2+
    sonuçtan önce push kanıtlı değilse `scoring.class_oot` onu OOT_RETRO sayar (I13). İletiler kasa kodu taşımaz (yalnız sayı)."""
    from . import scoring as sc
    from .provenance import canonical_sha256

    root = Path(root)
    proofs = _load_proofs(root, proofs)
    problems: list[str] = []
    s2 = s2_gate_problems(root=root, proofs=proofs)
    if s2:
        problems.append(f"S2 (model başına indirme) kapısı: {len(s2)} sorun")
    problems += vault_docs_evidence(root, VAULT_OPENING_DOCS, proofs)[1]
    state = vault_marker_state(root, proofs)
    if not state.committed:
        problems.append("işaret dosyası commit'li değil")
    elif not state.unchanged:
        problems.append("işaret dosyası commit'ten sonra değişmiş")
    elif state.proof is None:
        problems.append("işaret dosyası push kanıtı yok")
    sealed = _sealed_codes(root)
    if state.present:
        problems += [f"işaret dosyası: {p}" for p in
                     vault_marker_problems(json.loads((root / VAULT_MARKER_REL).read_text(encoding="utf-8")), sealed)]
    git = sc.Git(root)
    d1_dir, post_dir = root / S3_OUTPUT_DIRS[0], root / S3_OUTPUT_DIRS[1]
    committed = set(_git(root, "ls-tree", "-r", "--name-only", "HEAD", "--", *S3_OUTPUT_DIRS).splitlines())
    status = _git(root, "status", "--porcelain", "--untracked-files=all", "--", *S3_OUTPUT_DIRS).splitlines()
    changed = {line[3:] for line in status if line and not line.startswith("??")}
    n_untracked = sum(line.startswith("??") for line in status)
    if n_untracked:
        problems.append(f"S3 çıktı dizinlerinde izlenmeyen {n_untracked} dosya")
    members = set(_vault_map(root))
    names = [p.stem for p in d1_dir.glob("*.json")] + ([p.name for p in post_dir.iterdir() if p.is_dir()] if post_dir.exists() else [])
    outside = sum(n not in members for n in names)
    if outside:
        problems.append(f"S3 çıktı dizinlerinde kohort dışında {outside} ad")
    manifest_bytes = _git_bytes(root, f"HEAD:{MANIFEST_OOT_REL}")
    if manifest_bytes is None:
        problems.append(f"{MANIFEST_OOT_REL}: HEAD'de yok (D_1 pinleri commit'li değil)")
    manifest = list(csv.DictReader(io.StringIO(manifest_bytes.decode("utf-8")))) if manifest_bytes else []
    tally: Counter[str] = Counter()
    for t in sealed:
        rel = f"{S3_OUTPUT_DIRS[0]}/{t}.json"
        doc = None
        if not (root / rel).exists():
            tally["kasa D_1 satırı dosyası yok"] += 1
        else:
            doc = json.loads((root / rel).read_text(encoding="utf-8"))
            if d1_rows_problems(doc, manifest):
                tally["kasa d1_rows bekçisi (commit'li MANIFEST_OOT'a karşı) geçmedi"] += 1
            kind = _cup_problem(rel, committed, changed, git, proofs)
            if kind:
                tally[f"kasa d1_rows: {kind}"] += 1
        primary = oot_post_d1_primary(t, post_dir)
        if primary is None:
            tally["kasa üyesinin etkin POST_D1 kaydı yok"] += 1
            continue
        rpath, rec = primary
        kind = _cup_problem(rpath.relative_to(root).as_posix(), committed, changed, git, proofs)
        if kind:
            tally[f"kasa POST_D1 kaydı: {kind}"] += 1
        if doc is not None and (rec.get("d1_rows") or {}).get("sha256") != canonical_sha256(doc):
            tally["kasa POST_D1 kaydının d1_rows sha256'sı D_1 satırı dosyasının kanonik sha'sı değil"] += 1
    return problems + [f"{k}: {n} üye" for k, n in sorted(tally.items())]


# ---------------------------------------------------------------- sürücüler (M-H)

def vault_d1(*, root: Path = ROOT, qdir: Optional[Path] = None, downloader: Optional[Downloader] = None,
             prober: Optional[Prober] = None, proofs: Optional[Sequence[Mapping[str, Any]]] = None,
             now: Optional[datetime] = None, calendar: Optional[oc.SessionCalendar] = None, code_root: Optional[Path] = None,
             stats: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """VA1 (M-A, M-B, M-C, M-D): M-B kapısı -> takvim kapanışı probu (`check_calendar_closures`) -> `open_vault` (HEAD'deki
    MANIFEST_OOT'un her pini yeniden indirilir) -> her SEALED üyenin yalnız D_1'e kadar ayıklanması (`VaultFetcher`) -> bütün
    belgeler hazırsa yazım: registry/oot/d1_rows/<T>.json ('xb'; aynı bayt -> UNCHANGED, farklı -> DUR) ve D_1 pinleri
    MANIFEST_OOT'a (yalnız ekleme) -> işaret dosyası EN SON (M-D). Herhangi bir uyuşmazlıkta hiçbir kasa dosyası yazılmaz. Açık
    kümenin dosyalarına dokunulmaz. Dönen: yalnız sayılar."""
    root = Path(root)
    code_root = root if code_root is None else Path(code_root)
    proofs = _load_proofs(root, proofs)
    docs_evidence, problems = vault_docs_evidence(root, VAULT_OPENING_DOCS, proofs)
    if problems:
        raise GateError("kasa açılmaz (M-B): " + "; ".join(problems))
    download_gate(root=root, proofs=proofs)
    qdir = quarantine_dir(qdir, repo_root=root)
    check_calendar_closures(prober, qdir=qdir, evidence_path=root / CAL_EVIDENCE_REL)
    calendar = calendar or load_calendar_oot(bist_dir=root / "data" / "raw" / "bist")
    manifest_path = root / MANIFEST_OOT_REL
    before = _git_bytes(root, f"HEAD:{MANIFEST_OOT_REL}")
    if not before:
        raise GateError("kasa açılmaz: MANIFEST_OOT HEAD'de yok")
    if not manifest_path.read_bytes().startswith(before):
        raise OotOutcomeError("MANIFEST_OOT çalışma kopyası HEAD'dekinin öneki değil (yalnız ekleme kuralı; DUR)")
    before_rows = list(csv.DictReader(io.StringIO(before.decode("utf-8"))))
    fresh: dict[tuple[str, str], tuple[bytes, str]] = {}
    redownload: dict[str, int] = {}
    unsealed = open_vault(root=root, qdir=qdir, downloader=downloader, proofs=proofs, manifest_rows=before_rows, fresh=fresh,
                          stats=redownload)
    fetcher = VaultFetcher(qdir=qdir, downloader=downloader, manifest_rows=read_manifest_oot(manifest_path),
                           evidence_path=root / CAL_EVIDENCE_REL, fresh=fresh, now=now)
    vault = _vault_map(root)
    _, rows = reg.read_cohort(root / COHORT_REL)
    d1_dir = root / S3_OUTPUT_DIRS[0]
    planned = []
    for r in reg.cohort_members(rows):
        t = r["ticker"]
        if vault[t] != reg.VAULT_SEALED:
            continue
        ext = resolve_member(t, r["first_trading_date"], calendar, vault, fetch=fetcher, unsealed=unsealed, d1_only=True)
        doc = d1_row_doc(ext, calendar)
        d1 = doc["d1"]["session_date"]
        planned.append((r["first_trading_date"], d1, d1_dir / f"{t}.json", doc, [p for p in ext.pins if p.date == d1]))
    have = {(m["date"], m["kind"]): m for m in read_manifest_oot(manifest_path)}
    merged = dict(have)
    for *_, pins in planned:
        for p in pins:
            if (p.date, p.kind) in merged and merged[(p.date, p.kind)]["sha256"] != p.sha256:
                raise oc.SourceChanged(f"{p.kind.upper()} {p.date}: pinli sha256 farklı (DUR)")
            merged.setdefault((p.date, p.kind), p.as_row())
    actions = []
    for _, _, path, doc, _ in planned:                      # bütün denetimler yazımdan önce: DUR'da hiçbir şey yazılmaz
        if d1_rows_problems(doc, list(merged.values())):
            raise OotOutcomeError("bir kasa D_1 satırı belgesi d1_rows bekçisinden geçmedi (DUR; hiçbir dosya yazılmadı)")
        actions.append(d1_row_action(path, pretty_json_bytes(doc)))
    n_before = len(have)
    for (_, _, path, doc, pins), action in zip(planned, actions):
        append_manifest_oot(pins, manifest_path)
        if action == "CREATED":
            oc._write_new(path, pretty_json_bytes(doc))
    n_after = len(read_manifest_oot(manifest_path))
    pinned_dates = {d for d, _ in have}
    marker = build_vault_marker(root=root, docs_evidence=docs_evidence, redownload=redownload,
                                manifest_before={"path": MANIFEST_OOT_REL, "source": "HEAD", "sha256": sha256_bytes(before),
                                                 "n_rows": len(before_rows)},
                                now=now, code_root=code_root)
    marker_action = write_vault_marker(marker, root / VAULT_MARKER_REL, unsealed)
    if stats is not None:
        stats.update(fetch_network=fetcher.n_network, fetch_from_open_vault=fetcher.n_from_fresh,
                     fetch_quarantined=fetcher.n_quarantined, fetch_zips=len(fetcher.keys),
                     fetch_non_iso_tarih=fetcher.n_dotted())
    return {"documents": len(docs_evidence), "redownload": dict(redownload), "sealed_extracted": len(planned),
            "written": actions.count("CREATED"), "unchanged": actions.count("UNCHANGED"),
            "d1_after_first_trading_date": sum(d1 != ftd for ftd, d1, *_ in planned),
            "new_d1_dates_not_previously_pinned": len({d1 for _, d1, *_ in planned} - pinned_dates),
            "manifest_rows_added": n_after - n_before, "manifest_rows": n_after, "marker": marker_action,
            "n_sealed": marker["n_sealed"]}


def vault_post_d1(*, root: Path = ROOT, now: Optional[datetime] = None,
                  proofs: Optional[Sequence[Mapping[str, Any]]] = None) -> dict[str, Any]:
    """VA2 (M-G; `s3_post_d1` kalıbı): işaret dosyası commit'li ve değişmemiş olmalı (değilse DUR; hiçbir şey yazılmaz ve hiçbir
    zip açılmaz — bu komut zip açmaz). registry/oot/d1_rows/'daki HER kasa üyesi dosyası için eski kohort POST_D1 kaydı (REFUSED ve
    NOT_APPLICABLE dahil). DuplicateRecord -> "zaten var"; başka her FreezeError -> DUR. Kohort dışı ad -> DUR (ad yazılmaz)."""
    from . import freeze as fz

    root = Path(root)
    state = vault_marker_state(root, proofs)
    if not (state.committed and state.unchanged):
        raise GateError("kasa POST_D1 kayıtları yazılmaz: işaret dosyası commit'li ve değişmemiş değil (DUR)")
    d1_dir, post_dir = root / S3_OUTPUT_DIRS[0], root / S3_OUTPUT_DIRS[1]
    vault = _vault_map(root)
    files = sorted(d1_dir.glob("*.json"))
    outside = sum(p.stem not in vault for p in files)
    if outside:
        raise OotOutcomeError(f"d1_rows: kohort dışında {outside} dosya (DUR)")
    sealed_files = [p for p in files if vault[p.stem] == reg.VAULT_SEALED]
    written = already = 0
    for p in sealed_files:
        try:
            fz.write_oot_post_d1_record(p.stem, now=now, post_dir=post_dir, d1_rows_dir=d1_dir,
                                        records_dir=root / "registry" / "oot" / "records", models_dir=root / "models",
                                        root=root, code_root=root)
            written += 1
        except fz.DuplicateRecord:
            already += 1
    status: Counter[str] = Counter()
    codes: Counter[str] = Counter()
    for p in sealed_files:
        _, rec = oot_post_d1_primary(p.stem, post_dir)
        for c in rec["models"]:
            status[c["status"]] += 1
            if c.get("refusal"):
                codes[f"{c['status']}:{c['refusal']['code']}"] += 1
    return {"d1_rows": len(sealed_files), "written": written, "already_present": already, "records": written + already,
            "status": dict(sorted(status.items())), "codes": dict(sorted(codes.items()))}


def vault_s5(*, root: Path = ROOT, qdir: Optional[Path] = None, downloader: Optional[Downloader] = None,
             prober: Optional[Prober] = None, proofs: Optional[Sequence[Mapping[str, Any]]] = None,
             now: Optional[datetime] = None, calendar: Optional[oc.SessionCalendar] = None,
             stats: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """VB (M-H, M-I): B kapısı (`vault_s3_gate_problems`; sorun varsa HİÇBİR zip ve HEAD yok) -> yetki (`vault_marker_unsealed`) ->
    takvim probu -> her SEALED üye için D_1…D_10 (`VaultFetcher`: her zip o koşuda indirilir) -> savunmalar (pencere ≤ D_10; D_1
    ve D_1 bülten sha'ları d1_rows'la aynı) -> bütün üyeler hazırsa yazım: data/outcomes_oot/<T>.csv, raw/<T>.json, MANIFEST_OOT
    (yalnız ekleme). Açık kümenin dosyalarına dokunulmaz. Dönen: yalnız sayılar."""
    root = Path(root)
    proofs = _load_proofs(root, proofs)
    problems = vault_s3_gate_problems(root=root, proofs=proofs)
    if problems:
        raise GateError(f"vault-s5 başlamaz: kasa D_1 satırları, POST_D1 kayıtları ya da işaret dosyası commit'li, değişmemiş ve "
                        f"push kanıtlı değil ({len(problems)} sorun): " + "; ".join(problems[:5]) + (" …" if len(problems) > 5 else ""))
    unsealed = vault_marker_unsealed(root, proofs)
    qdir = quarantine_dir(qdir, repo_root=root)
    check_calendar_closures(prober, qdir=qdir, evidence_path=root / CAL_EVIDENCE_REL)
    calendar = calendar or load_calendar_oot(bist_dir=root / "data" / "raw" / "bist")
    outcomes_dir = root / "data" / "outcomes_oot"
    manifest_path = root / MANIFEST_OOT_REL
    fetcher = VaultFetcher(qdir=qdir, downloader=downloader, manifest_rows=read_manifest_oot(manifest_path),
                           evidence_path=root / CAL_EVIDENCE_REL, now=now)
    vault = _vault_map(root)
    _, rows = reg.read_cohort(root / COHORT_REL)
    planned = []
    for r in reg.cohort_members(rows):
        t = r["ticker"]
        if vault[t] != reg.VAULT_SEALED:
            continue
        ext = resolve_member(t, r["first_trading_date"], calendar, vault, fetch=fetcher, unsealed=unsealed)
        assert_window_bound(ext)
        d1doc = json.loads((root / S3_OUTPUT_DIRS[0] / f"{t}.json").read_text(encoding="utf-8"))["d1"]
        d1 = ext.resolution.d1
        if (d1 != d1doc["session_date"] or ext.thb[d1].sha256 != d1doc["thb"]["sha256"]
                or ext.thm[d1].sha256 != d1doc["thm"]["sha256"]):
            raise OotOutcomeError("bir kasa üyesinin D_1'i ya da D_1 bülten sha'sı d1_rows'la aynı değil (DUR; hiçbir sonuç "
                                  "dosyası yazılmadı)")
        planned.append((t, ext, outcome_rows_oot(ext, _ipo_price(t, root), calendar)))
    have = {(m["date"], m["kind"]): m["sha256"] for m in read_manifest_oot(manifest_path)}
    for _, ext, _ in planned:
        for p in ext.pins:
            if have.setdefault((p.date, p.kind), p.sha256) != p.sha256:
                raise oc.SourceChanged(f"{p.kind.upper()} {p.date}: pinli sha256 farklı (DUR; hiçbir sonuç dosyası yazılmadı)")
    n_before = len(read_manifest_oot(manifest_path))
    out: dict[str, Any] = {"extracted": {}}
    for t, ext, orows in planned:
        action = write_outcome_oot(t, orows, outcomes_dir)
        raw_path = outcomes_dir / RAW_COPIES_NAME / f"{t}.json"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(pretty_json_bytes(raw_copies(ext)))
        append_manifest_oot(ext.pins, manifest_path)
        out["extracted"][t] = {"action": action, "n_sessions": len(ext.resolution.sessions),
                               "n_read": len(set(ext.thb) | set(ext.thm)), "statuses": [x["status"] for x in orows]}
    if stats is not None:
        stats.update(fetch_network=fetcher.n_network, fetch_quarantined=fetcher.n_quarantined, fetch_zips=len(fetcher.keys),
                     fetch_non_iso_tarih=fetcher.n_dotted())
    ex = list(out["extracted"].values())
    return {"extracted": len(ex), "actions": dict(sorted(Counter(e["action"] for e in ex).items())),
            "n_sessions": {str(k): v for k, v in sorted(Counter(e["n_sessions"] for e in ex).items())},
            "read_more_than_resolved": sum(e["n_read"] > e["n_sessions"] for e in ex),
            "row_status": dict(sorted(Counter(s for e in ex for s in e["statuses"]).items())),
            "manifest_rows_added": len(read_manifest_oot(manifest_path)) - n_before}


# ============================================================ CLI (SPEC_DEVIATIONS I29, I33)
#
# python -m borsai.outcomes_oot {probe|calendar-evidence|s3|s3-post-d1|s5|vault-d1|vault-post-d1|vault-s5} [--pace SANİYE]
#                                [--quarantine YOL]
# Çıktı yalnız SAYI (JSON): hiçbir kod, satır, fiyat, getiri ya da limit yazılmaz. Ayıklama davranışı fonksiyonlardadır; CLI
# yalnız kapıyı, HEAD probunu (200 ya da 404; başka her kod DUR, GET denenmez) ve indirme temposunu ekler. Hata -> DUR (çıkış 2).

DEFAULT_PACE = 0.5
COMMANDS = ("probe", "calendar-evidence", "s3", "s3-post-d1", "s5", "vault-d1", "vault-post-d1", "vault-s5")
Head = Callable[[str], Mapping[str, Any]]


def head_status(url: str) -> dict[str, Any]:
    """HEAD (gövde okunmaz; GET yok): {status, content_type, content_length}. Yalnız resmi kaynak."""
    if urllib.parse.urlparse(url).hostname != oc.SOURCE_HOST:
        raise OotOutcomeError(f"izinli kaynak dışı: {url}")
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": oc.USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            status, headers = resp.status, resp.headers
    except urllib.error.HTTPError as exc:
        status, headers = exc.code, exc.headers
    get = (lambda k: headers.get(k, "") or "") if headers is not None else (lambda k: "")  # noqa: E731
    return {"status": int(status), "content_type": get("Content-Type"), "content_length": get("Content-Length")}


def strict_prober(head: Optional[Head] = None, log: Optional[list[dict[str, Any]]] = None) -> Prober:
    """XU100-boşluk probu (T6): HEAD 200 -> yayımlanmış (takvim yanlış; `check_xu100_gap_closures` DUR), 404 -> yayımlanmamış;
    başka her kod -> OotOutcomeError (DUR; yalnız durum kodu, Content-Type, Content-Length)."""
    head = head or head_status

    def probe(url: str) -> bool:
        r = dict(head(url))
        if log is not None:
            log.append(r)
        if r["status"] not in (200, 404):
            raise OotOutcomeError(f"HEAD {r['status']} (200 ya da 404 değil; GET denenmez, DUR): Content-Type "
                                  f"{r.get('content_type', '')!r}, Content-Length {r.get('content_length', '')!r}")
        return r["status"] == 200

    return probe


def paced_downloader(pace: float, downloader: Optional[Downloader] = None, *,
                     sleep: Callable[[float], None] = time.sleep, stats: Optional[dict[str, int]] = None) -> Downloader:
    """`--pace`: her GERÇEK ağ indirmesinden önce `pace` saniye bekler. `fetch_quarantine` indiriciyi yalnız karantinada
    dosya yokken çağırır; karantinadan okuma beklemez. `stats["network_downloads"]` indirme sayısını tutar."""
    base = downloader or oc.download_bytes

    def get(url: str) -> tuple[bytes, str]:
        if pace > 0:
            sleep(pace)
        if stats is not None:
            stats["network_downloads"] = stats.get("network_downloads", 0) + 1
        return base(url)

    return get


def s3_post_d1(*, root: Path = ROOT, now: Optional[datetime] = None) -> dict[str, Any]:
    """S3b (SPEC_DEVIATIONS I31): registry/oot/d1_rows/'daki HER dosya için eski kohort POST_D1 kaydı (REFUSED ve
    NOT_APPLICABLE dahil; hiçbiri atlanmaz). DuplicateRecord -> "zaten var" (sayılır); başka her FreezeError -> DUR.
    Durum ve kod sayıları skorlamanın seçeceği kayıttan (`oot_post_d1_primary`)."""
    from . import freeze as fz

    root = Path(root)
    d1_dir, post_dir = root / S3_OUTPUT_DIRS[0], root / S3_OUTPUT_DIRS[1]
    open_members = {t for t, v in _vault_map(root).items() if reg.is_open(v)}
    files = sorted(d1_dir.glob("*.json"))
    outside = sum(p.stem not in open_members for p in files)
    if outside:
        raise OotOutcomeError(f"d1_rows: açık küme dışında {outside} dosya (DUR)")
    written = already = 0
    for p in files:
        try:
            fz.write_oot_post_d1_record(p.stem, now=now, post_dir=post_dir, d1_rows_dir=d1_dir,
                                        records_dir=root / "registry" / "oot" / "records", models_dir=root / "models",
                                        root=root)
            written += 1
        except fz.DuplicateRecord:
            already += 1
    status: Counter[str] = Counter()
    codes: Counter[str] = Counter()
    for p in files:
        _, rec = oot_post_d1_primary(p.stem, post_dir)
        for c in rec["models"]:
            status[c["status"]] += 1
            if c.get("refusal"):
                codes[f"{c['status']}:{c['refusal']['code']}"] += 1
    return {"d1_rows": len(files), "written": written, "already_present": already, "records": written + already,
            "status": dict(sorted(status.items())), "codes": dict(sorted(codes.items()))}


def run_command(command: str, *, root: Path = ROOT, qdir: Optional[Path] = None, pace: float = DEFAULT_PACE,
                downloader: Optional[Downloader] = None, head: Optional[Head] = None,
                proofs: Optional[Sequence[Mapping[str, Any]]] = None, now: Optional[datetime] = None,
                calendar: Optional[oc.SessionCalendar] = None, sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    """Bir CLI komutu; dönen sözlükte yalnız sayılar (ve prob tarihleri). Hata yukarı çıkar (`main` DUR yazar)."""
    root = Path(root)
    probes: list[dict[str, Any]] = []
    stats = {"network_downloads": 0}
    prober = strict_prober(head, probes)
    kw = dict(root=root, qdir=qdir, downloader=paced_downloader(pace, downloader, sleep=sleep, stats=stats),
              prober=prober, proofs=proofs, now=now, calendar=calendar)
    net = lambda: {"network_downloads": stats["network_downloads"],  # noqa: E731
                   "probe_status": dict(sorted(Counter(str(r["status"]) for r in probes).items()))}
    if command == "probe":
        download_gate(root=root, proofs=proofs)
        evidence = root / CAL_EVIDENCE_REL
        dates = check_calendar_closures(prober, qdir=quarantine_dir(qdir, repo_root=root), evidence_path=evidence)
        return {"command": command, "gate": "OPEN", "mode": "EVIDENCE" if evidence.exists() else "XU100_GAP_ONLY",
                "n_checked": len(dates), "published": sum(r["status"] == 200 for r in probes),
                "checked": [{"date": d, **{k: r.get(k, "") for k in ("status", "content_type", "content_length")}}
                            for d, r in zip(dates, probes)], **net()}
    if command == "calendar-evidence":                   # EK1 K3: yalnız Takvim C'nin hafta içi tam kapanışları
        download_gate(root=root, proofs=proofs)
        base = head or head_status
        rows = calendar_evidence_rows(qdir=quarantine_dir(qdir, repo_root=root), downloader=kw["downloader"], now=now,
                                      head=lambda u: probes.append(dict(base(u))) or probes[-1])
        action = write_calendar_evidence(rows, root / CAL_EVIDENCE_REL)
        count = lambda key: dict(sorted(Counter(key(r) for r in rows).items()))  # noqa: E731
        return {"command": command, "action": action, "n_rows": len(rows), "sources": count(lambda r: r["source"]),
                "decisions": count(lambda r: r["decision"]),
                "decisions_by_source": count(lambda r: f"{r['source']}:{r['decision']}"),
                "xu100_gap": {r["date"]: r["decision"] for r in rows if r["source"] == SOURCE_XU100_GAP},
                "trading_sessions": [r["date"] for r in rows if r["decision"] == EV_TRADING_SESSION], **net()}
    if command == "s3":
        out = extract_d1_rows(**kw)
        return {"command": command, "written": len(out["written"]), "unchanged": len(out["unchanged"]),
                "total": len(out["written"]) + len(out["unchanged"]),
                "d1_after_first_trading_date": len(out["d1_after_first_trading_date"]), **net()}
    if command == "s3-post-d1":
        return {"command": command, **s3_post_d1(root=root, now=now)}
    if command == "s5":
        problems = s3_gate_problems(root=root, proofs=proofs)
        if problems:                                     # T3: S3 çıktıları kanıtlı değilse hiçbir bülten indirilmez
            raise GateError(f"S5 başlamaz: S3 çıktıları commit'li, değişmemiş ve push kanıtlı değil ({len(problems)} sorun): "
                            + "; ".join(problems[:5]) + (" …" if len(problems) > 5 else ""))
        out = extract_open_members(**kw)
        ex = list(out["extracted"].values())
        return {"command": command, "extracted": len(ex),
                "actions": dict(sorted(Counter(e["action"] for e in ex).items())),
                "n_sessions": {str(k): v for k, v in sorted(Counter(e["n_sessions"] for e in ex).items())},
                "sealed_not_opened": out["sealed_not_opened"], **net()}
    if command == "vault-d1":                            # M-H: VA1 (kasa açılışı; tek seferlik)
        fs: dict[str, Any] = {}
        out = vault_d1(**kw, stats=fs)
        return {"command": command, "gate": "OPEN", **out, **fs, **net()}
    if command == "vault-post-d1":                       # M-H: VA2 (zip açmaz)
        return {"command": command, **vault_post_d1(root=root, now=now, proofs=proofs)}
    if command == "vault-s5":                            # M-H: VB (önce B kapısı; sorun varsa hiçbir zip ve HEAD yok)
        fs = {}
        out = vault_s5(**kw, stats=fs)
        return {"command": command, **out, **fs, **net()}
    raise ValueError(f"bilinmeyen komut: {command}")


def main(argv: Optional[Sequence[str]] = None, **inject: Any) -> int:
    from . import freeze as fz

    parser = argparse.ArgumentParser(prog="python -m borsai.outcomes_oot",
                                     description="Eski kohort S3/S5 (KARARLAR D6) ve kasa açılışı (SPEC_DEVIATIONS M): "
                                                 "prob, Takvim C kapanışları için bülten kanıtı, D_1 satırları, POST_D1 "
                                                 "kayıtları, D_1…D_10 satırları. Çıktı "
                                                 "yalnız sayı (JSON).")
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("--pace", type=float, default=DEFAULT_PACE, metavar="SANİYE",
                        help=f"her gerçek ağ indirmesinden önce bekleme (varsayılan {DEFAULT_PACE}; karantinadan okuma beklemez)")
    parser.add_argument("--quarantine", type=Path, metavar="YOL",
                        help=f"karantina dizini (varsayılan ${QUARANTINE_ENV} ya da {DEFAULT_QUARANTINE}; repo dışında)")
    args = parser.parse_args(argv)
    if args.pace < 0:
        parser.error("--pace negatif olamaz")
    try:
        out = {**run_command(args.command, qdir=args.quarantine, pace=args.pace, **inject), "durum": "TAMAM"}
        code = 0
    except (OotOutcomeError, oc.OutcomeError, fz.FreezeError, urllib.error.URLError, TimeoutError) as exc:
        out = {"command": args.command, "durum": "DUR", "hata": type(exc).__name__, "mesaj": str(exc)}
        code = 2
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

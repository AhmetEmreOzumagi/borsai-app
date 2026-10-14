"""Resmi sonuç verisi: Borsa İstanbul THB (fiyat) ve THM (limit) bültenleri -> data/outcomes/<TICKER>.csv.
SPEC_SCORING §1-§4, §9. Yalnız stdlib.

İndirme (SPEC_SCORING §1; legacy `collect_historical99_bist_raw_v1.py` `source_url`):
    https://www.borsaistanbul.com/data/{thb,thm}/YYYY/MM/{kind}YYYYMMDD1.zip
Ham zip baytları değiştirilmeden `data/raw/bist/<kind>/YYYY/<kind>YYYYMMDD1.zip` altına yazılır
('xb': var olan dosya yeniden yazılmaz) ve `data/raw/bist/MANIFEST.csv`'ye bir satır eklenir.
H99 SESSIONS dosyasında sha256'sı pinli bir bülten (2026-08-06…2026-08-19) başka baytlarla
gelirse indirme durur (kaynak değişmiş olabilir). Yalnız www.borsaistanbul.com'a çıkılır.

Sıra kuralı (CLAUDE.md): 2026-08-19 sonrası bülten ancak `models/INDEX.json`'daki (ve `models/INDEX_POST_D1.json`'daki)
bütün model JSON'ları, `registry/records/` ve `registry/post_d1/` commit edilmişse indirilir (`sequence_guard`).

Ayrıştırma: legacy `parse_archive_bytes` (cp1254, ';', iki başlık satırı, ad tabanlı sütunlar).
Değerler ham metinden `Decimal(str)`; float'a hiç girmez.

Tanımlar (SPEC_SCORING §2, §3, §9):
  resmi seans     = H99 takvimi ∪ Faz 2A uzatması, counts_as_official_session (tam + yarım gün),
                    eksi ilan dışı kapanışlar (hafta içi, THB hiç yayımlanmamış ve sonraki seansınki
                    yayımlanmış gün; `data/raw/bist/UNANNOUNCED_CLOSURES.csv`)
  traded(a, s)    = THB'de `<a>.E` satırı var VE TOPLAM SOZLESME SAYISI > 0 VE KAPANIS FIYATI > 0
  D_1, D_h        = traded olan ilk / h'inci resmi seans, payın THB'de ilk göründüğü seanstan başlayarak
  15 seans sınırı = ilk görünüşten itibaren 15 resmi seansta D_10 oluşmadıysa eksik ufuklar TARGET_UNAVAILABLE
  tam gün durdurma: traded değil -> sayılmaz, D_h kayar; `shifted_by_suspension` = D_1'den o ufka dek
                    atlanan seans sayısı. Gün içi durdurma (GECICI DURDURMA = 1, traded) sayılır, halt_flag = 1.
                    0/1 dışı kod -> UnknownOfficialCode (satır elle incelenene kadar skorlanmaz; komut durur)
  tavan etiketi   = Decimal(KAPANIS) == Decimal(UST LIMIT), o seansın THM'si; THM satırı yok, limit boş
                    ya da ≤ 0 -> NA (etiket tahmin edilmez)
  L               = D_1'den ardışık tavan sayısı; ilk 0'da durur; önce NA gelirse L bilinmez
  R_h             = close(D_h) / ipo_price − 1 (kesin kesir, 50 anlamlı hane; legacy `exact_return`)
  Y_h             = 1[close(D_h) > ipo_price];  h ∈ {1, 3, 5, 10}; ipo_price registry/inputs/<T>.json'dan

Satır durumu: OK | NA_LIMIT (fiyat var, tavan etiketi NA) | PENDING (seans henüz yok) | TARGET_UNAVAILABLE.
Yeniden koşuda yalnız PENDING satırları dolar; dolu bir satır değişecekse `OutcomeConflict` (resmi veri değişti).

Kullanım:
  .venv/bin/python -m borsai.outcomes fetch 2026-08-17            # tek seansın THB+THM'si (kaynak sınaması)
  .venv/bin/python -m borsai.outcomes update [--through YYYY-MM-DD]  # eksik seanslar + sonuç dosyaları
  .venv/bin/python -m borsai.outcomes completeness [--through YYYY-MM-DD]  # SPEC_SCORING §4 tamlık denetimi
"""
from __future__ import annotations

import argparse
import bisect
import csv
import io
import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

from . import registry as reg
from .market20 import CALENDAR_A_PATH, CALENDAR_A_SHA256, CALENDAR_B_EXT_PATH, CALENDAR_B_EXT_SHA256
from .provenance import ISTANBUL, ROOT, sha256_bytes, sha256_file

BIST_DIR = ROOT / "data" / "raw" / "bist"
MANIFEST_NAME = "MANIFEST.csv"
CLOSURES_NAME = "UNANNOUNCED_CLOSURES.csv"
OUTCOMES_DIR = ROOT / "data" / "outcomes"
COMPLETENESS_NAME = "COMPLETENESS.csv"
SESSIONS_PATH = ROOT / "data" / "raw" / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv"
SESSIONS_SHA256 = "eca620d3a5e8fed0b118bab556da5ce519257a4b2e14efcd22065f5bcdc93da9"  # data/data_version.json

SOURCE_HOST = "www.borsaistanbul.com"
USER_AGENT = "BorsAi-Faz2B-Official-BIST/1.0"
KINDS = ("thb", "thm")
SEQUENCE_CUTOFF = "2026-08-19"   # CLAUDE.md sıra kuralı: bu tarihten sonraki bülten ancak modeller dondurulduysa
N_SESSIONS = 10
MAX_SEEN = 15
TARGET_H = (1, 3, 5, 10)
EXACT_DIGITS = 50

STATUS_OK = "OK"
STATUS_NA_LIMIT = "NA_LIMIT"
STATUS_PENDING = "PENDING"
STATUS_TARGET_UNAVAILABLE = "TARGET_UNAVAILABLE"
ROW_STATUSES = (STATUS_OK, STATUS_NA_LIMIT, STATUS_PENDING, STATUS_TARGET_UNAVAILABLE)
NA = "NA"

KEY_COLUMNS = {"ticker": "ISLEM  KODU", "date": "TARIH"}
# POST_D1 kaydının D_1 alanları (SPEC_POST_D1_V0 §7.6; H19 özel işlem alanları). Adlar 2026 THB başlığıyla birebir
# (57 sütun; tests/test_outcomes.py::test_l5_thb_d1_columns_match_pinned_2026_header). Değerler ham metin kalır.
THB_D1_COLUMNS = {"open": "ACILIS FIYATI", "high": "EN YUKSEK FIYAT", "low": "EN DUSUK FIYAT", "volume": "TOPLAM ISLEM ADEDI",
                  "turnover": "TOPLAM ISLEM HACMI", "aof": "A.O.F", "special_volume": "OZEL ISLEM BILDIRIMI ISLEM ADEDI",
                  "special_turnover": "OZEL ISLEM BILDIRIMI ISLEM HACMI"}
THB_COLUMNS = {"close": "KAPANIS FIYATI", "trade_count": "TOPLAM SOZLESME SAYISI", "halt": "GECICI DURDURMA",
               "name": "BULTEN ADI", "group": "ENSTRUMAN GRUBU", "market": "PAZAR", **THB_D1_COLUMNS}
THM_COLUMNS = {"reference": "REFERANS FIYATI", "upper": "UST LIMIT FIYATI", "lower": "ALT LIMIT FIYATI"}
# Legacy toplayıcının ad tabanlı zorunlu sütunları (SPEC_SCORING §1) + POST_D1 kaydının D_1 alanları (§7.6: REQUIRED
# genişler); ek sütunlar yalnız tamlık denetiminde. OUTCOME_COLUMNS değişmez (D1 alanları kayıtta ve pinli bültende).
REQUIRED = {"thb": ("ISLEM  KODU", "TARIH", "KAPANIS FIYATI", "TOPLAM SOZLESME SAYISI", "GECICI DURDURMA")
            + tuple(THB_D1_COLUMNS.values()),
            "thm": ("ISLEM  KODU", "TARIH", "REFERANS FIYATI", "UST LIMIT FIYATI", "ALT LIMIT FIYATI")}

MANIFEST_COLUMNS = ("date", "kind", "url", "sha256", "bytes", "internal_filename", "downloaded_at", "http_last_modified")
CLOSURE_COLUMNS = ("date", "kind", "url", "http_status", "later_session_published", "detected_at")
OUTCOME_COLUMNS = ("h", "session_date", "close_raw", "upper_limit_raw", "reference_raw", "trade_count_raw", "halt_flag",
                   "half_day", "shifted_by_suspension", "ceiling_close", "R_h", "Y_h", "ipo_price", "thb_sha256",
                   "thm_sha256", "status")


class OutcomeError(RuntimeError):
    pass


class NotPublished(OutcomeError):
    """Bülten sunucuda yok (HTTP 404): henüz yayımlanmadı ya da ilan dışı kapanış."""


class SourceChanged(OutcomeError):
    pass


class OutcomeConflict(OutcomeError):
    """Dolu bir sonuç satırı yeniden hesapta değişiyor: resmi veri değişmiş olabilir."""


class UnknownOfficialCode(OutcomeError):
    pass


class SequenceRuleError(OutcomeError):
    pass


# ============================================================ kaynak adları

def compact(market_date: str) -> str:
    return market_date.replace("-", "")


def source_url(market_date: str, kind: str) -> str:
    """Legacy `source_url` (SESSIONS dosyasındaki thb_source_url / thm_source_url kalıbı)."""
    return f"https://{SOURCE_HOST}/data/{kind}/{market_date[:4]}/{market_date[5:7]}/{kind}{compact(market_date)}1.zip"


def internal_name(market_date: str, kind: str) -> str:
    return f"{kind}{compact(market_date)}1.csv"


def local_path(market_date: str, kind: str, bist_dir: Path = BIST_DIR) -> Path:
    return Path(bist_dir) / kind / market_date[:4] / f"{kind}{compact(market_date)}1.zip"


# ============================================================ ayrıştırma (legacy parse_archive_bytes)

def parse_archive_bytes(data: bytes, expected_internal: str) -> dict[str, Any]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        if names != [expected_internal]:
            raise OutcomeError(f"ZIP iç dosya adı: beklenen {expected_internal}, bulunan {names}")
        text = archive.read(expected_internal).decode("cp1254")
    reader = csv.reader(io.StringIO(text.lstrip("\ufeff")), delimiter=";")
    records = [row for row in reader if any(cell != "" for cell in row)]
    if len(records) <= 2:
        raise OutcomeError("resmi arşiv CSV'sinde veri satırı yok")
    headers, english = records[0], records[1]
    if len(headers) != len(english):
        raise OutcomeError("iki başlık satırının genişliği farklı")
    rows = records[2:]
    if any(len(r) != len(headers) for r in rows):
        raise OutcomeError("veri satırı genişliği başlıktan farklı")
    return {"headers": headers, "english_headers": english, "rows": rows, "schema_width": len(headers)}


def validate_required_schema(parsed: Mapping[str, Any], kind: str) -> None:
    missing = sorted(set(REQUIRED[kind]) - set(parsed["headers"]))
    if missing:
        raise OutcomeError(f"{kind.upper()} ad tabanlı zorunlu sütunlar yok: {missing}")


@dataclass(frozen=True)
class ThbRow:
    code: str
    close: str
    trade_count: str
    halt: str
    name: str = ""
    group: str = ""
    market: str = ""
    open: str = ""                # POST_D1 D_1 alanları (THB_D1_COLUMNS), ham metin
    high: str = ""
    low: str = ""
    volume: str = ""
    turnover: str = ""
    aof: str = ""
    special_volume: str = ""
    special_turnover: str = ""


@dataclass(frozen=True)
class ThmRow:
    code: str
    reference: str
    upper: str
    lower: str


@dataclass
class Bulletin:
    """Bir seansın bülteni: işlem kodu -> satır. Aynı kod iki kez geçerse `conflicts`'e düşer ve o
    kod okunmak istenirse hata verilir (legacy SOURCE_CONFLICT)."""

    market_date: str
    kind: str
    sha256: str
    rows: dict[str, Any] = field(default_factory=dict)
    conflicts: set[str] = field(default_factory=set)

    def get(self, code: str) -> Any:
        if code in self.conflicts:
            raise OutcomeError(f"{self.kind.upper()} {self.market_date}: {code} iki kez geçiyor (SOURCE_CONFLICT)")
        return self.rows.get(code)

    def __contains__(self, code: str) -> bool:
        return code in self.rows or code in self.conflicts

    def codes(self) -> set[str]:
        return set(self.rows) | self.conflicts


def parse_bulletin(data: bytes, market_date: str, kind: str) -> Bulletin:
    parsed = parse_archive_bytes(data, internal_name(market_date, kind))
    validate_required_schema(parsed, kind)
    h = {name: i for i, name in enumerate(parsed["headers"])}
    out = Bulletin(market_date, kind, sha256_bytes(data))
    for r in parsed["rows"]:
        if r[h["TARIH"]] != market_date:
            raise OutcomeError(f"{kind.upper()} {market_date}: satır tarihi {r[h['TARIH']]!r}")
        code = r[h["ISLEM  KODU"]]
        if kind == "thb":
            opt = lambda col: r[h[col]] if col in h else ""  # noqa: E731
            row: Any = ThbRow(code, r[h["KAPANIS FIYATI"]], r[h["TOPLAM SOZLESME SAYISI"]], r[h["GECICI DURDURMA"]],
                              opt("BULTEN ADI"), opt("ENSTRUMAN GRUBU"), opt("PAZAR"),
                              **{name: r[h[col]] for name, col in THB_D1_COLUMNS.items()})
        else:
            row = ThmRow(code, r[h["REFERANS FIYATI"]], r[h["UST LIMIT FIYATI"]], r[h["ALT LIMIT FIYATI"]])
        if code in out.rows or code in out.conflicts:
            out.rows.pop(code, None)
            out.conflicts.add(code)
        else:
            out.rows[code] = row
    return out


def dec(raw: str) -> Optional[Decimal]:
    """Ham metin -> Decimal; boş ya da sayı değilse None."""
    text = (raw or "").strip()
    if not text:
        return None
    try:
        v = Decimal(text)
    except InvalidOperation:
        return None
    return v if v.is_finite() else None


# ============================================================ takvim

@dataclass(frozen=True)
class SessionCalendar:
    sessions: tuple[str, ...]          # resmi seanslar (tam + yarım gün), artan
    half_days: frozenset[str]
    first_day: str
    last_day: str
    closures: tuple[str, ...] = ()     # ilan dışı kapanışlar (sessions'tan çıkarıldı)
    sha256: str = ""

    def sessions_from(self, day: str) -> tuple[str, ...]:
        return self.sessions[bisect.bisect_left(self.sessions, day):]

    def previous(self, day: str) -> Optional[str]:
        i = bisect.bisect_left(self.sessions, day)
        return self.sessions[i - 1] if i > 0 else None

    def is_half(self, day: str) -> bool:
        return day in self.half_days

    def covers(self, day: str) -> bool:
        return self.first_day <= day <= self.last_day

    def without(self, closures: Iterable[str]) -> "SessionCalendar":
        cl = tuple(sorted(set(closures) | set(self.closures)))
        return SessionCalendar(tuple(s for s in self.sessions if s not in cl), self.half_days, self.first_day,
                               self.last_day, cl, self.sha256)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def load_calendar(*, bist_dir: Path = BIST_DIR, apply_closures: bool = True) -> SessionCalendar:
    """H99 Pay Piyasası takvimi (2023-09-22…2026-08-19) ∪ Faz 2A uzatması (2026-08-20…2026-12-31).
    İki dosyanın sha256'sı market20'deki pinli değerlerle denetlenir; günler ardışık olmalı."""
    for path, sha in ((CALENDAR_A_PATH, CALENDAR_A_SHA256), (CALENDAR_B_EXT_PATH, CALENDAR_B_EXT_SHA256)):
        if sha256_file(path) != sha:
            raise OutcomeError(f"{path.name} sha256 pinli değerle uyuşmuyor")
    days: list[str] = []
    sessions: list[str] = []
    half: set[str] = set()
    for r in _read_csv(CALENDAR_A_PATH):
        days.append(r["calendar_date"])
        if r["counts_as_official_session"] == "TRUE":
            sessions.append(r["calendar_date"])
            if r["session_status"] == "OPEN_HALF_DAY":
                half.add(r["calendar_date"])
        elif r["counts_as_official_session"] != "FALSE":
            raise OutcomeError(f"H99 takvimi: {r['calendar_date']} counts_as_official_session {r['counts_as_official_session']!r}")
    for r in _read_csv(CALENDAR_B_EXT_PATH):
        days.append(r["calendar_date"])
        if r["counts_as_official_session"] == "YES":
            sessions.append(r["calendar_date"])
            if r["half_day"] == "YES":
                half.add(r["calendar_date"])
        elif r["counts_as_official_session"] != "NO":
            raise OutcomeError(f"takvim uzatması: {r['calendar_date']} counts_as_official_session {r['counts_as_official_session']!r}")
    for a, b in zip(days, days[1:]):
        if date.fromisoformat(b) - date.fromisoformat(a) != timedelta(days=1):
            raise OutcomeError(f"takvim ardışık değil: {a} -> {b}")
    cal = SessionCalendar(tuple(sessions), frozenset(half), days[0], days[-1],
                          sha256=f"{CALENDAR_A_SHA256}+{CALENDAR_B_EXT_SHA256}")
    if apply_closures:
        cal = cal.without(r["date"] for r in read_closures(bist_dir))
    return cal


# ============================================================ manifest, indirme, sıra kuralı

def read_manifest(bist_dir: Path = BIST_DIR) -> list[dict[str, str]]:
    p = Path(bist_dir) / MANIFEST_NAME
    return _read_csv(p) if p.exists() else []


def read_closures(bist_dir: Path = BIST_DIR) -> list[dict[str, str]]:
    p = Path(bist_dir) / CLOSURES_NAME
    return _read_csv(p) if p.exists() else []


def _append_csv(path: Path, columns: Sequence[str], row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n")
    if new:
        w.writeheader()
    w.writerow({k: row.get(k, "") for k in columns})
    with path.open("a", encoding="utf-8", newline="") as fh:
        fh.write(buf.getvalue())


def _write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as fh:  # var olan dosya asla yeniden yazılmaz
        fh.write(data)


def h99_pinned_sha256() -> dict[tuple[str, str], str]:
    """(tarih, tür) -> H99 SESSIONS dosyasındaki bülten sha256'sı (2023-09-22…2026-08-19)."""
    if sha256_file(SESSIONS_PATH) != SESSIONS_SHA256:
        raise OutcomeError("H99 SESSIONS dosyası sha256'sı pinli değerle uyuşmuyor")
    out: dict[tuple[str, str], str] = {}
    for r in _read_csv(SESSIONS_PATH):
        for kind in KINDS:
            key, sha = (r["target_session_date"], kind), r[f"{kind}_sha256"]
            if out.setdefault(key, sha) != sha:
                raise OutcomeError(f"SESSIONS: {key} için iki farklı sha256")
    return out


Downloader = Callable[[str], tuple[bytes, str]]


def download_bytes(url: str, attempts: int = 3) -> tuple[bytes, str]:
    """(baytlar, HTTP Last-Modified). 404 -> NotPublished (yeniden denenmez)."""
    if urllib.parse.urlparse(url).hostname != SOURCE_HOST:
        raise OutcomeError(f"izinli kaynak dışı: {url}")
    last: Optional[Exception] = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                if resp.status != 200:
                    raise OutcomeError(f"HTTP {resp.status}")
                data = resp.read()
                if len(data) <= 100:
                    raise OutcomeError(f"yanıt çok kısa ({len(data)} bayt)")
                return data, resp.headers.get("Last-Modified", "")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise NotPublished(f"HTTP 404: {url}") from exc
            last = exc
        except (urllib.error.URLError, OutcomeError, TimeoutError) as exc:
            last = exc
        if attempt + 1 < attempts:
            time.sleep(2 ** attempt)
    raise OutcomeError(f"indirilemedi: {url}: {last}")


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


GUARDED_DIRS = ("models", "registry/records", "registry/post_d1")


def sequence_guard(market_date: str, *, root: Path = ROOT) -> None:
    """2026-08-19 sonrası bülten ancak kayıtlı bütün model JSON'ları ve tahmin kayıtları HEAD'de
    commit edilmiş ve çalışma kopyasında değişmemişse indirilir (CLAUDE.md sıra kuralı). POST_D1 modellerinin
    dizini (models/INDEX_POST_D1.json) varsa o ve listelediği model dosyaları da (proje sahibi kararı 4); POST_D1
    kayıtları (registry/post_d1/) da: commit edilmemiş bir POST_D1 kaydı varken bülten indirilmez (SPEC_POST_D1_V0 §7.4)."""
    if market_date <= SEQUENCE_CUTOFF:
        return
    index = json.loads((root / "models" / "INDEX.json").read_text(encoding="utf-8"))
    paths = ["models/INDEX.json"] + [f"models/{e['file']}" for e in index["models"]]
    post_index = root / "models" / "INDEX_POST_D1.json"
    if post_index.exists():
        paths += ["models/INDEX_POST_D1.json"] + [f"models/{e['file']}"
                                                  for e in json.loads(post_index.read_text(encoding="utf-8"))["models"]]
    tracked = set(_git(root, "ls-files", "--", *GUARDED_DIRS).splitlines())
    missing = [p for p in paths if p not in tracked]
    for sub in GUARDED_DIRS[1:]:
        d = root / sub
        records = [p.relative_to(root).as_posix() for p in d.rglob("*.json")] if d.exists() else []
        missing += [p for p in records if p not in tracked]
    dirty = _git(root, "status", "--porcelain", "--untracked-files=all", "--", *GUARDED_DIRS)
    if missing or dirty:
        raise SequenceRuleError(f"{market_date} bülteni indirilemez: model/kayıt dosyaları commit edilmemiş "
                                f"({missing[:5]}{' …' if len(missing) > 5 else ''}; {dirty[:200]})")


def _now_istanbul(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).astimezone(ISTANBUL).replace(microsecond=0).isoformat()


def fetch(market_date: str, kind: str, *, bist_dir: Path = BIST_DIR, downloader: Optional[Downloader] = None,
          pinned: Optional[Mapping[tuple[str, str], str]] = None, now: Optional[datetime] = None,
          root: Path = ROOT, guard: bool = True) -> Bulletin:
    """Yerel dosya varsa onu (manifest sha256'sıyla denetleyerek), yoksa resmi kaynaktan indirir."""
    path = local_path(market_date, kind, bist_dir)
    manifest = {(r["date"], r["kind"]): r for r in read_manifest(bist_dir)}
    pinned = h99_pinned_sha256() if pinned is None else pinned
    expected = pinned.get((market_date, kind))
    if path.exists():
        data = path.read_bytes()
        m = manifest.get((market_date, kind))
        if m is None or m["sha256"] != sha256_bytes(data):
            raise OutcomeError(f"{path}: manifest satırı yok ya da sha256 uyuşmuyor")
        if expected is not None and m["sha256"] != expected:
            raise SourceChanged(f"{kind.upper()} {market_date}: yerel sha256 H99 SESSIONS {expected} ile uyuşmuyor")
        return parse_bulletin(data, market_date, kind)
    if guard:
        sequence_guard(market_date, root=root)
    url = source_url(market_date, kind)
    data, last_modified = (downloader or download_bytes)(url)
    sha = sha256_bytes(data)
    if expected is not None and sha != expected:
        raise SourceChanged(f"{kind.upper()} {market_date}: sha256 {sha} != H99 SESSIONS {expected}; kaynak değişmiş olabilir")
    bulletin = parse_bulletin(data, market_date, kind)  # yazmadan önce ayrışıyor mu
    _write_new(path, data)
    _append_csv(Path(bist_dir) / MANIFEST_NAME, MANIFEST_COLUMNS, {
        "date": market_date, "kind": kind, "url": url, "sha256": sha, "bytes": len(data),
        "internal_filename": internal_name(market_date, kind), "downloaded_at": _now_istanbul(now),
        "http_last_modified": last_modified})
    return bulletin


def local_bulletin(market_date: str, kind: str, bist_dir: Path = BIST_DIR) -> Optional[Bulletin]:
    """Ağa çıkmadan: yerel dosya (manifest sha256'sıyla) ya da None."""
    path = local_path(market_date, kind, bist_dir)
    if not path.exists():
        return None
    data = path.read_bytes()
    m = {(r["date"], r["kind"]): r for r in read_manifest(bist_dir)}.get((market_date, kind))
    if m is None or m["sha256"] != sha256_bytes(data):
        raise OutcomeError(f"{path}: manifest satırı yok ya da sha256 uyuşmuyor")
    return parse_bulletin(data, market_date, kind)


# ============================================================ D_h ve tavan etiketi (SPEC_SCORING §2, §3, §9)

@dataclass(frozen=True)
class Session:
    date: str
    h: int
    close_raw: str
    trade_count_raw: str
    halt_flag: int
    half_day: int
    shifted_by_suspension: int

    @property
    def close(self) -> Decimal:
        return Decimal(self.close_raw)


@dataclass(frozen=True)
class Resolution:
    ticker: str
    first_appearance: Optional[str]
    sessions: tuple[Session, ...]
    pending: bool      # bülteni henüz olmayan bir seansa gelindi
    exhausted: bool    # 15 seans sınırı doldu

    @property
    def d1(self) -> Optional[str]:
        return self.sessions[0].date if self.sessions else None


def equity_code(ticker: str) -> str:
    return f"{ticker}.E"


def traded(row: Optional[ThbRow]) -> bool:
    if row is None:
        return False
    tc, close = dec(row.trade_count), dec(row.close)
    return tc is not None and tc > 0 and close is not None and close > 0


def _halt_flag(ticker: str, day: str, row: ThbRow) -> int:
    if row.halt not in ("0", "1"):
        raise UnknownOfficialCode(f"{ticker} {day}: GECICI DURDURMA = {row.halt!r} (UNKNOWN_OFFICIAL_CODE; elle inceleme)")
    return int(row.halt)


def resolve_sessions(ticker: str, calendar: SessionCalendar, thb_by_date: Mapping[str, Any], *,
                     start: Optional[str] = None, max_seen: int = MAX_SEEN) -> Resolution:
    """SPEC_SCORING §9. `thb_by_date`: tarih -> Bulletin (ya da kod -> ThbRow sözlüğü); anahtarı olmayan
    resmi seansın bülteni henüz yok demektir (PENDING). `start`: ilk görünüşün aranmaya başlandığı gün."""
    code = equity_code(ticker)
    begin = start if start is not None else min(thb_by_date)
    first = None
    for s in calendar.sessions_from(begin):
        if s not in thb_by_date:
            return Resolution(ticker, None, (), True, False)
        if code in thb_by_date[s]:
            first = s
            break
    if first is None:
        return Resolution(ticker, None, (), True, False)
    out: list[Session] = []
    seen = skipped = 0
    pending = exhausted = False
    for s in calendar.sessions_from(first):
        seen += 1
        if seen > max_seen:
            exhausted = True
            break
        if s not in thb_by_date:
            pending = True
            break
        row = thb_by_date[s].get(code)
        halt = _halt_flag(ticker, s, row) if row is not None else 0
        if traded(row):
            out.append(Session(s, len(out) + 1, row.close, row.trade_count, halt, int(calendar.is_half(s)), skipped))
            if len(out) == N_SESSIONS:
                break
        elif out:
            skipped += 1   # tam gün durdurma: sayılmaz, D_h kayar
    else:
        pending = len(out) < N_SESSIONS   # takvim bitti: uzatılana kadar bekler
    return Resolution(ticker, first, tuple(out), pending, exhausted)


def ceiling_label(ticker: str, session: Session, thm_by_date: Mapping[str, Any]) -> Optional[int]:
    """1[Decimal(close) == Decimal(üst limit)]; THM satırı yok, limit boş ya da ≤ 0 -> None (NA)."""
    lim = (thm_by_date.get(session.date) or {}).get(equity_code(ticker))
    upper = dec(lim.upper) if lim is not None else None
    if upper is None or upper <= 0:
        return None
    return int(session.close == upper)


def streak(labels: Sequence[Optional[int]]) -> Optional[int]:
    """L: D_1'den ardışık tavan sayısı. İlk 0'da durur; önce NA ya da eksik gün gelirse None."""
    n = 0
    for x in labels:
        if x is None:
            return None
        if x == 0:
            return n
        n += 1
    return n if len(labels) == N_SESSIONS else None


def exact_return(close: str, ipo_price: str) -> tuple[str, int]:
    """Legacy `exact_return`: kesin kesir, 50 anlamlı haneli Decimal metni ve Y = 1[close > ipo]."""
    c, p = Fraction(Decimal(close)), Fraction(Decimal(ipo_price))
    if p <= 0:
        raise OutcomeError("arz fiyatı pozitif olmalı")
    r = c / p - 1
    if r == 0:
        text = "0"
    else:
        with localcontext() as ctx:
            ctx.prec = EXACT_DIGITS
            text = format(Decimal(r.numerator) / Decimal(r.denominator), "f").rstrip("0").rstrip(".")
    return text, int(r > 0)


# ============================================================ sonuç dosyası

def outcome_rows(ticker: str, ipo_price: str, calendar: SessionCalendar, thb_by_date: Mapping[str, Any],
                 thm_by_date: Mapping[str, Any], *, start: Optional[str] = None) -> list[dict[str, str]]:
    res = resolve_sessions(ticker, calendar, thb_by_date, start=start)
    rows: list[dict[str, str]] = []
    for h in range(1, N_SESSIONS + 1):
        row = {c: "" for c in OUTCOME_COLUMNS}
        row["h"] = str(h)
        if h <= len(res.sessions):
            s = res.sessions[h - 1]
            lim = (thm_by_date.get(s.date) or {}).get(equity_code(ticker))
            label = ceiling_label(ticker, s, thm_by_date)
            row.update(session_date=s.date, close_raw=s.close_raw, trade_count_raw=s.trade_count_raw,
                       upper_limit_raw=lim.upper if lim else "", reference_raw=lim.reference if lim else "",
                       halt_flag=str(s.halt_flag), half_day=str(s.half_day),
                       shifted_by_suspension=str(s.shifted_by_suspension),
                       ceiling_close=NA if label is None else str(label), ipo_price=ipo_price,
                       thb_sha256=getattr(thb_by_date[s.date], "sha256", ""),
                       thm_sha256=getattr(thm_by_date.get(s.date), "sha256", ""),
                       status=STATUS_NA_LIMIT if label is None else STATUS_OK)
            if h in TARGET_H:
                row["R_h"], y = exact_return(s.close_raw, ipo_price)
                row["Y_h"] = str(y)
        else:
            row["status"] = STATUS_TARGET_UNAVAILABLE if res.exhausted else STATUS_PENDING
        rows.append(row)
    return rows


def outcome_path(ticker: str, outcomes_dir: Path = OUTCOMES_DIR) -> Path:
    return Path(outcomes_dir) / f"{ticker}.csv"


def read_outcome(path: Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != OUTCOME_COLUMNS:
            raise OutcomeError(f"{path}: sütunlar {reader.fieldnames}")
        return list(reader)


def _rows_bytes(rows: Sequence[Mapping[str, str]]) -> bytes:
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=OUTCOME_COLUMNS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r[k] for k in OUTCOME_COLUMNS})
    return buf.getvalue().encode("utf-8")


def write_outcome(ticker: str, rows: Sequence[Mapping[str, str]], outcomes_dir: Path = OUTCOMES_DIR) -> str:
    """CREATED | UPDATED | UNCHANGED. Var olan dosyada yalnız PENDING satırlar değişebilir."""
    path = outcome_path(ticker, outcomes_dir)
    payload = _rows_bytes(rows)
    if path.exists():
        old = read_outcome(path)
        for a, b in zip(old, rows):
            if a["status"] != STATUS_PENDING and dict(a) != {k: b[k] for k in OUTCOME_COLUMNS}:
                raise OutcomeConflict(f"{ticker} h={a['h']}: dolu satır değişiyor ({a} -> {dict(b)}); resmi veri değişmiş olabilir")
        if path.read_bytes() == payload:
            return "UNCHANGED"
        path.write_bytes(payload)
        return "UPDATED"
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_new(path, payload)
    return "CREATED"


# ============================================================ kapsam ve güncelleme

def ipo_price_of(ticker: str) -> Optional[str]:
    p = reg.INPUTS_DIR / f"{ticker}.json"
    if not p.exists():
        return None
    return reg.load_inputs(p)[0]["fields"]["ipo_price_tl"]["value"]


def in_scope_ipos() -> list[dict[str, str]]:
    """ipos.csv'de FROZEN ya da SKIPPED (halka arz) satırlar, ilk işlem gününe göre."""
    _, rows = reg.read_ipos()
    return sorted((r for r in rows if r["status"] in reg.IPO_STATUSES), key=lambda r: (r["first_trading_date"], r["ticker"]))


def available_sessions(calendar: SessionCalendar, start: str, through: str, *, bist_dir: Path = BIST_DIR,
                       kinds: Sequence[str] = KINDS) -> tuple[dict[str, Bulletin], dict[str, Bulletin]]:
    """Yerel bültenler (ağ yok): start..through arasındaki resmi seanslardan dosyası olanlar; ilk eksik
    seansta durur (sonrası PENDING)."""
    thb: dict[str, Bulletin] = {}
    thm: dict[str, Bulletin] = {}
    for s in calendar.sessions_from(start):
        if s > through:
            break
        b = local_bulletin(s, "thb", bist_dir)
        m = local_bulletin(s, "thm", bist_dir) if "thm" in kinds else None
        if b is None or ("thm" in kinds and m is None):
            break
        thb[s] = b
        if m is not None:
            thm[s] = m
    return thb, thm


def _record_closure(s: str, kind: str, later: str, bist_dir: Path, now: Optional[datetime]) -> None:
    _append_csv(Path(bist_dir) / CLOSURES_NAME, CLOSURE_COLUMNS, {
        "date": s, "kind": kind, "url": source_url(s, kind), "http_status": "404",
        "later_session_published": later, "detected_at": _now_istanbul(now)})


def download_range(calendar: SessionCalendar, start: str, through: str, *, kinds: Sequence[str] = KINDS,
                   bist_dir: Path = BIST_DIR, downloader: Optional[Downloader] = None,
                   now: Optional[datetime] = None, root: Path = ROOT,
                   pinned: Optional[Mapping[tuple[str, str], str]] = None) -> dict[str, Any]:
    """start..through arasındaki resmi seansların bültenlerini indirir (yerelde olanı yeniden indirmez).
    THB 404: bir sonraki resmi seansın THB'si yayımlanmışsa ilan dışı kapanış (UNANNOUNCED_CLOSURE,
    takvimden çıkar); değilse henüz yayımlanmamıştır, durulur. Dönüş: son tam seans ve sayılar."""
    pinned = h99_pinned_sha256() if pinned is None else pinned
    last = None
    fetched = 0
    closures: list[str] = []
    sessions = [s for s in calendar.sessions_from(start) if s <= through]
    i = 0
    while i < len(sessions):
        s = sessions[i]
        before = local_path(s, "thb", bist_dir).exists()
        try:
            fetch(s, "thb", bist_dir=bist_dir, downloader=downloader, pinned=pinned, now=now, root=root)
        except NotPublished:
            later = next((t for t in sessions[i + 1:] if _published(t, bist_dir, downloader)), None)
            if later is None:
                break
            _record_closure(s, "thb", later, bist_dir, now)
            closures.append(s)
            i += 1
            continue
        fetched += not before
        for kind in kinds:
            if kind != "thb":
                before_k = local_path(s, kind, bist_dir).exists()
                fetch(s, kind, bist_dir=bist_dir, downloader=downloader, pinned=pinned, now=now, root=root)
                fetched += not before_k
        last = s
        i += 1
    return {"through_session": last, "files_fetched": fetched, "unannounced_closures": closures}


def _published(s: str, bist_dir: Path, downloader: Optional[Downloader]) -> bool:
    if local_path(s, "thb", bist_dir).exists():
        return True
    try:
        (downloader or download_bytes)(source_url(s, "thb"))
    except NotPublished:
        return False
    return True


def build_outcomes(calendar: SessionCalendar, through: str, *, bist_dir: Path = BIST_DIR,
                   outcomes_dir: Path = OUTCOMES_DIR, write: bool = True) -> dict[str, Any]:
    """Kapsam içi her arz için sonuç satırları (yerel bültenlerden). `write=False`: yalnız hesap."""
    ipos = in_scope_ipos()
    out: dict[str, Any] = {}
    if not ipos:
        return out
    start = calendar.previous(min(r["first_trading_date"] for r in ipos)) or min(r["first_trading_date"] for r in ipos)
    thb, thm = available_sessions(calendar, start, through, bist_dir=bist_dir)
    for r in ipos:
        t = r["ticker"]
        price = ipo_price_of(t)
        if price is None:
            out[t] = {"status": "NO_IPO_PRICE", "note": "registry/inputs/<T>.json yok (SKIPPED arz)"}
            continue
        rows = outcome_rows(t, price, calendar, thb, thm, start=start)
        action = write_outcome(t, rows, outcomes_dir) if write else "NOT_WRITTEN"
        out[t] = {"action": action, "rows": rows, "listed_first_trading_date": r["first_trading_date"]}
    return out


def as_of_session(calendar: Optional[SessionCalendar] = None, *, bist_dir: Path = BIST_DIR) -> Optional[str]:
    """THB ve THM'si yerelde bulunan, kesintisiz dizinin son resmi seansı (kapsamın ilk arzından önceki
    seanstan başlayarak)."""
    calendar = calendar or load_calendar(bist_dir=bist_dir)
    ipos = in_scope_ipos()
    if not ipos:
        return None
    first = min(r["first_trading_date"] for r in ipos)
    start = calendar.previous(first) or first
    thb, _ = available_sessions(calendar, start, calendar.last_day, bist_dir=bist_dir)
    return max(thb) if thb else None


def update(*, through: Optional[str] = None, today: Optional[str] = None, bist_dir: Path = BIST_DIR,
           outcomes_dir: Path = OUTCOMES_DIR, downloader: Optional[Downloader] = None,
           now: Optional[datetime] = None, root: Path = ROOT) -> dict[str, Any]:
    calendar = load_calendar(bist_dir=bist_dir)
    today = today or datetime.now(ISTANBUL).date().isoformat()
    limit = min(through or today, today)
    ipos = in_scope_ipos()
    first = min(r["first_trading_date"] for r in ipos)
    start = calendar.previous(first) or first
    dl = download_range(calendar, start, limit, bist_dir=bist_dir, downloader=downloader, now=now, root=root)
    calendar = load_calendar(bist_dir=bist_dir)  # ilan dışı kapanışlar eklenmiş olabilir
    as_of = dl["through_session"]
    built = build_outcomes(calendar, as_of, bist_dir=bist_dir, outcomes_dir=outcomes_dir) if as_of else {}
    return {"calendar_start": start, "through_session": as_of, "files_fetched": dl["files_fetched"],
            "unannounced_closures": dl["unannounced_closures"],
            "outcomes": {t: {k: v for k, v in o.items() if k != "rows"} for t, o in built.items()}}


# ============================================================ tamlık denetimi (SPEC_SCORING §4)

INSTRUMENT_GROUPS = {  # THB 'ENSTRUMAN GRUBU'; yalnız EQT paydır
    "EQT": "pay",
    "ECW": "varant (alım)",
    "EPW": "varant (satım)",
    "XCR": "sertifika",
    "ETF": "borsa yatırım fonu",
    "GMF": "fon",
    "GSF": "fon",
    "GMS": "fon",
    "EMS": "fon",
    "AOF": "fon",
}
EQUITY_GROUP = "EQT"
BUYIN = "BUYIN"
BUYIN_REASON = "var olan payın temerrüt işlem kodu; halka arz değil"
C_BUYIN = "TEMERRUT_PAZARI"
C_NON_EQUITY = "PAY_DISI_ARAC"
C_REGISTERED = "IPOS_CSV"
C_CODE_CHANGE = "KOD_DEGISIKLIGI"
C_UNEXPLAINED = "ACIKLANAMAYAN_YENI_PAY"
COMPLETENESS_COLUMNS = ("first_seen", "code", "ticker", "name", "instrument_group", "market", "traded_first_seen",
                        "classification", "reason", "ipos_status", "ipos_first_trading_date")


def completeness(calendar: SessionCalendar, start: str, through: str, *, bist_dir: Path = BIST_DIR,
                 ipos_rows: Optional[Sequence[Mapping[str, str]]] = None) -> dict[str, Any]:
    """start..through arasındaki her resmi seansta Pay Piyasası THB'sinde İLK KEZ görünen işlem kodları
    (taban: start'tan önceki son resmi seansın THB'si ve pencerede daha önce görülen kodlar).

    Sınıflama kuralları (sonuç görülmeden, kodla; 0 numaralı kural EK 1 kararıyla sonradan eklendi):
      0 temerrüt (buy-in) pazarı satırı: PAZAR ya da YAPISAL BAZDA PIYASA ALT BOLUMU (İng. MARKET) = BUYIN,
        ya da ENSTRUMAN TIPI BUYIN ile başlıyor         -> TEMERRUT_PAZARI (var olan payın temerrüt kodu)
      1 ENSTRUMAN GRUBU ≠ EQT                         -> PAY_DISI_ARAC (varant, sertifika, fon …)
      2 pay ve ticker ipos.csv'de                      -> IPOS_CSV:<status>[:<skip_reason>]
      3 pay; aynı gün kaybolan bir pay koduyla aynı BULTEN ADI -> KOD_DEGISIKLIGI:<eski kod>
      4 aksi halde                                     -> ACIKLANAMAYAN_YENI_PAY (olası yeni halka arz: DUR)
    Ayrıca ipos.csv'deki (FROZEN/SKIPPED) ve ilk işlem günü ≤ through her arz pencerede yeni pay olarak
    görünmeli (`listed_not_seen`)."""
    if ipos_rows is None:
        _, ipos_rows = reg.read_ipos()
    by_ticker: dict[str, list[Mapping[str, str]]] = {}
    for r in ipos_rows:
        by_ticker.setdefault(r["ticker"], []).append(r)
    base_day = calendar.previous(start)
    if base_day is None:
        raise OutcomeError(f"{start} öncesinde takvim seansı yok")
    thb, _ = available_sessions(calendar, base_day, through, bist_dir=bist_dir, kinds=("thb",))
    days = sorted(thb)
    if not days or days[0] != base_day or days[-1] != through:
        raise OutcomeError(f"tamlık denetimi için THB eksik: {base_day}..{through} (yerelde {days[:1]}..{days[-1:]})")
    seen = thb[base_day].codes()
    out: list[dict[str, str]] = []
    for prev_day, d in zip(days, days[1:]):
        b = thb[d]
        codes = b.codes()
        vanished = {c: r.name for c, r in thb[prev_day].rows.items() if r.group == EQUITY_GROUP and c not in codes}
        buyin = _buyin_codes(b, bist_dir) if codes - seen else set()
        for code in sorted(codes - seen):
            row = b.rows.get(code)
            group = row.group if row else ""
            ticker = code.split(".")[0]
            reg_rows = by_ticker.get(ticker, [])
            ipo = next((x for x in reg_rows if x["status"] in reg.IPO_STATUSES), reg_rows[0] if reg_rows else None)
            entry = {"first_seen": d, "code": code, "ticker": ticker, "name": row.name if row else "",
                     "instrument_group": group, "market": row.market if row else "",
                     "traded_first_seen": str(int(traded(row))), "ipos_status": ipo["status"] if ipo else "",
                     "ipos_first_trading_date": ipo["first_trading_date"] if ipo else ""}
            if code in buyin:
                entry["classification"], entry["reason"] = C_BUYIN, BUYIN_REASON
            elif group != EQUITY_GROUP:
                entry["classification"] = C_NON_EQUITY
                entry["reason"] = INSTRUMENT_GROUPS.get(group, f"pay dışı araç ({group or 'grup yok'})")
            elif ipo is not None:
                entry["classification"] = C_REGISTERED
                entry["reason"] = ":".join(x for x in (ipo["status"], ipo["skip_reason"]) if x)
            else:
                old = next((c for c, n in sorted(vanished.items()) if row and n and n == row.name), None)
                if old is not None:
                    entry["classification"], entry["reason"] = C_CODE_CHANGE, f"eski kod {old}"
                else:
                    entry["classification"], entry["reason"] = C_UNEXPLAINED, "olası yeni halka arz; DUR ve raporla"
            out.append(entry)
        seen |= codes
    new_equity = {e["ticker"] for e in out if e["instrument_group"] == EQUITY_GROUP}
    listed_not_seen = [r["ticker"] for r in ipos_rows if r["status"] in reg.IPO_STATUSES
                       and r["first_trading_date"] and start <= r["first_trading_date"] <= through
                       and r["ticker"] not in new_equity]
    unexplained = [e for e in out if e["classification"] == C_UNEXPLAINED]
    return {"baseline_session": base_day, "start": start, "through": through, "sessions": len(days) - 1,
            "new_codes": out, "unexplained": unexplained, "listed_not_seen": listed_not_seen,
            "ok": not unexplained and not listed_not_seen}


def _buyin_codes(bulletin: Bulletin, bist_dir: Path = BIST_DIR) -> set[str]:
    """Bültendeki temerrüt (buy-in) pazarı kodları. Aynı yerel zip (sha256'sı bülteninkiyle aynı olmalı) ad
    tabanlı yeniden okunur; bu sütunlar yalnız tamlık sınıflamasında kullanılır."""
    data = local_path(bulletin.market_date, "thb", bist_dir).read_bytes()
    if sha256_bytes(data) != bulletin.sha256:
        raise OutcomeError(f"THB {bulletin.market_date}: yerel dosya ayrıştırılan bültenle aynı değil")
    parsed = parse_archive_bytes(data, internal_name(bulletin.market_date, "thb"))
    h = {name: i for i, name in enumerate(parsed["headers"])}
    col = lambda r, name: r[h[name]] if name in h else ""  # noqa: E731
    return {r[h["ISLEM  KODU"]] for r in parsed["rows"]
            if BUYIN in (col(r, "PAZAR"), col(r, "YAPISAL BAZDA PIYASA ALT BOLUMU"))
            or col(r, "ENSTRUMAN TIPI").startswith(BUYIN)}


def write_completeness(result: Mapping[str, Any], outcomes_dir: Path = OUTCOMES_DIR) -> Path:
    path = Path(outcomes_dir) / COMPLETENESS_NAME
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=COMPLETENESS_COLUMNS, lineterminator="\n")
    w.writeheader()
    for e in result["new_codes"]:
        w.writerow({k: e.get(k, "") for k in COMPLETENESS_COLUMNS})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(buf.getvalue().encode("utf-8"))
    return path


# ============================================================ CLI

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Resmi BIST THB/THM sonuçları (SPEC_SCORING §1-§4).")
    sub = parser.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="tek seansın THB ve THM'sini indir (yerelde varsa denetle)")
    f.add_argument("date")
    u = sub.add_parser("update", help="eksik seansları indir ve kapsam içi her arzın sonuç dosyasını üret")
    u.add_argument("--through", default=None)
    c = sub.add_parser("completeness", help="pencerede ilk kez görünen işlem kodları (SPEC_SCORING §4)")
    c.add_argument("--start", default=reg.SCOPE_START)
    c.add_argument("--through", default=None)
    args = parser.parse_args(argv)
    if args.cmd == "fetch":
        res = {k: fetch(args.date, k).sha256 for k in KINDS}
        print(json.dumps({"date": args.date, "sha256": res}, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "update":
        print(json.dumps(update(through=args.through), ensure_ascii=False, indent=2))
        return 0
    calendar = load_calendar()
    through = args.through or as_of_session(calendar)
    if through is None:
        parser.error("yerelde bülten yok; önce update")
    base = calendar.previous(args.start)
    dl = download_range(calendar, base, through, kinds=("thb",))
    calendar = load_calendar()
    if dl["through_session"] != through:
        raise OutcomeError(f"THB {through}'e kadar tamamlanamadı ({dl['through_session']})")
    result = completeness(calendar, args.start, through)
    path = write_completeness(result)
    print(json.dumps({k: v for k, v in result.items() if k != "new_codes"} | {"file": str(path),
                      "n_new_codes": len(result["new_codes"])}, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())

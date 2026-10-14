"""Tahmin sicili: payda (ipos.csv), girdi belgeleri, legacy rolleri ve birincil kayıt seçimi.
Yalnız stdlib (masaüstü uygulaması da okur).

- `registry/ipos.csv` (SPEC_SCORING §4): arz başına bir satır, append-only.
- `registry/inputs/<TICKER>.json` (şema `borsai.inputs/1`): listeleme öncesi resmi belgelerden
  girdiler. Her dolu alan kaynak belge kimliği, yayın zamanı ve belgenin sha256'sını taşır;
  boş alan `missing_reason` taşır (tahmin, türetme, ikincil kaynak yok).
- `inputs_pit_ok` (SPEC_SCORING §5): her dolu alanın kaynağı ilk işlem gününden (Europe/Istanbul
  tarihi) önce yayımlanmış ve belge dosyası sha256'sıyla eşleşiyor.
- `registry/legacy_roles.json`: registry/legacy_frozen kayıtlarının SPEC_SCORING §6 rolleri.
- `select_primary`: SPEC_SCORING §6 birincil kayıt kuralı (sonuç görülmeden, önceden ilan).
- POST_D1 aşaması (SPEC_POST_D1_V0 §7): `registry/post_d1/<TICKER>/` kayıtları, `t_open` (D_1'i izleyen ilk resmi seans
  09:40:00+03:00), `select_primary_post_d1`, `post_d1_record_problems` (bekçi: yalnız D_1 alanları, yalnız `d1` bloğunda).
- POST_BREAK aşaması (SPEC_BREAK_V0 §9; makine sıralı): `registry/post_break/<TICKER>/` makine kayıtları, `post_break_record_problems`
  (bekçi: yalnız D_1..D_b, h > b sonuç anahtarı ve D_b sonrası bülten adı/sha'sı yok).

Sınıf (LIVE / LATE_RECORD / RETRO) burada ETİKETLENMEZ; Faz 2B'de git DAG'ı, push kanıtı ve
tarihlerden hesaplanır.
"""
from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

from .features import PB_REQUIRED_FIELDS
from .provenance import ISTANBUL, ROOT, sha256_file

REGISTRY_DIR = ROOT / "registry"
INPUTS_DIR = REGISTRY_DIR / "inputs"
RECORDS_DIR = REGISTRY_DIR / "records"
IPOS_PATH = REGISTRY_DIR / "ipos.csv"
LEGACY_ROLES_PATH = REGISTRY_DIR / "legacy_roles.json"
LEGACY_DIR = REGISTRY_DIR / "legacy_frozen"

# ---------------------------------------------------------------- payda (SPEC_SCORING §4)

SCOPE_START = "2026-08-07"
IPOS_COLUMNS: tuple[str, ...] = ("ticker", "company", "first_trading_date", "listing_source_id", "status",
                                 "skip_reason", "note", "added_at")
STATUSES = ("FROZEN", "SKIPPED", "OUT_OF_SCOPE")
SKIP_REASONS = ("NO_RECORD_BEFORE_LISTING", "PUSH_PROOF_MISSING", "INPUTS_NOT_AVAILABLE")
IPO_STATUSES = ("FROZEN", "SKIPPED")
KNOWN_TICKERS = ("CITAS", "VEYAS", "TKNKA", "KPEKS", "INTET", "BKRGY", "NETGL")
_SOURCE_ID = re.compile(r"^KAP_\d+$")


class RegistryError(ValueError):
    pass


def _iso_date(value: str) -> bool:
    try:
        return date.fromisoformat(value).isoformat() == value
    except (TypeError, ValueError):
        return False


def _iso_datetime_with_offset(value: str) -> bool:
    try:
        return datetime.fromisoformat(value).tzinfo is not None
    except (TypeError, ValueError):
        return False


def valid_skip_reason(value: str) -> bool:
    return value in SKIP_REASONS or (value.startswith("OTHER:") and len(value) > len("OTHER:"))


def read_ipos(path: Path = IPOS_PATH) -> tuple[list[str], list[dict[str, str]]]:
    with Path(path).open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def validate_ipos(header: Sequence[str], rows: Sequence[Mapping[str, str]]) -> list[str]:
    """Şema sorunları (boş liste = geçerli)."""
    problems: list[str] = []
    if tuple(header) != IPOS_COLUMNS:
        problems.append(f"sütunlar {tuple(header)} != {IPOS_COLUMNS}")
        return problems
    seen: set[str] = set()
    for i, r in enumerate(rows, start=2):
        where = f"satır {i} ({r.get('ticker')})"
        status, reason = r["status"], r["skip_reason"]
        if status not in STATUSES:
            problems.append(f"{where}: status {status!r}")
        if status == "FROZEN" and reason:
            problems.append(f"{where}: FROZEN satırda skip_reason dolu")
        if status != "FROZEN" and not valid_skip_reason(reason):
            problems.append(f"{where}: FROZEN olmayan satırda skip_reason boş ya da geçersiz ({reason!r})")
        if status == "OUT_OF_SCOPE" and not reason.startswith("OTHER:"):
            problems.append(f"{where}: OUT_OF_SCOPE nedeni OTHER:<metin> olmalı")
        if not _SOURCE_ID.match(r["listing_source_id"]):
            problems.append(f"{where}: listing_source_id {r['listing_source_id']!r}")
        if not _iso_datetime_with_offset(r["added_at"]):
            problems.append(f"{where}: added_at {r['added_at']!r}")
        if status in IPO_STATUSES:
            if not r["ticker"] or not r["company"]:
                problems.append(f"{where}: ticker/company boş")
            if r["ticker"] in seen:
                problems.append(f"{where}: aynı arz iki kez")
            seen.add(r["ticker"])
            if not _iso_date(r["first_trading_date"]) or r["first_trading_date"] < SCOPE_START:
                problems.append(f"{where}: first_trading_date {r['first_trading_date']!r} (kapsam {SCOPE_START}+)")
        elif r["first_trading_date"] and not _iso_date(r["first_trading_date"]):
            problems.append(f"{where}: first_trading_date {r['first_trading_date']!r}")
    return problems


def append_ipos(new_rows: Sequence[Mapping[str, str]], path: Path = IPOS_PATH) -> None:
    """Append-only: var olan satırlar değişmez; aynı arz (FROZEN/SKIPPED) ikinci kez eklenmez."""
    path = Path(path)
    header, rows = (list(IPOS_COLUMNS), []) if not path.exists() else read_ipos(path)
    combined = rows + [dict(r) for r in new_rows]
    problems = validate_ipos(header, combined)
    if problems:
        raise RegistryError("; ".join(problems))
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=IPOS_COLUMNS, lineterminator="\n")
    if not path.exists():
        writer.writeheader()
    for r in new_rows:
        writer.writerow({k: r.get(k, "") for k in IPOS_COLUMNS})
    with path.open("a", encoding="utf-8", newline="") as fh:
        fh.write(buf.getvalue())


# ---------------------------------------------------------------- girdi belgeleri

INPUTS_SCHEMA = "borsai.inputs/1"
V15_FIELDS: tuple[str, ...] = (
    "ipo_price_tl", "shares_offered", "post_ipo_share_capital", "capital_increase_shares",
    "existing_share_sale_shares", "total_demand_multiple", "total_demand_filter_status",
    "additional_sale_shares", "ipo_size_tl",
)
PB_FIELDS: tuple[str, ...] = PB_REQUIRED_FIELDS
DATE_FIELDS: tuple[str, ...] = ("first_trading_date", "bookbuilding_start", "bookbuilding_end")
INPUT_FIELDS: tuple[str, ...] = V15_FIELDS + PB_FIELDS + DATE_FIELDS
FIELD_SOURCE_KEYS: tuple[str, ...] = ("source_id", "source_document", "source_published_at", "source_sha256", "source_path")
F3_ORIGINS = ("SOURCE_REPORTED", "SOURCE_REPORTED_APPROX", "CALCULATED_FROM_SOURCE_TOTALS", "CALCULATED_FROM_PRIMARY_TOTALS")
FILTER_STATUSES = ("NOT_SPECIFIED", "UNFILTERED", "FILTERED")


def load_inputs(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = Path(path).read_bytes()
    return json.loads(raw.decode("utf-8")), raw


def istanbul_date(timestamp: str) -> str:
    """Zaman damgasının Europe/Istanbul takvim tarihi (Türkiye 2016'dan beri UTC+3)."""
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise RegistryError(f"zaman dilimi yok: {timestamp!r}")
    return dt.astimezone(ISTANBUL).date().isoformat()


def validate_inputs(doc: Mapping[str, Any]) -> list[str]:
    """Yapısal denetim: bütün alanlar var; dolu alan kaynak kimliği/yayın zamanı/sha taşır ve
    kaynak tablosuyla tutarlı; boş alan gerekçe taşır."""
    problems: list[str] = []
    if doc.get("schema_version") != INPUTS_SCHEMA:
        return [f"schema_version {doc.get('schema_version')!r}"]
    if not doc.get("ticker"):
        problems.append("ticker yok")
    fields = doc.get("fields") or {}
    sources = doc.get("sources") or {}
    for name in INPUT_FIELDS:
        if name not in fields:
            problems.append(f"{name}: alan yok")
            continue
        f = fields[name]
        if f.get("value") is None:
            if not f.get("missing_reason"):
                problems.append(f"{name}: boş alan missing_reason taşımıyor")
            continue
        if not isinstance(f["value"], str):
            problems.append(f"{name}: değer metin değil ({f['value']!r})")
        for key in FIELD_SOURCE_KEYS:
            if not f.get(key):
                problems.append(f"{name}: {key} yok")
        src = sources.get(f.get("source_id"))
        if src is None:
            problems.append(f"{name}: kaynak {f.get('source_id')!r} kaynak tablosunda yok")
            continue
        for fk, sk in (("source_published_at", "published_at"), ("source_sha256", "sha256"), ("source_path", "path")):
            if f.get(fk) != src.get(sk):
                problems.append(f"{name}: {fk} kaynak tablosuyla uyuşmuyor")
        if not _iso_datetime_with_offset(f.get("source_published_at", "")):
            problems.append(f"{name}: yayın zamanı ISO + saat dilimi değil")
    for name in DATE_FIELDS:
        v = fields.get(name, {}).get("value")
        if v is not None and not _iso_date(v):
            problems.append(f"{name}: ISO tarih değil ({v!r})")
    f3 = fields.get("total_demand_multiple", {})
    if f3.get("value") is not None and f3.get("origin") not in F3_ORIGINS:
        problems.append(f"total_demand_multiple: origin {f3.get('origin')!r}")
    fs = fields.get("total_demand_filter_status", {}).get("value")
    if fs is not None and fs not in FILTER_STATUSES:
        problems.append(f"total_demand_filter_status {fs!r}")
    return problems


def inputs_pit_problems(doc: Mapping[str, Any], *, root: Path = ROOT, check_files: bool = True,
                        as_of: Optional[str] = None) -> list[str]:
    """SPEC_SCORING §5 inputs_pit_ok'un girdi kısmı: her dolu alanın kaynak belgesi ilk işlem
    gününden (Istanbul tarihi) KESİN önce yayımlanmış; belge dosyası var ve sha256 eşleşiyor.
    `as_of` verilirse yayın zamanı ondan sonra olamaz. f6 kısmı kayıttaki market20 bloğundadır."""
    problems = validate_inputs(doc)
    fields = doc.get("fields") or {}
    t = fields.get("first_trading_date", {}).get("value")
    checked_files: set[str] = set()
    for name in INPUT_FIELDS:
        f = fields.get(name) or {}
        if f.get("value") is None or not f.get("source_published_at"):
            continue
        pub = f["source_published_at"]
        if t is not None and not istanbul_date(pub) < t:
            problems.append(f"{name}: kaynak {f['source_id']} yayını {pub} ilk işlem günü {t}'den önce değil")
        if as_of is not None and datetime.fromisoformat(pub) > datetime.fromisoformat(as_of):
            problems.append(f"{name}: kaynak {f['source_id']} kayıt zamanından sonra yayımlanmış")
        path = f.get("source_path")
        if check_files and path and path not in checked_files:
            checked_files.add(path)
            p = root / path
            if not p.exists():
                problems.append(f"{name}: belge dosyası yok ({path})")
            elif sha256_file(p) != f["source_sha256"]:
                problems.append(f"{name}: belge sha256 uyuşmuyor ({path})")
    return problems


def model_inputs(doc: Mapping[str, Any]) -> dict[str, Optional[str]]:
    """predict fonksiyonlarına giden düz girdi sözlüğü (değerler belgedeki metin)."""
    fields = doc["fields"]
    return {name: fields[name].get("value") for name in V15_FIELDS + PB_FIELDS}


# ---------------------------------------------------------------- legacy rolleri (SPEC_SCORING §6)

LEGACY_ROLES_SCHEMA = "borsai.legacy_roles/1"
LEGACY_ROLES = ("PRIMARY", "INVALID_USE", "PRIMARY_SEPARATE_MODEL")
LEGACY_TIME_PROOFS = ("GIT_PUSH", "SELF_REPORTED")


def load_legacy_roles(path: Path = LEGACY_ROLES_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_legacy_roles(doc: Mapping[str, Any], *, root: Path = ROOT) -> list[str]:
    """Her legacy_frozen kaydı tam bir kez; dosya sha256'ları eşleşiyor; roller şartnamedeki gibi."""
    problems: list[str] = []
    if doc.get("schema_version") != LEGACY_ROLES_SCHEMA:
        return [f"schema_version {doc.get('schema_version')!r}"]
    entries = doc.get("records", [])
    dirs = sorted(p.name for p in (root / "registry" / "legacy_frozen").iterdir() if p.is_dir())
    named = sorted(e["record"] for e in entries)
    if named != dirs:
        problems.append(f"legacy kayıt kümesi {named} != {dirs}")
    covered: set[str] = set()
    for e in entries:
        if e["role"] not in LEGACY_ROLES or e["time_proof"] not in LEGACY_TIME_PROOFS:
            problems.append(f"{e['record']}: rol/zaman kanıtı {e['role']!r}/{e['time_proof']!r}")
        if e.get("legacy_import") is not True:
            problems.append(f"{e['record']}: legacy_import true değil")
        if e["role"] == "PRIMARY" and not e.get("has_official_f3"):
            problems.append(f"{e['record']}: birincil kayıtta resmi f3 yok")
        if e["role"] == "INVALID_USE" and e.get("has_official_f3"):
            problems.append(f"{e['record']}: geçersiz kullanım f3'lü olamaz")
        if e["time_proof"] == "GIT_PUSH" and not e.get("push_proof_created_at"):
            problems.append(f"{e['record']}: GIT_PUSH ama push_proof_created_at yok")
        for rel, sha in e["files"].items():
            p = root / rel
            covered.add(rel)
            if not p.exists() or sha256_file(p) != sha:
                problems.append(f"{e['record']}: {rel} yok ya da sha256 uyuşmuyor")
    for p in (root / "registry" / "legacy_frozen").rglob("*"):
        rel = p.relative_to(root).as_posix()
        if p.is_file() and rel not in covered and rel not in doc.get("shared_files", {}):
            problems.append(f"legacy dosyası hiçbir kayda bağlı değil: {rel}")
    return problems


def legacy_links(ticker: str, doc: Optional[Mapping[str, Any]] = None) -> list[dict[str, Any]]:
    doc = doc if doc is not None else load_legacy_roles()
    return [dict(e) for e in doc["records"] if e["ticker"] == ticker]


# ---------------------------------------------------------------- birincil kayıt (SPEC_SCORING §6)

# f3 (talep katı) isteyen kayıtlı modeller. Tek kaynak burasıdır (SPEC_DEVIATIONS F13): SPEC_SCORING §6 metni
# dört modeli adıyla sayar, `ceiling_path_v0` ondan sonra donduruldu ve f3'süz girdiyi reddeder (gömülü
# ceiling_hazard_v0 kuralı). Sıfır model ve PB varyantı f3 istemez. Denetim: tests/test_faz4_ceiling_path.py::test_13b.
# Faz 7: `ceiling_hazard_v1_clip/_real/_pooled` f3'süz girdiyi v0 gibi reddeder (SPEC_HAZARD_V1 §9 "miras"); kural satırı
# `ceiling_hazard_v1_pooled@INF` f3 istemez (SPEC_DEVIATIONS J). Bir model INDEX'te değilken buradaki adı etkisizdir.
# Faz 7C: `fall_d10_v0_h99` ve `_pooled` f3'süz girdiyi F3_MISSING ile reddeder (SPEC_C_V0 §9); `fall_d10_v0_addsale` (yalnız ek
# satış) ve kural satırı `fall_d10_v0_pooled@ZERO` f3 istemez: en erken kayıt kuralı (SPEC_DEVIATIONS K16, J24 kalıbı).
F3_MODELS = frozenset({"v1_5_h99", "v1_6_h99", "v1_5_market20_v0", "ceiling_hazard_v0", "ceiling_path_v0",
                       "ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled",
                       "fall_d10_v0_h99", "fall_d10_v0_pooled"})


@dataclass(frozen=True)
class Candidate:
    """Bir (model, arz) için aday kayıt. `track`: REGISTRY (bu sicilin kaydı; zaman kanıtı
    commit push'u), GIT_PUSH (push kanıtlı legacy) ya da SELF_REPORTED (legacy, yalnız beyan)."""

    record_id: str
    model_id: str
    track: str
    has_official_f3: bool
    recorded_at: str
    push_created_at: Optional[str] = None
    inputs_pit_ok: bool = True
    cancelled: bool = False
    invalid_use: bool = False
    bookbuilding_start: Optional[str] = None


def _proven_before(c: Candidate, d1: str) -> bool:
    return c.push_created_at is not None and istanbul_date(c.push_created_at) < d1


def select_primary(model_id: str, candidates: Iterable[Candidate], d1: str) -> dict[str, Any]:
    """SPEC_SCORING §6. İki iz ayrı seçilir ve asla birleştirilmez:
    `proven` (REGISTRY + GIT_PUSH) birincil canlı metriğe, `self_reported` ikincil satıra gider.

    - f3 isteyen modeller: resmi f3'lü kayıtlar arasında D_1'den önce push kanıtlı EN SON kayıt;
      yoksa en erken inputs_pit_ok kaydı (LATE_RECORD adayı).
    - PB modelleri ve kurallar: EN ERKEN kayıt; kayıt ilk talep toplama gününden sonra
      oluşturulduysa `pb_after_bookbuild_start = 1` (yine skorlanır).
    İptal edilmiş ve geçersiz kullanım kayıtları hiç aday değildir."""
    pool = [c for c in candidates if c.model_id == model_id and not c.cancelled and not c.invalid_use]
    out: dict[str, Any] = {"model_id": model_id}
    for track_name, tracks in (("proven", ("REGISTRY", "GIT_PUSH")), ("self_reported", ("SELF_REPORTED",))):
        cands = [c for c in pool if c.track in tracks]
        choice, rule = None, None
        if model_id in F3_MODELS:
            cands = [c for c in cands if c.has_official_f3]
            live = [c for c in cands if _proven_before(c, d1)]
            if live:
                choice, rule = max(live, key=lambda c: (c.push_created_at, c.recorded_at)), "LATEST_PUSH_PROVEN_BEFORE_D1"
            else:
                late = [c for c in cands if c.inputs_pit_ok]
                if late:
                    choice = min(late, key=lambda c: (c.push_created_at or "9999", c.recorded_at))
                    rule = "EARLIEST_LATE_RECORD"
        elif cands:
            choice = min(cands, key=lambda c: (c.push_created_at or "9999", c.recorded_at))
            rule = "EARLIEST_RECORD"
        entry: dict[str, Any] = {"record_id": choice.record_id if choice else None, "rule": rule or "NO_ELIGIBLE_RECORD"}
        if choice is not None and model_id not in F3_MODELS and choice.bookbuilding_start:
            made = istanbul_date(choice.push_created_at or choice.recorded_at)
            entry["pb_after_bookbuild_start"] = int(made >= choice.bookbuilding_start)
        out[track_name] = entry
    return out


# ---------------------------------------------------------------- POST_D1 aşaması (SPEC_POST_D1_V0 §7)

POST_D1_DIR = REGISTRY_DIR / "post_d1"
POST_D1_RECORD_SCHEMA = "borsai.post_d1_record/1"
# §7.3: T_open = D2_cal + 09:40:00 Europe/Istanbul (Pay Piyasası Prosedürü Ek-9, açılış emir toplama; tam ve yarım gün
# aynı). Türkiye 2016'dan beri sabit UTC+3 (provenance.ISTANBUL); yerel saat hiçbir yerde kullanılmaz.
T_OPEN_TIME = time(9, 40, 0)
T_OPEN_OFFSET = ISTANBUL
CALENDAR_NOT_AVAILABLE = "CALENDAR_NOT_AVAILABLE"


class CalendarNotAvailable(RegistryError):
    """D_1'i izleyen resmi seans takvimde yok (takvim 2026-12-31'de biter): T_open tahmin edilmez (etiketli hata)."""

    code = CALENDAR_NOT_AVAILABLE


def d2_cal(d1: str, calendar: Any) -> str:
    """§7.3 `D2_cal(a)`: resmi takvimde (SPEC_SCORING §2 official_sessions: tam + yarım gün, ilan dışı kapanışlar
    düşülmüş) D_1'den sonraki ilk seans günü. Payın o gün işlem görüp görmediğine bakılmaz: sınır takvimden.
    `calendar`: `outcomes.SessionCalendar` (sessions artan, first_day, last_day)."""
    if not _iso_date(d1):
        raise RegistryError(f"D_1 ISO tarih değil: {d1!r}")
    if not calendar.first_day <= d1 <= calendar.last_day:
        raise CalendarNotAvailable(f"{CALENDAR_NOT_AVAILABLE}: D_1 {d1} takvim dışında ({calendar.first_day}…{calendar.last_day})")
    later = [s for s in calendar.sessions if s > d1]
    if not later:
        raise CalendarNotAvailable(f"{CALENDAR_NOT_AVAILABLE}: takvimde D_1 {d1}'den sonra resmi seans yok "
                                   f"(takvim {calendar.last_day}'de bitiyor; uzatılana kadar T_open hesaplanmaz)")
    return later[0]


def t_open(d1: str, calendar: Any) -> datetime:
    """§7.3 `T_open(a)` = D2_cal(a) + 09:40:00+03:00 (saat dilimli an)."""
    return datetime.combine(date.fromisoformat(d2_cal(d1, calendar)), T_OPEN_TIME, tzinfo=T_OPEN_OFFSET)


def parse_instant(timestamp: str) -> datetime:
    """ISO zaman damgası (Z ya da ofsetli) -> saat dilimli an; ofsetsiz metin hata."""
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise RegistryError(f"zaman dilimi yok: {timestamp!r}")
    return dt


def before_t_open(timestamp: Optional[str], t_open_at: datetime) -> bool:
    """`timestamp` (push kanıtı created_at ya da kayıt anı) T_open'dan KESİN önce mi (an karşılaştırması)."""
    return timestamp is not None and parse_instant(timestamp) < t_open_at


@dataclass(frozen=True)
class PostD1Candidate:
    """Bir arzın POST_D1 kaydı (skorlama adayı). `push_created_at`: kaydı ekleyen commit'i kapsayan en erken kanıt."""

    record_id: str
    recorded_at: str
    push_created_at: Optional[str] = None
    inputs_pit_ok: bool = True
    cancelled: bool = False


def select_primary_post_d1(candidates: Iterable[PostD1Candidate], t_open_at: datetime) -> dict[str, Any]:
    """§7.4 birincil POST_D1 kaydı (sonuç görülmeden, önceden ilan): T_open'dan önce push kanıtlı EN ERKEN kayıt; yoksa
    inputs_pit_ok_post_d1 olan en erken kayıt (LATE_RECORD adayı). İptal edilmiş kayıt aday değildir."""
    pool = [c for c in candidates if not c.cancelled]
    live = [c for c in pool if before_t_open(c.push_created_at, t_open_at)]
    if live:
        c = min(live, key=lambda c: (parse_instant(c.push_created_at), c.recorded_at))
        return {"record_id": c.record_id, "rule": "EARLIEST_PUSH_PROVEN_BEFORE_T_OPEN"}
    late = [c for c in pool if c.inputs_pit_ok]
    if late:
        c = min(late, key=lambda c: (c.push_created_at or "9999", c.recorded_at))
        return {"record_id": c.record_id, "rule": "EARLIEST_INPUTS_PIT_OK"}
    return {"record_id": None, "rule": "NO_ELIGIBLE_RECORD"}


# §7.4 bekçisi: D_1 alanları (ham bülten alanları ve D_1'den türeyen sonuç adları) yalnız `d1` bloğunda. Donmuş tahmin kodu
# (predict_post_d1, predict_path.conditional) D_1'den türeyen değerleri çıktısının şu alt ağaçlarına da yazar; onlar da
# yalnız D_1 satırından hesaplanır (değişmez kod): models[].output.{d1_features, warnings, path_conditional.D1} ve üst düzey
# d1_features. h ≥ 2 sonucunu adlandıran anahtar HİÇBİR yerde olamaz.
POST_D1_FIELDS_RAW: tuple[str, ...] = ("open", "high", "low", "close", "volume", "turnover", "aof", "trade_count", "halt",
                                       "special_trade_volume", "special_trade_turnover", "reference_price", "upper_limit",
                                       "lower_limit")
POST_D1_D1_KEYS = frozenset(POST_D1_FIELDS_RAW) | {
    "ceiling_close_D1", "R_D1", "Y_D1", "realized_return", "official_close", "kapanis", "kapanis_fiyati", "closing_price",
    "ust_limit"}
POST_D1_OUTCOME_WORDS = frozenset({"realized", "realized_L", "target_return", "above_ipo_flag", "ceiling_streak_L", "outcome"})
_H_KEY = re.compile(r"^(?:R_D|Y_D|ceiling_close_D|realized_close_D|close_D|upper_limit_D|thb_D|thm_D)(\d+)$")
_BULLETIN_NAME = re.compile(r"(th[bm])(20\d{6})1\.(?:zip|csv)")
_SHA = re.compile(r"^[0-9a-f]{64}$")
_D1_SUBTREES = (("d1",), ("d1_features",), ("models", "*", "output", "d1_features"), ("models", "*", "output", "warnings"),
                ("models", "*", "output", "path_conditional", "D1"))


def _walk(obj: Any, path: tuple = ()) -> Iterable[tuple[tuple, Any, Any]]:
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            yield path, k, v
            yield from _walk(v, path + (k,))
    elif isinstance(obj, list):
        for v in obj:
            yield path, None, v
            yield from _walk(v, path + ("*",))


def _under(path: tuple, prefix: tuple) -> bool:
    return len(path) >= len(prefix) and all(p == "*" or p == q for p, q in zip(prefix, path))


def post_d1_record_problems(rec: Mapping[str, Any], manifest: Mapping[tuple[str, str], Mapping[str, str]]) -> list[str]:
    """§7.4 bekçisi ve §7.3 inputs_pit_ok_post_d1 (ii)–(iv) (tek tanım; tests/test_outcome_guard.py de bunu çağırır):
    - `d1.session_h` = 1; bütün `session_date` değerleri D_1;
    - h ≥ 2 sonucunu adlandıran anahtar (R_D2, ceiling_close_D3 …) ya da sonuç sözcüğü hiçbir yerde yok;
    - D_1 alanları (`fields_raw` adları, ceiling_close_D1 …) yalnız `d1` bloğunda (ve donmuş kodun D_1 alt ağaçlarında);
    - bülten atıfları (d1.thb, d1.thm ve metindeki her bülten adı) tam olarak D_1 tarihli; sha256 MANIFEST'teki pinli
      değere eşit; kayıttaki hiçbir sha256 D_1 dışı bir bültenin pinli sha'sı değil.
    `manifest`: (tarih, tür) -> data/raw/bist/MANIFEST.csv satırı."""
    out: list[str] = []
    if rec.get("record_type") == "CANCELLATION":
        return out
    d1 = (rec.get("d1") or {}).get("session_date")
    if not d1 or not _iso_date(d1):
        return [f"d1.session_date yok ya da ISO değil: {d1!r}"]
    if (rec.get("d1") or {}).get("session_h") != 1:
        out.append(f"d1.session_h = {(rec.get('d1') or {}).get('session_h')!r} (1 olmalı)")
    other_sha = {m["sha256"]: key for key, m in manifest.items() if key[0] != d1}
    compact = d1.replace("-", "")
    for path, key, value in _walk(rec):
        if key is not None:
            m = _H_KEY.match(str(key))
            if (m and int(m.group(1)) >= 2) or key in POST_D1_OUTCOME_WORDS:
                out.append(f"{'.'.join(map(str, path + (key,)))}: D_1 dışı (h ≥ 2) sonuç anahtarı")
            if key in POST_D1_D1_KEYS and not any(_under(path, p) for p in _D1_SUBTREES):
                out.append(f"{'.'.join(map(str, path + (key,)))}: D_1 alanı d1 bloğu dışında")
            if key == "session_date" and value != d1:
                out.append(f"{'.'.join(map(str, path + (key,)))}: {value!r} D_1 değil")
        if isinstance(value, str):
            for bm in _BULLETIN_NAME.finditer(value):
                if bm.group(2) != compact:
                    out.append(f"{'.'.join(map(str, path + ((key,) if key is not None else ())))}: D_1 dışı bülten atfı")
            if _SHA.match(value) and value in other_sha:
                out.append(f"{'.'.join(map(str, path + ((key,) if key is not None else ())))}: D_1 dışı bültenin sha256'sı "
                           f"({other_sha[value][1]} {other_sha[value][0]})")
    for kind in ("thb", "thm"):
        ref = (rec.get("d1") or {}).get(kind) or {}
        pinned = manifest.get((d1, kind))
        if pinned is None:
            out.append(f"d1.{kind}: MANIFEST'te D_1 satırı yok")
        elif ref.get("sha256") != pinned["sha256"] or ref.get("url") != pinned.get("url"):
            out.append(f"d1.{kind}: sha256/url MANIFEST'teki pinli değerle aynı değil")
        if not str(ref.get("file", "")).endswith(f"/{kind}{compact}1.zip"):
            out.append(f"d1.{kind}.file D_1 tarihli değil: {ref.get('file')!r}")
    return out


# ---------------------------------------------------------------- POST_BREAK aşaması (SPEC_BREAK_V0 §9; makine sıralı)
# Makine kaydı `registry/post_break/<TICKER>/machine_<UTC>_<kısa-sha>.json` (şema borsai.post_break_machine_record/1, append-only,
# exposure_class = MACHINE_SEQUENCED): skorlama anında donmuş model JSON'u, D_1..D_b'nin sha-pinli resmi bültenleri ve listeleme
# öncesi girdi dosyasından deterministik üretilir (`freeze.write_post_break_machine_record`); insan değer girmez. Kayıt sınıf
# taşımaz (`scoring` hesaplar). Bekçi ayrı fonksiyondur; `post_d1_record_problems` değişmez (SPEC_DEVIATIONS N).

POST_BREAK_DIR = REGISTRY_DIR / "post_break"
POST_BREAK_RECORD_SCHEMA = "borsai.post_break_machine_record/1"
POST_BREAK_RECORD_TYPE = "MACHINE"
POST_BREAK_STAGE = "POST_BREAK"
POST_BREAK_B_MAX = 9                                        # kayıt yalnız b ∈ 1..9 için yazılır (§1.2)
# Kırılma hedefleri (taban etiketleri) ve D_{b+h} alanları: h > b ise hiçbir yerde olamaz (_H_KEY'e ek; aynı kural).
_H_KEY_FLOOR = re.compile(r"^(?:lower_limit_D|floor_close_D)(\d+)$")
POST_BREAK_OUTCOME_WORDS = POST_D1_OUTCOME_WORDS | {"y_F1", "y_F2", "realized_F1", "realized_F2"}
_POST_BREAK_DATE_KEYS = frozenset({"date", "session_date", "break_date"})


def post_break_inputs_pit_problems(doc: Mapping[str, Any], d1: str, *, root: Path = ROOT) -> list[str]:
    """§3, §9.3 `inputs_ref.inputs_pit_ok`: girdi belgesinin `inputs_pit_problems`'ı (her dolu alanın kaynağı ilk işlem gününden
    kesin önce, belge sha256'sı eşleşiyor) VE `shares_offered`'ın kaynak yayını gerçekleşen D_1'den (Istanbul tarihi) kesin önce
    (§3: "PIT: source_published_at < D_1"). Boş liste = PIT."""
    problems = inputs_pit_problems(doc, root=root)
    so = (doc.get("fields") or {}).get("shares_offered") or {}
    pub = so.get("source_published_at")
    if so.get("value") is None or not pub:
        problems.append("shares_offered: değer ya da kaynak yayın zamanı yok")
    elif not istanbul_date(pub) < d1:
        problems.append(f"shares_offered: kaynak yayını {pub} gerçekleşen D_1 {d1}'den önce değil")
    return problems


def post_break_record_problems(rec: Mapping[str, Any], manifest: Mapping[tuple[str, str], Mapping[str, str]]) -> list[str]:
    """§9.2 makine kaydı bekçisi (K-LB-4; tek tanım: tests/test_outcome_guard.py ve `scoring.inputs_pit_problems_break` bunu çağırır).
    D_b ve b kaydın kendisinden (`streak.break_date`, `streak.b`):
    - `streak.sessions` tam olarak h = 1..b, tarihler kesin artan (takvim sırası), son seans D_b; `break_day` h = b ve D_b;
    - h > b sonucunu adlandıran anahtar (R_D5, ceiling_close_D6, lower_limit_D7 …) ya da sonuç sözcüğü hiçbir yerde;
    - tarih anahtarları (date, session_date, break_date) D_b'den sonra değil;
    - metindeki her bülten adı D_1..D_b seans günlerinden birinin; kayıttaki hiçbir sha256 D_1..D_b dışı bir bültenin pinli sha'sı
      değil (D_b sonrası bülten adı ya da sha'sı -> kırmızı);
    - her seansın thb/thm atfı: sha256 MANIFEST'teki pinli değere eşit, dosya adı o günün bülteni.
    `manifest`: (tarih, tür) -> data/raw/bist/MANIFEST.csv satırı. Boş liste = temiz."""
    out: list[str] = []
    if rec.get("record_type") == "CANCELLATION":
        return out
    if (rec.get("schema_version"), rec.get("record_type"), rec.get("record_stage")) != (
            POST_BREAK_RECORD_SCHEMA, POST_BREAK_RECORD_TYPE, POST_BREAK_STAGE):
        out.append("şema / kayıt türü / aşama POST_BREAK makine kaydı değil")
    streak = rec.get("streak") or {}
    b, db = streak.get("b"), streak.get("break_date")
    if not isinstance(b, int) or isinstance(b, bool) or not 1 <= b <= POST_BREAK_B_MAX or not db or not _iso_date(db):
        return out + [f"streak.b / streak.break_date geçersiz: {b!r} / {db!r}"]
    sessions = streak.get("sessions") or []
    hs = [s.get("h") for s in sessions]
    dates = [s.get("date") for s in sessions]
    if hs != list(range(1, b + 1)):
        out.append(f"streak.sessions h = {hs} (1..{b} olmalı)")
    if not all(isinstance(d, str) and _iso_date(d) for d in dates) or any(x >= y for x, y in zip(dates, dates[1:])):
        out.append(f"streak.sessions tarihleri takvim sırasında değil: {dates}")
    if not dates or dates[-1] != db:
        out.append(f"son seans {dates[-1] if dates else None!r} D_b {db!r} değil")
    bd = rec.get("break_day") or {}
    if bd.get("h") != b or bd.get("session_date") != db:
        out.append(f"break_day h / session_date ({bd.get('h')!r}, {bd.get('session_date')!r}) (b, D_b) değil")
    session_days = {d.replace("-", "") for d in dates if isinstance(d, str)}
    compact_b = db.replace("-", "")
    session_keys = {(d, k) for d in dates for k in ("thb", "thm")}
    other_sha = {m["sha256"]: key for key, m in manifest.items() if key not in session_keys}
    for path, key, value in _walk(rec):
        where = ".".join(map(str, path + ((key,) if key is not None else ())))
        if key is not None:
            m = _H_KEY.match(str(key)) or _H_KEY_FLOOR.match(str(key))
            if (m and int(m.group(1)) > b) or key in POST_BREAK_OUTCOME_WORDS:
                out.append(f"{where}: D_b sonrası (h > b) sonuç anahtarı")
            if key in _POST_BREAK_DATE_KEYS and isinstance(value, str) and _iso_date(value) and value > db:
                out.append(f"{where}: {value!r} D_b'den sonra")
        if isinstance(value, str):
            for bm in _BULLETIN_NAME.finditer(value):
                if bm.group(2) > compact_b:
                    out.append(f"{where}: D_b sonrası bülten atfı")
                elif bm.group(2) not in session_days:
                    out.append(f"{where}: D_1..D_b seans günü dışı bülten atfı")
            if _SHA.match(value) and value in other_sha:
                day, kind = other_sha[value]
                out.append(f"{where}: {'D_b sonrası' if day > db else 'D_1..D_b dışı'} bültenin sha256'sı ({kind} {day})")
    for s in sessions:
        d = s.get("date")
        for kind in ("thb", "thm"):
            ref = s.get(kind) or {}
            pinned = manifest.get((d, kind))
            if pinned is None:
                out.append(f"streak.sessions h={s.get('h')} {kind}: MANIFEST'te {d} satırı yok")
            elif ref.get("sha256") != pinned["sha256"]:
                out.append(f"streak.sessions h={s.get('h')} {kind}: sha256 MANIFEST'teki pinli değerle aynı değil")
            if not isinstance(d, str) or not str(ref.get("file", "")).endswith(f"/{kind}{d.replace('-', '')}1.zip"):
                out.append(f"streak.sessions h={s.get('h')} {kind}.file o günün bülteni değil: {ref.get('file')!r}")
    return out


# ================================================================ Faz 6: H99 öncesi eski kohort (zaman-dışı; ZD)
# Şartname docs/specs_faz6/SPEC_OOT_PRE_H99_V0.md; proje sahibi kararları docs/specs_faz6/KARARLAR.md D1–D8 (çeliştiği yerde
# KARARLAR geçerli). Eşleme docs/faz6/OOT_TANIM_ESLEME.md; yorumlar docs/SPEC_DEVIATIONS.md bölüm I.
#
# - registry/oot/cohort_pre_h99.csv (§1, append-only): payda. `vault` ve `regime_tags` YALNIZ burada (tek kaynak; I2);
#   girdi dosyaları doğrulanmış halleriyle bayt-eşit alınır, bu iki alanı taşımaz.
# - registry/oot/{inputs,source_docs,candidate_features}/ (S1), records/ (S2), d1_rows/ ve post_d1/ (S3).
# - Kasa (D2): tohumlu, ilk işlem yılı içinde tabakalı %50; maruz kodlar çekilişten önce çıkarılıp açık kümeye yazılır.
# - Sınıf (OOT_BLIND / OOT_RETRO) burada ETİKETLENMEZ; scoring.class_oot git DAG'ı ve push kanıtlarından hesaplar.

OOT_DIR = REGISTRY_DIR / "oot"
COHORT_PATH = OOT_DIR / "cohort_pre_h99.csv"
OOT_INPUTS_DIR = OOT_DIR / "inputs"
OOT_SOURCE_DOCS_DIR = OOT_DIR / "source_docs"
OOT_CANDIDATE_DIR = OOT_DIR / "candidate_features"
OOT_RECORDS_DIR = OOT_DIR / "records"
OOT_D1_ROWS_DIR = OOT_DIR / "d1_rows"
OOT_POST_D1_DIR = OOT_DIR / "post_d1"
OOT_SCALE = "OOT_PRE_H99"
COHORT_START, COHORT_END = "2020-01-01", "2023-09-21"      # D1; H99'un ilk üyesi HATSN 2023-09-22 (§1)

COHORT_COLUMNS: tuple[str, ...] = ("ticker", "company", "first_trading_date", "listing_source_id", "listing_source_sha256",
                                   "sale_method", "market", "year", "status", "reason", "vault", "regime_tags", "added_at")
COHORT_MEMBER, COHORT_OUT_OF_SCOPE, COHORT_PENDING, COHORT_CANCELLED = "MEMBER", "OUT_OF_SCOPE", "PENDING", "CANCELLED"
COHORT_STATUSES = (COHORT_MEMBER, COHORT_OUT_OF_SCOPE, COHORT_PENDING, COHORT_CANCELLED)
SALE_ON_EXCHANGE, SALE_OFF_EXCHANGE = "ON_EXCHANGE", "OFF_EXCHANGE_BOOKBUILD"   # KAP BIST bildirimi "Halka Arz Yöntemi"
SALE_METHODS = (SALE_ON_EXCHANGE, SALE_OFF_EXCHANGE)
SALE_METHOD_NONE = "NONE"                                   # halka arzsız kotasyon (yalnız OUT_OF_SCOPE)
MARKETS = ("YILDIZ", "ANA", "ALT", "GIP")

VAULT_OPEN, VAULT_SEALED = "OPEN", "SEALED"
VAULT_EXPOSED_ARCHIVE, VAULT_EXPOSED_CODEX = "EXPOSED_ARCHIVE", "EXPOSED_CODEX"
VAULT_VALUES = (VAULT_OPEN, VAULT_SEALED, VAULT_EXPOSED_ARCHIVE, VAULT_EXPOSED_CODEX)        # KARARLAR D2 (I3)
OPEN_SET = frozenset({VAULT_OPEN, VAULT_EXPOSED_ARCHIVE, VAULT_EXPOSED_CODEX})             # açık küme (kasa dışı)
# D2: kasaya giremeyenler (çekilişten önce çıkarılır, açık kümede kalır). EXPOSED_ARCHIVE: arşivde D_2…D_10'unu içeren ham
# bülten fiziksel olarak var (D_10 ≥ 2023-09-22; şartname §7, §11-5). EXPOSED_CODEX: Codex günlüğünde listeleme sonrası bir KAP
# başlığı görüldü (değer yok).
EXPOSED_TICKERS: dict[str, str] = {"TARKM": VAULT_EXPOSED_ARCHIVE, "GIPTA": VAULT_EXPOSED_ARCHIVE,
                                   "ADGYO": VAULT_EXPOSED_ARCHIVE, "REEDR": VAULT_EXPOSED_ARCHIVE,
                                   "PNLSN": VAULT_EXPOSED_CODEX}
EXPOSURE_CLASS = {VAULT_EXPOSED_ARCHIVE: "ARCHIVE_PRESENT_NOT_READ", VAULT_EXPOSED_CODEX: "CODEX_POST_LISTING_HEADLINE_SEEN"}
# D8-1: 28 üyenin listeleme sonrası SPK bülteni kurumsal işlem satırı görüldü (fiyat/getiri değil); kasaya girebilirler. Ticker
# listesi (verified EXPOSURE.md §3) bu görevde OKUNMADI; yalnız sayı. Üye başına etiket S6'da makineyle okunur (I14).
SPK_CORPORATE_ACTION_ROW_SEEN = "SPK_CORPORATE_ACTION_ROW_SEEN"
N_SPK_CORPORATE_ACTION_ROW_SEEN = 28
VAULT_SEED = 20260924
EXPOSED_ARCHIVE_FIRST_BULLETIN = "2023-09-22"               # arşivdeki (H99) ilk bülten günü

_TICKER = re.compile(r"^[A-Z0-9]{2,6}$")


def read_cohort(path: Path = COHORT_PATH) -> tuple[list[str], list[dict[str, str]]]:
    with Path(path).open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def active_cohort(rows: Sequence[Mapping[str, str]]) -> dict[str, dict[str, str]]:
    """Ticker -> etkin satır (CANCELLED ile düşülmemiş son satır). Sıra dosya sırasıdır (append-only)."""
    out: dict[str, dict[str, str]] = {}
    for r in rows:
        if r["status"] == COHORT_CANCELLED:
            out.pop(r["ticker"], None)
        else:
            out[r["ticker"]] = dict(r)
    return out


def cohort_members(rows: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    """Etkin MEMBER satırları (first_trading_date, ticker) sırasıyla."""
    return sorted((r for r in active_cohort(rows).values() if r["status"] == COHORT_MEMBER),
                  key=lambda r: (r["first_trading_date"], r["ticker"]))


def validate_cohort(header: Sequence[str], rows: Sequence[Mapping[str, str]]) -> list[str]:
    """§1 payda dosyası (boş liste = geçerli): sütunlar, durumlar, alan biçimleri, kasa değer kümesi (D2), maruz kodların açık
    kümede olması, `regime_tags` sözdizimi, kohort penceresi; CANCELLED kuralı (§1: hata bulunursa iptal satırı düşülür, eski
    satır kalır): iptal satırı aynı ticker'ın etkin bir satırını düşer ve neden taşır; etkin satır ticker başına en çok bir."""
    problems: list[str] = []
    if tuple(header) != COHORT_COLUMNS:
        return [f"sütunlar {tuple(header)} != {COHORT_COLUMNS}"]
    active: set[str] = set()
    for i, r in enumerate(rows, start=2):
        where = f"satır {i} ({r.get('ticker')})"
        status, t = r["status"], r["ticker"]
        if status not in COHORT_STATUSES:
            problems.append(f"{where}: status {status!r}")
            continue
        if not _TICKER.match(t or ""):
            problems.append(f"{where}: ticker biçimi")
        if not _iso_datetime_with_offset(r["added_at"]):
            problems.append(f"{where}: added_at {r['added_at']!r}")
        if status == COHORT_CANCELLED:
            if t not in active:
                problems.append(f"{where}: CANCELLED satırı etkin bir satırı düşmüyor")
            if not r["reason"].strip():
                problems.append(f"{where}: CANCELLED satırında neden yok")
            active.discard(t)
            continue
        if t in active:
            problems.append(f"{where}: aynı ticker için ikinci etkin satır (önce CANCELLED gerekir)")
        active.add(t)
        if not _SOURCE_ID.match(r["listing_source_id"]) or not _SHA.match(r["listing_source_sha256"]):
            problems.append(f"{where}: listing_source_id/sha256 biçimi")
        if not _iso_date(r["first_trading_date"]) or r["year"] != r["first_trading_date"][:4]:
            problems.append(f"{where}: first_trading_date/year {r['first_trading_date']!r}/{r['year']!r}")
        if not r["company"].strip():
            problems.append(f"{where}: company boş")
        if status == COHORT_OUT_OF_SCOPE:
            if not r["reason"].strip():
                problems.append(f"{where}: OUT_OF_SCOPE nedeni boş")
            if r["vault"] or r["regime_tags"]:
                problems.append(f"{where}: OUT_OF_SCOPE satırında vault/regime_tags dolu")
            continue
        if not COHORT_START <= r["first_trading_date"] <= COHORT_END:
            problems.append(f"{where}: first_trading_date kohort penceresi {COHORT_START}…{COHORT_END} dışında")
        if r["sale_method"] not in SALE_METHODS or r["market"] not in MARKETS:
            problems.append(f"{where}: sale_method/market {r['sale_method']!r}/{r['market']!r}")
        if status == COHORT_PENDING:
            if not r["reason"].strip():
                problems.append(f"{where}: PENDING nedeni boş")
            continue
        if r["reason"]:
            problems.append(f"{where}: MEMBER satırında reason dolu")
        if r["vault"] not in VAULT_VALUES:
            problems.append(f"{where}: vault {r['vault']!r} (değer kümesi {VAULT_VALUES})")
        exposed = EXPOSED_TICKERS.get(t)
        if (exposed or r["vault"] in (VAULT_EXPOSED_ARCHIVE, VAULT_EXPOSED_CODEX)) and r["vault"] != exposed:
            problems.append(f"{where}: maruz kod kümesi (D2) ile vault uyuşmuyor ({r['vault']!r} != {exposed!r})")
        try:
            tags = parse_regime_tags(r["regime_tags"])
        except RegistryError as exc:
            problems.append(f"{where}: regime_tags {exc}")
            continue
        if tags.get("MARKET") != r["market"] or bool(tags.get("SALE_ON_EXCHANGE")) != (r["sale_method"] == SALE_ON_EXCHANGE):
            problems.append(f"{where}: regime_tags MARKET/SALE_ON_EXCHANGE satırla tutarsız")
        if exposed and not tags.get(exposed):
            problems.append(f"{where}: regime_tags {exposed} taşımıyor")
    return problems


def cohort_bytes(rows: Sequence[Mapping[str, str]], header: bool = True) -> bytes:
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=COHORT_COLUMNS, lineterminator="\n")
    if header:
        w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in COHORT_COLUMNS})
    return buf.getvalue().encode("utf-8")


def append_cohort(new_rows: Sequence[Mapping[str, str]], path: Path = COHORT_PATH) -> None:
    """Append-only: var olan baytlar değişmez; birleşik dosya doğrulayıcıdan geçmezse hiçbir şey yazılmaz."""
    path = Path(path)
    header, rows = (list(COHORT_COLUMNS), []) if not path.exists() else read_cohort(path)
    problems = validate_cohort(header, rows + [dict(r) for r in new_rows])
    if problems:
        raise RegistryError("; ".join(problems))
    payload = cohort_bytes(new_rows, header=not path.exists())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as fh:
        fh.write(payload)


def cohort_append_only_problems(old: bytes, new: bytes) -> list[str]:
    """Bir sürümden sonrakine yalnız satır eklenebilir (eski baytlar yeni dosyanın öneki)."""
    return [] if new.startswith(old) else ["cohort dosyası append-only değil: eski baytlar yeni dosyanın öneki değil"]


# ---------------------------------------------------------------- kasa çekilişi (KARARLAR D2; şartname §9 K2)

def draw_vault(members: Sequence[Mapping[str, str]], *, seed: int = VAULT_SEED,
               exposed: Mapping[str, str] = EXPOSED_TICKERS) -> dict[str, str]:
    """ticker -> vault. Algoritma (sonuç görülmeden; deterministik):
      1. MEMBER satırları (first_trading_date, ticker) ile sıralanır; maruz kodlar (D2) çıkarılıp kendi değerleriyle yazılır;
      2. kalanlar ilk işlem yılı tabakalarına ayrılır (tabaka içi sıra 1'deki sıra);
      3. tek bir `numpy.random.Generator(PCG64(seed))`, yıllar artan sırayla: tabakada n aday varsa
         `rng.choice(n, size=n // 2, replace=False)` indeksleri SEALED, kalanlar OPEN (I4: tek sayıda aşağı yuvarlama).
    numpy yalnız burada yüklenir (registry stdlib kalır)."""
    import numpy as np

    rng = np.random.Generator(np.random.PCG64(seed))
    out: dict[str, str] = {}
    strata: dict[str, list[str]] = {}
    for r in sorted(members, key=lambda r: (r["first_trading_date"], r["ticker"])):
        if r["ticker"] in exposed:
            out[r["ticker"]] = exposed[r["ticker"]]
        else:
            strata.setdefault(r["first_trading_date"][:4], []).append(r["ticker"])
    for year in sorted(strata):
        tickers = strata[year]
        sealed = {int(i) for i in rng.choice(len(tickers), size=len(tickers) // 2, replace=False)}
        for i, t in enumerate(tickers):
            out[t] = VAULT_SEALED if i in sealed else VAULT_OPEN
    return out


def vault_counts(rows: Sequence[Mapping[str, str]]) -> dict[str, dict[str, int]]:
    """Yıl × kasa değeri sayıları (kod adı olmadan; rapor ve test)."""
    out: dict[str, dict[str, int]] = {}
    for r in cohort_members(rows):
        out.setdefault(r["year"], {v: 0 for v in VAULT_VALUES})[r["vault"]] += 1
    return out


def is_open(vault: str) -> bool:
    """Açık küme = OPEN ∪ EXPOSED_* (kasa dışı)."""
    return vault in OPEN_SET


# ---------------------------------------------------------------- rejim etiketleri (şartname §7; yalnız kural tarihleri, arz
# belgeleri ve arz fiyatından; sonuç verisi okunmaz)

# Fiyat adımı tablosu (paylar). T2015: 30/11/2015 BISTECH geçişi (Dış Duyuru 2015/88) → 05/11/2023; PPP Rev. 39 karşılaştırma
# cetveli "ESKİ METİN" s.320 (kurallar_arastirma.md §3; 2019-12-31 THM `FIYAT ADIMI` alanıyla aynı, FEASIBILITY §3).
# T2023: 06/11/2023'ten itibaren (Duyuru 2023/19412) = donmuş tavan yolu JSON'larındaki tablo (`predict_path.TICK_TABLE`).
TICK_TABLE_T2015: tuple[tuple[Optional[str], str], ...] = (("20", "0.01"), ("50", "0.02"), ("100", "0.05"), (None, "0.10"))
TICK_T2023_START = "2023-11-06"
# Günlük fiyat marjı: 13/03/2020'den itibaren Yıldız ve Ana %10 (Duyuru 2020/20, "ikinci duyuruya kadar"; PPP Rev. 54 hâlâ
# listeliyor); 04/11/2019–12/03/2020 Yıldız %20, Ana G1 %20, Ana G2 %15 (Duyuru 2019/65; kurallar_arastirma.md §1).
MARGIN_CHANGE = "2020-03-13"
MARGIN_PATH = "0.10"                                        # tavan yolu JSON'unun sabiti (`predict_path.MARGIN`)
# Açığa satış yasakları (kurallar_arastirma.md §10): 02/03/2020'den itibaren tüm paylarda (SPK 28/02/2020 kararı, 02/03/2020
# duyurusu; BIST-30 için 01/07/2020'de kalktı, BIST-30 DIŞI paylar için kaldırılma tarihi BULUNAMADI) ve 06/02/2023'ten
# itibaren (SPK-B 2023/6-7, karar 6/155; yeni arzlar BIST-50 dışı → pencere boyunca sürüyor).
SHORT_SELL_BANS: tuple[tuple[str, Optional[str], str], ...] = (
    ("2020-03-02", None, "SHORT_SELL_BAN_2020_END_NOT_FOUND"),   # bitişi bulunamadı (I9)
    ("2023-02-06", None, "SHORT_SELL_BAN"),
)
# Tahsis ve satış yöntemi rejimi (kurallar_arastirma.md §6–7): 11/11/2021 Kurul Kararı 59/1669 (SPK-B 2021/57; PD ≤ 100 mn TL
# → borsada satış zorunlu); 30/03/2023 i-SPK.128.21 (SPK-B 2023/21; PD ≤ 750 mn → borsada satış, bireysele eşit dağıtım).
# Başvuru günü: talep toplama başlangıcı (satış anı; I8).
ALLOC_REGIMES: tuple[tuple[str, str], ...] = (("2021-11-11", "THRESH100_20211111"), ("2023-03-30", "EQUAL_DIST_20230330"))
ALLOC_BEFORE = "PRE_20211111"
REGIME_FLAGS = frozenset({"SALE_ON_EXCHANGE", "PRICE_RANGE_BOOKBUILD", "TICK_TABLE_MISMATCH", "MARGIN_NOT_10PCT",
                          "SHORT_SELL_BAN", "SHORT_SELL_BAN_2020_END_NOT_FOUND", VAULT_EXPOSED_ARCHIVE, VAULT_EXPOSED_CODEX})
REGIME_VALUES: dict[str, tuple[str, ...]] = {
    "TICK_TABLE_EPOCH": ("T2015", "T2023"),
    "MARGIN_RULE": ("PRE_20200313", "POST_20200313"),
    "ALLOC_REGIME": (ALLOC_BEFORE,) + tuple(v for _, v in ALLOC_REGIMES),
    "MARKET": MARKETS,
}
# §7 R3 ve MARGIN satırı: rejim yüzünden o arzda uygulanamaz (NOT_APPLICABLE_REGIME) sayılan modeller (I6, I7). Faz 7'nin kural
# satırı `ceiling_hazard_v1_pooled@INF` de şartnamenin "`@INF` kuralları"dır (SPEC_OOT_PRE_H99_V0 §7 MARGIN_RULE lafzı; SPEC_DEVIATIONS
# L); v1 adayları ve (C) modelleri hazard / V1.5 ailesi gibi uygulanabilir (tavan etiketi THM'den; (C) tavan hedefi değil).
PATH_MODELS = ("ceiling_path_v0", "pb_ceiling_path_v0")
MARGIN_MODELS = ("base_always_ceiling", "ceiling_hazard_v0@INF", "pb_ceiling_v0@INF", "ceiling_path_v0@INF",
                 "ceiling_path_v0", "pb_ceiling_path_v0", "ceiling_hazard_v1_pooled@INF")
NA_TICK_TABLE_MISMATCH = "TICK_TABLE_MISMATCH"
NA_MARGIN_NOT_10PCT = "MARGIN_NOT_10PCT"


def _tick_of(x: Any, table: Sequence[tuple[Optional[str], str]]) -> Any:
    from decimal import Decimal

    for lim, s in table:
        if lim is None or x < Decimal(lim):
            return Decimal(s)
    raise AssertionError("tablo sonu")  # pragma: no cover


def limit_path_with(price: Any, table: Sequence[tuple[Optional[str], str]], *, margin: str = MARGIN_PATH,
                    days: int = 10) -> tuple[Any, tuple[Any, ...]]:
    """(snap(P), C_1..C_days) verilen fiyat adımı tablosuyla (`predict_path.limit_path` tanımı aynen, tablo parametre):
    b_1 = P kendi seviyesinin adımına HALF_UP; C_k = floor(C_{k−1}·(1 + marj) / adım) · adım (adım yuvarlanan değerin
    seviyesinden). Kesin Decimal (Inexact tuzağı açık). JSON tablosuyla `predict_path.limit_path`'e eşitliği testlidir."""
    from decimal import (ROUND_FLOOR, ROUND_HALF_EVEN, ROUND_HALF_UP, Context, Decimal, DivisionByZero, Inexact,
                         InvalidOperation, Overflow, localcontext)

    ctx = Context(prec=60, rounding=ROUND_HALF_EVEN, traps=[InvalidOperation, DivisionByZero, Overflow, Inexact])
    with localcontext(ctx):
        p, m = Decimal(str(price)), Decimal(margin)
        s = _tick_of(p, table)
        b = (p / s).to_integral_value(rounding=ROUND_HALF_UP) * s
        snapped, C = b, []
        for _ in range(days):
            y = b * (1 + m)
            st = _tick_of(y, table)
            b = (y / st).to_integral_value(rounding=ROUND_FLOOR) * st
            C.append(b)
    return snapped, tuple(C)


def tick_table_epoch(d1: str) -> str:
    return "T2023" if d1 >= TICK_T2023_START else "T2015"


def tick_table_mismatch(price: Any, epoch: str) -> bool:
    """§7 R3: C_1..C_10 (ve D1 baz fiyatı) dönemin tablosuyla ve donmuş JSON tablosuyla ayrı hesaplanır; farklıysa True."""
    from .predict_path import TICK_TABLE

    table = TICK_TABLE_T2015 if epoch == "T2015" else TICK_TABLE
    return limit_path_with(price, table) != limit_path_with(price, TICK_TABLE)


def calendar_window(first_trading_date: str, sessions: Sequence[str], n: int = 10) -> tuple[str, ...]:
    """Takvimden D_1…D_n penceresi (resmi seanslar, first_trading_date dahil). Sonuç verisi değil: payın işlem görüp
    görmediğine bakılmaz (gerçekleşen D_h S5'te THB'den)."""
    out = tuple(s for s in sessions if s >= first_trading_date)[:n]
    if len(out) < n:
        raise RegistryError(f"takvim {first_trading_date}'ten sonra {n} seans içermiyor")
    return out


def _single_price(value: Any) -> Optional[str]:
    from .features import PBRefusal, parse_pb_decimal

    try:
        return str(parse_pb_decimal(value, "ipo_price_try"))
    except PBRefusal:
        return None


def price_is_range(value: Any) -> bool:
    """`ipo_price_try` fiyat aralığı mı (SPEC_PB_V0 §5 reddiyle aynı ayrıştırıcı: `features.parse_pb_decimal`)."""
    from .features import PB_PRICE_RANGE, PBRefusal, parse_pb_decimal

    try:
        parse_pb_decimal(value, "ipo_price_try")
    except PBRefusal as exc:
        return exc.code == PB_PRICE_RANGE
    return False


def compute_regime_tags(*, first_trading_date: str, market: str, sale_method: str, ipo_price_tl: Any, ipo_price_try: Any,
                        bookbuilding_start: str, sessions: Sequence[str], vault: str) -> dict[str, Any]:
    """Şartname §7 tablosu (sonuçsuz). Dönen: bayrak -> True, anahtar -> değer. Tanımlar:
      SALE_ON_EXCHANGE        KAP BIST bildirimi "Halka Arz Yöntemi" = Borsada
      PRICE_RANGE_BOOKBUILD   SPK A.1 satış fiyatı aralık (`ipo_price_try`)
      TICK_TABLE_EPOCH        D_1'de (= first_trading_date) geçerli tablo; TICK_TABLE_MISMATCH: arz fiyatlarından (ipo_price_tl
                              ve tek değerliyse ipo_price_try) biri için C_1..C_10 dönem ve JSON tablosuyla farklı
      MARGIN_RULE             D_1 < 2020-03-13 ise PRE; MARGIN_NOT_10PCT: PRE ve Yıldız/Ana (marj %15–%20)
      SHORT_SELL_BAN(_2020_END_NOT_FOUND)  takvim D_1…D_10 penceresi bir yasak dönemiyle kesişiyor
      ALLOC_REGIME            talep toplama başlangıcında geçerli rejim
      MARKET                  işlem göreceği pazar; EXPOSED_*: kasa değeri maruzsa."""
    if market not in MARKETS or sale_method not in SALE_METHODS:
        raise RegistryError(f"market/sale_method {market!r}/{sale_method!r}")
    tags: dict[str, Any] = {"MARKET": market}
    if sale_method == SALE_ON_EXCHANGE:
        tags["SALE_ON_EXCHANGE"] = True
    if price_is_range(ipo_price_try):
        tags["PRICE_RANGE_BOOKBUILD"] = True
    epoch = tick_table_epoch(first_trading_date)
    tags["TICK_TABLE_EPOCH"] = epoch
    prices = [ipo_price_tl] + ([p] if (p := _single_price(ipo_price_try)) is not None else [])
    if any(tick_table_mismatch(p, epoch) for p in prices if p not in (None, "")):
        tags["TICK_TABLE_MISMATCH"] = True
    pre = first_trading_date < MARGIN_CHANGE
    tags["MARGIN_RULE"] = "PRE_20200313" if pre else "POST_20200313"
    if pre and market in ("YILDIZ", "ANA"):
        tags["MARGIN_NOT_10PCT"] = True
    window = calendar_window(first_trading_date, sessions)
    for start, end, name in SHORT_SELL_BANS:
        if window[-1] >= start and (end is None or window[0] <= end):
            tags[name] = True
    tags["ALLOC_REGIME"] = ALLOC_BEFORE
    for start, name in ALLOC_REGIMES:
        if bookbuilding_start >= start:
            tags["ALLOC_REGIME"] = name
    if vault in (VAULT_EXPOSED_ARCHIVE, VAULT_EXPOSED_CODEX):
        tags[vault] = True
    return tags


def format_regime_tags(tags: Mapping[str, Any]) -> str:
    parts = [k if v is True else f"{k}={v}" for k, v in tags.items()]
    return "|".join(sorted(parts))


def parse_regime_tags(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for part in (text.split("|") if text else []):
        key, sep, value = part.partition("=")
        if sep:
            if key not in REGIME_VALUES or value not in REGIME_VALUES[key]:
                raise RegistryError(f"bilinmeyen etiket değeri {part!r}")
            out[key] = value
        elif key in REGIME_FLAGS:
            out[key] = True
        else:
            raise RegistryError(f"bilinmeyen etiket {part!r}")
    missing = [k for k in REGIME_VALUES if k not in out]
    if missing:
        raise RegistryError(f"zorunlu etiketler yok: {missing}")
    if format_regime_tags(out) != text:
        raise RegistryError("etiketler kanonik sırada değil")
    return out


def regime_not_applicable(tags: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    """model_id -> {code, reason}: rejim yüzünden o arzda uygulanamaz (§7). Kayıtta NOT_APPLICABLE_REGIME hücresi olur."""
    out: dict[str, dict[str, str]] = {}
    if tags.get("MARGIN_NOT_10PCT"):
        for m in MARGIN_MODELS:
            out[m] = {"code": NA_MARGIN_NOT_10PCT, "reason": "D_1'de günlük fiyat marjı %10 değil (§7 MARGIN_RULE, "
                      f"{tags.get('MARGIN_RULE')}); kural/limit yolu 0.10 marjını varsayar"}
    if tags.get("TICK_TABLE_MISMATCH"):
        for m in PATH_MODELS:
            out.setdefault(m, {"code": NA_TICK_TABLE_MISMATCH, "reason": "C_1..C_10 dönemin fiyat adımı tablosuyla ve JSON "
                               f"tablosuyla farklı (§7 R3, {tags.get('TICK_TABLE_EPOCH')})"})
    return out


# ---------------------------------------------------------------- G1: registry/oot/ sonuç alanı taşımaz

OOT_OUTCOME_KEYS = frozenset({
    "close", "official_close", "kapanis", "kapanis_fiyati", "closing_price", "upper_limit", "ust_limit", "realized",
    "realized_return", "target_return", "above_ipo_flag", "ceiling_streak_L", "outcome",
    *(f"R_D{h}" for h in range(1, 11)), *(f"Y_D{h}" for h in range(1, 11)), *(f"ceiling_close_D{k}" for k in range(1, 11)),
    "R_h", "Y_h", "ceiling_close", "close_raw", "upper_limit_raw"})


def json_keys(obj: Any) -> Iterable[str]:
    for _, k, _v in _walk(obj):
        if k is not None:
            yield str(k)


def oot_outcome_key_problems(root: Path = ROOT) -> list[str]:
    """G1 (şartname §2 S1): registry/oot/ altında (d1_rows ve post_d1 hariç: yalnız D_1, `oot_d1_problems`) hiçbir JSON
    anahtarı ya da CSV başlığı sonuç alanı adı değildir."""
    out: list[str] = []
    base = Path(root) / "registry" / "oot"
    for p in sorted(base.rglob("*")) if base.exists() else []:
        rel = p.relative_to(root).as_posix()
        if rel.startswith(("registry/oot/d1_rows/", "registry/oot/post_d1/")) or not p.is_file():
            continue
        if p.suffix == ".json":
            bad = set(json_keys(json.loads(p.read_text(encoding="utf-8")))) & OOT_OUTCOME_KEYS
        elif p.suffix == ".csv":
            with p.open(encoding="utf-8-sig", newline="") as fh:
                bad = set(csv.DictReader(fh).fieldnames or []) & OOT_OUTCOME_KEYS
        else:
            continue
        if bad:
            out.append(f"{rel}: sonuç alanı {sorted(bad)}")
    return out


# ---------------------------------------------------------------- kohort satırları (S1; docs/specs_faz6/ekler/evren_listesi.csv)

UNIVERSE_PATH = ROOT / "docs" / "specs_faz6" / "ekler" / "evren_listesi.csv"


def build_cohort_rows(universe: Sequence[Mapping[str, str]], inputs_dir: Path, sessions: Sequence[str], added_at: str,
                      *, seed: int = VAULT_SEED) -> list[dict[str, str]]:
    """Evren listesi (§1 üyelik kararı, S0 eki) + girdi belgeleri (arz fiyatı, SPK fiyatı, talep toplama başlangıcı) + takvim
    -> cohort_pre_h99.csv satırları, evren listesinin sırasıyla. `vault` `draw_vault`'tan, `regime_tags`
    `compute_regime_tags`'ten; ikisi de sonuç verisi okumaz."""
    rows: list[dict[str, str]] = []
    for u in universe:
        rows.append({"ticker": u["ticker"], "company": u["company"], "first_trading_date": u["first_trading_date"],
                     "listing_source_id": f"KAP_{u['kap_notice_id']}", "listing_source_sha256": u["kap_pdf_sha256"],
                     "sale_method": u["sale_method_kap"], "market": u["market"], "year": u["year"], "status": u["status"],
                     "reason": u["reason"], "vault": "", "regime_tags": "", "added_at": added_at})
    members = [r for r in rows if r["status"] == COHORT_MEMBER]
    vault = draw_vault(members, seed=seed)
    for r in members:
        doc = load_inputs(Path(inputs_dir) / f"{r['ticker']}.json")[0]
        f = doc["fields"]
        if f["first_trading_date"]["value"] != r["first_trading_date"]:
            raise RegistryError(f"{r['ticker']}: girdi belgesinin first_trading_date'i evren listesiyle aynı değil")
        r["vault"] = vault[r["ticker"]]
        r["regime_tags"] = format_regime_tags(compute_regime_tags(
            first_trading_date=r["first_trading_date"], market=r["market"], sale_method=r["sale_method"],
            ipo_price_tl=f["ipo_price_tl"]["value"], ipo_price_try=f["ipo_price_try"]["value"],
            bookbuilding_start=f["bookbuilding_start"]["value"], sessions=sessions, vault=r["vault"]))
    return rows

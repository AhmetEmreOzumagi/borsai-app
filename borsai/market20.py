"""f6_market20: 20 seanslık XU100 getirisi (SPEC_MARKET20_V0 §2-§4). Yalnız stdlib.

    sessions = takvimde resmi seans sayılan günler (artan)
    i  = bisect_left(sessions, ref_date) − 1        # ref_date'ten KESİN önceki son seans
    S0 = sessions[i];  S20 = sessions[i − 20]       # 21 kapanış, 20 aralık
    f6 = XU100[S0] / XU100[S20] − 1                 # Decimal, 60 hane, ROUND_HALF_EVEN

`ref_date`: backtest'te ve nihai fit'te T (first_trading_date); canlıda tahmin
tarihi (Europe/Istanbul). XU100 bir sonuç değil, tahmin anındaki girdidir; f6
asla impute edilmez. Geçerlilik kurallarından biri tutmazsa sonuç RET'tir
(`Market20Result.refusal`, SPEC_MARKET20_V0 §3):

  1 CALENDAR_NOT_COVERING  takvim ref_date − 1 gününü içermiyor (takvim sonu hatası
                           düzeltmesi: legacy 2026-09-30 için sessizce S0 = 2026-08-19 veriyordu)
  2 INSUFFICIENT_HISTORY   i < 20
  3 XU100_CLOSE_MISSING    penceredeki 21 seansın herhangi birinde kapanış yok
  4 STALE_S0               ref_date − S0 > 12 takvim günü
  5 PREDICTION_TOO_EARLY   canlıda T − tahmin tarihi > 12 takvim günü
  6 XU100_INTEGRITY        indexName ≠ XU100, aynı tarihte çelişen değer ya da değer ≤ 0
  7 as_of                  hisTs < ref_date olmayan kayıt hiç okunmaz

Rol ayrımı: f6'yı bu modül üretir ve dondurma girdisine yazar; uygulama yalnız
hazır f6 ile `borsai.predict_market20.predict` çağırır (stdlib predict takvim ya
da JSON okumaz). Tanım SPEC_MARKET20_V0 §10'da `borsai/features.py: market20`
olarak geçer; buraya konma nedeni docs/SPEC_DEVIATIONS.md'dedir.
"""
from __future__ import annotations

import bisect
import csv
import json
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from pathlib import Path
from typing import Any, Optional, Sequence

from .provenance import ROOT, sha256_file

RAW_DIR = ROOT / "data" / "raw"
CALENDAR_B_PATH = RAW_DIR / "v2_market20_official_pay_calendar_evidence_r4.csv"
CALENDAR_B_SHA256 = "49b58029715881a7f1a304afb7e41fcff3d5c1c7a8896de3ed9bb555fb02d159"
CALENDAR_A_PATH = RAW_DIR / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_pay_session_calendar.csv"
CALENDAR_A_SHA256 = "15d4d975db53a42006c1e57bab7b5f11eab52f281069cc90f0c38361770bf9cb"
XU100_PATH = RAW_DIR / "official_bist_xu100_graphic_pinned_through_20260819.json"
XU100_SHA256 = "34859d7eefdb552a31f6476e2230a07a825ada3ee769a2a7646f12399c303fdf"
# Faz 2A (SPEC_MARKET20_V0 §4): 2026-08-19 sonrası. Eski dosyalar kalır; canlı f6 en yeni pinli dosyayı okur.
# Takvim uzatması Takvim B şemasıyla, BIST 2026 tatil tablosundan (docs/PROVENANCE.md §7).
CALENDAR_B_EXT_PATH = RAW_DIR / "pay_calendar_b_extension_20260820_20261231.csv"
CALENDAR_B_EXT_SHA256 = "273ca0e7f815c7bb1a0ce562ba7060d2dc806603f2112cdde460195cbebc6432"
XU100_PINNED: tuple[tuple[Path, str], ...] = (
    (XU100_PATH, XU100_SHA256),
    (RAW_DIR / "xu100" / "xu100_graphic_20260922.json", "04637c911f912e007522790520191ae99ad5cf47f8d38a4360698ea3038397fe"),
)

# ---- Takvim C (Faz 6, eski kohort; SPEC_OOT_PRE_H99_V0 §4, §10; docs/faz6/OOT_TANIM_ESLEME.md "Takvim C")
# 2020-01-01…2023-09-21, Takvim B uzatmasıyla aynı sütunlar. Kaynak: BIST Pay Piyasası yıllık tatil tabloları (URL ve sha256
# docs/specs_faz6/ekler/takvim_2020_2023.md ile aynı; PDF'ler repoda değil, bu görevde indirilmedi: sha'sı bu değerlerle
# eşleşen yerel kopyalardan elle döküldü). Tam kapanış = tabloda "seans yapılmayacaktır" yazan her gün (hafta sonu dahil);
# yarım gün = "yarım gün seans yapılacaktır". Tabloda olmayan hafta içi kapanışlar yalnız XU100_GAP_CLOSURES'ta (aşağı).
CALENDAR_C_PATH = RAW_DIR / "pay_calendar_c_20200101_20230921.csv"
CALENDAR_C_SHA256 = "6dfd6134584a1a14211c3a56b5b274fef321f666bf870ce99605a97bee16fe4e"
CALENDAR_C_FIRST, CALENDAR_C_LAST = "2020-01-01", "2023-09-21"
CALENDAR_COLUMNS = ("calendar_date", "weekday_name", "is_weekend", "full_closure", "half_day", "counts_as_official_session",
                    "source_year", "source_pdf", "source_pdf_sha256", "source_locator", "verification_status")
HOLIDAY_TABLES_2020_2023: dict[int, dict[str, Any]] = {
    2020: {"url": "https://www.borsaistanbul.com/files/pay-piyasasi-2020-yili-tatil-tablosu.pdf",
           "sha256": "a71e242bd8412d743801072f4acfab1f83a2288d826eb0d7c2057d1d17f2fb3b",
           "full": ("2020-01-01", "2020-04-23", "2020-05-01", "2020-05-19", "2020-05-23", "2020-05-24", "2020-05-25",
                    "2020-05-26", "2020-07-15", "2020-07-31", "2020-08-01", "2020-08-02", "2020-08-03", "2020-08-30",
                    "2020-10-29"),
           "half": ("2020-07-30", "2020-10-28")},
    2021: {"url": "https://borsaistanbul.com/files/PayPiyasasi2021YiliTatilTablosu.pdf",
           "sha256": "9a2b21f0655c532b772274e3126d0b18c4cd71cccc39b3497290323d36de56ba",
           "full": ("2021-01-01", "2021-04-23", "2021-05-01", "2021-05-13", "2021-05-14", "2021-05-15", "2021-05-19",
                    "2021-07-15", "2021-07-20", "2021-07-21", "2021-07-22", "2021-07-23", "2021-08-30", "2021-10-29"),
           "half": ("2021-05-12", "2021-07-19", "2021-10-28")},
    2022: {"url": "https://www.borsaistanbul.com/files/pay-piyasasi-2022-yili-tatil-tablosu.pdf",
           "sha256": "fe1e6fe64473adf2aab281c07e069129e8c1f330440eced31a597d627db8086a",
           "full": ("2022-01-01", "2022-04-23", "2022-05-01", "2022-05-02", "2022-05-03", "2022-05-04", "2022-05-19",
                    "2022-07-11", "2022-07-12", "2022-07-15", "2022-08-30"),
           "half": ("2022-07-08", "2022-10-28")},
    2023: {"url": "https://www.borsaistanbul.com/files/pay-piyasasi-2023-yili-tatil-tablosu.pdf",
           "sha256": "696bc0f5668f7108a999f097ef5468b3d009842b72d96e4b7cf7b8aa06cf9df8",
           "full": ("2023-01-01", "2023-04-21", "2023-04-22", "2023-04-23", "2023-05-01", "2023-05-19", "2023-06-28",
                    "2023-06-29", "2023-06-30", "2023-07-01", "2023-07-15", "2023-08-30", "2023-10-28", "2023-10-29"),
           "half": ("2023-04-20", "2023-06-27")},
}
# Tatil tablosunda olmayan, pinli XU100 serisinde kapanışı olmayan hafta içi günler: 2023-02-09…14 Şubat 2023 depremi kapanışı
# (BIST kapatma duyurusu bulunamadı: docs/specs_faz6/ekler/kurallar_arastirma.md §13; SPEC_MARKET20_V0 §1 "5 günün 4'ü") ve
# 2023-04-24 (tatil tablosunda yok; ekler/takvim_2020_2023.md "elle doğrulanacak"). Kanıt yalnız XU100 boşluğu; S5'te bülten
# indirmeden önce THB HEAD probuyla denetlenir (`outcomes_oot.check_xu100_gap_closures`: yayımlanmışsa DUR).
XU100_GAP_CLOSURES: tuple[str, ...] = ("2023-02-09", "2023-02-10", "2023-02-13", "2023-02-14", "2023-04-24")
C_LOCATOR_FULL = "OFFICIAL_FULL_CLOSURES_LITERAL_TRANSCRIPTION"
C_LOCATOR_HALF = "OFFICIAL_HALF_DAYS_LITERAL_TRANSCRIPTION"
C_LOCATOR_OPEN = "NOT_LISTED_IN_OFFICIAL_FULL_CLOSURES_OR_OFFICIAL_HALF_DAYS"
C_LOCATOR_WEEKEND = "CALENDAR_ARITHMETIC_WEEKEND_NOT_A_HOLIDAY_TABLE_ENTRY"
C_LOCATOR_XU100_GAP = "NOT_LISTED_IN_HOLIDAY_TABLE_NO_XU100_CLOSE_UNANNOUNCED_CLOSURE"
C_STATUS = "FAZ6_TRANSCRIBED_SESSION_SET_EQUALS_XU100_DATES_20200101_20230921"
C_STATUS_XU100_GAP = "FAZ6_XU100_GAP_ONLY_THB_HEAD_PROBE_PENDING_S5"
WEEKDAY_NAMES = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")

WINDOW_SESSIONS = 20
MAX_STALE_DAYS = 12
MAX_LEAD_DAYS = 12
MARKET20_CONTEXT = Context(prec=60, rounding=ROUND_HALF_EVEN)
INDEX_NAME = "XU100"

CALENDAR_NOT_COVERING = "CALENDAR_NOT_COVERING"
INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
XU100_CLOSE_MISSING = "XU100_CLOSE_MISSING"
STALE_S0 = "STALE_S0"
PREDICTION_TOO_EARLY = "PREDICTION_TOO_EARLY"
XU100_INTEGRITY = "XU100_INTEGRITY"
REFUSAL_CODES = (CALENDAR_NOT_COVERING, INSUFFICIENT_HISTORY, XU100_CLOSE_MISSING, STALE_S0,
                 PREDICTION_TOO_EARLY, XU100_INTEGRITY)


class Market20IntegrityError(ValueError):
    """XU100 kayıt bütünlüğü ya da revizyon denetimi hatası."""


@dataclass(frozen=True)
class Calendar:
    name: str
    days: tuple[str, ...]      # takvimdeki her gün (artan, ardışık)
    sessions: tuple[str, ...]  # resmi seans sayılan günler (artan)
    sha256: str

    @property
    def last_date(self) -> str:
        return self.days[-1]

    def extended(self, extra: Sequence[tuple[str, bool]], name: str) -> "Calendar":
        """Sonuna (tarih, seans_mı) günleri eklenmiş kopya (sentetik testler ve Faz 2 uzatması)."""
        days = list(self.days) + [d for d, _ in extra]
        sessions = list(self.sessions) + [d for d, s in extra if s]
        _check_consecutive(days, name)
        return Calendar(name=name, days=tuple(days), sessions=tuple(sessions), sha256="SYNTHETIC")


@dataclass(frozen=True)
class XU100Record:
    date: str
    index_name: str
    close: Decimal


@dataclass(frozen=True)
class Market20Result:
    ref_date: str
    f6: Optional[Decimal]
    refusal: Optional[str]
    S0_date: Optional[str] = None
    S20_date: Optional[str] = None
    close_S0: Optional[Decimal] = None
    close_S20: Optional[Decimal] = None
    calendar_sha256: Optional[str] = None
    xu100_sha256: Optional[str] = None

    def as_record(self) -> dict[str, Any]:
        """Dondurma kaydına yazılacak biçim (Decimal'ler metin)."""
        s = lambda v: None if v is None else str(v)  # noqa: E731
        return {"ref_date": self.ref_date, "f6": s(self.f6), "refusal": self.refusal, "S0_date": self.S0_date,
                "S20_date": self.S20_date, "close_S0": s(self.close_S0), "close_S20": s(self.close_S20),
                "calendar_sha256": self.calendar_sha256, "xu100_sha256": self.xu100_sha256}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _check_sha(path: Path, expected: Optional[str]) -> str:
    actual = sha256_file(path)
    if expected is not None and actual != expected:
        raise Market20IntegrityError(f"{Path(path).name} sha256 {actual} != {expected}")
    return actual


def _check_consecutive(days: Sequence[str], name: str) -> None:
    for a, b in zip(days, days[1:]):
        if date.fromisoformat(b) - date.fromisoformat(a) != timedelta(days=1):
            raise Market20IntegrityError(f"{name}: takvim günleri ardışık değil ({a} -> {b})")


def load_calendar_b(path: Path = CALENDAR_B_PATH, expected_sha256: Optional[str] = CALENDAR_B_SHA256) -> Calendar:
    """Takvim B: 1327 ardışık takvim günü, 910 seans (`counts_as_official_session == "YES"`)."""
    sha = _check_sha(path, expected_sha256)
    rows = _read_csv(path)
    days = [r["calendar_date"] for r in rows]
    _check_consecutive(days, "Takvim B")
    sessions = [r["calendar_date"] for r in rows if r["counts_as_official_session"] == "YES"]
    return Calendar(name="B", days=tuple(days), sessions=tuple(sessions), sha256=sha)


def load_calendar_a(path: Path = CALENDAR_A_PATH, expected_sha256: Optional[str] = CALENDAR_A_SHA256) -> Calendar:
    """Takvim A: H99 oturum takvimi (`counts_as_official_session == "TRUE"`), 2023-09-22'de başlar."""
    sha = _check_sha(path, expected_sha256)
    rows = _read_csv(path)
    days = [r["calendar_date"] for r in rows]
    _check_consecutive(days, "Takvim A")
    sessions = [r["calendar_date"] for r in rows if r["counts_as_official_session"] == "TRUE"]
    return Calendar(name="A", days=tuple(days), sessions=tuple(sessions), sha256=sha)


def load_calendar_b_extended(
    path: Path = CALENDAR_B_EXT_PATH, expected_sha256: Optional[str] = CALENDAR_B_EXT_SHA256,
    base: Optional[Calendar] = None,
) -> Calendar:
    """Takvim B + Faz 2A uzatması (aynı şema). Uzatma B'nin son gününün ertesinde başlamalı ve
    ardışık olmalı; `sha256` alanı iki dosyanın sha'sını taşır ("<B>+<uzatma>")."""
    base = base or load_calendar_b()
    sha = _check_sha(path, expected_sha256)
    rows = _read_csv(path)
    extra = [(r["calendar_date"], r["counts_as_official_session"] == "YES") for r in rows]
    if not extra or date.fromisoformat(extra[0][0]) - date.fromisoformat(base.last_date) != timedelta(days=1):
        raise Market20IntegrityError("takvim uzatması Takvim B'nin son gününün ertesinde başlamıyor")
    cal = base.extended(extra, name="B+EXT")
    return Calendar(name=cal.name, days=cal.days, sessions=cal.sessions, sha256=f"{base.sha256}+{sha}")


def calendar_c_rows() -> list[dict[str, str]]:
    """Takvim C satırları (yalnız sabitlerden; dosya bunun baytlarıdır, test yeniden üretir)."""
    rows = []
    d, end = date.fromisoformat(CALENDAR_C_FIRST), date.fromisoformat(CALENDAR_C_LAST)
    while d <= end:
        day, table = d.isoformat(), HOLIDAY_TABLES_2020_2023[d.year]
        weekend = d.weekday() >= 5
        full, half, gap = day in table["full"], day in table["half"], day in XU100_GAP_CLOSURES
        if full and half:
            raise Market20IntegrityError(f"{day}: hem tam kapanış hem yarım gün")
        locator = (C_LOCATOR_FULL if full else C_LOCATOR_HALF if half else C_LOCATOR_XU100_GAP if gap
                   else C_LOCATOR_WEEKEND if weekend else C_LOCATOR_OPEN)
        session = not (weekend or full or gap)
        rows.append({"calendar_date": day, "weekday_name": WEEKDAY_NAMES[d.weekday()], "is_weekend": "YES" if weekend else "NO",
                     "full_closure": "YES" if full else "NO", "half_day": "YES" if half else "NO",
                     "counts_as_official_session": "YES" if session else "NO", "source_year": str(d.year),
                     "source_pdf": table["url"], "source_pdf_sha256": table["sha256"], "source_locator": locator,
                     "verification_status": C_STATUS_XU100_GAP if gap else C_STATUS})
        d += timedelta(days=1)
    return rows


def calendar_c_bytes() -> bytes:
    import io

    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=CALENDAR_COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(calendar_c_rows())
    return buf.getvalue().encode("utf-8")


def load_calendar_c(path: Path = CALENDAR_C_PATH, expected_sha256: Optional[str] = None) -> Calendar:
    """Takvim C (eski kohort f6'sı; SPEC_MARKET20_V0 §3 kuralları aynen, ref_date = first_trading_date, §4-e)."""
    sha = _check_sha(path, CALENDAR_C_SHA256 if expected_sha256 is None else expected_sha256)
    rows = _read_csv(path)
    days = [r["calendar_date"] for r in rows]
    _check_consecutive(days, "Takvim C")
    if (days[0], days[-1]) != (CALENDAR_C_FIRST, CALENDAR_C_LAST):
        raise Market20IntegrityError(f"Takvim C aralığı {days[0]}…{days[-1]}")
    sessions = [r["calendar_date"] for r in rows if r["counts_as_official_session"] == "YES"]
    return Calendar(name="C", days=tuple(days), sessions=tuple(sessions), sha256=sha)


def half_days_c(path: Path = CALENDAR_C_PATH) -> frozenset[str]:
    _check_sha(path, CALENDAR_C_SHA256)
    return frozenset(r["calendar_date"] for r in _read_csv(path) if r["half_day"] == "YES")


def load_oot_sources() -> tuple[Calendar, list[XU100Record], str]:
    """Eski kohort f6'sı için (Takvim C, en yeni pinli XU100, sha). Takvim C'nin bütün aralığında seans günleri = XU100
    kaydı olan günler (SPEC_MARKET20_V0 §4-5; fark varsa DUR)."""
    calendar = load_calendar_c()
    records, sha = load_xu100_latest()
    check_calendar_vs_xu100(calendar, records, CALENDAR_C_FIRST, CALENDAR_C_LAST)
    return calendar, records, sha


def oot_market20(first_trading_date: str, sources: Optional[tuple[Calendar, list[XU100Record], str]] = None) -> Market20Result:
    """Eski kohort (SPEC_OOT_PRE_H99_V0 §4): ref_date = first_trading_date (backtest/geç kayıt tanımı, §4-e), Takvim C."""
    calendar, records, sha = sources or load_oot_sources()
    return market20(first_trading_date, calendar, records, xu100_sha256=sha)


def check_calendar_vs_xu100(calendar: Calendar, records: Sequence[XU100Record], start: str, end: str) -> None:
    """SPEC_MARKET20_V0 §4-5: [start, end] aralığında XU100 kaydı olan günler = takvim seans günleri.
    Fark varsa Market20IntegrityError (DUR): ilan dışı kapanışı ya da eksik kaydı yakalar."""
    sessions = {d for d in calendar.sessions if start <= d <= end}
    closes = {r.date for r in records if start <= r.date <= end}
    if sessions != closes:
        diff = sorted(sessions ^ closes)
        raise Market20IntegrityError(f"takvim/XU100 gün kümesi farkı {start}…{end}: {diff[:5]} (toplam {len(diff)})")


def load_xu100_latest() -> tuple[list[XU100Record], str]:
    """En yeni pinli XU100 dosyası; sha denetlenir ve her eski pinli dosyanın bütün kayıtları
    bunda Decimal-eşit olmalıdır (revizyon denetimi, §4-2)."""
    path, sha = XU100_PINNED[-1]
    records, actual = load_xu100(path, sha)
    for old_path, old_sha in XU100_PINNED[:-1]:
        check_revision(load_xu100(old_path, old_sha)[0], records)
    return records, actual


def load_live_sources() -> tuple[Calendar, list[XU100Record], str]:
    """Canlı/geç kayıt f6'sı için (takvim B+uzatma, en yeni XU100, sha). Uzatılan aralıkta
    son XU100 kaydına kadar takvim ↔ XU100 gün kümesi çapraz denetlenir."""
    base = load_calendar_b()
    calendar = load_calendar_b_extended(base=base)
    records, sha = load_xu100_latest()
    start = (date.fromisoformat(base.last_date) + timedelta(days=1)).isoformat()
    check_calendar_vs_xu100(calendar, records, start, min(max(r.date for r in records), calendar.last_date))
    return calendar, records, sha


def parse_xu100_payload(text: str) -> list[XU100Record]:
    """Ham BIST grafik yanıtı -> kayıtlar. Değerler JSON sözcüğünden kesin Decimal
    (`parse_float=Decimal`; binary64'e hiç uğramaz)."""
    payload = json.loads(text, parse_float=Decimal)
    if payload.get("status") != "success":
        raise Market20IntegrityError(f"XU100 yanıt durumu 'success' değil: {payload.get('status')!r}")
    out: list[XU100Record] = []
    for rec in payload["data"]:
        value = rec.get("clval")
        if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
            raise Market20IntegrityError(f"XU100 {rec.get('hisTs')}: kapanış sayı değil ({value!r})")
        out.append(XU100Record(date=str(rec.get("hisTs")), index_name=str(rec.get("indexName")), close=Decimal(value)))
    return out


def load_xu100(path: Path = XU100_PATH, expected_sha256: Optional[str] = XU100_SHA256) -> tuple[list[XU100Record], str]:
    """Pinli dosya: sha256 denetlenir ve bütün dosya kural 6'yı geçmelidir."""
    sha = _check_sha(path, expected_sha256)
    records = parse_xu100_payload(Path(path).read_text(encoding="utf-8"))
    closes_by_date(records)
    return records, sha


def closes_by_date(records: Sequence[XU100Record]) -> dict[str, Decimal]:
    """Kural 6: yalnız XU100; aynı tarihte çelişen iki değer yok; değer > 0."""
    closes: dict[str, Decimal] = {}
    for r in records:
        if r.index_name != INDEX_NAME:
            raise Market20IntegrityError(f"{r.date}: indexName {r.index_name!r} != {INDEX_NAME}")
        if not r.close > 0:
            raise Market20IntegrityError(f"{r.date}: kapanış pozitif değil ({r.close})")
        if r.date in closes and closes[r.date] != r.close:
            raise Market20IntegrityError(f"{r.date}: aynı tarihte çelişen iki kapanış")
        closes[r.date] = r.close
    return closes


def check_revision(old: Sequence[XU100Record], new: Sequence[XU100Record]) -> None:
    """SPEC_MARKET20_V0 §4-2: eski pinli dosyanın her kaydı yeni dosyada Decimal-eşit
    olmalı; yalnız ekleme kabul edilir. Aksi halde Market20IntegrityError (DUR)."""
    old_closes, new_closes = closes_by_date(old), closes_by_date(new)
    changed = [d for d, v in old_closes.items() if new_closes.get(d) != v]
    if changed:
        raise Market20IntegrityError(f"XU100 revizyonu: {len(changed)} eski kayıt değişmiş ya da silinmiş (ilk: {sorted(changed)[0]})")


def market20(
    ref_date: str,
    calendar: Calendar,
    xu100: Sequence[XU100Record],
    *,
    xu100_sha256: Optional[str] = None,
    live: bool = False,
    first_trading_date: Optional[str] = None,
) -> Market20Result:
    """f6 ya da RET (neden koduyla). Canlıda `ref_date` = tahmin tarihi ve
    `first_trading_date` = beklenen T verilir (kural 5)."""
    ref = date.fromisoformat(ref_date)
    base = dict(ref_date=ref_date, calendar_sha256=calendar.sha256, xu100_sha256=xu100_sha256)

    def refuse(code: str, **extra: Any) -> Market20Result:
        return Market20Result(f6=None, refusal=code, **base, **extra)

    if date.fromisoformat(calendar.last_date) < ref - timedelta(days=1):
        return refuse(CALENDAR_NOT_COVERING)
    sessions = list(calendar.sessions)
    i = bisect.bisect_left(sessions, ref_date) - 1
    if i < WINDOW_SESSIONS:
        return refuse(INSUFFICIENT_HISTORY)
    window = sessions[i - WINDOW_SESSIONS: i + 1]
    s0, s20 = window[-1], window[0]
    visible = [r for r in xu100 if r.date < ref_date]  # kural 7: as_of
    try:
        closes = closes_by_date(visible)
    except Market20IntegrityError:
        return refuse(XU100_INTEGRITY, S0_date=s0, S20_date=s20)
    if any(d not in closes for d in window):
        return refuse(XU100_CLOSE_MISSING, S0_date=s0, S20_date=s20)
    if (ref - date.fromisoformat(s0)).days > MAX_STALE_DAYS:
        return refuse(STALE_S0, S0_date=s0, S20_date=s20)
    if live:
        if first_trading_date is None:
            raise ValueError("canlı market20 çağrısı first_trading_date ister")
        if (date.fromisoformat(first_trading_date) - ref).days > MAX_LEAD_DAYS:
            return refuse(PREDICTION_TOO_EARLY, S0_date=s0, S20_date=s20)
    with localcontext(MARKET20_CONTEXT):
        f6 = closes[s0] / closes[s20] - Decimal(1)
    return Market20Result(f6=f6, refusal=None, S0_date=s0, S20_date=s20, close_S0=closes[s0],
                          close_S20=closes[s20], **base)


def h99_market20(tickers_and_dates: Sequence[tuple[str, str]]) -> dict[str, Market20Result]:
    """Eğitim/backtest: ref_date = T, Takvim B, pinli XU100."""
    calendar = load_calendar_b()
    records, sha = load_xu100()
    return {t: market20(ftd, calendar, records, xu100_sha256=sha) for t, ftd in tickers_and_dates}

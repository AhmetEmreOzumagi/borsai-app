"""TÜİK TÜFE genel endeksi (2025=100) ve T − 2 ay kuralı (SPEC_HAZARD_V1 §3.2, §9, §12; KARARLAR K3). Yalnız stdlib.

Dosya `data/raw/tuik/tufe_genel_2025_100.csv` (sütunlar month, index, release_date, bulletin_id, source_url, source_sha256;
üretici `data/raw/tuik/build_tufe_csv.py`, kaynak TÜİK veri portalındaki pinli tablo ve her ayın kendi bülteni):

    month_for(T)  = T'nin ayı − 2          (ör. 2026-09-25 -> 2026-07, 2026-10-01 -> 2026-08, 2020-01-06 -> 2019-11)
    index_for(T)  = {month, index, release_date, file_sha256, rule}; ay dosyada yoksa RET TUFE_MISSING,
                    release_date ≥ T ise RET TUFE_NOT_PIT (bekçi; kural gereği olamaz: m − 2'nin bülteni m − 1'de yayımlanır)

Ay eklemek veri sürümünü değiştirmez: yeni ay dosyanın sonuna bir satırdır, eski satırlar bayt-eşit kalır. Pin
(`prefix_sha256(through_month)`) başlık dahil dosyanın `through_month` satırına kadarki baytlarının sha256'sıdır; ekleme
onu değiştirmez, eski bir satırın, temel yılın ya da zincirlemenin değişmesi değiştirir (RET TUFE_FILE_MISMATCH; yeni veri
sürümü = yeni model_id, CLAUDE.md kural 5).

Deflasyonun aritmetiği (f1r = büyüklük / (endeks / 100)) tahmin yolundadır: `borsai.predict_hazard.real_size` (tek tanım).
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Optional

from .provenance import ROOT

TUFE_REL = "data/raw/tuik/tufe_genel_2025_100.csv"
TUFE_PATH = ROOT / TUFE_REL
COLUMNS: tuple[str, ...] = ("month", "index", "release_date", "bulletin_id", "source_url", "source_sha256")
SERIES = "TUIK_TUFE_GENEL_2025_100"
MONTH_RULE = "T_MONTH_MINUS_2"
UNIT = "2025 TL"
FIRST_MONTH = "2019-11"          # eski kohortun ilk T'si 2020-01 -> 2019-11 (§3.2 kapsam)
LAG_MONTHS = 2

# Ret kodları (SPEC_HAZARD_V1 §9 REFUSED_TUFE_*; mevcut kalıp: sabit REFUSED_X, değer "X", ör. REFUSED_F3_MISSING = "F3_MISSING").
TUFE_MISSING = "TUFE_MISSING"
TUFE_NOT_PIT = "TUFE_NOT_PIT"
TUFE_FILE_MISMATCH = "TUFE_FILE_MISMATCH"
REFUSAL_CODES: tuple[str, ...] = (TUFE_MISSING, TUFE_NOT_PIT, TUFE_FILE_MISMATCH)

# Aylık ekleme komutu (tek metin: kayıt ön koşulunun hata iletisi, docs/PROVENANCE.md §11 ve testler bunu kullanır). Ay m'nin
# bülteni yayımlanınca (m + 1'in 3'ü, 10:00) o bültenin "Tüketici fiyat endeksi ve değişim oranları" tablosu tarayıcıyla
# indirilir; komut tabloyu doğrular ve dosyanın sonuna tek satır ekler (eski satırlar bayt-eşit; `data/raw/tuik/build_tufe_csv.py`).
APPEND_COMMAND = (".venv/bin/python data/raw/tuik/build_tufe_csv.py --append-month {month} --bulletin-id <bülten sayısı> "
                  "--release <YYYY-MM-DDT10:00:00+03:00> --xls <indirilen tablo .xls> --download-url '<indirme bağlantısı>' "
                  "--sha256 <indirilen tablonun sha256'sı>")


def append_command(month: str) -> str:
    return APPEND_COMMAND.format(month=month)


_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")


class TufeError(ValueError):
    """Dosya biçimi ya da süreklilik ihlali (değer düzeltilmez; durulur)."""


class TufeRefusal(ValueError):
    """Tahmin girdisi hazırlanamadı: `code` ∈ REFUSAL_CODES, `month` ilgili ay."""

    def __init__(self, code: str, month: Optional[str], message: str) -> None:
        self.code = code
        self.month = month
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class TufeRow:
    month: str
    index: str            # kaynak metni (Decimal ile okunur)
    release_date: str     # o ayın kendi bülteninin yayım günü (Europe/Istanbul)
    bulletin_id: str
    source_url: str
    source_sha256: str


@dataclass(frozen=True)
class TufeTable:
    rows: dict[str, TufeRow]          # ay -> satır, dosya sırası
    raw: bytes
    file_sha256: str
    path: str

    @property
    def months(self) -> list[str]:
        return list(self.rows)

    def prefix_bytes(self, through_month: str) -> bytes:
        """Başlık + ilk satırdan `through_month` satırına kadar (dahil) dosya baytları."""
        if through_month not in self.rows:
            raise TufeRefusal(TUFE_FILE_MISMATCH, through_month, f"pin ayı {through_month} dosyada yok")
        n = self.months.index(through_month) + 2          # başlık satırı + (sıra + 1) veri satırı
        lines = self.raw.split(b"\n")
        return b"\n".join(lines[:n]) + b"\n"

    def prefix_sha256(self, through_month: str) -> str:
        return hashlib.sha256(self.prefix_bytes(through_month)).hexdigest()


def month_add(month: str, k: int) -> str:
    y, m = int(month[:4]), int(month[5:7]) - 1 + k
    return f"{y + m // 12:04d}-{m % 12 + 1:02d}"


def month_for(T: str) -> str:
    """T (YYYY-MM-DD, ilk işlem günü) -> T'nin ayı − 2 (YYYY-MM). SPEC_HAZARD_V1 §12 sözde kodu aynen."""
    y, m = int(T[:4]), int(T[5:7])
    m -= LAG_MONTHS
    if m <= 0:
        y, m = y - 1, m + 12
    return f"{y:04d}-{m:02d}"


def parse(raw: bytes, path: str = TUFE_REL) -> TufeTable:
    """Biçim ve süreklilik denetimli okuma. Aylar FIRST_MONTH'tan başlar ve boşluksuz artar; her satırın yayımı referans
    ayını izleyen ayın ≥ 3. günü; endeks pozitif Decimal; kimlik ve sha biçimleri."""
    text = raw.decode("utf-8")
    if not raw.endswith(b"\n") or b"\r" in raw:
        raise TufeError(f"{path}: satır sonu LF değil ya da dosya LF ile bitmiyor")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if tuple(reader.fieldnames or ()) != COLUMNS:
        raise TufeError(f"{path}: sütunlar {reader.fieldnames} != {COLUMNS}")
    rows: dict[str, TufeRow] = {}
    expect = FIRST_MONTH
    for r in reader:
        m = r["month"]
        if not _MONTH.match(m) or m != expect:
            raise TufeError(f"{path}: ay {m!r} beklenen {expect} değil (süreklilik)")
        expect = month_add(m, 1)
        try:
            idx = Decimal(r["index"])
        except InvalidOperation as exc:
            raise TufeError(f"{path}: {m} endeks {r['index']!r}") from exc
        if not idx.is_finite() or idx <= 0 or r["index"] != r["index"].strip():
            raise TufeError(f"{path}: {m} endeks {r['index']!r}")
        rd = r["release_date"]
        if not _DATE.match(rd) or rd[:7] != month_add(m, 1) or int(rd[8:10]) < 3:
            raise TufeError(f"{path}: {m} yayım günü {rd!r} referans ayını izleyen ayın 3'ünden önce ya da o ayda değil")
        if not r["bulletin_id"].isdigit() or not _SHA.match(r["source_sha256"]) or not r["source_url"].startswith("https://"):
            raise TufeError(f"{path}: {m} bülten kimliği / kaynak biçimi")
        rows[m] = TufeRow(m, r["index"], rd, r["bulletin_id"], r["source_url"], r["source_sha256"])
    if not rows:
        raise TufeError(f"{path}: satır yok")
    return TufeTable(rows=rows, raw=raw, file_sha256=hashlib.sha256(raw).hexdigest(), path=path)


def load(path: Path = TUFE_PATH) -> TufeTable:
    path = Path(path)
    rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
    return parse(path.read_bytes(), rel)


def verify_pin(table: TufeTable, pin: Mapping[str, Any]) -> None:
    """Model/veri sürümü pini: {through_month, prefix_sha256}. Ekleme serbest; önekin değişmesi RET TUFE_FILE_MISMATCH."""
    got = table.prefix_sha256(pin["through_month"])
    if got != pin["prefix_sha256"]:
        raise TufeRefusal(TUFE_FILE_MISMATCH, pin["through_month"],
                          f"{table.path} önek sha256 {got} != pin {pin['prefix_sha256']} ({pin['through_month']}'a kadar); "
                          "eski satır, temel yıl ya da zincirleme değişmiş: yeni veri sürümü gerekir")


def index_for(T: str, table: TufeTable) -> dict[str, Any]:
    """T'nin deflatörü: {month, index (metin), release_date, bulletin_id, file_sha256, rule}. Ay yoksa RET TUFE_MISSING;
    yayım T'den önce değilse RET TUFE_NOT_PIT (`inputs_pit_ok` bekçisi)."""
    month = month_for(T)
    row = table.rows.get(month)
    if row is None:
        raise TufeRefusal(TUFE_MISSING, month, f"TÜFE {month} ayı {table.path} dosyasında yok (T = {T})")
    if not row.release_date < T:
        raise TufeRefusal(TUFE_NOT_PIT, month, f"TÜFE {month} yayımı {row.release_date}, T = {T}'den önce değil")
    return {"month": row.month, "index": row.index, "release_date": row.release_date, "bulletin_id": row.bulletin_id,
            "file_sha256": table.file_sha256, "rule": MONTH_RULE}


def pin_of(table: TufeTable, through_month: Optional[str] = None) -> dict[str, str]:
    """Şartname/veri sürümü pini (dosyanın bugünkü son ayı varsayılan)."""
    m = through_month or table.months[-1]
    return {"path": table.path, "series": SERIES, "through_month": m, "prefix_sha256": table.prefix_sha256(m)}

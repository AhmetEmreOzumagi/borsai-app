#!/usr/bin/env python3
"""Takvim C'nin (data/raw/pay_calendar_c_20200101_20230921.csv) BAĞIMSIZ denetimi: `borsai` import edilmez.
1) BIST tatil tablosu PDF'leri resmi siteden indirilmiş (curl; sha256 pinlerle karşılaştırılır, ekler/takvim_2020_2023.md).
2) PDF metni (macOS PDFKit, Swift `pdftext`) kural tabanlı ayrıştırılır: bir tarih, kendisini içeren SON "... seans
   yapılmayacaktır." parçasında geçiyorsa tam kapanış, SON "... yarım gün seans yapılacaktır." parçasında geçiyorsa yarım gün
   (takas cümleleri atlanır: "tarihli"/"gerçekleş" içeren satırlar ve "takas"tan sonrası; yıl yazılmamışsa tablonun yılı).
3) Takvim C'nin 1360 satırı tek tek: full_closure / half_day / counts_as_official_session / source_locator / source_pdf(_sha256)
   beklenenle karşılaştırılır; beklenen seans = hafta içi ∧ tabloda tam kapanış değil ∧ XU100 boşluğu değil.
4) XU100 (pinli seri) gün kümesi = seans kümesi; tabloda olmayan hafta içi XU100 boşlukları listelenir."""
import csv
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
PDF_DIR = Path(sys.argv[2]).resolve()          # indirilen PDF'ler
PDFTEXT = Path(sys.argv[3]).resolve()          # Swift PDFKit metin çıkarıcı
CSV = ROOT / "data/raw/pay_calendar_c_20200101_20230921.csv"
EKLER = (ROOT / "docs/specs_faz6/ekler/takvim_2020_2023.md").read_text(encoding="utf-8")
PINS = {int(m.group(1)): (m.group(2), m.group(3)) for m in re.finditer(r"\| (20\d\d) \| (https://\S+) \| `([0-9a-f]{64})` \|", EKLER)}
MONTHS = {m: i + 1 for i, m in enumerate("Ocak Şubat Mart Nisan Mayıs Haziran Temmuz Ağustos Eylül Ekim Kasım Aralık".split())}
DATE_RE = re.compile(r"\b(\d{1,2}) (Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)(?: (\d{4}))?")

print("sha256 pinleri (takvim_2020_2023.md) ↔ indirilen PDF:")
texts = {}
for year, (url, sha) in sorted(PINS.items()):
    f = PDF_DIR / url.rsplit("/", 1)[1]
    got = hashlib.sha256(f.read_bytes()).hexdigest()
    print(f"  {year}: {'EŞİT' if got == sha else 'FARKLI'}  {f.name}  {got[:16]}…  ({f.stat().st_size} bayt)")
    assert got == sha
    texts[year] = subprocess.run([str(PDFTEXT), str(f)], check=True, capture_output=True, text=True).stdout


def parse(year, text):
    full, half = {}, {}
    seg = []
    for line in text.splitlines():
        low = line.lower()
        if "tarihli" in low or "gerçekleş" in low:      # takas cümleleri ("… tarihli işlemlerin takası … gerçekleştirilecektir")
            continue
        if "takas" in low:                                # "… seans yapılmayacaktır. 1 Ocak 2023 Pazar takas yapılmayacaktır."
            line = line[:low.index("takas")]
            if "yapıl" not in line.lower():               # yalnız takas cümlesi: tarihleri toplama
                continue
        for d, mon, y in DATE_RE.findall(line):
            seg.append(date(int(y) if y else year, MONTHS[mon], int(d)).isoformat())
        low = line.lower()
        if "yapılmayacaktır" in low:
            for x in seg:
                full[x] = True
                half.pop(x, None)
            seg = []
        elif "yapılacaktır" in low:
            for x in seg:
                half[x] = True
                full.pop(x, None)
            seg = []
    return set(full), set(half)


table_full, table_half = {}, {}
for year, text in texts.items():
    f, h = parse(year, text)
    table_full[year], table_half[year] = f, h
    print(f"\n{year} tablosu (PDF metninden): tam kapanış {len(f)}: {sorted(f)}")
    print(f"{year} tablosu (PDF metninden): yarım gün {len(h)}: {sorted(h)}")
    assert not (f & h)
    md_half = re.search(rf"\| {year} \| .*? \| `[0-9a-f]+` \| (.*?) \|", EKLER).group(1)
    print(f"  ekler/takvim_2020_2023.md yarım günleri: {md_half} -> {'EŞİT' if set(md_half.split(', ')) == h else 'FARKLI'}")

xu = json.load((ROOT / "data/raw/xu100/xu100_graphic_20260922.json").open())["data"]
closes = {r["hisTs"] for r in xu if r["indexName"] == "XU100"}
rows = list(csv.DictReader(CSV.open(encoding="utf-8", newline="")))
print(f"\nTakvim C: {len(rows)} satır, {rows[0]['calendar_date']}…{rows[-1]['calendar_date']}; sha256 {hashlib.sha256(CSV.read_bytes()).hexdigest()[:16]}…")
all_full = set().union(*table_full.values())
all_half = set().union(*table_half.values())
weekday_gaps = sorted(r["calendar_date"] for r in rows if date.fromisoformat(r["calendar_date"]).weekday() < 5
                      and r["calendar_date"] not in closes)
gap_not_in_table = sorted(d for d in weekday_gaps if d not in all_full)
print("hafta içi XU100 boşlukları:", len(weekday_gaps), "| tabloda olmayanlar (XU100_GAP_CLOSURES adayı):", gap_not_in_table)
problems = []
n_session = 0
per_year_gaps = {}
for r in rows:
    d = r["calendar_date"]
    dt = date.fromisoformat(d)
    weekend = dt.weekday() >= 5
    full = d in all_full
    half = d in all_half
    gap = d in gap_not_in_table
    session = not weekend and not full and not gap
    n_session += session
    exp = {"full_closure": "YES" if full else "NO", "half_day": "YES" if half else "NO",
           "counts_as_official_session": "YES" if session else "NO", "is_weekend": "YES" if weekend else "NO",
           "source_year": str(dt.year), "source_pdf": PINS[dt.year][0], "source_pdf_sha256": PINS[dt.year][1],
           "weekday_name": ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"][dt.weekday()]}
    for k, v in exp.items():
        if r[k] != v:
            problems.append((d, k, r[k], v))
    loc = r["source_locator"]
    exp_loc = ("OFFICIAL_FULL_CLOSURES_LITERAL_TRANSCRIPTION" if full else "OFFICIAL_HALF_DAYS_LITERAL_TRANSCRIPTION" if half
               else "NOT_LISTED_IN_HOLIDAY_TABLE_NO_XU100_CLOSE_UNANNOUNCED_CLOSURE" if gap
               else "CALENDAR_ARITHMETIC_WEEKEND_NOT_A_HOLIDAY_TABLE_ENTRY" if weekend
               else "NOT_LISTED_IN_OFFICIAL_FULL_CLOSURES_OR_OFFICIAL_HALF_DAYS")
    if loc != exp_loc:
        problems.append((d, "source_locator", loc, exp_loc))
    if (r["verification_status"] == "FAZ6_XU100_GAP_ONLY_THB_HEAD_PROBE_PENDING_S5") != gap:
        problems.append((d, "verification_status", r["verification_status"], gap))
    if session != (d in closes):
        problems.append((d, "XU100", "seans" if session else "kapanış", "XU100 var" if d in closes else "XU100 yok"))
    per_year_gaps.setdefault(dt.year, []).append(d) if (not weekend and d not in closes) else None
print(f"satır satır karşılaştırma: {len(rows)} satır, uyuşmazlık {len(problems)}")
for p in problems[:20]:
    print("  UYUŞMAZLIK", p)
print("seans sayısı (beklenen):", n_session, "| dosyadaki YES:", sum(r["counts_as_official_session"] == "YES" for r in rows))
print("yıl bazında seans:", {y: sum(r["counts_as_official_session"] == "YES" and r["source_year"] == str(y) for r in rows) for y in PINS})
print("yıl bazında XU100 kapanışı olan gün:", {y: sum(1 for d in closes if d.startswith(str(y)) and d <= "2023-09-21") for y in PINS})
print("yıl bazında hafta içi XU100 boşluğu:", {y: len(v) for y, v in sorted(per_year_gaps.items())})
print("yarım günlerde XU100 kapanışı var:", all(d in closes for d in all_half if d <= "2023-09-21"))
print("2023-10-28 tabloda:", "tam kapanış" if "2023-10-28" in all_full else "yarım gün" if "2023-10-28" in all_half else "yok",
      "(Takvim C aralığı dışında)")
print("borsai sys.modules içinde mi:", "borsai" in sys.modules)

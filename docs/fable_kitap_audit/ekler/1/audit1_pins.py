"""KITAP_AUDIT_1 Adım 4: kodda ve belgelerde pinli her ham dosyanın sha256'sını yeniden hesapla; .source.json ve manifest tutarlılığı.
borsai import edilmez. Çıktıya bülten dosya adı yazılmaz (yalnız sayılar)."""
import csv, hashlib, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
out = []; P = lambda *a: out.append(" ".join(str(x) for x in a))
HEX = re.compile(r"\b[0-9a-f]{64}\b")

# 1) Kod sabitleri -> dosya
pins = {
 "borsai/outcomes.py:SESSIONS_SHA256": ("data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv", "eca620d3a5e8fed0b118bab556da5ce519257a4b2e14efcd22065f5bcdc93da9"),
 "borsai/market20.py:CALENDAR_A_SHA256": ("data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_pay_session_calendar.csv", "15d4d975db53a42006c1e57bab7b5f11eab52f281069cc90f0c38361770bf9cb"),
 "borsai/market20.py:CALENDAR_B_SHA256": ("data/raw/v2_market20_official_pay_calendar_evidence_r4.csv", "49b58029715881a7f1a304afb7e41fcff3d5c1c7a8896de3ed9bb555fb02d159"),
 "borsai/market20.py:CALENDAR_B_EXT_SHA256": ("data/raw/pay_calendar_b_extension_20260820_20261231.csv", "273ca0e7f815c7bb1a0ce562ba7060d2dc806603f2112cdde460195cbebc6432"),
 "borsai/market20.py:CALENDAR_C_SHA256": ("data/raw/pay_calendar_c_20200101_20230921.csv", "6dfd6134584a1a14211c3a56b5b274fef321f666bf870ce99605a97bee16fe4e"),
 "borsai/market20.py:XU100_SHA256": ("data/raw/official_bist_xu100_graphic_pinned_through_20260819.json", "34859d7eefdb552a31f6476e2230a07a825ada3ee769a2a7646f12399c303fdf"),
 "borsai/market20.py:XU100_PINNED[1]": ("data/raw/xu100/xu100_graphic_20260922.json", "04637c911f912e007522790520191ae99ad5cf47f8d38a4360698ea3038397fe"),
 "borsai/data.py:PB_SHA256": ("data/raw/PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv", "5e52d4d23b4f196ef0fd44fb6d4f4edab0ea326241288b036952c30c5e24a613"),
 "borsai/specs.py:H99_DATA_VERSION_SHA256": ("data/data_version.json", "a0c7d082dacdbde03f53d1c4af1ce9f7983f9946abc80062de570f4a1df1f977"),
 "borsai/specs.py:V2_DATA_VERSION_SHA256": ("data/data_version_v2.json", "2ee8d51be3f026ad05ff7b4894f9512809556b3da2fd2d0b06256b7de5ee525a"),
}
# sabitlerin kodda gerçekten bu değerle durduğunu da doğrula
code = {p: Path(ROOT / p).read_text(encoding="utf-8") for p in ("borsai/outcomes.py", "borsai/market20.py", "borsai/data.py", "borsai/specs.py")}
for name, (rel, expected) in pins.items():
    f = name.split(":")[0]
    P(f"[ÖLÇTÜM] {name}: kodda var={expected in code[f]} dosya sha eşit={sha(ROOT / rel) == expected} ({rel})")
# TÜFE önek pini
tufe = (ROOT / "data/raw/tuik/tufe_genel_2025_100.csv").read_bytes()
lines = tufe.split(b"\n"); months = [l.split(b",")[0].decode() for l in lines[1:] if l]
n = months.index("2026-08") + 2
prefix = b"\n".join(lines[:n]) + b"\n"
P("[ÖLÇTÜM] TUFE_PIN prefix(2026-08) sha =", hashlib.sha256(prefix).hexdigest()[:16], "kodda var:", hashlib.sha256(prefix).hexdigest() in code["borsai/specs.py"],
  "| önek == tam dosya:", prefix == tufe, "| ay sayısı", len(months), months[0], "…", months[-1])
# data_version kaynakları
for vf in ("data/data_version.json", "data/data_version_v2.json"):
    v = json.loads((ROOT / vf).read_text())
    P(f"[ÖLÇTÜM] {vf}: tablo sha eşit={sha(ROOT / v['table']) == v['sha256']} bayt eşit={(ROOT / v['table']).stat().st_size == v['bytes']} builder sha eşit={sha(ROOT / v['builder']) == v['builder_sha256']}",
      "kaynaklar:", [(s["path"].split("/")[-1][:30], sha(ROOT / s["path"]) == s["sha256"]) for s in v["sources"]])
v2 = json.loads((ROOT / "data/data_version_v2.json").read_text())
coh = (ROOT / v2["cohort"]["path"]).read_bytes()
P("[ÖLÇTÜM] kohort önek pini:", hashlib.sha256(coh[:v2["cohort"]["bytes"]]).hexdigest() == v2["cohort"]["prefix_sha256"], "| dosya bayt", len(coh), "pin bayt", v2["cohort"]["bytes"])
# açık küme birleşik sha (kod adı yazılmaz)
with open(ROOT / "registry/oot/cohort_pre_h99.csv", encoding="utf-8", newline="") as fh:
    crows = list(csv.DictReader(fh))
P("[ÖLÇTÜM] kohort sütunları:", list(crows[0].keys()))
vault_col = next(c for c in crows[0] if "vault" in c.lower())
status_col = next((c for c in crows[0] if c in ("status", "membership_status")), None)
from collections import Counter
P("[ÖLÇTÜM] kohort satır", len(crows), "| kasa etiketi:", dict(Counter(r[vault_col] for r in crows)), "| durum:", dict(Counter(r[status_col] for r in crows)) if status_col else "-")
open_m = [r for r in crows if r[vault_col] != "SEALED" and (status_col is None or r[status_col] == "MEMBER")]
ident = lambda items: hashlib.sha256(("\n".join(items) + "\n").encode()).hexdigest()
for kind, d, ext in (("oot_inputs", "registry/oot/inputs", ".json"), ("oot_outcomes", "data/outcomes_oot", ".csv")):
    paths = sorted(ROOT / d / f"{r['ticker']}{ext}" for r in open_m)
    got = ident(sorted(f"{p.name}\t{sha(p)}" for p in paths))
    P(f"[ÖLÇTÜM] {kind}: n={len(paths)} (pin n={v2[kind]['n']}) birleşik sha eşit={got == v2[kind]['files_sha256']}")
# TÜİK .source.json
sj = json.loads((ROOT / "data/raw/tuik/tufe_degisim_oranlari_bulten_58290.source.json").read_text())
xls = ROOT / sj["file"]
P("[ÖLÇTÜM] TÜİK source.json: xls var", xls.exists(), "sha eşit", sha(xls) == sj["sha256"], "bayt eşit", xls.stat().st_size == sj["bytes"], "yayım", sj["bulletin"]["published_at"], "| fetched", sj["fetched_at_utc"])
with open(ROOT / "data/raw/tuik/tufe_genel_2025_100.csv", encoding="utf-8", newline="") as fh:
    trows = list(csv.DictReader(fh))
P("[ÖLÇTÜM] tufe_genel: source_sha256 == xls sha:", all(r["source_sha256"] == sj["sha256"] for r in trows), "| source_url == download_url:", all(r["source_url"] == sj["download_url"] for r in trows),
  "| bulletin_id farklı:", len({r["bulletin_id"] for r in trows}), "| 2025 ortalaması:", sum(float(r["index"]) for r in trows if r["month"].startswith("2025")) / 12)
with open(ROOT / "data/raw/tuik/tufe_bultenleri.csv", encoding="utf-8", newline="") as fh:
    brows = {r["month"]: r for r in csv.DictReader(fh)}
P("[ÖLÇTÜM] tufe_bultenleri satır", len(brows), "| tufe_genel ile ay kümesi eşit:", set(brows) == {r["month"] for r in trows},
  "| release_date == bülten tarihi:", sum(brows[r["month"]]["release_datetime"][:10] != r["release_date"] for r in trows), "farklı",
  "| bulletin_id eşit:", sum(brows[r["month"]]["bulletin_id"] != r["bulletin_id"] for r in trows), "farklı")
# yayım günü kuralı: izleyen ayın 3'ü ya da sonraki iş günü
from datetime import date, timedelta
late = []
for r in trows:
    y, m = int(r["month"][:4]), int(r["month"][5:])
    nxt = date(y + (m // 12), m % 12 + 1, 3)
    while nxt.weekday() >= 5: nxt += timedelta(days=1)
    rel = date.fromisoformat(r["release_date"])
    if rel != nxt: late.append((r["month"], r["release_date"], nxt.isoformat()))
P("[ÖLÇTÜM] TÜFE yayım günü '3'ü ya da sonraki iş günü' kuralına uymayan:", len(late), late)
# canlı bülten manifesti ↔ zip'ler (ad yazılmaz)
with open(ROOT / "data/raw/bist/MANIFEST.csv", encoding="utf-8", newline="") as fh:
    man = list(csv.DictReader(fh))
ok = missing = bad = 0
for r in man:
    p = ROOT / "data/raw/bist" / r["kind"] / r["date"][:4] / f"{r['kind']}{r['date'].replace('-', '')}1.zip"
    if not p.exists(): missing += 1
    elif sha(p) == r["sha256"] and p.stat().st_size == int(r["bytes"]): ok += 1
    else: bad += 1
zips = sum(1 for p in (ROOT / "data/raw/bist").rglob("*.zip"))
P("[ÖLÇTÜM] MANIFEST.csv satır", len(man), "| zip var+sha+bayt eşit", ok, "| eksik", missing, "| uyuşmayan", bad, "| diskteki zip sayısı", zips, "| manifestte olmayan zip:", zips - ok - bad)
# H99 SESSIONS'taki pinli bülten sha'ları ile MANIFEST kesişimi (2026-08-06…08-19)
with open(ROOT / "data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv", encoding="utf-8-sig", newline="") as fh:
    srows = list(csv.DictReader(fh))
h99 = {}
for r in srows:
    for k in ("thb", "thm"): h99[(r["target_session_date"], k)] = r[f"{k}_sha256"]
mm = {(r["date"], r["kind"]): r["sha256"] for r in man}
inter = set(h99) & set(mm)
P("[ÖLÇTÜM] H99 pinli bülten (tarih,tür) sayısı", len(h99), "| canlı manifestle kesişen", len(inter), "| sha farklı:", sum(h99[k] != mm[k] for k in inter))
with open(ROOT / "data/raw/bist/MANIFEST_OOT.csv", encoding="utf-8", newline="") as fh:
    moot = list(csv.DictReader(fh))
P("[ÖLÇTÜM] MANIFEST_OOT satır", len(moot), "| tür:", dict(Counter(r["kind"] for r in moot)), "| tarih aralığı", min(r["date"] for r in moot), "…", max(r["date"] for r in moot),
  "| repoda zip var mı:", sum((ROOT / "data/raw/bist" / r["kind"] / r["date"][:4] / f"{r['kind']}{r['date'].replace('-', '')}1.zip").exists() for r in moot))
# tatil tablosu PDF sha'ları: takvim dosyaları ↔ market20 sabitleri (PDF'ler repoda yok)
m20 = code["borsai/market20.py"]
with open(ROOT / "data/raw/pay_calendar_c_20200101_20230921.csv", encoding="utf-8", newline="") as fh:
    cC = list(csv.DictReader(fh))
shaC = {r["source_year"]: r["source_pdf_sha256"] for r in cC}
P("[ÖLÇTÜM] Takvim C yıl->pdf sha kodda var:", {y: s in m20 for y, s in shaC.items()}, "| PDF repoda var:", any(p.suffix == ".pdf" for p in (ROOT / "data/raw").rglob("*")))
# pinsiz dosyalar: data/raw altında hiçbir sabit/sürüm dosyasında sha'sı geçmeyen dosyalar
all_text = "\n".join(code.values()) + (ROOT / "data/data_version.json").read_text() + (ROOT / "data/data_version_v2.json").read_text() + \
           (ROOT / "data/raw/tuik/tufe_degisim_oranlari_bulten_58290.source.json").read_text() + Path(ROOT / "borsai/outcomes_oot.py").read_text() + Path(ROOT / "borsai/tufe.py").read_text()
for p in sorted(ROOT.joinpath("data/raw").rglob("*")):
    if p.is_file() and p.suffix != ".zip" and "__pycache__" not in str(p):
        P(f"[ÖLÇTÜM] pin? {p.relative_to(ROOT)} sha-in-code={sha(p) in all_text}")
Path(__file__).with_suffix(".out.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))

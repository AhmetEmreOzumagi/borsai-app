"""KITAP_AUDIT_1 Adım 6 (canlı): girdi belgeleri (20 alan, kaynak sha, PIT), kaynak manifestleri, sonuç dosyalarının zip'lerden bağımsız
yeniden üretimi (bayt-eşit), tamlık denetiminin bağımsız tekrarı, bülten biçimi, Last-Modified, SPK nesne kimliği zamanı, NETGL taban günleri.
borsai import edilmez. Çıktıya bülten dosya adı yazılmaz."""
import csv, io, json, glob, hashlib, zipfile, bisect, os
from collections import Counter
from datetime import datetime, timezone, timedelta
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]; RAW = ROOT / "data/raw"; IST = timezone(timedelta(hours=3))
def rd(p, enc="utf-8-sig"):
    with open(p, encoding=enc, newline="") as fh: return list(csv.DictReader(fh))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
out = []; P = lambda *a: out.append(" ".join(str(x) for x in a))
FIELDS = ("ipo_price_tl","shares_offered","post_ipo_share_capital","capital_increase_shares","existing_share_sale_shares","total_demand_multiple","total_demand_filter_status","additional_sale_shares","ipo_size_tl",
          "ipo_price_try","planned_pre_ipo_capital","planned_post_ipo_capital","planned_capital_increase_shares","planned_existing_share_sale","planned_base_offer_shares","planned_additional_sale_ceiling","planned_max_offer_shares",
          "first_trading_date","bookbuilding_start","bookbuilding_end")
# ---- girdiler
prices = {}; ftds = {}
for p in sorted(glob.glob(str(ROOT / "registry/inputs/*.json"))):
    d = json.load(open(p)); t = d["ticker"]; f = d["fields"]; src = d["sources"]
    T = f["first_trading_date"]["value"]; prices[t] = f["ipo_price_tl"]["value"]; ftds[t] = T
    missing = [k for k in FIELDS if f[k]["value"] is None]; extra = sorted(set(f) - set(FIELDS)); absent = [k for k in FIELDS if k not in f]
    probs = []
    for k in FIELDS:
        x = f[k]
        if x["value"] is None:
            if not x.get("missing_reason"): probs.append(f"{k}: missing_reason yok")
            continue
        s = src.get(x["source_id"])
        if s is None: probs.append(f"{k}: kaynak yok"); continue
        if x["source_sha256"] != s["sha256"] or x["source_published_at"] != s["published_at"] or x["source_path"] != s["path"]: probs.append(f"{k}: kaynak tablosuyla farklı")
        if not os.path.exists(ROOT / s["path"]) or sha(ROOT / s["path"]) != s["sha256"]: probs.append(f"{k}: belge sha")
        pub = datetime.fromisoformat(x["source_published_at"]).astimezone(IST).date().isoformat()
        if not pub < T: probs.append(f"{k}: yayım {pub} ≥ T")
        if k.startswith("planned") or k == "ipo_price_try":
            if s["kind"] != "SPK_BULLETIN": probs.append(f"{k}: PB alanı SPK değil")
            if not pub < f["bookbuilding_start"]["value"]: probs.append(f"{k}: SPK yayımı talep toplamadan önce değil")
    ids = {}
    D = lambda k: Decimal(f[k]["value"])
    ids["A"] = D("planned_post_ipo_capital") == D("planned_pre_ipo_capital") + D("planned_capital_increase_shares")
    ids["B"] = D("planned_base_offer_shares") == D("planned_capital_increase_shares") + D("planned_existing_share_sale")
    ids["C"] = D("planned_max_offer_shares") == D("planned_base_offer_shares") + D("planned_additional_sale_ceiling")
    ids["so"] = D("shares_offered") == D("capital_increase_shares") + D("existing_share_sale_shares") + D("additional_sale_shares")
    ids["f1"] = D("ipo_size_tl") == D("ipo_price_tl") * D("shares_offered")
    P(f"[ÖLÇTÜM] girdi {t}: T={T} alan={len(f)} eksik alan={absent} boş={missing} ek={extra} kaynak n={len(src)} sorun={probs} özdeşlik={ids} stage={d.get('stage')} basis={d.get('collected_at_basis')}")
# ---- bülten ayrıştırma (bağımsız)
def parse(zpath, kind, day):
    data = Path(zpath).read_bytes()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist(); text = z.read(names[0]).decode("cp1254")
    rec = [r for r in csv.reader(io.StringIO(text.lstrip("﻿")), delimiter=";") if any(c != "" for c in r)]
    hdr, eng, rows = rec[0], rec[1], rec[2:]
    assert len(hdr) == len(eng) and all(len(r) == len(hdr) for r in rows), "genişlik"
    h = {n: i for i, n in enumerate(hdr)}
    assert all(r[h["TARIH"]] == day for r in rows), "tarih"
    byc = {}; conf = set()
    for r in rows:
        c = r[h["ISLEM  KODU"]]
        if c in byc or c in conf: byc.pop(c, None); conf.add(c)
        else: byc[c] = r
    return {"h": h, "rows": byc, "conf": conf, "sha": hashlib.sha256(data).hexdigest(), "ncol": len(hdr), "names": names, "hdr": hdr}
man = rd(RAW / "bist/MANIFEST.csv", "utf-8")
mkey = {(r["date"], r["kind"]): r for r in man}
thb = {}; thm = {}; ncols = Counter(); lm = Counter(); tick_col = Counter()
for r in man:
    z = RAW / "bist" / r["kind"] / r["date"][:4] / f"{r['kind']}{r['date'].replace('-', '')}1.zip"
    b = parse(z, r["kind"], r["date"]); assert b["sha"] == r["sha256"] and b["names"] == [r["internal_filename"]]
    (thb if r["kind"] == "thb" else thm)[r["date"]] = b; ncols[(r["kind"], b["ncol"])] += 1
    lmt = datetime.strptime(r["http_last_modified"], "%a, %d %b %Y %H:%M:%S GMT"); lm[(r["kind"], "aynı gün" if lmt.date().isoformat() == r["date"] else "farklı gün", "sabah<09GMT" if lmt.hour < 9 else "akşam≥12GMT" if lmt.hour >= 12 else "gündüz")] += 1
    if r["kind"] == "thm": tick_col["FIYAT ADIMI" in b["hdr"]] += 1
P("[ÖLÇTÜM] bülten sütun sayıları:", dict(ncols), "| Last-Modified (tür, gün, saat):", dict(lm), "| THM'de FIYAT ADIMI sütunu var:", dict(tick_col))
P("[ÖLÇTÜM] THB 2026 başlık (ilk 12):", thb[max(thb)]["hdr"][:12], "| son sütun:", thb[max(thb)]["hdr"][-1], "| THM başlık:", thm[max(thm)]["hdr"])
# ---- takvim A ∪ B uzatması
sessions = [r["calendar_date"] for r in rd(RAW / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_pay_session_calendar.csv") if r["counts_as_official_session"] == "TRUE"] + \
           [r["calendar_date"] for r in rd(RAW / "pay_calendar_b_extension_20260820_20261231.csv", "utf-8") if r["counts_as_official_session"] == "YES"]
half = {r["calendar_date"] for r in rd(RAW / "pay_calendar_b_extension_20260820_20261231.csv", "utf-8") if r["half_day"] == "YES"} | {r["calendar_date"] for r in rd(RAW / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_pay_session_calendar.csv") if r["session_status"] == "OPEN_HALF_DAY"}
P("[ÖLÇTÜM] UNANNOUNCED_CLOSURES.csv var:", (RAW / "bist/UNANNOUNCED_CLOSURES.csv").exists(), "| 2026-08-18…09-30 resmi seans:", len([s for s in sessions if "2026-08-18" <= s <= "2026-09-30"]),
  "| THB+THM ikisi de yerelde olan seans:", len([s for s in sessions if s in thb and s in thm]), "| THB var THM yok seans:", len([s for s in sessions if s in thb and s not in thm]))
# ---- sonuç dosyası yeniden üretimi
def dec(x):
    try: v = Decimal((x or "").strip()); return v if v.is_finite() else None
    except Exception: return None
def exact_return(close, price):
    r = Fraction(Decimal(close)) / Fraction(Decimal(price)) - 1
    if r == 0: return "0", 0
    with localcontext() as ctx:
        ctx.prec = 50; return format(Decimal(r.numerator) / Decimal(r.denominator), "f").rstrip("0").rstrip("."), int(r > 0)
COLS = ("h","session_date","close_raw","upper_limit_raw","reference_raw","trade_count_raw","halt_flag","half_day","shifted_by_suspension","ceiling_close","R_h","Y_h","ipo_price","thb_sha256","thm_sha256","status")
start = sessions[bisect.bisect_left(sessions, min(ftds.values())) - 1]
ok = 0; diffs = []
for t in sorted(ftds):
    code = f"{t}.E"; hb = {n: i for n, i in thb[max(thb)]["h"].items()}
    first = next((s for s in sessions[bisect.bisect_left(sessions, start):] if s in thb and code in (thb[s]["rows"].keys() | thb[s]["conf"])), None)
    rows = []; seen = skipped = 0
    for s in sessions[bisect.bisect_left(sessions, first):]:
        seen += 1
        if seen > 15 or s not in thb: break
        b = thb[s]; r = b["rows"].get(code); h = b["h"]
        if r is not None:
            tc, cl, halt = dec(r[h["TOPLAM SOZLESME SAYISI"]]), dec(r[h["KAPANIS FIYATI"]]), r[h["GECICI DURDURMA"]]
            assert halt in ("0", "1")
            if tc and tc > 0 and cl and cl > 0:
                m = thm[s]; mr = m["rows"].get(code); mh = m["h"]
                up = dec(mr[mh["UST LIMIT FIYATI"]]) if mr else None
                lab = None if (up is None or up <= 0) else int(cl == up)
                row = dict.fromkeys(COLS, ""); hh = len(rows) + 1
                row.update(h=str(hh), session_date=s, close_raw=r[h["KAPANIS FIYATI"]], upper_limit_raw=mr[mh["UST LIMIT FIYATI"]] if mr else "", reference_raw=mr[mh["REFERANS FIYATI"]] if mr else "",
                           trade_count_raw=r[h["TOPLAM SOZLESME SAYISI"]], halt_flag=halt, half_day=str(int(s in half)), shifted_by_suspension=str(skipped), ceiling_close="NA" if lab is None else str(lab),
                           ipo_price=prices[t], thb_sha256=b["sha"], thm_sha256=m["sha"], status="NA_LIMIT" if lab is None else "OK")
                if hh in (1, 3, 5, 10): row["R_h"], y = exact_return(row["close_raw"], prices[t]); row["Y_h"] = str(y)
                rows.append(row)
                if len(rows) == 10: break
            elif rows: skipped += 1
    buf = io.StringIO(newline=""); w = csv.DictWriter(buf, fieldnames=COLS, lineterminator="\n"); w.writeheader(); w.writerows(rows)
    mine = buf.getvalue().encode(); disk = (ROOT / "data/outcomes" / f"{t}.csv").read_bytes()
    L = 0
    for x in rows:
        if x["ceiling_close"] != "1": break
        L += 1
    if mine == disk: ok += 1
    else: diffs.append(t)
    P(f"[ÖLÇTÜM] sonuç {t}: ilk görünüş={first} D1={rows[0]['session_date']} (kayıt T={ftds[t]}) D10={rows[-1]['session_date']} n={len(rows)} L={L} R_D10={rows[-1]['R_h'][:8]} Y={rows[-1]['Y_h']} bayt-eşit={mine == disk} halt/half/shift={sum(int(x['halt_flag']) for x in rows)}/{sum(int(x['half_day']) for x in rows)}/{rows[-1]['shifted_by_suspension']}")
P("[ÖLÇTÜM] 7 sonuç dosyası bayt-eşit yeniden üretildi:", ok, "| farklı:", diffs)
# NETGL taban günleri (§1.5.5): kapanış == alt limit D4..D10
for t in ("NETGL",):
    code = f"{t}.E"; floors = []
    for x in rd(ROOT / "data/outcomes" / f"{t}.csv", "utf-8"):
        m = thm[x["session_date"]]; mr = m["rows"][code]; lo = mr[m["h"]["ALT LIMIT FIYATI"]]
        floors.append((x["h"], Decimal(x["close_raw"]) == Decimal(lo), lo))
    P("[ÖLÇTÜM] NETGL kapanış == alt limit (h, eşit, alt limit):", floors)
# ---- tamlık bağımsız tekrar: THB'de ilk kez görünen EQT kodları (BUYIN hariç), 2026-08-07…09-30, taban 2026-08-06
days = sorted(d for d in thb)
seen = set(thb["2026-08-06"]["rows"]) | thb["2026-08-06"]["conf"]; new_eq = []
ipos = {r["ticker"]: r for r in rd(ROOT / "registry/ipos.csv", "utf-8")}
cls = Counter()
for d in days[1:]:
    b = thb[d]; h = b["h"]; codes = set(b["rows"]) | b["conf"]
    for c in sorted(codes - seen):
        r = b["rows"].get(c)
        if r is None: cls["çelişkili"] += 1; continue
        grp = r[h["ENSTRUMAN GRUBU"]]; mk = r[h.get("PAZAR", 0)] if "PAZAR" in h else ""; sub = r[h["YAPISAL BAZDA PIYASA ALT BOLUMU"]] if "YAPISAL BAZDA PIYASA ALT BOLUMU" in h else ""; tip = r[h["ENSTRUMAN TIPI"]] if "ENSTRUMAN TIPI" in h else ""
        if "BUYIN" in (mk, sub) or tip.startswith("BUYIN"): cls["buyin"] += 1
        elif grp != "EQT": cls["pay dışı"] += 1
        else:
            masked = c.endswith(".BE")  # bedelli kalan pay kodu: şirket adı/kodu maskelenir (eski kohort kasa kodlarıyla çakışabilir)
            new_eq.append((d, "***.BE" if masked else c, "***" if masked else r[h["BULTEN ADI"]][:25], ipos.get(c.split(".")[0], {}).get("status", "YOK")))
    seen |= codes
P("[ÖLÇTÜM] tamlık (bağımsız): pay dışı", cls["pay dışı"], "buyin", cls["buyin"], "| yeni EQT kodları:", new_eq)
P("[ÖLÇTÜM] yeni EQT kodlarından ipos.csv'de olmayan ticker:", [x for x in new_eq if x[3] == "YOK"])
# ---- SPK nesne kimliği zamanı (§3.2.3)
for p in sorted(glob.glob(str(ROOT / "registry/source_docs/*/MANIFEST.json"))):
    m = json.load(open(p)); docs = m["documents"] if isinstance(m.get("documents"), list) else list(m["documents"].values())
    for d in docs:
        if d["kind"] == "SPK_BULLETIN":
            oid = d["url"].split("/data/")[1].split("/")[0]; ts = datetime.fromtimestamp(int(oid[:8], 16), tz=timezone.utc).astimezone(IST).isoformat()
            P(f"[ÖLÇTÜM] SPK {Path(p).parent.name} {d['document_id']}: ObjectId zamanı={ts} published_at={d['published_at']} eşit={ts == d['published_at']} basis={d.get('published_at_basis')} printed={d.get('printed_date')} last_mod={d.get('http_last_modified')}")
        if d["kind"] == "KAP_ATTACHMENT_PDF":
            P(f"[ÖLÇTÜM] KAP ek {Path(p).parent.name} {d['document_id']}: %PDF ile başlıyor={Path(ROOT / d['path']).read_bytes()[:5] == b'%PDF-'} download_sha≠sha={d.get('download_sha256') != d['sha256']} transform={d.get('download_transform')}")
Path(__file__).with_suffix(".out.txt").write_text("\n".join(out) + "\n", encoding="utf-8"); print("\n".join(out))

"""KITAP_AUDIT_1 Adım 2 (f6) ve Adım 3 (nokta-zamanı): f6'yı Takvim B + pinli XU100'den sıfırdan; model JSON'undaki eğitim f6'larıyla ve
canlı kayıtların market20 bloklarıyla karşılaştır. TÜFE T−2 ayının yayımı T'den önce mi (99 + 7). borsai import edilmez."""
import bisect, csv, json, glob
from collections import Counter
from datetime import date
from decimal import Decimal, Context, ROUND_HALF_EVEN, localcontext
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]; RAW = ROOT / "data/raw"
def rd(p, enc="utf-8-sig"):
    with open(p, encoding=enc, newline="") as fh: return list(csv.DictReader(fh))
out = []; P = lambda *a: out.append(" ".join(str(x) for x in a))
master = {r["ticker"]: r["first_trading_date"] for r in rd(RAW / "HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv")}
calB = [r["calendar_date"] for r in rd(RAW / "v2_market20_official_pay_calendar_evidence_r4.csv", "utf-8") if r["counts_as_official_session"] == "YES"]
calA = [r["calendar_date"] for r in rd(RAW / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_pay_session_calendar.csv") if r["counts_as_official_session"] == "TRUE"]
ext = [r["calendar_date"] for r in rd(RAW / "pay_calendar_b_extension_20260820_20261231.csv", "utf-8") if r["counts_as_official_session"] == "YES"]
xu_old = {r["hisTs"]: r["clval"] for r in json.loads((RAW / "official_bist_xu100_graphic_pinned_through_20260819.json").read_text(), parse_float=Decimal)["data"]}
xu_new = {r["hisTs"]: r["clval"] for r in json.loads((RAW / "xu100/xu100_graphic_20260922.json").read_text(), parse_float=Decimal)["data"]}
CTX = Context(prec=60, rounding=ROUND_HALF_EVEN)
def f6(ref, sessions, xu):
    i = bisect.bisect_left(sessions, ref) - 1
    if i < 20: return None, "INSUFFICIENT_HISTORY", None, None
    s0, s20 = sessions[i], sessions[i - 20]
    vis = {d: v for d, v in xu.items() if d < ref}
    if s0 not in vis or s20 not in vis: return None, "XU100_CLOSE_MISSING", s0, s20
    if (date.fromisoformat(ref) - date.fromisoformat(s0)).days > 12: return None, "STALE_S0", s0, s20
    with localcontext(CTX): return vis[s0] / vis[s20] - 1, None, s0, s20
m20 = json.load(open(ROOT / "models/v1_5_market20_v0.json"))["market20_training"]
mism = []; vals = []; gaps = Counter(); s20min = "9999"
for t, T in master.items():
    v, ref, s0, s20 = f6(T, calB, xu_old)
    rec = m20[t]
    if ref or Decimal(rec["f6"]) != v or rec["S0_date"] != s0 or rec["S20_date"] != s20 or Decimal(rec["close_S0"]) != xu_old[s0]: mism.append((t, ref, str(v)[:10], rec["f6"][:10]))
    vals.append(v); gaps[(date.fromisoformat(T) - date.fromisoformat(s0)).days] += 1; s20min = min(s20min, s20)
    if not s0 < T: mism.append((t, "S0>=T"))
vals.sort()
P("[ÖLÇTÜM] f6 (Takvim B, eski XU100) 99 arz: model JSON market20_training ile uyuşmazlık:", len(mism), mism[:5], "| n JSON:", len(m20))
P("[ÖLÇTÜM] f6 min/medyan/maks:", f"{vals[0]:.4f} / {vals[49]:.4f} / {vals[-1]:.4f}", "| T−S0 gün dağılımı:", dict(sorted(gaps.items())), "| en erken S20:", s20min)
refA = [(t, f6(T, calA, xu_old)[1]) for t, T in master.items() if f6(T, calA, xu_old)[1]]
P("[ÖLÇTÜM] aynı hesap Takvim A ile ret:", refA)
P("[ÖLÇTÜM] model JSON calendar_sha256 tek değer:", {r["calendar_sha256"][:8] for r in m20.values()}, "| xu100_sha256:", {r.get("xu100_sha256", "")[:8] for r in m20.values()})
# canlı kayıtlar
live = calB + ext
def find(o, key):
    if isinstance(o, dict):
        if key in o: return o
        for v in o.values():
            r = find(v, key)
            if r: return r
    elif isinstance(o, list):
        for v in o:
            r = find(v, key)
            if r: return r
for p in sorted(glob.glob(str(ROOT / "registry/records/*/*.json"))):
    r = json.load(open(p)); t = Path(p).parent.name
    blk = find(r, "S0_date"); T = find(r, "first_trading_date")
    Tval = T["first_trading_date"]["value"] if isinstance(T.get("first_trading_date"), dict) else T["first_trading_date"]
    v, ref, s0, s20 = f6(blk["ref_date"], live, xu_new)
    tu = find(r, "tufe_month") or find(r, "release_date")
    P(f"[ÖLÇTÜM] canlı {t}: T={Tval} ref_date={blk['ref_date']} rule={blk.get('ref_date_rule')} S0={blk['S0_date']} S20={blk['S20_date']} "
      f"f6 kayıt={str(blk['f6'])[:12]} hesap={str(v)[:12]} eşit={Decimal(blk['f6']) == v} S0<ref≤T={blk['S0_date'] < blk['ref_date'] <= Tval} "
      f"xu_sha={blk.get('xu100_sha256','')[:8]} cal_sha={str(blk.get('calendar_sha256',''))[:8]}…{str(blk.get('calendar_sha256',''))[-8:]} tufe={json.dumps(tu, ensure_ascii=False)[:120] if tu else None} recorded_at={r.get('recorded_at')}")
# TÜFE PIT
tufe = {r["month"]: r for r in rd(RAW / "tuik/tufe_genel_2025_100.csv", "utf-8")}
def month_for(T):
    y, m = int(T[:4]), int(T[5:7]) - 2
    if m <= 0: y, m = y - 1, m + 12
    return f"{y:04d}-{m:02d}"
allT = dict(master)
for p in glob.glob(str(ROOT / "registry/inputs/*.json")):
    d = json.load(open(p)); allT[d["ticker"]] = d["fields"]["first_trading_date"]["value"]
tt2 = rd(ROOT / "data/training_table_v2.csv")
for r in tt2:
    if r["cohort"] == "OOT_OPEN": allT[r["ticker"]] = r["first_trading_date"]
margins = []; notpit = []
for t, T in allT.items():
    m = month_for(T); rel = tufe[m]["release_date"]
    d = (date.fromisoformat(T) - date.fromisoformat(rel)).days; margins.append(d)
    if not rel < T: notpit.append((t, T, m, rel))
P("[ÖLÇTÜM] TÜFE PIT: n =", len(allT), "(H99 99 + canlı 7 + OOT açık", len(allT) - 106, ") | release(T−2) ≥ T olan:", notpit, "| T − yayım gün min/maks:", min(margins), max(margins))
# T'nin günü 1–4 olan arzlar: T−1 ayının 3'ünde yayımlanan T−2 endeksi yine önce mi (sınır durumu)
early = [(t, T, tufe[month_for(T)]["release_date"]) for t, T in allT.items() if int(T[8:10]) <= 4]
P("[ÖLÇTÜM] T ayın 1–4'ünde olan arzlar ve T−2 yayım günü:", early)
# T−1 ayı kullanılsaydı PIT ihlali olur muydu? (kuralın gerekçesi)
viol1 = sum(not tufe.get(month_for(T)[:0] + (lambda y, m: f"{y + (m - 1) // 12:04d}-{(m - 1) % 12 + 1:02d}")(int(T[:4]), int(T[5:7]) - 1), {}).get("release_date", "9999") < T for t, T in allT.items() if int(T[5:7]) >= 2)
P("[ÖLÇTÜM] T−1 ayı kullanılsaydı yayımı T'den önce OLMAYAN arz sayısı (kural gerekçesi):", viol1)
# 79 UNKNOWN etkisi: PASS vs UNKNOWN etiket oranları (betimsel)
tt = rd(ROOT / "data/training_table.csv")
for s in ("PASS", "UNKNOWN"):
    rows = [r for r in tt if r["point_in_time_status"] == s]
    P(f"[ÖLÇTÜM] PIT {s}: n={len(rows)} D1 tavan oranı={sum(r['ceiling_close_D1']=='1' for r in rows)/len(rows):.2f} L≥3 oranı={sum(int(r['ceiling_streak_L'])>=3 for r in rows)/len(rows):.2f} Y_D10 oranı={sum(r['Y_D10']=='1' for r in rows)/len(rows):.2f} ftd aralığı={min(r['first_trading_date'] for r in rows)}…{max(r['first_trading_date'] for r in rows)}")
docs = (ROOT / "docs/DATA.md").read_text() + (ROOT / "docs/specs/SPEC_SCORING.md").read_text()
P("[ÖLÇTÜM] DATA.md 'UNKNOWN = 79' açıkça yazıyor:", "UNKNOWN` = 79" in docs or "UNKNOWN = 79" in docs, "| 'point-in-time kanıtı yok' ifadesi:", "point-in-time kanıtı yok" in docs)
Path(__file__).with_suffix(".out.txt").write_text("\n".join(out) + "\n", encoding="utf-8"); print("\n".join(out))

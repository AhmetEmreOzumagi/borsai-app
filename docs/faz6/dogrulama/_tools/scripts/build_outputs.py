"""verified/ çıktılarını kurar: registry/oot/inputs/<T>.json, candidate_features/<T>.json, source_docs/<T>/ (+MANIFEST.json).

Kullanım: python3 build_outputs.py [T ...]    (argümansız: karar dosyası olan bütün tickerlar)
Her ticker için kayıt satırları W/build_log/<T>.json'a (verification_log ve coverage için) yazılır.
"""
import datetime as dt
import json
import re
import shutil
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from blib import EV, N, W, bb_dates, codex_all, dec, fulltext, iso, methods, parse_listing, tick, tr_num  # noqa: E402

OUT = Path.home() / "Desktop/BorsAi_codex/verified"
REG = OUT / "registry/oot"
SPK = json.loads((W / "spk_final.json").read_text())
SPKR = json.loads((W / "spk_rows.json").read_text())
MANUAL = json.loads((W / "manual.json").read_text()) if (W / "manual.json").exists() else {}
CX = codex_all()
LOG = W / "build_log"
LOG.mkdir(exist_ok=True)

V15 = ["ipo_price_tl", "shares_offered", "post_ipo_share_capital", "capital_increase_shares", "existing_share_sale_shares",
       "total_demand_multiple", "total_demand_filter_status", "additional_sale_shares", "ipo_size_tl"]
PB = ["ipo_price_try", "planned_pre_ipo_capital", "planned_post_ipo_capital", "planned_capital_increase_shares",
      "planned_existing_share_sale", "planned_base_offer_shares", "planned_additional_sale_ceiling", "planned_max_offer_shares"]
DATES = ["first_trading_date", "bookbuilding_start", "bookbuilding_end"]
CAND = ["investor_count", "investor_count_by_group", "retail_demand_multiple", "domestic_institutional_demand_multiple",
        "foreign_institutional_demand_multiple", "distributed_by_group", "retail_allocation_pct",
        "domestic_institutional_allocation_pct", "foreign_institutional_allocation_pct", "distribution_method", "lead_broker",
        "price_stability_planned", "price_stability_days", "issuer_lockup_days", "shareholder_lockup_days", "sector",
        "participation_index_eligible", "market", "sale_method"]
COLLECTION_RULES = [
    "Yalnız resmi belgeler: KAP bildirimleri (Borsa İstanbul, aracı kurum, şirket) ve SPK haftalık bülteni; hepsi ilk işlem gününden (İstanbul) önce yayımlanmış. Belgeler resmi URL'den yeniden indirildi, sha256 ile pinlendi.",
    "Değerler belgedeki yazımdan: binlik noktalar atıldı, ondalık virgül noktaya çevrildi; başka dönüşüm yok ('milyon' yazımı açılırsa alanda unit_expansion notu var).",
    "Belgede olmayan alan boş (null) ve missing_reason ile; tahmin, türetme, ikincil kaynak yok. Tek istisna: aynı belgede iki nominal (toplam talep ve arz edilen) yazılıysa talep katı oran olarak hesaplandı (origin CALCULATED_FROM_SOURCE_TOTALS, derived: true, formül alanda).",
    "PB alanları (planned_*, ipo_price_try) H99 PB tablosuyla aynı tanımla SPK bülteni A.1 'İlk Halka Arzlar' tablosundan; planned_base_offer_shares = Bedelli + Mevcut Pay Satışı, planned_max_offer_shares = taban + Ek Pay Satışı ('-' = 0). SPK bülteninin yayın anı: bültenin basılı tarihi (2022 site göçü nedeniyle URL ObjectId zamanı kullanılamaz), gün sonu üst sınırı olarak yazıldı.",
    "Sermaye ayrımı sonuç belgesinde yazmıyorsa DATA_NOTES §2 kuralıyla planlanan ayrım taşındı (PLANNED_SPLIT_CARRIED_FULL_SUBSCRIPTION; koşullar alanda).",
    "Codex (+ GPT-6 Astra) çıkardı, Claude (verifier) doğruladı: her alanın provenance etiketi CODEX_VERIFIED | CODEX_CORRECTED | FILLED_BY_CLAUDE_VERIFIER.",
    "Gerçekleşen sonuç (fiyat, getiri, tavan) okunmadı ve yazılmadı; THB/THM indirilmedi.",
]


class Ctx:
    def __init__(self, t):
        self.t = t
        self.sources = {}   # sid -> meta
        self.files = {}     # sid -> (src path, dest name)
        self.log = []

    def add_kap(self, doc, att=None):
        if att is None:
            sid = f"KAP_{doc['id']}"
            name = f"KAP_{doc['id']}_bildirim.pdf"
            path, sha, url, acc = doc["pdf"], doc["pdf_sha256"], f"https://www.kap.org.tr/tr/api/BildirimPdf/{doc['id']}", doc["pdf_accessed_utc"]
            kind, did = "KAP_NOTIFICATION_PDF", f"KAP {doc['id']}"
        else:
            sid = f"KAP_{doc['id']}_EK{att['n']}"
            name = f"KAP_{doc['id']}_ek{att['n']}.pdf"
            path, sha, url, acc = att["path"], att["sha256"], att["url"], att["accessed_utc"]
            kind, did = "KAP_ATTACHMENT_PDF", f"KAP {doc['id']} ek {att['n']}"
        if sid not in self.sources:
            self.sources[sid] = {"kind": kind, "document_id": did, "published_at": doc["published_at"],
                                 "sha256": sha, "path": f"registry/oot/source_docs/{self.t}/{name}",
                                 "_url": url, "_accessed_utc": acc, "_published_at_basis": doc.get("published_at_basis", "KAP_PAGE"),
                                 "_kap_title": doc.get("kap_title"), "_subject": doc.get("subject"),
                                 "_text_method": ",".join(methods(path)), "_attachment_name": (att or {}).get("name"),
                                 "_raw_java_sha256": (att or {}).get("raw_sha256")}
            self.files[sid] = (path, name)
        return sid

    def add_spk(self):
        s = SPK[self.t]
        r = SPKR[self.t]
        no = r.get("no")
        if not no or "date" not in r:  # GENIL/BVSAN: spk_rows hata kaydı
            a1 = json.loads((W / "spk_a1.json").read_text())
            no, date = a1[s["file"]]["no"], a1[s["file"]]["date"]
            url = a1[s["file"]]["url"]
        else:
            date, url = r["date"], r["url"]
        y, n = no.split("/")
        sid = f"SPK_BULTEN_{y}_{n}"
        name = f"SPK_BULTEN_{y}-{n}.pdf"
        if sid not in self.sources:
            meta = json.loads(Path(s["file"] + ".meta.json").read_text())
            self.sources[sid] = {"kind": "SPK_BULLETIN", "document_id": f"SPK Bülteni {no}",
                                 "published_at": f"{date}T23:59:59+03:00", "sha256": s["sha256"],
                                 "path": f"registry/oot/source_docs/{self.t}/{name}",
                                 "_url": url, "_accessed_utc": meta["accessed_utc"],
                                 "_published_at_basis": "SPK_BULTEN_BASILI_TARIH_GUN_SONU_UST_SINIR",
                                 "_bulletin_date": date, "_text_method": ",".join(methods(s["file"]))}
            self.files[sid] = (s["file"], name)
        return sid


def rec(ctx, sid, value, quote=None, **extra):
    src = ctx.sources[sid]
    r = {"value": value, "source_id": sid, "source_document": src["document_id"], "source_published_at": src["published_at"],
         "source_sha256": src["sha256"], "source_path": src["path"]}
    if quote is not None:
        r["quote"] = quote
    r.update({k: v for k, v in extra.items() if v is not None})
    return r


def missing(reason, **extra):
    r = {"value": None, "missing_reason": reason}
    r.update({k: v for k, v in extra.items() if v is not None})
    return r


def cx_value(t, name):
    f = CX[t]["fields"].get(name)
    if name == "first_trading_date":
        return CX[t]["first_trading_date"], "OK"
    if f is None:
        return None, None
    v = f.get("value")
    if v in ("BULUNAMADI", "", None) or f.get("status") == "BULUNAMADI":
        return None, f.get("status")
    return v, f.get("status")


def same(a, b):
    if a is None or b is None:
        return False
    if isinstance(a, dict) or isinstance(b, dict):
        return False
    sa, sb = str(a).strip(), str(b).strip()
    if sa.lower() in ("true", "false") or sb.lower() in ("true", "false"):
        return sa.lower() == sb.lower()
    da, db = dec(sa), dec(sb)
    if da is not None and db is not None:
        return da == db
    na = re.sub(r"[\s\-–—]+", "-", sa.replace(",", ".")).lower()
    nb = re.sub(r"[\s\-–—]+", "-", sb.replace(",", ".")).lower()
    return na == nb


def provenance(t, name, field, codex_name=None):
    cv, cst = cx_value(t, codex_name or name)
    v = field.get("value")
    if v is None:
        if cv is not None:
            field["provenance"] = "CODEX_UNVERIFIABLE"
            field["codex_value"] = cv
            field["codex_status"] = cst
            return "UNVERIFIABLE"
        field["provenance"] = "MISSING"
        return "MISSING"
    if cv is None:
        field["provenance"] = "FILLED_BY_CLAUDE_VERIFIER"
        field["filled_by"] = "CLAUDE_VERIFIER"
        return "FILLED"
    if same(v, cv):
        field["provenance"] = "CODEX_VERIFIED"
        if cst == "PARTIAL":
            field["codex_status"] = "PARTIAL"
        return "VERIFIED"
    field["provenance"] = "CODEX_CORRECTED"
    field["codex_value"] = cv
    dv, dcx = dec(v), dec(cv)
    if dv is not None and dcx is not None and dcx.as_tuple().exponent < 0:
        from decimal import ROUND_HALF_UP
        if dv.quantize(Decimal(1).scaleb(dcx.as_tuple().exponent), rounding=ROUND_HALF_UP) == dcx:
            field["correction_kind"] = "PRECISION_ONLY"
            return "CORRECTED_PRECISION"
    field["correction_kind"] = "VALUE"
    return "CORRECTED"


def build(t):
    ev = EV[t]
    d = tick(t)
    dec_p = W / "decisions" / f"{t}.json"
    D = json.loads(dec_p.read_text()) if dec_p.exists() else {"fields": {}, "codex_check": {}}
    DF = D["fields"]
    man = MANUAL.get(t, {})
    ctx = Ctx(t)
    docs = {f"KAP_{x['id']}": x for x in d["docs"]}
    att_of = {}
    for x in d["docs"]:
        for a in x["attachments"]:
            att_of[f"KAP_{x['id']}_EK{a['n']}"] = (x, a)

    def use(sid):
        if sid in docs:
            return ctx.add_kap(docs[sid])
        if sid in att_of:
            return ctx.add_kap(*att_of[sid])
        if sid == "SPK":
            return ctx.add_spk()
        raise KeyError(sid)

    fields = {}
    notes = []

    def manual_field(r):
        if r.get("value") is None:
            return missing(r["missing_reason"], **{k: v for k, v in r.items() if k not in ("value", "missing_reason")})
        sid = use(r["source_id"])
        return rec(ctx, sid, r["value"], r.get("quote"), **{k: v for k, v in r.items() if k not in ("value", "source_id", "quote")})

    L = [x for x in d["docs"] if x["role"] == "LISTING"][0]
    lsid = ctx.add_kap(L)
    lp = parse_listing(fulltext(L["pdf"]))
    # ---- tarihler
    ftd = iso(lp["ftd"])
    if ftd == ev["first_trading_date"]:
        fields["first_trading_date"] = rec(ctx, lsid, ftd, lp["ftd_quote"])
    else:
        ltxt = N(fulltext(L["pdf"]))
        m = re.search(r"(\d{2}/\d{2}/\d{4}) tarihinden itibaren", ltxt)
        assert m and iso(m.group(1)) == ev["first_trading_date"], (t, ftd, ev["first_trading_date"])
        ftd = iso(m.group(1))
        fields["first_trading_date"] = rec(ctx, lsid, ftd, m.group(0),
                                           locator=f"yapılandırılmış alanda yazım hatası ('{lp['ftd_quote']}'); açıklama metnindeki tarih kullanıldı (KAP evren listesiyle aynı)")
        notes.append(f"BIST bildiriminin 'İşlem Görmeye Başlayacağı Tarih' alanı {lp['ftd']} (yazım hatası); açıklama metni {m.group(1)}")
    b0, b1 = bb_dates(lp["arz_tarihi"], ftd)
    fields["bookbuilding_start"] = rec(ctx, lsid, b0, lp["arz_tarihi_quote"])
    fields["bookbuilding_end"] = rec(ctx, lsid, b1, lp["arz_tarihi_quote"])
    # ---- listeleme alanları
    fields["ipo_price_tl"] = rec(ctx, lsid, tr_num(lp["baz"]), lp["baz_quote"],
                                 locator="BIST 'Payların İşlem Görmeye Başlaması' bildirimi Baz Fiyat alanı (arz fiyatı; 135/135 SPK tablosuyla çapraz denetlendi)")
    fields["shares_offered"] = rec(ctx, lsid, tr_num(lp["nominal"]), lp["nominal_quote"],
                                   locator="BIST bildirimi 'İşlem Görecek Payların Nominal Tutarı' = halka arz edilen (satılan) nominal")
    sermaye = lp["sermaye"]
    if sermaye and "milyon" in sermaye:
        val = str(int(Decimal(tr_num(sermaye.replace(" milyon", ""))) * 1_000_000))
        fields["post_ipo_share_capital"] = rec(ctx, lsid, val, lp["sermaye_quote"], unit_expansion=f"'{sermaye}' = {val}")
    elif sermaye:
        fields["post_ipo_share_capital"] = rec(ctx, lsid, tr_num(sermaye), lp["sermaye_quote"])
    else:
        fields["post_ipo_share_capital"] = missing("BIST bildiriminde sermaye cümlesi ayrıştırılamadı")
    # ---- SPK satırı (PB)
    spk_sid = ctx.add_spk()
    cols = SPK[t]["cols"]
    q = SPK[t]["quote"]
    loc = "SPK bülteni A.1 'İlk Halka Arzlar' tablosu satırı: Mevcut Sermaye, Yeni Sermaye, Bedelli, Bedelsiz, Mevcut Pay Satışı, Ek Pay Satışı, Satış Fiyatı"
    bdate = ctx.sources[spk_sid]["_bulletin_date"]
    pit_pb = bdate < b0

    def z(v):
        return "0" if v in ("-", "–", "—") else (tr_num(v) if v is not None else None)

    pb = {}
    price = cols["satis_fiyati"]
    price_v = tr_num(price) if re.fullmatch(r"[\d.,]+", price or "") else (price.replace(",", ".") if price else None)
    if re.fullmatch(r"\d+\.\d+", price or "") and not re.fullmatch(r"\d{1,3}(\.\d{3})+", price):
        price_v = price  # '3.52' gibi noktalı ondalık yazım
    pb["ipo_price_try"] = (price_v, "Satış Fiyatı", {"pb_semantics": "SPK_APPROVED_PLANNED_IPO_PRICE"})
    pb["planned_pre_ipo_capital"] = (z(cols["mevcut_sermaye"]), "Mevcut Sermaye", {})
    pb["planned_post_ipo_capital"] = (z(cols["yeni_sermaye"]) if cols["yeni_sermaye"] not in ("-",) else None, "Yeni Sermaye", {})
    pb["planned_capital_increase_shares"] = (z(cols["bedelli"]), "Bedelli", {})
    pb["planned_existing_share_sale"] = (z(cols["mevcut_pay_satisi"]), "Mevcut Pay Satışı; '-' = 0", {})
    ek = cols["ek_pay_satisi"]
    pb["planned_additional_sale_ceiling"] = (z(ek) if ek is not None else None,
                                             "Ek Pay Satışı; '-' = 0: SPK_TABLE_EXPLICIT_DASH__NO_PLANNED_ADDITIONAL_SALE" if ek in ("-",) else "Ek Pay Satışı", {})
    for name, (v, col, extra) in pb.items():
        if name in man:
            fields[name] = manual_field(man[name]["record"])
            continue
        if v is None or (name == "planned_post_ipo_capital" and not re.fullmatch(r"\d+(\.\d+)?", v or "")):
            reason = {"planned_post_ipo_capital": f"SPK tablosunda Yeni Sermaye hücresi '{cols['yeni_sermaye']}' (sayı değil)",
                      "planned_additional_sale_ceiling": "SPK tablosunda Ek Pay Satışı hücresi boş (tire yok); açık resmi beyan bulunmadı"}.get(name, f"SPK tablosunda {col} okunamadı")
            fields[name] = missing(reason, checked_sources=[spk_sid])
            continue
        fields[name] = rec(ctx, spk_sid, v, q, locator=f"{loc} ({col})", **extra)
    # SPK hücresi boşsa onaylı TSSD beyanı (H99 BESTE emsali: izahnamedeki "ek satış yoktur" beyanı)
    pbn = D.get("pb_notes") or {}
    st = pbn.get("additional_sale_statement")
    if fields["planned_additional_sale_ceiling"].get("value") is None and st and st.get("meaning") == "NONE":
        sid = use(st["source_id"])
        body = fulltext(ctx.files[sid][0]) or ""
        pub_ok = ctx.sources[sid]["published_at"][:10] < b0
        if N(st["quote"]) in body and pub_ok:
            fields["planned_additional_sale_ceiling"] = rec(ctx, sid, "0", st["quote"], zero_from_statement=True,
                                                            locator="SPK A.1 tablosunda Ek Pay Satışı hücresi boş; talep toplamadan önce KAP'ta yayımlanan TSSD'deki açık beyan (H99 BESTE emsali: KAP_APPROVED_PROSPECTUS ... EK_SATIS_YOKTUR)",
                                                            cross_checks=[{"source_id": spk_sid, "quote": q, "note": "SPK satırı; Ek Pay Satışı hücresi boş"}])
        else:
            notes.append(f"pb_notes ek satış beyanı kullanılmadı (alıntı birebir: {N(st['quote']) in body}, yayın talep toplamadan önce: {pub_ok})")
    for name, m in man.items():
        if name in PB and "record" in m and name not in ("planned_base_offer_shares", "planned_max_offer_shares"):
            fields[name] = manual_field(m["record"])
    # taban / azami
    base = None
    if fields["planned_capital_increase_shares"].get("value") is not None and fields["planned_existing_share_sale"].get("value") is not None:
        base = Decimal(fields["planned_capital_increase_shares"]["value"]) + Decimal(fields["planned_existing_share_sale"]["value"])
        fields["planned_base_offer_shares"] = rec(ctx, spk_sid, str(base), q,
                                                  locator="H99 PB tanımı: Bedelli + Mevcut Pay Satışı (tablo toplamı ayrıca yazmaz)",
                                                  derived=True, formula="Bedelli + Mevcut Pay Satışı ('-' = 0)")
    else:
        fields["planned_base_offer_shares"] = missing("Bedelli ya da Mevcut Pay Satışı yok")
    if base is not None and fields["planned_additional_sale_ceiling"].get("value") is not None:
        mx = base + Decimal(fields["planned_additional_sale_ceiling"]["value"])
        fields["planned_max_offer_shares"] = rec(ctx, spk_sid, str(mx), q, locator="H99 PB tanımı: planned_base_offer_shares + Ek Pay Satışı",
                                                 derived=True, formula="taban + Ek Pay Satışı ('-' = 0)")
    else:
        fields["planned_max_offer_shares"] = missing("taban ya da ek satış tavanı yok")
    for name in PB:
        f = fields[name]
        if f.get("value") is not None:
            f["pit_pb"] = {"bulletin_date": bdate, "bookbuilding_start": b0, "ok": pit_pb}
    if not pit_pb:
        notes.append(f"SPK bülten tarihi {bdate} talep toplama başlangıcı {b0}'dan önce değil")
    # ---- sonuç belgesi alanları
    def from_dec(name):
        f = DF.get(name)
        if f is None or f.get("value") is None:
            return None
        sid = use(f["source_id"])
        extra = {k: v for k, v in f.items() if k not in ("value", "source_id", "quote")}
        return rec(ctx, sid, f["value"], f.get("quote"), **extra)

    f3 = from_dec("total_demand_multiple")
    if f3:
        if f3.get("origin") == "CALCULATED_FROM_SOURCE_TOTALS":
            f3["derived"] = True
            f3["formula"] = f"{f3['numerator']} / {f3['denominator']} (10 ondalık ROUND_HALF_UP)"
        fields["total_demand_multiple"] = f3
    else:
        mr = (DF.get("total_demand_multiple") or {}).get("missing_reason") or "sonuç belgesi incelenmedi"
        fields["total_demand_multiple"] = missing(mr, checked_sources=D.get("result_docs_seen"))
    fs = DF.get("total_demand_filter_status")
    if f3 and fs and fs.get("value"):
        sid = use(fs.get("source_id") or f3["source_id"])
        fields["total_demand_filter_status"] = rec(ctx, sid, fs["value"], fs.get("quote"),
                                                   locator=fs.get("note") or ("belgede 'filtre' ifadesi yok (H99 kuralı: açık ifade yoksa NOT_SPECIFIED)" if fs["value"] == "NOT_SPECIFIED" else None))
    else:
        fields["total_demand_filter_status"] = missing("f3 yok; filtre durumu uygulanamaz (H99: NOT_APPLICABLE)")
    fields["ipo_size_tl"] = from_dec("ipo_size_tl") or missing((DF.get("ipo_size_tl") or {}).get("missing_reason") or "sonuç belgesi TL tutarı yazmıyor; fiyat × pay hesaplanmadı (f1 kodda fiyat × pay'a düşer)")
    # ayrım
    so = Decimal(fields["shares_offered"]["value"])
    pce = fields["planned_capital_increase_shares"].get("value")
    pes = fields["planned_existing_share_sale"].get("value")
    pek = fields["planned_additional_sale_ceiling"].get("value")
    ci = from_dec("capital_increase_shares")
    es = from_dec("existing_share_sale_shares")
    ad = from_dec("additional_sale_shares")
    usage = DF.get("additional_sale_usage_statement") or None
    fullsale = DF.get("full_sale_statement") or None
    carry = None
    if (ci is None or es is None) and pce is not None and pes is not None:
        base_v = Decimal(pce) + Decimal(pes)
        ek_v = Decimal(pek) if pek is not None else None
        ad_v = Decimal(ad["value"]) if ad else None
        cond_b = so == base_v
        cond_b_ek = ek_v is not None and ek_v > 0 and so == base_v + ek_v
        cond_c = (ek_v == 0) or (usage and usage.get("used") == "NONE") or (ad_v == 0)
        cond_a_src = fullsale if fullsale else {"source_id": lsid, "quote": lp["nominal_quote"]}
        if cond_b and cond_c:
            carry = ("PLANNED_SPLIT_CARRIED_FULL_SUBSCRIPTION", {
                "a_full_sale": cond_a_src, "b_shares_offered_equals_planned_base": f"{so} = {pce} + {pes}",
                "c_no_additional_sale": "SPK Ek Pay Satışı '-'" if ek_v == 0 else (usage or {"additional_sale_shares": "0"})})
        elif ad_v is not None and ad_v > 0 and ek_v is not None and ad_v <= ek_v and so == base_v + ad_v and not ad.get("derived"):
            carry = ("PLANNED_SPLIT_CARRIED_FULL_BASE_PLUS_STATED_ADDITIONAL_SALE", {
                "a_full_sale": cond_a_src, "b_shares_offered_equals_base_plus_stated_additional": f"{so} = {pce} + {pes} + {ad_v}",
                "c_additional_sale_stated": {"source_id": ad["source_id"], "quote": ad.get("quote")}})
        elif cond_b_ek and usage and usage.get("used") == "FULL":
            carry = ("PLANNED_SPLIT_CARRIED_FULL_SUBSCRIPTION_PLUS_FULL_ADDITIONAL_SALE", {
                "a_full_sale": cond_a_src, "b_shares_offered_equals_base_plus_additional": f"{so} = {pce} + {pes} + {pek}",
                "c_additional_sale_used_in_full": usage})
    if ci is None and not carry and pce == "0":
        ci = rec(ctx, spk_sid, "0", q, locator=f"{loc} (Bedelli '-': planlanan sermaye artırımı yok; arzda yeni pay çıkarılmaz)",
                 carry_rule="SPK_BEDELLI_DASH_NO_CAPITAL_INCREASE")
    if es is None and not carry and pes == "0":
        es = rec(ctx, spk_sid, "0", q, locator=f"{loc} (Mevcut Pay Satışı '-': planlanan ortak satışı yok)",
                 carry_rule="SPK_MEVCUT_PAY_SATISI_DASH_NO_EXISTING_SALE")
    if ci is None:
        if carry:
            fields["capital_increase_shares"] = rec(ctx, spk_sid, pce, q, locator=f"{loc} (Bedelli); sonuç belgesi ayrımı yazmıyor",
                                                    carry_rule=carry[0], carry_conditions=carry[1])
        else:
            fields["capital_increase_shares"] = missing("sonuç belgesinde ayrım yok ve DATA_NOTES §2 taşıma koşulları sağlanmıyor"
                                                        + (f" (satılan {so}, planlanan taban {Decimal(pce) + Decimal(pes)}, ek tavan {pek})" if pce is not None and pes is not None else ""))
    else:
        fields["capital_increase_shares"] = ci
    if es is None:
        if carry:
            fields["existing_share_sale_shares"] = rec(ctx, spk_sid, pes, q, locator=f"{loc} (Mevcut Pay Satışı; '-' = 0); sonuç belgesi ayrımı yazmıyor",
                                                       carry_rule=carry[0], carry_conditions=carry[1])
        else:
            fields["existing_share_sale_shares"] = missing("sonuç belgesinde ayrım yok ve DATA_NOTES §2 taşıma koşulları sağlanmıyor")
    else:
        fields["existing_share_sale_shares"] = es
    if ad is not None:
        fields["additional_sale_shares"] = ad
    elif pek == "0" and so == (Decimal(pce) + Decimal(pes) if pce is not None and pes is not None else None):
        fields["additional_sale_shares"] = rec(ctx, spk_sid, "0", q, locator=f"{loc} (Ek Pay Satışı '-': onaylı ek satış yok); satılan nominal = planlanan taban")
    else:
        fields["additional_sale_shares"] = missing((DF.get("additional_sale_shares") or {}).get("missing_reason") or "ek satış kullanımı belgede yazmıyor")
    # manuel geçersiz kılmalar (belge incelemesiyle)
    for name, m in man.items():
        if name in V15 + DATES and "record" in m:
            fields[name] = manual_field(m["record"])
    # ---- çapraz denetimler
    fields["ipo_price_tl"]["cross_checks"] = [{"source_id": spk_sid, "quote": q, "note": "SPK Satış Fiyatı"}]
    # ---- köken
    stats = {}
    for name in V15 + PB + DATES:
        cname = {"total_demand_filter_status": None}.get(name, name)
        if name == "total_demand_filter_status":
            cv = (CX[t]["fields"].get("total_demand_multiple") or {})
            f = fields[name]
            if cv.get("status") == "OK" and cv.get("filter_status") and f.get("value") is not None:
                if f["value"] == cv["filter_status"]:
                    f["provenance"] = "CODEX_VERIFIED"; stats[name] = "VERIFIED"
                else:
                    f["provenance"] = "CODEX_CORRECTED"; f["codex_value"] = cv["filter_status"]; stats[name] = "CORRECTED"
            elif f.get("value") is not None:
                f["provenance"] = "FILLED_BY_CLAUDE_VERIFIER"; f["filled_by"] = "CLAUDE_VERIFIER"; stats[name] = "FILLED"
            else:
                f["provenance"] = "MISSING"; stats[name] = "MISSING"
            continue
        stats[name] = provenance(t, name, fields[name], cname)
    # ---- girdi belgesi
    doc = {"schema_version": "borsai.inputs/1", "ticker": t, "company": ev["company"], "stage": "POST_BOOKBUILD_PRE_LISTING",
           "collected_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).replace(microsecond=0).isoformat(),
           "collected_at_basis": "LOCAL_CLOCK_SELF_REPORTED", "collection_rules": COLLECTION_RULES,
           "first_trading_date_source": lsid, "cohort": "OOT_PRE_H99", "sale_method": ev["sale_method_kap"], "market": ev["market"],
           "fields": {n: fields[n] for n in V15 + PB + DATES},
           "sources": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in ctx.sources.items()}}
    if notes:
        doc["notes"] = notes
    # ---- aday özellikler
    cand = {}
    for name in CAND:
        if name == "market":
            cand[name] = rec(ctx, lsid, lp["pazar"], f"İşlem Göreceği Pazar {lp['pazar']}")
        elif name == "sale_method":
            cand[name] = rec(ctx, lsid, lp["yontem"], lp["yontem_quote"])
        else:
            f = DF.get(name)
            if f and f.get("value") is not None:
                sid = use(f["source_id"])
                cand[name] = rec(ctx, sid, f["value"], f.get("quote"), **{k: v for k, v in f.items() if k not in ("value", "source_id", "quote")})
            else:
                cand[name] = missing((f or {}).get("missing_reason") or "incelenen belgelerde yok")
        cstat = provenance(t, name, cand[name])
        cc = (D.get("codex_check") or {}).get(name)
        f = cand[name]
        if name == "sale_method":
            cv, _ = cx_value(t, name)
            if cv is not None:
                on = lambda x: "ON" if re.search(r"borsada|in the exchange|on the exchange|birincil piyasa", x, re.I) else ("OFF" if re.search(r"borsa d[ıi]ş", x, re.I) else x)
                if on(str(cv)) == on(str(f["value"])):
                    f["provenance"] = "CODEX_VERIFIED"; f.pop("codex_value", None); f.pop("correction_kind", None); cstat = "VERIFIED"
        elif cc and cc.get("verdict") in ("FOUND_SAME", "FOUND_DIFFERENT", "NOT_FOUND_IN_DOCS", "NOT_APPLICABLE") and cstat not in ("FILLED",):
            v = cc["verdict"]
            if f.get("value") is None:
                f["provenance"] = "CODEX_UNVERIFIABLE"; cstat = "UNVERIFIABLE"
            elif v == "FOUND_SAME":
                f["provenance"] = "CODEX_VERIFIED"; f.pop("correction_kind", None); cstat = "VERIFIED"
            else:
                f["provenance"] = "CODEX_CORRECTED"; f["correction_kind"] = "VALUE_OR_DEFINITION"; cstat = "CORRECTED"
            f["codex_check"] = {k: cc.get(k) for k in ("codex_value", "verdict", "note") if cc.get(k)}
        stats["cand:" + name] = cstat
    cdoc = {"schema_version": "borsai.oot_candidate_features/1", "ticker": t, "company": ev["company"],
            "note": "Aday özellikler model girdisi DEĞİLDİR (KARARLAR D7). Adlar H99 ana tablosuyla aynı.",
            "fields": cand, "sources": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in ctx.sources.items()}}
    doc["sources"] = cdoc["sources"]  # aynı kaynak tablosu (girdi + aday)
    # yalnız girdi alanlarının kullandığı kaynaklar girdi belgesinde
    used_in = {f.get("source_id") for f in doc["fields"].values()}
    for f in doc["fields"].values():
        for cc in f.get("cross_checks", []) or []:
            used_in.add(cc.get("source_id"))
    doc["sources"] = {k: v for k, v in cdoc["sources"].items() if k in used_in}
    used_c = {f.get("source_id") for f in cand.values()}
    cdoc["sources"] = {k: v for k, v in cdoc["sources"].items() if k in used_c}
    # ---- yazım
    sd = REG / "source_docs" / t
    sd.mkdir(parents=True, exist_ok=True)
    manifest = []
    for sid, (src, name) in ctx.files.items():
        if sid not in used_in and sid not in used_c:
            continue
        dst = sd / name
        shutil.copyfile(src, dst)
        m = ctx.sources[sid]
        manifest.append({"source_id": sid, "file": name, "sha256": m["sha256"], "bytes": dst.stat().st_size, "url": m["_url"],
                         "published_at": m["published_at"], "published_at_basis": m["_published_at_basis"],
                         "accessed_at_utc": m["_accessed_utc"], "kind": m["kind"], "text_layer": m["_text_method"],
                         **({"kap_title": m["_kap_title"], "subject": m["_subject"]} if m.get("_kap_title") else {}),
                         **({"attachment_name": m["_attachment_name"], "raw_java_wrapped_sha256": m["_raw_java_sha256"]} if m.get("_attachment_name") else {}),
                         **({"bulletin_date": m["_bulletin_date"]} if m.get("_bulletin_date") else {})})
    for old in sd.iterdir():
        if old.name != "MANIFEST.json" and old.name not in {x["file"] for x in manifest}:
            old.unlink()
    (sd / "MANIFEST.json").write_text(json.dumps({"ticker": t, "documents": manifest}, ensure_ascii=False, indent=1) + "\n")
    (REG / "inputs").mkdir(parents=True, exist_ok=True)
    (REG / "candidate_features").mkdir(parents=True, exist_ok=True)
    (REG / "inputs" / f"{t}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    (REG / "candidate_features" / f"{t}.json").write_text(json.dumps(cdoc, ensure_ascii=False, indent=2) + "\n")
    (LOG / f"{t}.json").write_text(json.dumps({"ticker": t, "stats": stats, "carry": carry[0] if carry else None,
                                               "decision": bool(DF), "codex_check": D.get("codex_check", {}),
                                               "needs_search": D.get("needs_search", False)}, ensure_ascii=False, indent=1))
    return stats


if __name__ == "__main__":
    import glob
    ts = sys.argv[1:] or sorted(Path(f).stem for f in glob.glob(str(W / "decisions/*.json")))
    for t in ts:
        s = build(t)
        print(t, {k: v for k, v in s.items() if not k.startswith("cand:")})

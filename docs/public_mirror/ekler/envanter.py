#!/usr/bin/env python3
"""FAZ9_PUBLIC_INVENTORY adım 1: izlenen her dosyayı sınıflar, ekler/envanter.csv ve özet tabloyu yazar.

Yalnız okur. Yol sütunu hijyen için maskelenir: kasa (SEALED) kodları `<KASA>`, bülten zip adlarındaki 8 haneli tarih `YYYYMMDD`.
Kullanım: .venv/bin/python docs/public_mirror/ekler/envanter.py [--csv ekler/envanter.csv] [--summary]
"""
import csv, os, re, subprocess, sys, collections, io

ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
os.chdir(ROOT)

# --- kasa kodları yalnız bellekte
_rows = list(csv.DictReader(open("registry/oot/cohort_pre_h99.csv", encoding="utf-8-sig")))
SEALED = {r["ticker"] for r in _rows if r["vault"] == "SEALED"}
_SEALED_RE = re.compile(r"(?<![A-Z0-9])(?:" + "|".join(re.escape(s) for s in sorted(SEALED)) + r")(?![A-Z0-9])")
_BULLETIN_RE = re.compile(r"(th[bm])\d{8}(1\.zip)$")

def mask(path: str) -> str:
    p = _SEALED_RE.sub("<KASA>", path)
    p = _BULLETIN_RE.sub(r"\1YYYYMMDD\2", p)
    return p

# --- proje sahibinin iki kararı (FAZ9_PUBLIC_INVENTORY §Kurallar)
GIRMEZ_DIRS = ("registry/oot/source_docs/", "registry/oot/source_docs_faz7/", "registry/source_docs/", "data/raw/bist/")

def classify(path: str, size: int):
    """-> (tür, kaynak sahibi, durum, not)"""
    ext = os.path.splitext(path)[1].lower()
    base = os.path.basename(path)
    # 1) GİRMEZ dizinleri (karar verildi)
    if path.startswith(GIRMEZ_DIRS):
        if ext == ".pdf":
            owner = "SPK" if base.startswith("SPK_") else "KAP-şirket"
            return ("resmi belge", owner, "GİRMEZ", "KAP/SPK PDF; karar: aynaya girmez")
        if ext == ".zip":
            return ("ham veri", "BIST", "GİRMEZ", "THB/THM bülten zip; karar: aynaya girmez")
        if path.startswith("data/raw/bist/"):
            return ("kanıt", "proje", "GİRMEZ", "bülten indirme manifesti (URL, sha256, bayt); PDF/zip içermez; GİRMEZ dizininde — soru 7")
        if path.startswith("registry/oot/source_docs_faz7/"):
            return ("kanıt", "proje", "GİRMEZ", "Faz 7 belge manifesti (JSON, PDF yok); GİRMEZ dizininde — soru 7")
        return ("kanıt", "proje", "GİRMEZ", "belge manifesti (MANIFEST/ENUMERATION JSON); GİRMEZ dizininde — soru 7")
    # 2) kök dosyalar
    if "/" not in path:
        if path in ("CLAUDE.md", "README.md"):
            return ("belge", "proje", "GİRER", "")
        return ("kod", "proje", "GİRER", "yapılandırma")
    if path.startswith(".github/"):
        return ("kod", "proje", "GİRER", "CI iş akışı")
    # 3) kod ve testler
    if path.startswith("borsai/"):
        return ("kod", "proje", "GİRER", "")
    if path.startswith("legacy/"):
        return ("kod", "proje (eski repo)", "KARAR", "eski repodan birebir kopya; 4 test dosyası import eder — soru 10")
    if path.startswith("tests/reference/"):
        return ("türev veri", "proje (H99 türevi)", "KARAR", "altın ledger/benchmark; H99 getiri değerleri içerir; testler okur — soru 1")
    if path.startswith("tests/"):
        return ("test", "proje", "GİRER", "")
    if path.startswith("app/parity/golden/"):
        return ("türev veri", "proje (KAP girdisi)", "KARAR", "altın vektörler: KAP kaynaklı girdiler + model çıktıları — soru 1")
    if path.startswith("app/parity/"):
        return ("test" if ("test" in base or path.startswith("app/parity/incidents")) else "kod", "proje", "GİRER", "")
    if path.startswith("app/src-tauri/icons/"):
        return ("görsel", "belirsiz (Tauri şablonu?)", "KARAR", "uygulama ikonu; kaynağı repoda belgelenmemiş — soru 11")
    if path.startswith(("app/src-tauri/tests/", "app/src-tauri/crates/borsai_predict/tests/", "app/tests/")):
        return ("test", "proje", "GİRER", "fixture JSON'ları gerçek skor/kayıt dosyalarından türetilmiş olabilir")
    if path.startswith("app/docs/"):
        return (("görsel" if ext == ".png" else "belge"), "proje", "GİRER", "ekran görüntüsü" if ext == ".png" else "")
    if path.startswith("app/"):
        return ("kod", "proje", "GİRER", "")
    if path.startswith("data/") and ext == ".py":
        return ("kod", "proje", "GİRER", "")
    # 4) veri
    if path.startswith("data/raw/tuik/"):
        if ext in (".xls",):
            return ("resmi belge", "TÜİK", "KARAR", "TÜİK bülten tablosu (xls) — soru 2")
        if base.endswith(".source.json"):
            return ("kanıt", "TÜİK", "KARAR", "TÜİK indirme kaynağı/pin — soru 2")
        return ("türev veri", "TÜİK", "KARAR", "TÜFE serisi (TÜİK'ten türetilmiş CSV) — soru 2")
    if path.startswith("data/raw/xu100/") or "xu100" in base:
        return ("ham veri", "XU100 kaynağı (BIST)", "KARAR", "XU100 kapanış serisi (BIST grafik uç noktası, pinli) — soru 1")
    if path.startswith("data/raw/"):
        if "OFFICIAL_BIST_OUTCOME" in base or "pay_calendar" in base or "v2_market20_official_pay_calendar" in base:
            return ("türev veri", "BIST", "KARAR", "THB/THM'den türetilmiş kanonik tablo (ham değer sütunları içerir) — soru 1")
        if "PREBOOKBUILD" in base:
            return ("türev veri", "KAP-şirket + SPK", "KARAR", "izahname/SPK bülteninden derlenen planlanan arz yapısı — soru 1")
        return ("türev veri", "KAP-şirket", "KARAR", "KAP sonuç bildirimlerinden derlenen kohort tablosu — soru 1")
    if path.startswith("data/outcomes_oot/raw/"):
        return ("ham veri", "BIST", "KARAR", "bülten satırının alan alan kopyası (thb_row/thm_row), yalnız arzın kendi satırı — soru 1")
    if path.startswith(("data/outcomes/", "data/outcomes_oot/")):
        if base == "COMPLETENESS.csv":
            return ("kanıt", "proje", "KARAR", "tamlık denetimi (bülten pay kodları listesi) — soru 1")
        return ("türev veri", "BIST", "KARAR", "arz başına seans sonuçları (close_raw, upper_limit_raw bültenden aynen) — soru 1")
    if path.startswith("data/"):
        return ("türev veri", "BIST + KAP-şirket", "KARAR", "eğitim tablosu / sürüm dosyası — soru 1")
    # 5) modeller, skorlar, deney günlüğü
    if path.startswith("models/"):
        return ("model", "proje", "GİRER", "karar: modeller aynaya girer; parametreler BIST/KAP türevi veriden öğrenildi")
    if path.startswith("scores/"):
        return ("skor", "proje", "KARAR", "arz başına gerçekleşen getiri/tavan etiketi içerir (BIST türevi) — soru 1/3")
    if path.startswith("experiments/"):
        return (("belge" if ext == ".md" else "kanıt"), "proje", ("GİRER" if ext == ".md" else "KARAR"), "" if ext == ".md" else "deney günlüğü (metrikler, sha'lar) — soru 1")
    # 6) sicil
    if path.startswith("registry/push_proofs/"):
        return ("kanıt", "proje (GitHub yanıtı)", "KARAR", "GitHub API yanıtı: kullanıcı adı, avatar, kimlik URL'leri — soru 5")
    if path.startswith(("registry/records/", "registry/oot/records/", "registry/post_break/", "registry/oot/post_d1/", "registry/legacy_frozen/")):
        return ("kanıt", "proje", "KARAR", "dondurulmuş tahmin kaydı — soru 4")
    if path.startswith(("registry/inputs/", "registry/oot/inputs/", "registry/oot/candidate_features")):
        return ("türev veri", "KAP-şirket + SPK", "KARAR", "resmi belgelerden derlenen girdi alanları ve alıntılar — soru 4")
    if path.startswith("registry/oot/d1_rows/"):
        return ("türev veri", "BIST", "KARAR", "D1 seans satırı (bültenden) — soru 1/4")
    if path.startswith("registry/"):
        return ("kanıt", "proje", "KARAR", "sicil dizini/kohort/kasa açılışı — soru 4/6")
    # 7) belgeler
    if path.startswith("docs/prompts/"):
        return ("görev dosyası", "proje", "GİRER", "")
    if path.startswith("docs/specs_faz6/ekler/spk_tablolar/"):
        return ("resmi belge", "SPK", "KARAR", "SPK yıllık ilk halka arz tabloları (xlsx) — soru 2")
    if path.startswith("docs/faz6/dogrulama/_tools/logs/"):
        return ("kanıt", "proje (SPK/KAP alıntısı)", "KARAR", "doğrulama günlükleri; SPK bülten satır metinleri ve şirket adresleri — soru 8")
    if path.startswith("docs/"):
        if ext == ".png":
            return ("görsel", "proje", "GİRER", "")
        if ext in (".md",):
            return ("belge", "proje", "GİRER", "")
        if ext == ".html":
            return ("belge", "proje (Claude Design kanvası)", "GİRER", "tasarım panosu")
        return ("kanıt", "proje", "GİRER", "denetim/rapor eki")
    return ("diğer", "belirsiz", "KARAR", "sınıflanamadı")

def main():
    out_csv = "docs/public_mirror/ekler/envanter.csv"
    paths = subprocess.run(["git", "ls-files", "-z"], capture_output=True).stdout.split(b"\0")
    rows = []
    for p in paths:
        if not p:
            continue
        path = p.decode("utf-8", "surrogateescape")
        size = os.lstat(path).st_size
        tur, sahip, durum, not_ = classify(path, size)
        rows.append({"yol": mask(path), "boyut_bayt": size, "tur": tur, "kaynak_sahibi": sahip, "durum": durum, "not": not_})
    rows.sort(key=lambda r: r["yol"])
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["yol", "boyut_bayt", "tur", "kaynak_sahibi", "durum", "not"])
        w.writeheader(); w.writerows(rows)
    # özet
    by = collections.defaultdict(lambda: [0, 0])
    tot = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        k = (r["tur"], r["durum"]); by[k][0] += 1; by[k][1] += r["boyut_bayt"]
        tot[r["durum"]][0] += 1; tot[r["durum"]][1] += r["boyut_bayt"]
    print(f"satır: {len(rows)}; toplam MB: {sum(r['boyut_bayt'] for r in rows)/1e6:.1f}")
    print("\n| Tür | Durum | Dosya | MB |\n|---|---|---:|---:|")
    for (t, d), (n, b) in sorted(by.items(), key=lambda kv: (kv[0][1], -kv[1][1])):
        print(f"| {t} | {d} | {n} | {b/1e6:.1f} |")
    print("\n| Durum | Dosya | MB |\n|---|---:|---:|")
    for d, (n, b) in sorted(tot.items()):
        print(f"| {d} | {n} | {b/1e6:.1f} |")
    # sahip dağılımı
    own = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        own[(r["kaynak_sahibi"], r["durum"])][0] += 1; own[(r["kaynak_sahibi"], r["durum"])][1] += r["boyut_bayt"]
    print("\n| Kaynak sahibi | Durum | Dosya | MB |\n|---|---|---:|---:|")
    for (o, d), (n, b) in sorted(own.items(), key=lambda kv: (kv[0][1], -kv[1][1])):
        print(f"| {o} | {d} | {n} | {b/1e6:.1f} |")
    # KARAR grupları (üst yol)
    grp = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r["durum"] == "KARAR":
            parts = r["yol"].split("/")
            key = "/".join(parts[:3]) if parts[0] in ("registry", "data") and len(parts) > 3 else "/".join(parts[:2])
            key = re.sub(r"/<KASA>$", "/<T>", key)
            grp[key][0] += 1; grp[key][1] += r["boyut_bayt"]
    print("\n| KARAR grubu | Dosya | MB |\n|---|---:|---:|")
    for k, (n, b) in sorted(grp.items(), key=lambda kv: -kv[1][1]):
        print(f"| `{k}` | {n} | {b/1e6:.2f} |")
    # hijyen
    txt = open(out_csv, encoding="utf-8").read()
    print("\nhijyen (csv): kasa kodu", len(_SEALED_RE.findall(txt)), "; th[bm]+8 hane", len(re.findall(r"th[bm]\d{8}", txt)))
    print("GİRER tek dosya > 50 MB:", [r["yol"] for r in rows if r["durum"] != "GİRMEZ" and r["boyut_bayt"] > 50e6])
    print("en büyük 5 (GİRMEZ dışı):", [(r["yol"], round(r["boyut_bayt"]/1e6, 1)) for r in sorted(rows, key=lambda r: -r["boyut_bayt"]) if r["durum"] != "GİRMEZ"][:5])

if __name__ == "__main__":
    main()

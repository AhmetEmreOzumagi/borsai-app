"""shareholder_lockup_days: kapsanan (dominated) bileşen kuralı.
Değer = herhangi bir mevcut ortağın borsada satış kısıtının ilk gevşediği gün: aynı ortağın daha uzun ve en az o kadar
sıkı (MUTLAK >= FIYAT_ALTI) kısıtı tarafından kapsanan bileşen değeri belirlemez; kalanların en kısası alınır.
Ortak eşleştirmesi components 'who' alanlarından doğrulayıcı tarafından elle yapıldı (aşağıdaki gerekçeler).
Kullanım: python3 apply_dominance.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import T  # noqa: E402

NEW = {  # ticker: (yeni değer, gerekçe)
    "ATAKP": ("365", "tek ortak TFI Tab Gıda: MUTLAK 365 (onaydan) 20/412 MUTLAK 180'i kapsıyor"),
    "BIENY": ("365", "tek ortak Nurullah Ercan: MUTLAK 365 (işlem başlangıcından) 20/412 MUTLAK 180 ve FIYAT_ALTI 365'i kapsıyor"),
    "BVSAN": ("540", "iki ortak (Önder Bülbüloğlu, Bülbüloğlu Holding): MUTLAK 540 her birinin FIYAT_ALTI 365'ini kapsıyor"),
    "EUPWR": ("365", "her ortak: MUTLAK 365 ('dolaşımdaki payı artıracak şekilde satmama') 180 günlük hiç satmama ve 20/412 180'i kapsıyor; FIYAT_ALTI 365 de kapsanıyor"),
    "FORTE": ("730", "üç ortak: MUTLAK 730 her birinin FIYAT_ALTI 365'ini ve 20/412 MUTLAK 180'i kapsıyor"),
    "FZLGY": ("365", "dört ortak: MUTLAK 365 her birinin FIYAT_ALTI 365 ve 20/412 MUTLAK 180'ini kapsıyor"),
    "GENIL": ("730", "beş ortak MUTLAK 730; FIYAT_ALTI 365 (Abidin Gülmüş, Absel) kapsanıyor"),
    "IZENR": ("365", "beş ortak: MUTLAK 365 20/412 MUTLAK 180'i kapsıyor"),
    "KZGYO": ("365", "tek ortak Kuzu Toplu Konut: MUTLAK 365 MUTLAK 180'i kapsıyor"),
    "OFSYM": ("365", "bütün ortaklar: MUTLAK 365 MUTLAK 180'i kapsıyor"),
    "ONCSM": ("540", "üç ortak: MUTLAK 540 her birinin FIYAT_ALTI 365'ini kapsıyor"),
    "PLTUR": ("540", "aynı ortaklar: MUTLAK 540 (18 ay) FIYAT_ALTI 365'i kapsıyor"),
    "REEDR": ("365", "yedi ortak: MUTLAK 365 (b) 20/412 MUTLAK 180 ve FIYAT_ALTI 365'i kapsıyor"),
    "SDTTR": ("450", "iki ortak (Mehmet Dora, Mustafa Fatih Ünal): MUTLAK 450 (15 ay) FIYAT_ALTI 365'i kapsıyor"),
    "TATEN": ("365", "beş ortak: MUTLAK 365 20/412 MUTLAK 180'i kapsıyor"),
}
SAME = {"360": "365", "365": "365"}


def main():
    log = open(T / "logs" / "verifier_interventions.jsonl", "a", encoding="utf-8")
    for t, (nv, why) in NEW.items():
        p = T / "decisions" / f"{t}.json"
        d = json.loads(p.read_text())
        f = d["fields"]["shareholder_lockup_days"]
        old = f["value"]
        if old == nv:
            continue
        f["value"] = nv
        f["note"] = (f.get("note") or "") + (f" [kapsanan bileşen kuralı (doğrulayıcı): {old} -> {nv}; {why}. Değer = herhangi bir "
                                             "ortağın borsada satış kısıtının ilk gevşediği gün.]")
        cc = (d.get("codex_check") or {}).get("shareholder_lockup_days")
        if cc:
            cv = str(cc.get("codex_value"))
            same = cv == nv or SAME.get(cv) == nv
            cc["verdict"] = "FOUND_SAME" if same else "FOUND_DIFFERENT"
            cc["note"] = (cc.get("note") or "") + f" [kapsanan bileşen kuralı sonrası değer {nv}; Codex {cv} -> {cc['verdict']}]"
        p.write_text(json.dumps(d, ensure_ascii=False, indent=1))
        log.write(json.dumps({"ticker": t, "field": "shareholder_lockup_days",
                              "action": f"kapsanan bileşen kuralı: {old} -> {nv} ({why})", "value_changed": True},
                             ensure_ascii=False) + "\n")
        print(t, old, "->", nv, "codex:", cc and cc["verdict"])


if __name__ == "__main__":
    main()

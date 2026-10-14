"""Karar dosyalarında kural dışı türetmeleri boşaltır (idempotent). Yalnız iki nominalin oranı (f3) türetilebilir;
SPK tablosundaki '-' (planlanmamış ek satış) nedeniyle 0 yazılan ek satış korunur."""
import json, glob, sys
FIELDS = ("capital_increase_shares", "existing_share_sale_shares", "additional_sale_shares", "ipo_size_tl")
changed = []
for f in sorted(glob.glob('decisions/*.json')):
    d = json.load(open(f)); t = d['ticker']; mod = False
    for n in FIELDS:
        v = d['fields'].get(n)
        if not isinstance(v, dict) or v.get('value') is None or not v.get('derived'):
            continue
        if n == 'additional_sale_shares' and v['value'] == '0' and "'-'" in (v.get('formula') or ''):
            continue  # SPK '-' = planlanmış ek satış yok (H99/CITAS kuralı)
        d['fields'][n] = {"value": None,
                          "missing_reason": f"belgede tek sayı olarak yazılı değil; türetme ({v.get('formula')}) görev kuralı gereği kullanılmadı",
                          "derived_candidate": {k: v.get(k) for k in ('value', 'source_id', 'quote', 'formula', 'note') if v.get(k) is not None}}
        mod = True; changed.append((t, n, v['value']))
    if t == 'ULUFA':
        v = d['fields'].get('existing_share_sale_shares')
        if v and v.get('value') == '15000000':
            d['fields']['existing_share_sale_shares'] = {"value": None,
                "missing_reason": "belgedeki 15.000.000 ortak satışı ek satışı (7.500.000) içeriyor; H99 tanımında existing_share_sale_shares ek satış hariçtir (DATA_NOTES §4); ek satış hariç tutar belgede ayrı yazılmıyor",
                "derived_candidate": {k: v.get(k) for k in ('value', 'source_id', 'quote') if v.get(k) is not None}}
            mod = True; changed.append((t, 'existing_share_sale_shares', '15000000'))
    if mod:
        d['notes'] = (d.get('notes') or '') + ' | Doğrulayıcı son işlemi: türetilmiş ayrım alanları boşaltıldı (postprocess.py).'
        json.dump(d, open(f, 'w'), ensure_ascii=False, indent=1)
print(changed)

# FAZ9_KITAP_AUDIT_1_VERI — Veri katmanının bağımsız denetimi

**Model: Claude Code / Fable · yüksek**

- **TASK_ID:** `BORSAI_FAZ9_KITAP_AUDIT_1_20261008`
- **Klasör:** repo kökü `~/Desktop/BorsAi`. Ağ yok.
- **Ortak kurallar:** `docs/prompts/FAZ9_KITAP_AUDIT_ORTAK.md`. Önce onu oku; orada yazanlar burada tekrarlanmaz. Bu görevde `<n>` = 1, `<AD>` = VERI.
- **Rapor:** `docs/fable_kitap_audit/AUDIT_1_VERI.md`; ekler `docs/fable_kitap_audit/ekler/1/`.

## Kapsam

- `kitap/03_veri.md`'nin tamamı.
- `kitap/01_genel_bakis.md` §1.5 (NETGL'in yolculuğu) ve §1.6 (kilit sayılar).
- `kitap/10_dosya_dizini.md`'nin `data/` ve `registry/` satırları.

Walk-forward kesim kuralı (eğitim satırının etiket tarihi < T) Denetim 3'ün konusudur; burada yalnız veri düzeyindeki nokta-zamanı denetlenir (girdiler T anında yayımlanmış mıydı?).

## ÖNCE OKU

- CLAUDE.md
- `docs/fable_kitap_audit/README.md`
- `kitap/03_veri.md`
- `docs/DATA.md`, `docs/DATA_NOTES.md`, `docs/PROVENANCE.md`
- `data/data_version.json`, `data/data_version_v2.json`
- Kod: `borsai/data.py`, `features.py`, `horizons.py`, `outcomes.py`, `outcomes_oot.py`, `provenance.py`, `tufe.py`, `market20.py`, `registry.py` (girdi alanları ve payda), `data/build_training_table.py`
- Önceki uygunluk denetimi: `docs/fable_conformity_20260922/AUDIT.md`

## Adım 0

- `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -3`: HEAD `ee3796d` ya da torunu.
- `GIT_OPTIONAL_LOCKS=0 git diff --name-only ee3796d HEAD`: boş, ya da yalnız `docs/fable_kitap_audit/` ve `docs/prompts/FAZ9_KITAP_AUDIT_` ile başlayan yollar.
- `GIT_OPTIONAL_LOCKS=0 git status --porcelain --untracked-files=all` yalnız şunları gösterir:
  - `docs/prompts/FAZ10_FABLE_STREAK_SPEC.md`
  - `docs/prompts/TUFE_2026_09.md`
  - `docs/prompts/FAZ9_KITAP_AUDIT_*.md`
  - `docs/fable_kitap_audit/` altındaki dosyalar

  Başka bir şey varsa DUR.
- Koruma ölçümü → `ekler/1/koruma_once.txt`.

## Adımlar

Sıra önem sırasıdır. Oturum uzarsa bulgular kaybolmasın diye her adım bitince raporu güncelle.

**1. Etiketleri sıfırdan üret.** 99 arzın hepsi için, yalnız ham bülten metninden (`thb_raw_*`, `thm_raw_*`) hesapla. `borsai` import edilmez.
- Her seans için tavan bayrağı. Kılavuzdaki tanım (§3.5.1), şartname ve kod aynı tanımı mı kullanıyor? Karşılaştırma Decimal ile birebir mi?
- Seri uzunluğu L (0–10), getiriler R_h (h = 1, 3, 5, 10) ve yön Y_h.
- Sonuçları `data/training_table.csv` ve `training_table_v2.csv` ile karşılaştır.
- Üst limit bültenden mi okunuyor, hesaplanıyor mu? Hesaplanıyorsa fiyat adımı yuvarlaması (§3.5.1) bütün seanslarda bültenle tutuyor mu?
- §3.5.4'teki dağılımları ve §3.5.5'teki NETGL hesabını yeniden üret.

**2. Özellikleri sıfırdan üret.** 99 arz için ham kaynaklardan:
- f1–f5;
- f6 (market20): S0 ve S20 seçimi, takvim, XU100 revizyonu;
- f1r: TÜFE'nin T − 2 ay kuralı;
- pb1–pb4 ve tahsis rejimi.

Tablolarla karşılaştır. NETGL örneklerini (§3.6.2, §3.6.3) ve H99 ölçümlerini (aralıklar, medyanlar) yeniden hesapla.

**3. Nokta-zamanı (veri düzeyi).** Bir girdi, tahmin anı T'de yayımlanmış olmayan bir bilgiyi kullanıyor mu?
- **TÜFE:** `data/raw/tuik/tufe_bultenleri.csv`'deki yayım anlarıyla, H99'un 99 arzında ve 7 canlı arzda T − 2 ayının endeksi T'de yayımlanmış mıydı?
- **f6:** S0 < T mi? XU100 dosyasının T'den sonra yayımlanmış bir revizyonu kullanılıyor mu?
- **H99'un 79 arzındaki PIT `UNKNOWN` durumu (§3.8.4):** etkisi ne, belgelerde dürüstçe yazıyor mu?

**4. Ham kaynakların bütünlüğü.**
- Kodda ve belgelerde pinlenmiş her ham dosyanın sha256'sını yeniden hesapla.
- Pinli olup eksik olan, ya da var olup pinsiz olan dosyaları listele.
- `.source.json` dosyalarındaki adres, yayım anı ve sha alanları dosyayla tutarlı mı?
- §3.12'deki pin ve sabit tablosunun her satırını koddaki sabitle karşılaştır.

**5. H99 kohortu ve takvim.**
- Seçim kuralını (§3.3.1) ham veriden yeniden uygula: 99 arz ve tarih aralığı tutuyor mu?
- MASTER, PROV, SESSIONS ve TARGETS birbiriyle tutarlı mı? Örneğin TARGETS'taki `official_close`, SESSIONS'ta D_h kapanışına eşit mi?
- D_h eşlemesi: 99 arzın her ufku için takvimden say, `target_session_date` ile karşılaştır.
- Yarım günler, tatiller ve Takvim A/B/C iddiaları (§3.4).

**6. Canlı veri, payda ve sıra kuralı.**
- **Girdiler:** `registry/inputs/`'taki her arzda 20 alan, kaynak belge sha'ları `registry/source_docs/`'taki dosyalarla tutuyor mu? Boş alanların gerekçesi var mı?
- **Payda (CLAUDE.md kural 2):** repodaki bültenlerde başlangıçtan sonra işlem görmeye başlayan her arz `registry/ipos.csv`'de var mı? Eksik arz varsa KRİTİK.
- **Canlı sonuçlar:** `data/outcomes/<T>.csv`'yi 7 arz için bültenlerden sıfırdan yeniden hesapla. `COMPLETENESS.csv`'yi denetle.
- **Sıra kuralı:** 2026-08-19 sonrası bülten ve 2026-08-06 sonrası arz sonucu getiren ilk commit, Faz 1 model JSON'larını donduran commit'in torunu mu? git DAG ile göster.
- **Eski kohort:** OOT sonuç verisini getiren commit, OOT tahmin kayıtlarının hepsinin push kanıtından sonra mı? Kasa arzlarının sonucu repoda hiçbir yerde yok mu? Yalnız sayı yaz.

**7. Ön işleme ve eğitim tabloları.**
- Kırpma kantilleri (Type-7) ve z (ddof = 0) yalnız eğitim fold'undan mı hesaplanıyor? Klonda 3 fold'da test arzının değerini değiştir; dönüşüm bit-eşit kalmalı.
- `data_version` pinleri, `build_training_table.py`'nin durma koşulları ve `load_dataset`/`load_dataset_v2` denetimleri.

**8. Kılavuzun geri kalanı.**
- §1.5 ve §1.6'daki her sayı.
- §3.13'teki açık noktalar: hâlâ açık mı?
- `kitap/10`'un `data/` ve `registry/` satırlarındaki yolların varlığı.

## Commit

```
git add docs/prompts/FAZ9_KITAP_AUDIT_ORTAK.md docs/prompts/FAZ9_KITAP_AUDIT_1_VERI.md docs/fable_kitap_audit/README.md docs/fable_kitap_audit/kitap docs/fable_kitap_audit/AUDIT_1_VERI.md docs/fable_kitap_audit/ekler/1
git commit -m "BORSAI_FAZ9_KITAP_AUDIT_1: independent audit of the data layer against the project guide" -- docs/prompts/FAZ9_KITAP_AUDIT_ORTAK.md docs/prompts/FAZ9_KITAP_AUDIT_1_VERI.md docs/fable_kitap_audit/README.md docs/fable_kitap_audit/kitap docs/fable_kitap_audit/AUDIT_1_VERI.md docs/fable_kitap_audit/ekler/1
```

## Kabul kapısı

- **K1:** Etiketler ve özellikler 99 arzda sıfırdan üretildi. Uyuşmazlıkların kökü ölçüldü.
- **K2:** Payda, sıra kuralı ve nokta-zamanı maddeleri komut çıktısıyla gösterildi.
- **K3:** Rapor ortak biçimde. Her bulgunun kanıtı var. "Bakılmayanlar" listesi dürüst.
- **K4:** Koruma eşit, hijyen sayımları 0, commit yalnız izinli yollarda.

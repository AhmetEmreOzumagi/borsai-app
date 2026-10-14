# FAZ9_KITAP_AUDIT_2_ONCESI — Listeleme öncesi modellerin bağımsız denetimi

**Model: Claude Code / Fable · yüksek**

- **TASK_ID:** `BORSAI_FAZ9_KITAP_AUDIT_2_20261008`
- **Klasör:** repo kökü `~/Desktop/BorsAi`. Ağ yok.
- **Ortak kurallar:** önce `docs/prompts/FAZ9_KITAP_AUDIT_ORTAK.md`'yi oku. Bu görevde `<n>` = 2, `<AD>` = ONCESI.
- **Rapor:** `docs/fable_kitap_audit/AUDIT_2_ONCESI.md`. Ekler: `docs/fable_kitap_audit/ekler/2/`.

## Kapsam

- `kitap/04_listeleme_oncesi_modeller.md`'nin tamamı.
- `models/INDEX.json`'daki 27 model.

Etiket ve özelliklerin ham veriden üretimi Denetim 1'in işidir. Walk-forward kesimi, bootstrap ve canlı skorlar Denetim 3'ün işidir. Sen modellere odaklan: şartname, kod ve dondurulmuş JSON birbiriyle tutarlı mı, ve kılavuzdaki hükümler ledger'lardan yeniden üretilebiliyor mu?

## ÖNCE OKU

- CLAUDE.md
- `docs/fable_kitap_audit/README.md`
- `kitap/04_listeleme_oncesi_modeller.md`
- `docs/MODELS.md`
- `docs/SPEC_DEVIATIONS.md`
- Şartnameler:
  - `docs/specs/` (`SPEC_V1_6`, `SPEC_CEILING_V0`, `SPEC_PB_V0`, `SPEC_MARKET20_V0`, `SPEC_SCORING`)
  - `docs/specs_faz4/SPEC_CEILING_PATH_V0.md`
  - `docs/specs_faz7/` (`SPEC_HAZARD_V1`, `KARARLAR`)
  - `docs/specs_faz7_c/` (`SPEC_C_V0`, `KARARLAR_C`, `KESIF`)
- Kod:
  - eğitim: `borsai/fit.py`, `hazard.py`, `ceiling_path.py`, `preprocess.py`, `survival.py`
  - tahmin: `borsai/predict*.py`
  - `borsai/specs.py`
- Önceki denetimler (yeniden yapma; sonuçlarını iddia olarak kullan):
  - `docs/fable_faz4_audit/`
  - `docs/fable_faz5_audit/`
  - `docs/fable_faz7_audit/`
  - `docs/fable_faz7c_audit/`

## Adım 0

`FAZ9_KITAP_AUDIT_1_VERI.md`'nin Adım 0'ıyla aynı: HEAD, fark listesi ve izlenmeyen dosyalar. Sonra koruma ölçümünü `ekler/2/koruma_once.txt`'ye yaz.

## Adımlar

Sıra önem sırasıdır. Her adım bitince raporu güncelle.

**1. Harita ve kimlikler (§4.1).**
- `models/INDEX.json`'da 27 model mi var?
- Her modelin parametre hash'i, kendi JSON'unun kanonik sha'sıyla tutuyor mu?
- Şartname hash'i şartname dosyasıyla tutuyor mu?
- Kılavuzdaki model listesi INDEX'le birebir mi (ad, sayı, aile)?

**2. Ortak araç kutusu (§4.2).**
- L2 cezasının ölçeği: şartnamedeki (λ/2)·‖β‖² ile koddaki scikit-learn `C` arasındaki eşleme n'e göre doğru mu?
- Sabit terim cezasız mı?
- Type-7 kantil ve ddof = 0 z dönüşümü.

Her biri için şartname cümlesini ve kod satırını yan yana koy.

**3. `ceiling_hazard_v0` (§4.4).** Uygulamada en çok kullanılan model budur. Sıfırdan, `borsai` import etmeden kur:
- ayrık zamanlı tehlike modeli;
- gün grupları g1 = {1}, g2 = {2, 3}, g3 = {4..10};
- özellikler f1, f2, f3;
- λ = 10.

Sonra:
- Nihai fit'i (n = 97) yeniden yap. Dondurulmuş katsayılarla |Δ| ≤ 1e-6 olmalı.
- S_k = Π(1 − h_d) ve RPS = (1/10)·Σ(S_k − 1[L ≥ k])² tanımlarını şartname ve kodla karşılaştır.
- **NETGL için:** dondurulmuş model ve `registry/inputs/NETGL.json`'daki girdilerle h_1…h_10, S_1…S_10 ve E[L] = Σ S_k değerlerini hesapla. Kılavuzdaki NETGL sayılarıyla karşılaştır. Bunlar uygulamanın ekranda gösterdiği sayılardır (§1.5, §8.14 manşet, §8.16 tablosu):
  - ortalama 3.3 gün;
  - D1'de tavan %82;
  - j = 3 ve j = 6'da "yarın da tavan" %67;
  - j = 3'te kalan 1.9 gün;
  - P(L ≥ 5 | L ≥ 3) %45 ve P(L = 10 | L ≥ 3) %6.

  j ≥ 3 için olasılığın sabit kalması g3 grubunun doğal sonucu mu, yoksa bir hata mı? Hükmü ölçerek ver. Bu sabitlik proje sahibine "profesyonel durmuyor" diye takıldı. Yeni model fikri FAZ10'da; sen yalnız mevcut durumu tespit et.

  Kılavuz aynı ekranda geçmiş arzların oranını da veriyor: j = 3'te %80 (66 arzdan 53). Model %67 diyor. Bu fark modelin kalibrasyonu hakkında ne söylüyor? Backtest ledger'ında g3 günlerindeki tahmin edilen ve gerçekleşen devam oranlarını karşılaştır.

**4. Hüküm tablosu (§4.9).**
- Kılavuzdaki her model × hücre hükmünü ledger'dan yeniden üret: fark, %95 aralık, n ve ay sayısı. Bootstrap'ı kendin yaz: SPEC_DEVIATIONS C7 (ay blokları, 4000 tekrar, `random.Random(20260921)`); indeksleri şartnameden al.
- "Geçiyor" denen her hücrede aralık 0'ı dışlıyor mu, yön doğru mu (CLAUDE.md kural 6)? Aralığı 0'ı içerip "geçiyor" denen ya da tersi bir hücre KRİTİK'tir.
- Karşılaştırıcılar (her zaman tavan, eğitim medyanı, taban oranı, son-10 taban oranı) aynı arzlarda mı skorlanmış?

**5. Diğer aileler (§4.3, §4.5–§4.8).** Her ailede şunlara bak:
- Şartname, kod ve dondurulmuş JSON üçlüsü tutarlı mı?
- Birincil hücre ön kayıtlı mı? Şartname commit'i, backtest commit'inin atası mı (git DAG)? Birincil tanım sonradan değişmiş mi?
- §4.10'da "öne çıkan" denen her modelin nihai fit'ini yeniden yap ve dondurulmuş JSON'la karşılaştır.

Aileler:
- V1.5, V1.6 ve market20. Kılavuzda ikisi de `v1_5_h99`'a karşı, n = 87, "ayırt edilemiyor":
  - `v1_6_h99` D10 MAE: +0.0008 [−0.0003, +0.0028];
  - `v1_5_market20_v0` D5 MAE: −0.0008 [−0.0178, +0.0137].
- PB modelleri;
- `ceiling_path_v0`, `@INF` ve `pb_ceiling_path_v0`;
- tavan serisi v1 ailesi;
- `fall_d10_v0_*`.

**6. Model düzeyinde sızıntı.** Her aileden 2 fold seç ve şunları göster:
- test arzı eğitimde yok;
- eğitim satırlarının kullandığı etiketin son seansı T'den önce;
- test arzının değeri değiştirildiğinde fit bit-eşit kalıyor (klonda).

**7. Tahmin kodunun bağımsızlığı.** `predict*.py` ve kullandığı modüller yalnız standart kütüphaneyi mi import ediyor? Eğitim kodu numpy ve scikit-learn kullanıyor; bu ayrım kılavuzda doğru anlatılmış mı? Kanıt olarak import kapanışını göster.

**8. Kılavuzun geri kalanı.** §4.11'deki sınırlar ve dürüstlük notları gerçekten belgelerde ve kodda var mı?

## Commit

```
git add docs/prompts/FAZ9_KITAP_AUDIT_2_ONCESI.md docs/fable_kitap_audit/AUDIT_2_ONCESI.md docs/fable_kitap_audit/ekler/2
git commit -m "BORSAI_FAZ9_KITAP_AUDIT_2: independent audit of listing-time models against the project guide" -- docs/prompts/FAZ9_KITAP_AUDIT_2_ONCESI.md docs/fable_kitap_audit/AUDIT_2_ONCESI.md docs/fable_kitap_audit/ekler/2
```

## Kabul kapısı

- **K1:** `ceiling_hazard_v0` sıfırdan kuruldu; nihai fit ve NETGL sayıları ölçüldü.
- **K2:** §4.9'daki her hüküm ledger'dan, kendi bootstrap'ınla yeniden üretildi.
- **K3:** Şartname, kod ve JSON tutarlılığı her aile için gösterildi.
- **K4:** Koruma eşit, hijyen sayımları 0, commit yalnız izinli yollarda.

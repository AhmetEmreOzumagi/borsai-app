# BORSAI_FAZ7_C_IMPL_20260927 — uygulama ve backtest raporu

Görev: `docs/prompts/FAZ7_C_IMPL.md`. Şartname `docs/specs_faz7_c/SPEC_C_V0.md` (sha256 `d75c17cfec09…`, commit `4fe4e51`, push
kanıtlı) ve bağlayıcı kararlar `docs/specs_faz7_c/KARARLAR_C.md` (sha256 `2b60bec41924…`; çeliştiği yerde geçerli; bu görevde
commit A ile commit edildi, içeriği değişmedi) **değiştirilmedi**. Dört kimlik (`fall_d10_v0_h99`, `_pooled`, `_addsale`,
`_pooled@ZERO`) **dondurulmadı**: `models/`, `INDEX.json`, `INDEX_POST_D1.json` değişmedi. `registry/`, `scores/`, `data/`,
`legacy/`, `docs/specs*`, `docs/app/` ve `app/` değişmedi (T2 pini gerekmedi). push/tag/amend yok.

Bütün sayılar **backtest terazisindedir** (retrospektif walk-forward, H99 test arzları) ve **tasarıma maruzdur** (şartname §10:
özellikler H99'un ve eski kohortun açık kümesinin sonuçları görülerek, 2 054 varyant denenerek seçildi). Kasa (§5.2) ve canlı
(§5.3) teraziler bu raporda yoktur; hiçbir sayı toplanmaz. Fark = aday − karşılaştırılan (Brier, p_up = P(kapanış > arz),
kırpmasız); negatif = aday iyi. "Düşme olasılığı" = 1 − p_up; Brier ikisinde aynıdır.

## 0. Kısa sonuç

- **Yakın dönem birincil hücresi** (`fall_d10_v0_pooled − fall_d10_v0_h99`, D10 Brier, ilk işlem ≥ 2024-01-01): **−0.0058
  [−0.0340, +0.0219]**, n = 75 fold (22 ay, 21 olay) → etiket **"belirsiz"** (§5.1: alt uç 0'ın altında, üst uç +0.008'in
  üstünde). §6.2 beklentisi −0.002 [−0.015, +0.012], "belirsiz ya da tolerans içinde" → **aralık içinde**.
- **Proje sahibinin sorusu** ("eski arzları eğitime katmak bugünkü tahmini bozar mı?"): yakın dönem terazisinde cevap **"ayırt
  edilemiyor"** — nokta havuzun lehine (−0.0058; 33 fold havuz, 42 fold h99 iyi) ama aralık geniş; "bozuyor" değil, "tolerans
  içinde" de değil.
- **Sonucun kurala etkisi (§5.5, önceden yazılı):** k3 üç aday için de sağlanıyor — `pooled`'ın yakın dönem hücresi "bozuyor"
  değil; `h99` ve `addsale`'in yakın dönem − `base_rate` hücreleri tamamen 0'ın üstünde değil. Üçünün uygunluğu k1 ve k2 ile kasayı
  bekler; hepsi dondurulur ve listede kalır (§5.5-4, KARARLAR K4).
- **İlan edilmiş ikinciller** (aynı 75/76 fold): üç adayın da D10'da `base_rate`'e karşı noktası negatif; `h99` (−0.0434
  [−0.0773, −0.0048]) ve `pooled` (−0.0492 [−0.0670, −0.0296]) için aralık 0'ın altında, `addsale` için 0'ı içeriyor (−0.0065
  [−0.0301, +0.0161]). `v1_5_h99`'a karşı üçünün de aralığı 0'ı içeriyor. `pooled − pooled@ZERO` (özelliklerin payı) −0.0449
  [−0.0629, −0.0262].
- **T6 (§6.2 konumu):** yedi hücrenin yedisi **aralık içinde**; **beklentiden çok iyi: yok**.
- **Beklenen sayılar tablosu:** dokuz denetimin dokuzu tuttu (§2; "her fold'da eğitim D10 seansı < T" satırı proje sahibinin
  bu görevdeki kararıyla — K6, seçenek A — D10 fold'larında birebir, D5 fold'larında D5 kuralıyla).
- **B testleri A'da iki kusur buldu; ikisi de B'den önce ayrı küçük commit'lerle düzeltildi (model, backtest ve sayılar
  değişmedi):** (1) K14 — commit A'nın stdlib tahmini ufukların sözlük sırasını denetliyor, sıralı anahtarlı JSON'u (önizleme,
  donmuş dosya) reddediyordu → A2 (`1239e45`, yalnız `predict_fall.py`); (2) K15 — rapor kancası Faz 7C bölümünü Faz 7 ile Faz 5
  arasına yazıyordu, var olan Faz 7 bölüm testi o aralığı kestiği için kırmızıydı → A3 (`77d0ee5`, yalnız `report.py`; bölüm Faz 4
  ile Faz 7 arasında). Resmi koşu A'nın temiz koduyla; yeniden koşu A3 koduyla bayt-eşit.
- Sıradaki adım (görev yolu): Fable'ın bu şartnameden sıfırdan yeniden üretimi (ledger'lar |Δ| ≤ 1e-9), sonra dondurma.

## 1. Commit'ler

| Commit | Hash | İçerik |
|---|---|---|
| A | `3c93f9c731bdda0280e00c5e7f90b7f805572dca` | kod (`predict_fall.py`, `report_faz7c.py`; `backtest`, `fit`, `data`, `preprocess`, `specs`, `scoring`, `report` kancası), kurallar (etiket, δ, §6.2 konumu), sentetik ve birim testler (50), J16/J30 kalıbında sayaç istisnaları (A'da etkisiz), SPEC_DEVIATIONS K1–K13, KARARLAR_C, görev dosyası, T5 mutasyon kaydı, ölçüm betiği; gerçek veride walk-forward skoru ve aday nihai fiti YOK (yalnız `@ZERO`'nun şartnamede yazılı oranı ve plan yapıları) |
| (paralel) | `7be8394` | Fable'ın `BORSAI_APP_EK3_SPEC` commit'i (yalnız `docs/app/SPEC_APP_EK3.md` ve kendi görev dosyası); bu görevin değil |
| A2 | `1239e450aa969e2d01d8b7198ed54129932d7169` | K14: `predict_fall._check_params` ufuk kümesini denetler (sıra değil); sıralı anahtarlı gidiş-dönüş parite testi; 3 dosya, +7/−2 |
| A3 | `77d0ee5412ca8395ae29d4674008b67400216bf8` | K15: MODELS.md Faz 7C bölümü Faz 4 ile Faz 7 arasında (`report.py` kancası); Faz 7C bölüm testi; 3 dosya, +13/−7 |
| B | `acaca2d8b67fbacd3e2f8920670d317699e1bbb6` | resmi koşu (`experiments/log.jsonl` +4 `kind: backtest` satırı, context `faz7c_golden`, `git_commit` = A, `borsai_dirty` = false; +2 054 `kind: exploration` satırı); `tests/reference/macos_golden_faz7c/` (10 dosya); MODELS.md "Faz 7C" bölümü (+119 satır, yalnız ekleme); `tests/test_faz7c_golden.py` (15 test); `docs/faz7c/ekler/impl_test_runs.txt` |
| R | bu raporu içeren commit (dosya kendi hash'ini taşıyamaz) | bu rapor; `docs/faz7c/ekler/olcum_beklenen_sayilar.txt` (ölçüm betiğinin R anındaki çıktısı), `impl_test_runs.txt` son koşu |

Sıra A → A2 → A3 → B → R; A2 ve A3, B'nin testlerinin A'da bulduğu iki kusurun düzeltmesidir (§8). Resmi koşudan sonra `borsai/`'de
değişen yalnız `predict_fall.py` (A2) ve `report.py` (A3): `git diff 3c93f9c acaca2d -- borsai` bu iki dosya (testli); hiçbir model,
tarif, plan, eşik, ızgara ya da hücre tanımı değişmedi.

### Hash'ler

| Nesne | sha256 |
|---|---|
| `docs/specs_faz7_c/SPEC_C_V0.md` | `d75c17cfec09712174c86ac8619b5d51fb5681fc161f48455423b84d9e8db5ac` |
| `docs/specs_faz7_c/KARARLAR_C.md` | `2b60bec41924ac357b359a151737b9bc4a5a3b8fba30a1f75dab1e2eca2744a9` |
| `docs/specs_faz7_c/ekler/denenenler.csv` (keşif, 2 054 satır) | `25edc9a6e40c59a518cf54fa5a28fb4fe9d891bbac511cfa2fdb7f2b5e046f5b` |
| şartname sözlüğü (`spec_sha256`): `h99` / `pooled` / `addsale` / `pooled@ZERO` | `e21c0a32bb9861db0a6fd0e6ee0086d0c862160556fcac6bcede24a109adb46e` / `1054f2c2214734effce3cb65a150fbff646f7d1060b750c3d02d3aef3a0ec28f` / `b0b04566f98742978a62c44327fc5e5c1389fb7e333a86f4dfd4e0c4ac2172a1` / `0c96245fb80f6d538199d4fd6d73707ddcb7f5f28c6d8f9f65108f796ef35094` |
| ledger `h99` / `pooled` / `addsale` / `pooled@ZERO` | `01992680803ff35b7e7ee922e8a5597af02a3a587fa8d49aff919f2e31ae641b` / `e1c26cb68a26c06c2ca9291733edea10c8b98fc2486b011f60bd51349c3f6591` / `6e93e4be713cf117df3b21140b407b14ea9f8cddb994aaac591faceaa9541517` / `d08777b75c317a43fc12f9f2b50f2155dae44e850e121ab8d7a68985a4d67dd9` |
| nihai fit önizlemesi `h99` / `pooled` / `addsale` / `pooled@ZERO` | `a6c9e65eb567e5de9c09a853d49e76d51756a1c1e5cf4a3f1cfaefa1dd70866f` / `9e37a0fd33858353b1fb84e847a57b95ce998a0908d63006c354bc6abaadaccc` / `8c33da312573ffed6703a6a412b63af595ca0403584dab3a826baf57aaec4b8f` / `883ab7b913299ea369b801af3cd7b436199cf4debb51fae02bf2afb14f1da166` |
| `tests/reference/macos_golden_faz7c/MANIFEST.json` / `SHA256SUMS` | `b9104d6dfe3d74844349d57f8eb0bc34e782986992101ebdab496f1d01912c9a` / `b1d54fb1a770c0f0fd76ba7b103336953bed28453082b929d733ea19ef89bb63` |
| karşılaştırıcı ledger'ları (Faz 1A, pinli) `base_rate` / `v1_5_h99` | `898d2d849cc21a0461c88b816338c9d64d7b93b7d4ffafe726bfd3c56d5147e2` / `5c56da37bf7cece261fc5472ff0a2de8e242169755afc3aefb3c6c12b7fb049b` |
| `data/data_version.json` (H99 veri sürümü) / `data/data_version_v2.json` (v2) — değişmedi | `a0c7d082dacdbde03f53d1c4af1ce9f7983f9946abc80062de570f4a1df1f977` / `2ee8d51be3f026ad05ff7b4894f9512809556b3da2fd2d0b06256b7de5ee525a` |
| `borsai/` kaynak sha'sı (resmi koşu, `code_version`, commit A) | `516c0a3e7288…` (`faz7_support.borsai_tree_sha256_at(3c93f9c)` ile aynı; testli) |

## 2. Beklenen sayılar (görev tablosu; ölçülen)

Ölçüm `docs/faz7c/ekler/olcum_beklenen_sayilar.py` (yalnız okur; çıktıda arz kodu yok; kasa üyelerinin dosyaları okunmaz), ham
çıktı `docs/faz7c/ekler/olcum_beklenen_sayilar.txt` (R anında, HEAD = B). Aynı sayılar A ve B testlerinde assert'lidir.

| Denetim | Beklenen | Ölçülen | Sonuç |
|---|---|---|---|
| ek satış bayrağı | "0" → 0; "35000000" → 1; boş → `REFUSED_ADDITIONAL_SALE_MISSING`; "-1" → `INPUT_NEGATIVE`; bayrak = 1: H99 6, açık 13 | "0" → 0; "35000000" → 1; "" / None / "DATA_NOT_FOUND" → `ADDITIONAL_SALE_MISSING` (sabit `REFUSED_ADDITIONAL_SALE_MISSING`; J5 kalıbı, K2); "-1" → `INPUT_NEGATIVE`; bayrak = 1: H99 6/95 dolu alan, açık küme 13/70 | tuttu |
| eğitim kümeleri | `H99_F3_AS_PRESENT` 94 (D10 26, D5 18); `…_F3_AS_PRESENT` 161 (39, 29); `…_AS_PRESENT` 165 (40, 30) | 94 (26, 18; H99 94); 161 (39, 29; H99 94 + açık 67); 165 (40, 30; H99 95 + açık 70); şartname sözlükleriyle `fall_training_rows(check=True)` | tuttu |
| tablolar | `training_table.csv`, `training_table_v2.csv`, `data_version*.json` sha'ları değişmez; kasa kodu `data/`'da 0 | `b307cd0e…` / `5adda8b2…` sürüm dosyalarıyla aynı; `data_version.json` `a0c7d082…`, `data_version_v2.json` `2ee8d51b…` (şartname sabitleri); `data/` çalışma ağacı değişikliği 0; kohort bekçisi (64 kasa kodu, bütün `data/`) 0 sorun | tuttu |
| f1r | eğitim satırlarında `ceiling_hazard_v1_real`'in f1r ham değerleriyle bit-eşit | h99 94/94, havuz 161/161 (`ceiling_hazard_v1_pooled` ile) satırda Decimal metni aynı; TÜFE bilgisi aynı | tuttu |
| `@ZERO` | D10 p_up = 1 − 39/161, D5 = 1 − 29/161 (Fraction, bit-eşit) | D10 0.7577639751552795, D5 0.8198757763975155; `float(1 − Fraction(·, 161))` ile `==` | tuttu |
| fold planları | h99 ve pooled 94 test arzı; yakın dönem 75 fold, 22 ay, aynı ticker'lar; addsale 95; her fold'da eğitim D10 seansı < T | h99 ve pooled ufuk başına 94 test arzı (aynı ticker'lar); yakın dönem D10 75 fold (22 ay), ikisinde aynı 75 ticker; addsale 95 (yakın dönem 76); D10 fold'larında eğitim D10 seansı < T ihlali 0; D5 fold'larında D5 seansı < T ihlali 0 (proje sahibi kararı K6-A; D10 seansı T'den sonra olan D5 eğitim satırı h99 94, havuz 98, addsale 103 — sızıntı değil); skorlanabilir fold h99 82, pooled 94, addsale 95, @ZERO 94 (ufuk başına) | tuttu (K6 kararıyla) |
| karşılaştırıcılar | `base_rate` ve `v1_5_h99` ledger sha'ları pinli; V1.5 D10 Brier 0.1883 (81 fold) ledger'dan (\|Δ\| ≤ 1e-9) | pinler Faz 1A MANIFEST'iyle ve dosyalarla aynı (`898d2d84…`, `5c56da37…`); ledger'dan 0.18834296523191446 (81 fold), günlük değeriyle \|Δ\| = 0 (kırpmasız değer de aynı) | tuttu |
| bayt-eşitlik | V1.5/V1.6/PB/market20/v0/v1 altın ledger'ları ve 16 eski altın dosya bayt-eşit; `gen_golden --check` 25/0 | Faz 1A/1B/4/5/7 altın dizinleri (7 + 19 + 3 + 2 + 10 dosya) SHA256SUMS ile aynı, çalışma ağacında değişiklik 0; yeniden koşu testleri yeşil; `gen_golden --check` {"checked": 25, "different": []}; `test.sh` U46 yeşil | tuttu |
| günlük (B) | backtest satırlarında `spec_sha256` = SPEC_C_V0.md sha'sı; `exploration` satırları 2 054 ve `denenenler.csv` sha'sı | 4 `kind: backtest` satırı (context `faz7c_golden`, `git_commit` = A, `borsai_dirty` = false): `spec_document_sha256` = SPEC_C_V0.md sha'sı, `decisions_document_sha256` = KARARLAR_C.md sha'sı, `spec_sha256` = şartname sözlüğünün kanonik hash'i (J15/K9 kalıbı: belge sha'sını içerir); 2 054 `kind: exploration` satırı, hepsinde `source_sha256` `25edc9a6…`, içerik CSV'dekiyle sırası dahil aynı | tuttu (K9 okumasıyla) |

## 3. Yakın dönem birincil hücresi ve §6.2 konumu (T6)

Kural (commit A'da sabit; `borsai/report_faz7c.py: OPERATIONAL_RULES_FAZ7C`, `borsai/backtest.py: near_era_label_fall`; K8): havuz
ve h99 ledger'ları (ufuk D10) ticker ile eşleşir, ikisinde de Logit FIT_OK, ilk işlem ≥ 2024-01-01; Brier p_up ile, kırpmasız;
aralık C7 (ilk işlem ayı blokları, 4000 tekrar, `random.Random(20260921)`). Etiket: alt > 0 → "bozuyor"; üst ≤ +0.008 →
"tolerans içinde"; diğer → "belirsiz". Konum: nokta §6.2 aralığının (kapalı) içinde / altında ("beklentiden çok iyi") / üstünde.

| Hücre | n (ay) | pooled Brier | h99 Brier | fark | %95 aralık | pooled iyi / h99 iyi / eşit | Etiket | §6.2 beklenen | §6.2 aralık | §6.2 beklenen etiket | Konum |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `pooled − h99` **(birincil)** | 75 (22) | 0.1624 | 0.1682 | −0.0058 | [−0.0340, +0.0219] | 33 / 42 / 0 | **belirsiz** | −0.002 | [−0.015, +0.012] | "belirsiz" ya da "tolerans içinde" | **aralık içinde** |

Yakın dönem fold'larında olay (D10 kapanışı ≤ arz) 21 (şartname §5.1'in ölçtüğü 21 ile aynı). Hiçbir fold'da bit-eşit ya da
\|fark\| ≤ 1e-12 eşitlik yok. Bağlam (keşif, hüküm yok): bütün eşleşik D10 fold'larında (76, 23 ay) `pooled − h99` = −0.0081
[−0.0357, +0.0193]; 2023'te tek eşleşik fold.

## 4. İlan edilmiş ikinciller (§5.1; aynı yakın dönem fold'ları) ve §6.2 konumu

| Aday | Karşılaştırılan | Ufuk | n (ay) | aday | karş. | fark | %95 aralık | aday iyi / karş. iyi / eşit | aralık | §6.2 (beklenen, aralık) | Konum |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `h99` | `base_rate` | D10 | 75 (22) | 0.1682 | 0.2116 | −0.0434 | [−0.0773, −0.0048] | 56 / 19 / 0 | 0'ın altında | −0.025 [−0.055, +0.005] | aralık içinde |
| `h99` | `base_rate` | D5 | 75 (22) | 0.1243 | 0.1648 | −0.0405 | [−0.0742, −0.0074] | 59 / 16 / 0 | 0'ın altında | — | — |
| `h99` | `v1_5_h99` | D10 | 75 (22) | 0.1682 | 0.1737 | −0.0055 | [−0.0228, +0.0154] | 55 / 20 / 0 | 0'ı içeriyor | +0.010 [−0.020, +0.040] | aralık içinde |
| `pooled` | `base_rate` | D10 | 75 (22) | 0.1624 | 0.2116 | −0.0492 | [−0.0670, −0.0296] | 63 / 12 / 0 | 0'ın altında | −0.025 [−0.055, +0.005] | aralık içinde |
| `pooled` | `base_rate` | D5 | 75 (22) | 0.1340 | 0.1648 | −0.0308 | [−0.0495, −0.0170] | 62 / 13 / 0 | 0'ın altında | — | — |
| `pooled` | `v1_5_h99` | D10 | 75 (22) | 0.1624 | 0.1737 | −0.0113 | [−0.0465, +0.0281] | 55 / 20 / 0 | 0'ı içeriyor | +0.010 [−0.020, +0.040] | aralık içinde |
| `addsale` | `base_rate` | D10 | 76 (22) | 0.2087 | 0.2153 | −0.0065 | [−0.0301, +0.0161] | 56 / 20 / 0 | 0'ı içeriyor | −0.005 [−0.020, +0.010] | aralık içinde |
| `addsale` | `base_rate` | D5 | 76 (22) | 0.1699 | 0.1707 | −0.0008 | [−0.0186, +0.0153] | 60 / 16 / 0 | 0'ı içeriyor | — | — |
| `addsale` | `v1_5_h99` | D10 | 76 (22) | 0.2087 | 0.1782 | +0.0305 | [−0.0131, +0.0808] | 41 / 35 / 0 | 0'ı içeriyor | +0.010 [−0.020, +0.040] | aralık içinde |
| `pooled` | `pooled@ZERO` | D10 | 75 (22) | 0.1624 | 0.2073 | −0.0449 | [−0.0629, −0.0262] | 61 / 14 / 0 | 0'ın altında | — | — |

Okuma (backtest dili; "geçiyor" denmez): yakın dönemde `h99` ve `pooled` D10 ve D5'te `base_rate`'ten iyi (aralık 0'ın altında),
`addsale` ayırt edilemiyor; üçü de V1.5'in p_up başlığından ayırt edilemiyor (§6.2'nin "V1.5'i geçmesi beklenmez" beklentisiyle
uyumlu). `addsale`'in yakın dönem fold'ları 76'dır (H99'un ek satış alanı dolu ama f3'süz bir arzı: f3 istemez).
Keşif (hüküm yok): D5'te − `v1_5_h99`: h99 −0.0089 [−0.0245, +0.0068], pooled +0.0008 [−0.0392, +0.0388], addsale +0.0280
[−0.0197, +0.0795]; D5 `pooled − pooled@ZERO` −0.0283 [−0.0478, −0.0134]. Kural satırı `pooled@ZERO` − `base_rate` (bilgi): D10
−0.0043 [−0.0162, +0.0080] (havuz oranı ile H99 oranı).

## 5. Merdiven (§5.4; yalnız pay, D10, aynı yakın dönem fold'ları)

- addsale → h99 (f1r ve ln f3'ün payı; eğitim kümeleri de farklı: H99 94 / havuz 165): `h99 − addsale` = −0.0341 [−0.0768,
  +0.0060], n = 75 (22 ay).
- h99 → pooled (eski verinin payı): `pooled − h99` = −0.0058 [−0.0340, +0.0219], n = 75 (22 ay) (= birincil hücre).
- pooled@ZERO → pooled (özelliklerin payı): `pooled − pooled@ZERO` = −0.0449 [−0.0629, −0.0262], n = 75 (22 ay).

## 6. Fold özeti

- `h99`: ufuk başına 94 test arzı, 82 skorlanabilir (ilk 12'de eğitim n < 10). D10: FIT_OK 76, MODEL_NOT_FIT_SINGLE_CLASS 6 (erken
  fold'larda eğitimde düşen arz yok); seçilen C 0.001: 3, 0.01: 10, 0.1: 3, 1: 59, 10: 1. D5 aynı yapı (FIT_OK 76). Test arzı
  kırpılan (f1r ya da f3) D10 fold 28. f3 filtre dışlaması yok (H99'da açık FILTERED yok).
- `pooled`: ufuk başına 94 fold, hepsi FIT_OK; D10 seçilen C 1: 92, 10: 2. f3 filtre dışlaması (K5, J10 kuralı) D10 41, D5 39 fold
  (yakın dönemde 22 / 20; dışlanan hep açık kümenin 3 FILTERED üyesi); iç CV'de ayrıca dışlama olan fold 5 (D10), skorlanmayan iç
  tutulan 0. Eğitimdeki açık küme arzı 60…67 (67'den az: ilk iki D10 fold'unda D10 < T kuralı, K6; f3 filtre dışlaması olan fold'larda üç FILTERED üye).
- `addsale`: ufuk başına 95 fold, hepsi FIT_OK; seçilen C bütün fold'larda 1.
- `pooled@ZERO`: 94 fold, hepsi ZERO (kural); plan ve dışlama modelinkiyle aynı. (MODELS.md fold özetinde bu satır için yazan
  "ek satış sütunu sıfır varyansla düşen fold 94" ifadesi render kusurudur: kural satırının hiç sütunu yoktur; §9.)
- Resmi koşu 122 sn (günlük satırları 20:45:13 → 20:47:05 İstanbul; önizlemeler dahil), `--suite faz7c --write-golden --context
  faz7c_golden`, commit A'nın temiz ağacında.

## 7. Nihai fit önizlemesi (dondurulmadı; `models/`'e yazılmadı)

`backtest.final_fit_fall` (dondurmanın kullanacağı fonksiyon; K13) bütün eğitim kümesinde; dosyalar
`tests/reference/macos_golden_faz7c/` altında. Yeniden koşu `created_at`, `code_version`, `runtime` dışında aynı ve stdlib
`predict_fall.predict` (yazılmış JSON, sıralı anahtar) eğitim arzlarının hepsinde sklearn nihai fit'iyle \|Δ\| ≤ 1e-12 (§11-9;
commit B testi). Katsayılar p_up (P(kapanış > arz)) başlığınındır ve z-skorlu sütunlardadır: negatif katsayı düşme olasılığını
artırır.

| model_id | Ufuk | C (iç LOOCV) | sabit | f1r | ln f3 | ek satış | arz / olay | kırpma [p05, p95] (ham) | f3 filtre modu |
|---|---|---|---|---|---|---|---|---|---|
| `h99` | D10 | 1 | +1.4371 | −0.8566 | +1.1093 | −0.4207 | 94 / 26 | f1r [7.30435e+08, 6.11195e+09] 2025 TL; f3 [1.14774, 8.3635] | NOT_SPECIFIED |
| `h99` | D5 | 1 | +2.4245 | −1.0007 | +1.5284 | −0.4451 | 94 / 18 | aynı | NOT_SPECIFIED |
| `pooled` | D10 | 1 | +1.4939 | −0.5237 | +0.8520 | −0.8028 | 161 / 39 (H99 94, açık 67) | f1r [5.71126e+08, 6.2468e+09]; f3 [1.15, 18.1] | NOT_SPECIFIED |
| `pooled` | D5 | 1 | +2.0526 | −0.5850 | +0.9604 | −0.8166 | 161 / 29 | aynı | NOT_SPECIFIED |
| `addsale` | D10 | 1 | +1.2082 | — | — | −0.6144 | 165 / 40 (H99 95, açık 70) | — | — |
| `addsale` | D5 | 1 | +1.6113 | — | — | −0.6046 | 165 / 30 | — | — |
| `pooled@ZERO` | D10 | ZERO (kural) | p_up = 122/161 = 0.757764 | — | — | — | 161 / 39 | — | — |
| `pooled@ZERO` | D5 | ZERO (kural) | p_up = 132/161 = 0.819876 | — | — | — | 161 / 29 | — | — |

İç LOOCV Brier (seçilen **kalın**): `h99` D10 ZERO 0.20442, 0.0001 0.20416, 0.001 0.20196, 0.01 0.18577, 0.1 0.15565, **1
0.15168**, 10 0.15245, 100 0.15258; `pooled` D10 ZERO 0.18586 … **1 0.14588**, 10 0.14590, 100 0.14591; `addsale` D10 ZERO 0.18590 …
**1 0.16884**, 10 0.16890, 100 0.16890. Bütün nihai fit'lerde ilk sıradaki C yakınsadı (`final_fit_attempts` tek deneme). Havuz nihai
fit'inde (161 arz) f3 filtre modu NOT_SPECIFIED: dışlama yok. Ön işleme (z-skor öncesi ln uzayında) ortalama/σ: `h99` f1r 21.3786 /
0.6388, f3 1.0906 / 0.5985, ek satış 0.0638 / 0.2444; `pooled` f1r 21.3120 / 0.7110, f3 1.2663 / 0.7464, ek satış 0.1180 /
0.3226; `addsale` ek satış 0.1152 / 0.3192. `feature_ranges` ham: f1r (2025 TL) `h99` [4.80e+08, 1.35e+10], `pooled` [2.97e+08,
1.35e+10]; f3 `h99` [1.0, 14.6], `pooled` [1.0, 54.14]; ek satış {0, 1}.

[ÇIKARIM, test edilmedi] İşaretler §2.1 mekanizmalarıyla aynı yönde (büyük reel arz, düşük talep katı ve ek satış düşme
olasılığını artırır); havuzda ek satış katsayısı H99'dakinin yaklaşık iki katı (katsayı ağırlıkla açık kümeden öğrenilir: 19
bayraklı arzın 13'ü açık kümede), ln f3 ve f1r katsayıları küçülür (eski dönemin yüksek talep katları). Hüküm değildir.

## 8. Görev kurallarına göre notlar ve sapmalar

- **Proje sahibi kararı (bu görevde soruldu, 2026-09-27; SPEC_DEVIATIONS K6):** D5 fold'larının eğitim kesimi. Şartname §5.1
  "PLAN_V15 kuralları" ve havuz için "D_h seansı < T" der; §11-6 ve görev tablosu "her fold'da eğitim D10 seansı < T". Cevap
  **A — PLAN_V15 aynen** (D5'te D5 seansı < T; karşılaştırıcıların D5 fold'larıyla aynı kural). Soru commit A'dan önce, gerçek
  veride hiçbir fit yapılmadan soruldu.
- **Ek düzeltme commit'i A2 (`1239e45`; K14):** görev metninin sırası A → B → R'dir; B'nin gerçek önizleme testleri A'nın
  `predict_fall._check_params`'ında bir hata buldu (ufuk sırası denetimi sıralı anahtarlı JSON'u reddediyordu). "Kodu şartnameye
  uydurmak aynı model_id'dir" ilkesiyle yalnız `borsai/predict_fall.py` (tek satır: sıra yerine küme), A'nın sentetik parite testi
  (sıralı anahtarlı gidiş-dönüş) ve SPEC_DEVIATIONS K14 ayrı commit'te düzeltildi; düzeltmesiz kod testte kırmızı (4 başarısız),
  düzeltmeyle yeşil. Resmi koşu A'nın temiz koduyla yapılmıştı (`predict_fall` backtest, fit ve önizlemede kullanılmaz); B'nin
  yeniden koşu testi A2 koduyla bayt-eşit; `git diff 3c93f9c 1239e45 -- borsai` yalnız `predict_fall.py` (testli). Arada paralel
  Fable oturumunun `7be8394` commit'i var (yalnız `docs/app/SPEC_APP_EK3.md` ve kendi görev dosyası; bu görevin commit'lerine
  girmedi).
- **§5.1 parantezi** ("açık üyelerin son seansı ≤ 2023-10-04 < ilk fold → daima tam girer") yalnız T > 2023-10-04 için doğru: ilk
  H99 T'si 2023-09-22; ilk iki D10 ve ilk D5 fold'unda D_h < T kuralı bazı açık üyeleri dışarıda bırakır. Kural yazıldığı gibi
  uygulandı (K6; testli). Bu fold'lar yakın dönemde değildir.
- **Ek düzeltme commit'i A3 (`77d0ee5`; K15):** commit A'nın `report.py` kancası Faz 7C bölümünü Faz 7'den sonra, Faz 5'ten
  önce yazıyordu. B öncesi tam koşuda tek kırmızı `tests/test_faz7_golden.py::test_models_md_faz7_section` oldu: var olan test Faz 7
  bölümünü "## Faz 7" başlığından "## Faz 5" başlığına kadar keser ve Faz 7C'nin dört "kasa: bekliyor" satırını da saydı (9 ≠ 5);
  `test_faz7_frozen.py` aynı aralıkta "### Dondurma" sayar ve Faz 5 bölümü belgenin sonunda bitmelidir. Var olan testler
  değiştirilmedi; kanca Faz 4 ile Faz 7 arasına alındı (Faz 4 testi Faz 4'ten sona kadar keser; Faz 7C metni onun saydığı
  dizgeleri içermez, ölçüldü). Faz 7C testi yeni sırayı ve Faz 7 aralığındaki sayıyı (5) sınar. `git diff 1239e45 77d0ee5 --
  borsai` yalnız `report.py` (testli).
- **J10 kuralı (f3 filtre dışlaması) aynen uygulandı (K5):** şartname imputasyonsuz tarif ve "V1.5 filtre adımı aynen" der; birlikte
  uygulanabilmeleri için v1'deki proje sahibi kararının (J10) aynısı. Havuz D10 fold'larının 41'inde (yakın dönemde 22) açık kümenin
  3 FILTERED üyesi eğitim dışı; nihai fitte dışlama yok.
- **Varyant sayacı (T4; K10):** keşif satırları v2 veri sürümüne sayıldı (keşif `training_table_v2.csv` üzerinde yapıldı).
  Sayaçlar: H99 sürümü 22 → 23 (`fall_d10_v0_h99`), v2 sürümü 2 → 2 059 (3 (C) koşusu + 2 054 keşif). `scores/` yeniden
  üretilmedi; beş J16 testi ve `test_l9` J16/J30 kalıbıyla (`faz7c_support.faz7c_variants`, yalnız `scores.json` 8e3a623 ile
  bayt-eşitken, fark tam sayı) güncellendi; `test_experiment_log.py` türü kabul eder. `fall_d10_v0_h99`'un kendi kartı (H99 sürümü)
  keşfi saymaz: EK3 kartı ailenin keşif sayısını ayrıca göstermeli (§12).
- **T2:** pinli kaynakların hiçbiri değişmedi (`additional_sale_flag` ve bütün (C) tahmin kodu `borsai/predict_fall.py`'de); pin
  yenilenmedi, `app/` değişmedi; `gen_golden --check` 25/0 her aşamada.
- **Yerleşim (K1):** şartnamenin `features.additional_sale_flag`'ı `predict_fall.additional_sale_flag`; `data.select_training_rows`'u
  `data.select_fall_training_rows` + `data.additional_sale_shares` (v2 yükleyici aynen); `report.py`'ye Faz 7C kancası (J1 kalıbı).
- **Render kusuru (bilgi):** MODELS.md Faz 7C fold özetinde `pooled@ZERO` satırı "ek satış sütunu sıfır varyansla düşen fold 94"
  yazıyor; kural satırının hiç sütunu yoktur (sayım `logit_columns`'ta `add_sale` arar). Hiçbir sayıyı etkilemez; B/R yollarında
  `borsai/` olmadığından düzeltilmedi. Dondurma görevi Faz 7C bölümüne dondurma notunu eklerken (`report_faz7c.py`) düzeltmeli
  (kural satırında bu alan yazılmamalı).
- Proje sahibine başka soru: yok.

## 9. Test sayıları

| Koşu | Sonuç | Süre |
|---|---|---|
| Adım 0 taban (f89e41a) | 741 passed | 445.48 sn |
| A öncesi, deselect yok (izlenmeyen yeni kod ve test dosyalarıyla; `data/` değişmediği için temizlik bekçileri yeşil) | 791 passed | 495.05 sn |
| B öncesi 1 (A2 ile; resmi koşu, altın dizin, keşif satırları, MODELS.md, altın testler) | 805 passed, 1 failed (`test_faz7_golden.py::test_models_md_faz7_section`; K15) | 769.46 sn |
| B öncesi 2 (A3 ile) | 806 passed | 752.67 sn |
| B sonrası (commit'li, HEAD acaca2d) | 806 passed | 839.68 sn |

Ayrıca B öncesi etkilenen modüller (altın testler ilk yazıldığında, A2'den önce): `test_faz7c_golden.py`'de 4 kırmızı (stdlib
tahmin × 4 model; K14), öteki 173 yeşil. `bash app/scripts/test.sh`: adım 0, A öncesi ve B öncesi yeşil (cargo 94, npm 222,
parity 4, U46). `gen_golden --check`: her aşamada 25/0 (pin değişmedi). Faz 7C testleri: A'da 50 (`test_faz7c_model.py` 34,
`test_faz7c_backtest.py` 16; T5 eşik mutasyonu 3 kırmızı, `docs/faz7c/ekler/t5_mutasyon.txt`), B'de +15 (`test_faz7c_golden.py`;
yeniden koşu dahil ≈ 2.5 dk). Var olan testlerde değişiklik yalnız T4 kalıbında: beş J16 testi ve `test_faz5_live.py::test_l9`
(sayaç istisnası, K10) ve `test_experiment_log.py` (tür kabulü). Ham son satırlar: `docs/faz7c/ekler/impl_test_runs.txt`.

## 10. Hijyen ve maruziyet

- Kasa (SEALED, 64) üyelerinin hiçbir dosyası açılmadı; kasa kodları yalnız `registry.cohort_members` + bekçi/test fonksiyonları içinde,
  bellekte kullanıldı ve hiçbir çıktıya basılmadı (testler kod listesini yerel değişkende tutar; ölçüm betiği yalnız sayı basar).
  Kohort dosyası doğrudan okunmadı. `docs/faz6/dogrulama/EXPOSURE.md`, `docs/faz7/prospectus/EXPOSURE.md` ve Codex `exposure_log`'ları
  okunmadı. `denenenler.csv` ve `kesif_c.py` yalnız sayım/sha ve `_assert_open` sentetik kapalı kod testi için okundu/içe aktarıldı.
- Yeni dosyalarda (kod, testler, altın dizin, MODELS.md bölümü, günlük satırları, bu rapor) kasa kodu ve bülten adı kalıbı yok
  (A ve B testleri).
- Uygulayıcı yakın dönem sonuçlarını commit A'dan sonra, B koşusunun çıktısında gördü; sonra model kodunda, tanımlarda, eşikte ya
  da ızgarada değişiklik yok. Sonraki iki kod değişikliği A2 (stdlib tahminin JSON ufuk denetimi) ve A3 (MODELS.md bölüm sırası)
  sonuçla ilgisizdir; ikisi de B testlerinin bulgusudur.
- Ağ yok; push/tag/amend yok; `git add -A` kullanılmadı; paralel oturumun dosyaları (`docs/app/`, `docs/prompts/FAZ7_FABLE_APP_EK3_SPEC.md`)
  bu görevin commit'lerine girmedi.

## 11. Dondurma görevi için notlar

**Python (dondurma):**
- `models/INDEX.json` sonuna 4 giriş (`FAZ7C_MODEL_IDS` sırası: `fall_d10_v0_h99`, `_pooled`, `_addsale`, `_pooled@ZERO`); INDEX
  23 → 27; `INDEX_POST_D1.json` değişmez. JSON'lar `backtest.final_fit_fall` ile (önizlemeyle `created_at`, `code_version`,
  `runtime` dışında `==`; `tests/test_faz7c_golden.py` sınıyor). `fit.fit` (C) kimliklerini bilmez: `freeze.py` J25 kalıbıyla
  `final_fit_fall`'a yönlendirmeli (veri kümesi: h99 → `load_dataset`, ötekiler → `load_dataset_v2`; ek satış
  `data.additional_sale_shares`).
- Dondurma sırası tuzağı (J23/J25): `freeze.py` değişikliği ayrı bir kod commit'inde, dondurma temiz ağaçta.
- `freeze.model_kind(params)` bugün (C) JSON'unu (`algorithm = l2_logit_v1_6_grid`) "rule" sayar: `fall` türü eklenip `predict_fall.predict`'e yönlendirilmeli. Kayıt yazıcı (`build_record`, `build_oot_record`): `family = "fall_d10_v0"` p_up modelidir;
  `model_inputs["additional_sale_shares"]` (canlı ve eski kohort girdi şemasında zaten var), `tufe` bloğu (h99, pooled; v1 yolu,
  J26) ve `tufe_index`; `predict_fall.predict` çağrısı. `registry.F3_MODELS`'e f3 isteyen `fall_d10_v0_h99` ve `_pooled` eklenmeli
  (J24 kalıbı); `addsale` ve `@ZERO` f3 istemez (en erken kayıt kuralı).
- INDEX değişince kırılacak uygulama pinleri (J31 kalıbı): `app/parity/golden/MANIFEST.json` `models_index_sha256`,
  `app/tests/fixtures/ui/preflight_ok.json` ve `preflight_blocked.json` (INDEX sha'sı; `BORSAI_UPDATE_UI_FIXTURES=1`),
  `app/src-tauri/tests/build_embed.rs` yok sayılan liste (`ignored_model_ids` = 4 Faz 7 + 4 Faz 7C, EK3 öncesi). Geçici klonda
  "prova dondurma + tam test" önerilir: "23 model" varsayan testler (J30 kalıbı) ve `strip_frozen_faz7` benzeri bir
  `strip_frozen_faz7c` gerekecek.
- Skorlama: `scoring.FAZ7C_PRIMARY_CELLS` / `FAZ7C_OOT_PRIMARY_CELLS` / ikinciller (K11) (C) INDEX'e girince `PRIMARY_CELLS` /
  `OOT_PRIMARY_CELLS` ile birleştirilmeli (anahtar kümesini pinleyen iki test güncellenir); SCORES.md "(C) yakın dönem" satırı
  (C) INDEX'teyken kendiliğinden yazılır (`faz7c_near_era`). Canlı/kasa p_up hücrelerinin (D10 Brier − `base_rate`) hesabı V1.5
  yolundan; skorlar yeniden üretilince J16/J30/K10 istisnaları düşer (H99 kartları 23, v2 kartları 2 059 varyant).
- MODELS.md Faz 7C bölümüne dondurma notu (`report_faz7c.py`; Faz 5/7 kalıbı) ve §8'deki render kusurunun düzeltmesi. Bölüm Faz 4 ile Faz 7 arasındadır (K15): Faz 7 testleri "### Dondurma"yı yalnız Faz 7 → Faz 5 aralığında sayar, Faz 4 testi Faz 4'ten sona kadar yalnız varlık denetler; yeni "### Dondurma" başlığı ikisini de bozmaz (dondurma provasında doğrulanmalı).
- **Eski kohort ek kayıtları (sonraki görev):** `python -m borsai.freeze --oot registry/oot/cohort_pre_h99.csv --only-missing-models`
  135 üyede (C) 4 kimliğini içeren ek kayıt (v1'inkilerle aynı koşuda ya da `delta_of` zinciriyle); kasa üyeleri için yalnız
  listeleme öncesi girdiler (`registry/oot/inputs/<T>.json`; ek satış alanı orada, kasada 2 üyede boş → RET). Açık küme sınıfı
  OOT_RETRO (`n_oot_retro = 71`), kasada OOT_BLIND; model başına kapı; `oot_pre_h99_sealed` (19 + 4 v1 + 4 (C)).

## 12. EK3 (uygulama) için notlar

- **Rust tahmin portu** (`predict_fall.py` karşılığı): girdi V1.5 alanları + `tufe_index` / `tufe_refusal` + `additional_sale_shares`.
  f1r = `real_size(f1, tufe_index)` (Decimal 60 hane, tek bölme, sonra binary64; v1_real ile aynı); f3 `compute_features`'tan;
  add_sale = 1[Decimal(alan) > 0]. z: winsor f1r ve f3 (binary64 min/max), ln f1r ve f3 (`math.log`), (x − μ)/σ; add_sale yalnız
  (x − μ)/σ. p_up = sigmoid(intercept + Σ coef·z) V1.5 `_sigmoid` ve toplama sırasıyla aynı. `@ZERO`: `kind: constant`.
- Ret sırası ve kodları (K2): V1.5 girdi hataları → `F3_MISSING` → `F3_FILTER_STATUS_CONFLICT` → TÜFE kodu → `ADDITIONAL_SALE_MISSING`
  / `INPUT_NEGATIVE` / `INPUT_NOT_NUMERIC`; `addsale` yalnız ek satış alanını okur; `@ZERO` girdi istemez. Uyarılar
  `FEATURE_CLIPPED_TO_TRAINING_P05_P95` (f1r, f3), `OUT_OF_TRAINING_RANGE`. JSON denetimi ufuk kümesini karşılaştırır (sıra değil; K14).
- Çıktı V1.5 ufuk şekli (`return` null) + `clipped`, `clipped_features`, `f1r_raw`, `tufe_index_used`, `add_sale_used`. Kart
  "Düşüş (D10)" = 1 − p_up (§9); izinli sözcükler; kasa açılana kadar "kasa: bekliyor".
- Kartın varyant sayısı: §9 "exploration + backtest, aynı veri sürümü"; `h99` kartı H99 sürümündedir ve keşfi saymaz — ailenin
  keşif sayısı (2 054, v2) her (C) kartında ayrıca yazılmalı (K10).
- Altın vektör planı: `gen_golden.py` `PINNED_MODEL_IDS` (INDEX sırası) ve `predict_sources_sha256`'ya `borsai/predict_fall.py`
  eklenmeli (bugün pinli değil); 16 eski dosya bayt-eşit kalmalı (yeni girdi satırları yalnız yeni modellere). Önerilen satırlar:
  H99'un 99 arzı + `tufe_index` + ek satış (f3'süz ya da ek satışsız olanlar RET), açık kümenin 71 arzı, uç durumlar (p05/2, 2·p95,
  ek satış "", "-1", "abc", `tufe_refusal` kodları, filtre uyuşmazlığı). Kasa girdileri kasa açılmadan altın vektörlere girmez.

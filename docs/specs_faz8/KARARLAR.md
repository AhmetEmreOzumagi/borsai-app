# KARARLAR — SPEC_BREAK_V0 (Faz 8, kırılma akşamı modeli)

Yazım: 2026-10-01, Fable (görev BORSAI_FAZ8_FABLE_BREAK_SPEC_20261001). Bu belge şartname sayılır ve `SPEC_DOCUMENTS_FAZ8`'e girer; `SPEC_BREAK_V0.md` ile çeliştiği yerde **bu belge** bağlayıcıdır. §A proje sahibinin görev metninde verdiği kararlardır; §B şartnamenin kendi içinde verdiği kararların listesidir (Opus'a bırakılan karar yoktur); §C açık soruların karar sütunu orkestratör/proje sahibi tarafından doldurulur ve dondurmadan önce commit + push edilmiş olmalıdır. Dondurmadan sonra içerik değişmez; değişiklik yeni model_id demektir.

## A. Proje sahibinin bağlayıcı kararları (görev metni)

| # | Karar | Tarih | Şartnamedeki yeri |
|---|---|---|---|
| A1 | "Bize bugün lazım": eğitim yalnız güncel dönemle (H99, 2023-09 sonrası); eski kohort eğitime girmez | 2026-09-29 | §4.4 (`H99_BREAK_B_LE_9`) |
| A2 | "Hiçbir modelimizin geçmişte (2020–23) başarılı olması gerekmez": eski dönem testi bu model için yapılmaz; kapı iki aşamalı (yakın dönem backtest'i ön eleme, asıl sınav canlı); öne çıkan kuralı şimdi, önceden yazılır | 2026-10-01 | §5.2, §8 |
| A3 | Değişiklik = yeni model_id; terfi yok, yan yana modeller | CLAUDE.md | §1.1, §8-4 |

## B. Şartnamenin kendi kararları (özet; gerekçe şartnamede)

| # | Karar | Bölüm |
|---|---|---|
| B1 | **Devam**, birincil hedef **ertesi seans taban kapanışı** (y_F1); ikincil iki ardışık taban (y_F2). "D10 ≤ arz" için yeni fit edilmiş model **dur** (ideal Brier kazancı ≈ −0.008, ayırt edilemez); D10 kartta yastık kuralı (`D10_STRUCTURAL_ZERO`, parametre yok) + mevcut ürün | §0, §2 |
| B2 | Olay: b = L + 1 (ilk işlem görmüş tavan-dışı kapanış), kapsam b ∈ 1..9; **L = 0 dahil**; b = 10 ve L = 10 kapsam dışı; durdurma günleri sayılmaz (SPEC_SCORING §2) | §1.2 |
| B3 | Taban etiketi = `Decimal(KAPANIS) == Decimal(ALT LIMIT)` (THM; ham metin; "%10" varsayımı yok) — tavan etiketinin aynası | §2.1, §3 |
| B4 | Özellikler (2): `b_floor` (kapanış == alt limit), `b_turnover` = ln(hacim_b / shares_offered) (p05/p95 kırpma, z). Listeleme öncesi özellik miras alınmaz; f3 gerekmez; Z/B grubu, b, etkileşim özellik değil | §3 |
| B5 | Model: iki başlık L2-lojistik, V1.6 ızgarası + iç arz-bırak Brier (`_fit_logit`, Faz 7C yolu); kural satırı `break_floor_v0@ZERO`; dizin `models/INDEX_POST_BREAK.json` | §4 |
| B6 | Asıl karşılaştırıcı `PRODUCT_BREAK_FLOOR`: tavan yolu durum-2 karışımından türetilen P(ertesi seans taban) (eşik Lo(close_b)/P − 1); seri modelinden bağımsız, her arzda tanımlı | §5.1 |
| B7 | Birincil hücre: F1 Brier, model − `PRODUCT_BREAK_FLOOR`, yakın dönem fold'ları (ilk işlem ≥ 2024-01-01). İlan edilmiş ikincil: − `@ZERO`, F2 iki hücre, − `base_floor_by_type`. Brier kırpmasız | §5.2 |
| B8 | Beklenti: birincil −0.080 [−0.140, −0.020]; − `@ZERO` −0.040 [−0.080, 0.000]. "Çok iyi": birincil < −0.160 ya da üst uç < −0.080 ya da `@ZERO` farkı < −0.090 | §6 |
| B9 | Walk-forward kesimi T = kırılma akşamı tarihi; eğitim satırı ancak hedef seansı (D_{b+1} / D_{b+2}) kesin önce; ≥ 10 satır / 5 olay / 5 olay-dışı; blok = ilk işlem ayı | §7 |
| B10 | Canlı aşama `POST_BREAK` **makine sıralı**: insan kaydı yok; tahmin skorlama anında dondurulmuş JSON + pinli bültenler + `registry/inputs`'tan; `registry/post_break/<T>/machine_*.json` append-only; sınıf `MACHINE_SEQUENCED` / `RETRO` (LIVE formülde var, v0'da üretici yok); ölçek `live_break`, hiçbir ölçekle toplanmaz; `n_live / n_machine` kırılımı zorunlu | §9 |
| B11 | b = 1 akşamı tek akış: `post_d1_hazard_v0` (L ≥ 1) ve `break_floor_v0` (b = 1) birbirini dışlar; ikinci kayıt yok | §9.5 |
| B12 | Öne çıkan kuralı: aşama 1 (canlı n < 30) yalnız yakın dönem k1 (ürün VE `@ZERO` hücrelerinin üst ucu < 0) ve "ön eleme" etiketiyle; aşama 2 (n ≥ 30) yalnız canlı k2 (aynı iki hücre). Eski dönem hiçbir aşamada yok | §8 |
| B13 | Rejim uyarısı `FON_KRIZI_2026` (D_1 ≥ 2026-09-16): kartta metin ve `regime_tags` kırılımı; model girdisi değil; n'den düşülmez. Önceden yazılı okuma: model tabanı az tahmin eder | §6, §11 |
| B14 | Bant varsayımı (±%10, içe yuvarlama, D1 baz fiyat) açık varsayımdır; `BAND_RULE_MISMATCH` korur; dondurmadan önce rev. 54 doğrulanır | §1.3 |
| B15 | Ret kodları B3 biçimi, öneksiz; kapsam dışı ret değildir | §3, §11 |
| B16 | Her durumda v0 bu şartnameyle dondurulur; "basit kuraldan ayırt edilemiyor" (a) ise dondurulur ama öne çıkarılmaz | §6 |

## C. Açık sorular (SPEC_BREAK_V0 §14) — karar sütunu proje sahibi/orkestratör

| # | Soru | Fable önerisi | Karar | Tarih |
|---|---|---|---|---|
| C1 | Birincil hedef: ertesi seans taban mı, D10 ≤ arz mı? | **Ertesi seans taban.** D10 istenirse cevap "dur" (uygulama yok) | Birincil hedef ertesi seans taban kapanışı (y_F1). D10 için yeni fit edilmiş model yok; yalnız yastık kuralı + mevcut ürün. | 2026-10-01 |
| C2 | Makine sıralı satırlar canlı terazide `live_break` ölçeğinde n'e sayılsın mı; CLAUDE.md kural 1'e §9.4 cümlesi eklensin mi? | **Evet / evet.** (b) gece kaydı ileride yükseltme | `MACHINE_SEQUENCED` satırları `live_break` ölçeğinde n'e sayılır. CLAUDE.md kural 1'e SPEC_BREAK_V0 §9.4'teki cümle **aynen** eklenir. | 2026-10-01 |
| C3 | L = 0 (b = 1) kapsamda mı? | **Evet** (18/82; aynı mekanizma; Z/B keşifte) | L = 0 (b = 1) kapsamda. | 2026-10-01 |
| C4 | `FON_KRIZI_2026` uyarısının bitiş tarihi | **Açık kalsın**; proje sahibi tarih verince buraya yazılır | `FON_KRIZI_2026` uyarısı proje sahibi tarih verene kadar açık. | 2026-10-01 |
| C5 | Rev. 54 (21.09.2026) bant/baz fiyat doğrulaması | **Dondurmadan önce** orkestratör doğrular; değiştiyse §2.4/§5.1 sabitleri burada yeni değerle yazılır (özellikler etkilenmez) | Rev. 54 bant ve baz fiyat doğrulaması bu görevin adım 0b'sinde yapılır. | 2026-10-01 |

**Orkestratör notu (maruziyet eki):** Orkestratörün 1 Ekim keşfinde, taban üstünde bozulan arzlarda ertesi seans taban oranı **6/47 ≈ 0.128** idi (düşüşle bozulan 5/31, yükselişle 1/16). Şartname §6'da bu oran ≈ 0.08 diye çıkarılmıştı.
- Bu oranla ideal kazanç −0.051 yerine ≈ −0.042 olur; merkez beklenti `@ZERO`'ya karşı ≈ −0.03'tür.
- §6'daki beklenti aralıkları **değişmez**; bu not yalnız kayıt içindir ve backtest'ten önce yazılır.

Ek notlar (bağlayıcı):
- **Maruziyet:** hipotez H99'dan doğdu (orkestratör tablosu); özellik seçimi tek değişkenli profilden sonra yazıldı; H99 backtest'i ön elemedir. Bu belge ve şartname `experiments/log.jsonl`'a girmez; backtest koşusu `spec_document_sha256` ile bu iki dosyayı pinler.
- **Hijyen:** bu dizinde bülten adı kalıbı ve kasa kodu yoktur (kabul testi 14 ile denetlenir). Kasa, eski kohort ve OOT dosyaları bu görevde açılmadı.
- **Gösterim:** kart ve Rust desteği uygulama EK 5 görevindedir; bu görevler `app/`'e dokunmaz.

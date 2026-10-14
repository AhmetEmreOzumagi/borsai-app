# SPEC_BREAK_V0 — kırılma akşamı modeli (`break_floor_v0`, kural satırı `break_floor_v0@ZERO`)

Görev: BORSAI_FAZ8_FABLE_BREAK_SPEC_20261001. Yazım: 2026-10-01, Fable. Yol: şartname (bu belge) → Opus uygulama ve backtest → Fable bağımsız yeniden üretim → dondurma → canlı sicil. Bu belge `docs/specs_faz8/` altındadır; `docs/specs*` (Faz 1–7C), `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `tests/`, `app/` ve `CLAUDE.md` değişmemiştir. Bağlayıcı kararlar ve açık sorular `KARARLAR.md`'de; profil betiği ve çıktısı `ekler/`.

**Beyan (K3).** Bu şartname yazılırken **hiçbir model fit edilmedi, hiçbir walk-forward ya da canlı skor hesaplanmadı**; eski kohort, kasa ve OOT dosyaları (`registry/oot/`, `data/outcomes_oot/`, `scores/scores_oot.json`) **açılmadı**; `data/outcomes/` altındaki 7 canlı arzın dosyası açılmadı. Bakılanlar: (a) orkestratörün maruziyet tablosu (aşağıda, aynen); (b) H99'da kırılma akşamına kadarki alanların **tek değişkenli** profili (`ekler/m8_kirilma_profil.py` → `ekler/profil_kirilma.txt`; betik b. seanstan sonraki hiçbir satırı okumaz, sonuç sütunlarıyla birleştirme yapmaz); (c) `docs/MODELS.md`'nin Faz 4 / 5 / 7C bölümleri (karşılaştırıcı başarımı; koşullu keşif tabloları); (d) `docs/live/NETGL_D10_RAPOR.md` (NETGL'nin gerçekleşen yolu; NETGL bu model için zaten RETRO'dur); (e) `docs/arastirma/TR_HALKA_ARZ_PIYASASI_20261001.md`. Maruziyetin tamamı §12'dedir.

**Maruziyet beyanı — başta.** Hipotez ("kırılma türü sonraki günleri ayırır") aynı H99 verisinden doğdu. Orkestratör bu görevi yazmadan önce H99'da şuna baktı (kırılma günü b = L + 1; tür: `close == lower_limit` → taban; `close < reference` → düşüş; aksi → yükseliş/yatay):

| Kırılma (L ≥ 1, L < 10) | n | sonrasında ≥ 2 ardışık taban | D10 ≤ arz fiyatı | ort. R10 |
|---|---|---|---|---|
| tabanda kapanış | 32 | 18 | 9 | +0.258 |
| düşüşle, taban üstü | 27 | 2 | 7 | +0.421 |
| yükseliş/yatay | 8 | 0 | 0 | +0.852 |

Ek: D1 tavan değil (L = 0): 18 arzın 13'ünde D10 ≤ arz; D1 tavan kapatan 81 arzda 16. L = 10: 14 arz. Kırılma günü taban olan 35 arzın (bütün L'ler) 19'unda ertesi gün de taban. **Bu tablo tasarıma maruzdur**; H99 backtest'i bu yüzden yalnız ön elemedir (proje sahibi kararı, 1 Ekim). Tablonun ötesinde hiçbir özellik–sonuç ilişkisine bakılmadı.

İşaretler: **[ÖLÇTÜM]** = bu oturumda dosyadan/komuttan (`profil_kirilma.txt` satır atıflı); **[MARUZ]** = orkestratör tablosundan; **[ÇIKARIM]** = yorum; **[KARAR]** = bağlayıcı karar. Görev metnindeki 0–14 maddeleri → bölümler §0–§14 (aynı numara).

## Özet (10 satır)

1. **§0 sonucu: DEVAM — ama D10 hedefiyle değil.** "D10 ≤ arz" için kırılma türünün eklediği bilgi ürünün bugünkü cevabından ayırt edilemeyecek kadar küçüktür (ideal Brier kazancı ≈ −0.008; §0) → o hedef için yeni fit edilmiş model **"dur"**; D10 sorusu kırılma akşamı **yastık kuralı** (mekanik, öğrenilmez) + mevcut `ceiling_path_v0` durum-2 görünümüyle cevaplanır. Kazanç **ertesi seans taban kapanışı** hedefindedir (tabanda bozulanların %56'sında ≥ 2 ardışık taban, taban üstünde %7 [MARUZ]); ürün bu soruya bugün ters yönde cevap verir (§5).
2. **Olay:** kırılma akşamı = L + 1 = b. seansın (ilk tavan olmayan **işlem görmüş** kapanış) resmi THB yayımı; b ∈ 1..9 kapsamda (L = 0 dahil); b = 10 ve L = 10 → model çağrılmaz. H99'da 82 kırılma akşamı (b = 1: 18; 2 ≤ b ≤ 9: 64) [ÖLÇTÜM §1].
3. **Birincil hedef:** y_F1 = 1[close(D_{b+1}) == lower_limit(D_{b+1})] (ertesi seans taban kapanışı; THM Decimal eşitliği, tavan etiketinin aynası). İkincil: y_F2 = 1[D_{b+1} ve D_{b+2} taban]. D10 ≤ arz için model çıktısı **yok**; yalnız kural (§2.4).
4. **Özellikler (2):** `b_floor` = 1[close_b == lower_limit_b] ve `b_turnover` = ln(hacim_b / shares_offered) (eğitim p05/p95 kırpma, z-skor). Listeleme öncesi özellik miras alınmaz; f3 gerekmez (VEYAS tipi arzlar da kapsamda).
5. **Model:** iki başlık (F1, F2) L2-lojistik, V1.6 C ızgarası + iç arz-bırak Brier (`_fit_logit`, Faz 7C yolu); serbest parametre başlık başına 3 (2 β + sabit); beklenen olay ≈ 22–24 / 82 (F1) → ≈ 11 olay/parametre. Kural satırı `break_floor_v0@ZERO` (eğitim oranı). Yastık kuralı (`D10_STRUCTURAL_ZERO`) parametre değil, kod.
6. **Birincil hücre:** F1 Brier, `break_floor_v0` − **ürünün kırılma akşamı cevabı** (tavan yolu durum-2 karışımından türetilen P(ertesi seans taban), §5.1), yakın dönem fold'ları (ilk işlem ≥ 2024-01-01; beklenen 69 fold). İlan edilmiş ikincil: − `@ZERO`; F2 aynı iki hücre.
7. **Önceden yazılmış beklenti (§6):** birincil −0.080 [−0.140, −0.020] (dışlaması olası); − `@ZERO` −0.040 [−0.080, 0.000]. "Çok iyi" eşiği: birincil fark < −0.16 ya da üst uç < −0.08 ya da `@ZERO` farkı < −0.09 → Fable yeniden üretimi zorunlu (zaten planda; eşik eşleşme şartını bağlar).
8. **Canlı aşama `POST_BREAK` — makine sıralı [KARAR]:** kayıt akşamı YOK. Tahmin, dondurulmuş JSON + D_b'ye kadarki sha-pinli resmi bültenler + `registry/inputs/<T>.json`'daki `shares_offered`'dan skorlama anında deterministik üretilir ve `registry/post_break/<T>/` altına append-only yazılır (`exposure_class = MACHINE_SEQUENCED`, eski kohort kalıbı). Sınıf: model JSON'u D_b'den sonraki ilk bülten commit'inin atası ve push kanıtlı ise `MACHINE_SEQUENCED`, değilse `RETRO`. İnsan kanalı yapısal olarak kapalı; akşam yükü sıfır. Skor dosyası `scores/scores_break.json`, ölçek `live_break` (hiçbir ölçekle toplanmaz).
9. **Öne çıkan kuralı (önceden):** aşama 1 (canlı n < 30): yalnız yakın dönem ön elemesi (k1: hem birincil hem `@ZERO` hücresinin üst ucu < 0) ile ve "ön eleme (tasarıma maruz)" etiketiyle; aşama 2 (canlı n ≥ 30): yalnız canlı hücreler (aynı iki hücre). Eski dönem hiçbir aşamada kullanılmaz.
10. **Bedel:** Opus A+B 2 oturum, Fable yeniden üretim 1, dondurma 1, skorlama/makine kayıt 1–2, uygulama EK 5 2 → **7–8 oturum**; proje sahibinin akşam iş yükü **0**. Rejim dışı (fon krizi, D1 ≥ 2026-09-16) uyarısı kartta metin, model girdisi değil.

---

## 0. Değer mi? (devam / dur)

### 0.1 Ürün kırılma akşamı bugün ne söylüyor? [ÖLÇTÜM kod; `borsai/predict_path.py: conditional_after_break`, uygulama `app/src-tauri/src/commands/path.rs` AFTER_BREAK]

Seri t = L gününde kırıldığında ürün `ceiling_path_v0` kaydının durum-2 görünümünü gösterir (SPEC_CEILING_PATH_V0 §7): h > b için atomlar (close(D_t)/P)·(1 + v) − 1, v ∈ hücre(g(t), h − t), eşit ağırlık; medyan, p_up, q10/q90. Üç özelliği vardır:
- **Kırılma gününü hiç kullanmaz:** ölçek son tavan gününün kapanışıdır (close_t), kırılma günü kapanışı (close_b) değil; hücre m = h − t yine t'ye göredir. Tabanda bozulan arzda ürünün bütün atomları fiilen bir limit adımı (≈ %10) yukarıdadır.
- **Kırılma türünü kullanmaz:** aynı t için taban, düşüş ve yükseliş kırılmaları aynı dağılımı alır (SPEC_CEILING_PATH_V0 §3 hücreleri yalnız g ∈ {Z, B} ve m ile tanımlı).
- **"Yarın taban mı" çıktısı yoktur;** ama karışımdan türetilebilir: P_ürün(D_{b+1} taban) = ağırlığı (close_t)(1 + v) ≤ Lo(close_b) olan atomların toplamı (Lo = alt limit işlevi; §5.1). Tabanda bozulan arzda bu eşik v ≤ ≈ −0.19'dur (çift taban), taban üstünde bozulan arzda v ≤ ≈ −0.10…−0.15. Hücre aynı olduğundan ürün **taban üstünde bozulan arza daha yüksek "yarın taban" olasılığı verir** — gözlenen yönün tersi [MARUZ: ≥ 2 ardışık taban %56'ya karşı %7].

### 0.2 Yeni model ne kadar ekleyebilir? (maruziyet tablosundan; yeni skor yok)

- **D10 ≤ arz:** kırılma türü neredeyse ayırmıyor: 9/32 = 0.28, 7/27 = 0.26, 0/8 = 0 (havuz 16/67 = 0.24). Mükemmel kalibre üç sınıflı tahmin Brier'i = (32·0.28·0.72 + 27·0.26·0.74 + 0)/67 = 0.174; tek oran 0.24·0.76 = 0.182 → **ideal kazanç −0.008**. Walk-forward büzmesiyle daha az. n ≈ 60'ta aralık yarı genişliği ≈ 0.035 (Faz 7C yakın dönem hücreleri: ±0.02–0.04). Kırılma gününün ek bilgisi (close_b/close_t ∈ [0.9, 1.1]) yastığı bir adım değiştirir; bu da küçüktür. **Ürünün cevabından ayırt edilemez.** D10'da asıl belirleyici yastık aritmetiğidir ve o öğrenilmez, kodlanır: H99'daki 82 kırılma akşamının 16'sında D10 ≤ arz **mekanik olarak imkânsızdır** (hepsi b ≥ 7); mümkün olan 66 arzda [MARUZ] 29 olay (b = 1: 13/18; 2 ≤ b ≤ 6: 16/48) [ÖLÇTÜM §5 + MARUZ]. Ürün bu sıfırı zaten verir (atomlar fiziksel sınırlı; §3).
- **Ertesi seans taban:** kırılma günü taban olan 35 arzın 19'unda ertesi gün taban (0.54); taban üstünde bozulanlarda ≥ 2 ardışık taban 2/35 → ertesi gün taban oranı küçük (üst sınır belirsiz; ≈ 0.05–0.10 [ÇIKARIM]). İki sınıflı ideal Brier ≈ (35·0.25 + 47·0.07)/82 ≈ 0.146; tek oran (≈ 0.27) ≈ 0.197 → **ideal kazanç ≈ −0.05**; ürünün türetilmiş cevabı (0.1'de ters yönlü) tek orandan da kötüdür (≈ 0.24, §6 türetmesi) → ürüne karşı ≈ −0.08. Walk-forward büzmesiyle −0.03…−0.05 (`@ZERO`'ya karşı); n ≈ 65'te yarı genişlik ≈ 0.03 → **dışlaması olası.**

### 0.3 Kazanç hangi hedefte ve ne büyüklükte? [KARAR]

Birincil hedef **ertesi seans taban kapanışı (y_F1)**; ikincil **iki ardışık taban (y_F2)**. Gerekçe: (i) kazanç yalnız burada ölçülebilir büyüklüktedir; (ii) ürünün burada cevabı yoktur ya da terstir; (iii) proje sahibinin "düşer mi" sorusuna kırılma akşamı en doğru cevap "yarın da tabanda kilitli kalır mı" sorusudur: tabanda kilit = çıkış yok, ve yastık k_b adım ise D10 ≤ arz için en az ⌈k_b⌉ ardışık tabana yakın bir düşüş gerekir (§2.4). D10 ≤ arz hedefi için **model çıktısı tanımlanmaz**; kart D10 için yastık kuralını ve ürünün mevcut p_up(D10)'unu gösterir.

### 0.4 Bedeli nedir?

| Kalem | Tahmin |
|---|---|
| Opus A (kod, tablo, tarif, kurallar, testler) + B (backtest, MODELS.md, günlük) | 2 oturum |
| Fable sıfırdan yeniden üretim | 1 |
| Dondurma (`models/INDEX_POST_BREAK.json`, push, kanıt) | 1 |
| Skorlama bloğu + makine kayıt yazıcı + `docs/SCORES.md` §8 | 1–2 |
| Uygulama (EK 5: Rust portu, kart, altın pin) | 2 |
| **Toplam** | **7–8 oturum** |
| Proje sahibi akşam yükü | **0** (makine sıralı; §9). İsteğe bağlı LIVE yükseltmesi v0'da yok |
| Yeni veri alanı / belge toplama | yok (yalnız pinli resmi bültenler + mevcut `registry/inputs`) |

### 0.5 Sonuç

**Devam — birincil hedef "ertesi seans taban kapanışı" olmak şartıyla; "D10 ≤ arz" için yeni fit edilmiş model DUR'dur (beklenen kazanç ≈ −0.008 Brier, ürünün bugünkü cevabından ayırt edilemez), o soru yastık kuralı ve mevcut ürünle cevaplanır.** Proje sahibi D10'u birincil hedef olarak ısrar ederse bu şartnamenin cevabı "dur"dur (açık soru 1).

## 1. Olay ve kapsam

**1.1 Kimlik [KARAR].** `model_id = break_floor_v0`; `algorithm = l2_logit_v1_6_grid` (V1.5/V1.6/Faz 7C Logit yolu); `stage = POST_BREAK`; `family = break_floor_v0`; kural satırı `break_floor_v0@ZERO` (C = ZERO; aday değil, INDEX'te kayıtlı). Dizin: `models/INDEX_POST_BREAK.json` (ayrı dizin; POST_D1 emsali H4). Şartnamedeki herhangi bir şey (olay tanımı, özellik, dönüşüm, ızgara, eğitim kümesi, fold kuralı, karşılaştırıcı tanımı) değişirse yeni model_id (CLAUDE.md kural 5). Terfi yok; yan yana.

**1.2 Kırılma akşamı tanımı [KARAR].** SPEC_SCORING §2–§3 tanımlarıyla: D_h = payın işlem gördüğü h'inci resmi seans; `ceiling_close_k = 1[Decimal(close_k) == Decimal(upper_limit_k)]`; L = D1'den başlayan kesintisiz tavan sayısı. **b = L + 1**: ilk tavan olmayan **işlem görmüş** kapanışın seans numarası. **Kırılma akşamı E_b** = D_b'nin tarihi, THB yayımından sonra (ölçülen 18:25–18:40, SPEC_POST_D1_V0 §7.2). Kapsam: **b ∈ 1..9** (D_{b+1} ≤ D10 var). H99'da [ÖLÇTÜM §1]: b dağılımı 1: 18, 2: 11, 3: 4, 4: 13, 5: 12, 6: 8, 7: 6, 8: 6, 9: 4, 10: 3; L = 10: 14.

| Durum | Davranış [KARAR] |
|---|---|
| **L = 0 (b = 1; D1 tavan değil)** | **Kapsamda.** Mekanizma (tabandaki satıcı kuyruğu) aynı; özellikler aynı alanlardan tanımlı; D1'de referans = snap(P) (SPEC_CEILING_PATH_V0 §2). H99'da 18 arz; taban kapanış 4/18 [ÖLÇTÜM §2]. `post_d1_hazard_v0` bu arzlarda `NOT_APPLICABLE`'dır; aynı akşam iki model, biri kapsam dışı — tek akış (§9.5). Grup göstergesi (Z/B) **özellik değildir** (bütçe §4); kırılım keşif |
| **b = 10** (seri D9'a kadar, D10'da bozuldu) | D_{b+1} yok → hedef tanımsız → `NOT_APPLICABLE_B10`; payda sayacı `n_not_applicable_b10`. H99: 3 |
| **L = 10** (seri hiç bozulmadı) | Kırılma akşamı yok → `NOT_APPLICABLE_NO_BREAK`; H99: 14. D10 sorusu zaten gerçekleşmiştir |
| **b = 9** | F1 tanımlı (D10), **F2 tanımsız** (D11 yok) → F2 başlığı `TARGET_UNDEFINED_F2`; tahmin üretilmez |
| **Tam gün durdurma** (THB satırı yok ya da sözleşme = 0 ya da kapanış ≤ 0) | Seans sayılmaz, D_h kayar (SPEC_SCORING §2); kırılma, işlem görmüş ilk tavan-dışı kapanıştır. Hedef D_{b+1} de işlem görmüş sonraki seanstır; durdurma seriyi ve hedefi bozmaz. 15 seans sınırı → `TARGET_UNAVAILABLE` (bütün modeller için aynı anda) |
| **Yarım gün** (D_b ya da D_{b+1}) | Seans sayılır; tahmin üretilir; `WARN_B_HALF_DAY` / hedef satırına `half_day` işareti. H99'da D_b yarım gün 1/85 [ÖLÇTÜM §7] |
| **Gün içi geçici durdurma** (D_b) | Tahmin + `WARN_B_INTRADAY_HALT` |
| **Alt limit yok** (D_b THM satırı yok ya da `ALT LIMIT FIYATI` boş/≤ 0) | RET `B_LIMIT_NA` (`b_floor` tanımsız; tahmin edilmez). H99'da 0 [ÖLÇTÜM §7] |
| **Üst limit NA bir seansta** (tavan etiketi NA) | L ve b o arzda hesaplanamaz (SPEC_SCORING §3) → `NOT_SCORABLE_STREAK_NA` |
| **Hedef seansta alt limit NA** (D_{b+1} THM yok) | y_F1 NA → `TARGET_LABEL_NA` (tahmin yazılır, skorlanmaz; sayılır) |
| **Taban etiketi, yarım/durdurma günü** | Etiket yine Decimal eşitliğidir; kural sabiti kullanılmaz |

**1.3 Açık varsayımlar (dondurmadan önce orkestratör doğrular).** (i) Günlük fiyat marjı ±%10, limitler içe yuvarlanır, D1 baz fiyatı arz fiyatının adıma oturtulmuş hali (SPEC_CEILING_PATH_V0 §2; H99'da alt limit 990/990 birebir); BIST Pay Piyasası Prosedürü rev. 54 (21.09.2026) içeriği doğrulanmadı. Model bu sabitleri **özellik tanımında kullanmaz** (taban etiketi THM alanıyla Decimal eşitliğidir); yalnız **yastık kuralı** (§2.4) ve ürün karşılaştırıcısının eşiği (§5.1) 0.9 ve adım tablosuna dayanır. Koruma: her kırılma akşamında THM'den `lower_limit_b / reference_b` ölçülür; [0.9, 0.9020] dışındaysa `BAND_RULE_MISMATCH` uyarısı, yastık rozeti gösterilmez, satır `regime_tags`'e `BAND_CHANGED` alır (model tahmini yine üretilir ve skorlanır). (ii) `referans_b = kapanış_{b−1}` (H99'da 67/67 [ÖLÇTÜM §7]).

## 2. Hedefler ve tek birincil

**2.1 Birincil [KARAR].** `y_F1 = 1[Decimal(close(D_{b+1})) == Decimal(lower_limit(D_{b+1}))]` — ertesi işlem görmüş seansın resmi THB kapanışı o seansın THM alt limitine eşit (tavan etiketinin aynası, SPEC_SCORING §3 kuralıyla; "%10" varsayımı yok, ham metin Decimal). Çıktı `p_floor_F1 = P(y_F1 = 1)`. Tanımsız: b = 10, L = 10, THM NA (§1.2).

**2.2 İkincil [KARAR].** `y_F2 = 1[D_{b+1} taban VE D_{b+2} taban]` (F ≥ 2, F = D_{b+1}'den başlayan ardışık taban kapanış sayısı). Çıktı `p_floor_F2`. b ≤ 8'de tanımlı. **Not:** F ≥ 2, kırılma günü tabansa "≥ 3 ardışık taban"a değil, kırılmadan **sonraki** iki güne bakar; maruziyet tablosunun "sonrasında ≥ 2 ardışık taban" sütunu budur.

**2.3 Neden "D10 ≤ arz" değil.** §0.2. Ayrıca D10 hedefi b'ye göre giderek daha çok mekaniktir (b ≥ 7'de imkânsız; b = 6'da yalnız bütün kalan günler taban ise mümkün: mümkün en düşük D10/P ∈ (0.9, 1] olan 8/66 arz [ÖLÇTÜM §5]) ve olay sayısı yakın dönemde küçüktür.

**2.4 D10 için kural (parametre yok; kod) [KARAR].** Kırılma akşamı için `D10_STRUCTURAL_ZERO`: `min10 = Lo^{(10 − b)}(close_b)` (alt limit işlevi `predict_path.lower_limit`, 10 − b kez; Decimal); `min10 > P` ise **P(D10 ≤ arz) = 0 (yapısal)** rozeti; değilse `k_b = ln(close_b/P)/ln(1/0.9)` ve `r_b = 10 − b` ile "arz altı için kalan r_b seansta ≈ ⌈k_b⌉ taban gerekir" metni ve ürünün mevcut durum-2 p_up(D10)'u. Yaklaşık kural k_b ≥ r_b ile adım zinciri H99'da 82/82 aynı sonucu verir [ÖLÇTÜM §5]. Bu bir model değildir; skorlanmaz; `BAND_RULE_MISMATCH`'te gösterilmez.

## 3. Özellikler (2; mekanizmayla; sonuç görmeden)

Kaynak: D_b tarihli resmi THB ve THM (`<TICKER>.E` satırı; alan adları `borsai/outcomes.py: THB_COLUMNS / THM_COLUMNS`), ham metin → `Decimal(str)`. `shares_offered`: canlıda `registry/inputs/<T>.json` `fields.shares_offered.value` (PIT: `source_published_at < D_1`, `registry.inputs_pit_problems`); H99'da `training_table.csv` `shares_offered` (f1/f2 ile aynı alan; ek satış dahil olduğu arzlarda dahil, DATA_NOTES §4).

| Ad | Tanım | Alan | Birim | Dönüşüm (eğitimden, arz düzeyinde, fold içinde) |
|---|---|---|---|---|
| `b_floor` | 1[`Decimal(KAPANIS FIYATI)_b == Decimal(ALT LIMIT FIYATI)_b`] | THB `KAPANIS FIYATI`; THM `ALT LIMIT FIYATI` | 0/1 | z-skor (ortalama, popülasyon std ddof = 0); σ = 0 ise düşer |
| `b_turnover` | ln(`TOPLAM ISLEM ADEDI`_b / `shares_offered`) | THB `TOPLAM ISLEM ADEDI` | ln(pay/pay) | [p05, p95] kırpma (Type-7, `preprocess.quantile_type7`, ln ölçeğinde — H11 kalıbı) → z-skor |

**Eşitlik ve adım kuralı [KARAR].** `b_floor` ham metinlerin Decimal eşitliğidir ("10.12" == "10.120"; adım/yuvarlama uygulanmaz) — tavan etiketiyle aynı kural; düzeltilmiş `close`/`lower_limit` sütunları kullanılmaz. H99'da kapanış ya tam alt limitte ya da ≥ 5 adım üstünde: "1–4 adım üstü" 0/64 [ÖLÇTÜM §3] → "tabana ≤ 1 adım" kutusu gereksiz. Gün boyu taban kilidi (`EN YUKSEK == ALT LIMIT`) H99'da 7/64 + 1/18 [ÖLÇTÜM §3]: özellik olarak çok seyrek; yalnız `WARN_B_FLOOR_LOCK_ALLDAY` bilgi işareti ve keşif kırılımı. "Tabana dokundu ama üstünde kapandı" 4/64: `b_floor = 0`.

**Neden bu ikisi [ÇIKARIM, sonuç görülmeden].**
- **Taban kapanışı:** fiyat alt limitteyken satış emirleri limitte kuyruk oluşturur; kapanış tam limitteyse kuyruk gün sonunda tükenmemiştir ve ertesi sabah aynı fiyat seviyesinin bir adım altında yeniden kuyruk olur (tavan kilidinin aynası; Bildik & Gülay 2006 "kilitlenme dokunmadan farklı"; PLOS ONE 2015 tabanda kapanan günden sonraki gün ~%86 aynı yön [özet düzeyi]). Taban üstünde kapanış, satıcıların gün içinde alıcı bulduğunu gösterir. Beklenen: β_floor > 0 (F1 ve F2'de).
- **El değiştirme:** tabanda kapanan günde hacim **alıcıların** kararıdır (satıcı kuyruğu sonsuz gibi davranır): yüksek hacim = kuyruğun büyük kısmı emildi; düşük hacim = kuyruk sürüyor. Taban üstü kapanışta yüksek hacim = satıcıların çıkışı tamamlandı. İki durumda da beklenen β_turn < 0 (düşük güven; karşı-mekanizma: yüksek hacim "çok satıcı var" demek olabilir → β_turn > 0). İşaret başarı ölçütü değildir. H99'da kırılma günü el değiştirme medyanı 1.63 × arz edilen pay (taban kırılmalarında 1.04, taban üstünde 1.92) ve seri günlerinin ortalamasının 8.3 katı [ÖLÇTÜM §4]; dağılım geniş (p05 0.11, p95 2.9) → ln ve kırpma.
- **Etkileşim (floor × turnover) alınmadı:** 3. parametre; olay bütçesi (§4) izin vermez; v1 adayı.
- **Alınmayanlar:** b ya da r_b (hedef ertesi gündür, yastık ertesi günün tabanını mekanik sınırlamaz); Z/B grubu (18 arz; mekanizma ortak); seri hacim şoku `hacim_b / ort(hacim D1..D_L)` (el değiştirmeyle örtüşür; b = 1'de tanımsız); açılış/AOF konumu (kapanış türüyle örtüşür: AOF bant konumu medyanı 0.34 [ÖLÇTÜM §3]); sözleşme sayısı (hacimle ln ölçeğinde örtüşür); VBTS kademesi (KAP ilanı; 3 vaka, kriter gizli; v0 dışı); fiyat istikrarı (izahname alanı, H99'da 20/99); **listeleme öncesi özellikler (f1–f3, ek satış) miras alınmaz** — soru "kırılma günü ne söylüyor"dur ve f3'süz arzlar da kapsamda kalır.

**Eksik / tutarsız hâller.**

| Durum | Davranış |
|---|---|
| D_b THM alt limiti boş/≤ 0 | RET `B_LIMIT_NA` |
| `TOPLAM ISLEM ADEDI`_b boş/≤ 0 iken sözleşme > 0 | RET `B_VOLUME_INVALID` |
| D_b açılış/en yüksek/en düşük boş ya da ≤ 0 | RET `B_FIELD_INVALID` (H24 kalıbı; H99'da 0) |
| `shares_offered` yok/≤ 0 | RET `INPUT_SHARES_OFFERED` |
| `shares_offered` PIT değil (`source_published_at ≥ D_1`) | tahmin + `inputs_pit_ok = false` → sınıf RETRO (§9.3) |
| `b_turnover` eğitim p05/p95 dışı | kırpılır, `clipped: true`, `B_TURNOVER_CLIPPED_TO_TRAINING_P05_P95` |
| özellik eğitim min/max dışı | `OUT_OF_TRAINING_RANGE` uyarısı |
| `OZEL ISLEM BILDIRIMI ISLEM ADEDI`_b > 0 | hacim düzeltilmez; `WARN_B_SPECIAL_TRADES` |
| `EN YUKSEK_b == ALT LIMIT_b` | `WARN_B_FLOOR_LOCK_ALLDAY` (bilgi) |
| `lower_limit_b / reference_b ∉ [0.9, 0.9020]` | `BAND_RULE_MISMATCH` (§1.3) |

Ret kodları B3 biçimindedir: `refused = {code, field, reason}`, öneksiz; kapsam dışı `not_applicable = {code ∈ {B10, NO_BREAK}, reason}`.

## 4. Model sınıfı ve parametre bütçesi

**4.1 Model [KARAR].** Başlık h ∈ {F1, F2} için bağımsız L2-lojistik: `logit P(y_h = 1) = α_h + β_h · z`, z = z-skorlu (`b_floor`, `b_turnover`). SPEC_V1_6 §3 Logit yolu aynen (Faz 7C ile aynı giriş noktası `fit_fall_horizon` ya da eşdeğeri; `_fit_logit`, `V1_6_C_GRID = (ZERO, 0.0001, 0.001, 0.01, 0.1, 1, 10, 100)`, iç arz-bırak LOOCV Brier ile seçim, eşitlikte `rank_C`, aday başına yakınsamama politikası, azınlık sınıfı < 2 → `fallback_C`; ön işleme her iç bölmede yalnız o bölmenin eğitim satırlarından). Yeni tarif `BREAK_V0_RECIPE`: `substantive = ("b_floor", "b_turnover")`, `winsor = ("b_turnover",)`, `log = ()` (ln özellik tanımında), `indicator = False`, `impute = False`. Eski tarifler ve altın dosyalar bayt-eşit kalır.

**4.2 Sıfır model [KARAR].** `break_floor_v0@ZERO`: her başlık için C = ZERO, p = eğitim oranı (kapalı biçim, Fraction; `fall_d10_v0_pooled@ZERO` kalıbı). INDEX_POST_BREAK'te kayıtlı kural satırı; backtest'te fold'un eğitim oranı ("kırılmalar arasındaki taban oranı", genişleyen pencere). Ayrıca `@INF` gerekmez (lojistikte ZERO ucu zaten yalnız sabit).

**4.3 Bütçe.** F1: 82 satır, beklenen olay ≈ 22–24 [MARUZ 19 taban→taban + taban üstü kırılmalardan ≈ 3–5, ÇIKARIM]; 2 β → ≈ 11 olay/parametre (≥ 10). F2: 78 satır (b ≤ 8), olay ≈ 20–23 → ≈ 10–11. Azınlık sınıfı `b_floor = 1`: 35/82. Üçüncü özellik bütçeyi 7'ye düşürür → alınmadı. Yakın dönem alt kümesinde (69 fold) eğitim kümesi fold'a göre 13…81 satır; erken fold'larda ZERO seçimi olası (§6).

**4.4 Eğitim (dondurma).** Küme `H99_BREAK_B_LE_9`: SESSIONS dosyasından kurulan kırılma tablosu (§7.1), b ≤ 9 olan 82 arz (F2 başlığı b ≤ 8: 78). Kesim 2026-08-19 (sonuç seansları ≤ 2026-08-19; H99'un son arzı QUICK, D1 2026-08-06). JSON alanları: V1.5/7C kalıbı + `stage: "POST_BREAK"`, `horizons: {F1: {p_floor: {kind: logit | constant, columns, coef, intercept}}, F2: {...}}`, `preprocessing {columns, winsor.b_turnover.{p05,p95}, mean, std, dropped}`, `feature_ranges`, `target_definition: {F1: "close(D_{b+1}) == lower_limit(D_{b+1})", F2: "F1 and close(D_{b+2}) == lower_limit(D_{b+2})"}`, `event_definition: "b = L + 1, first traded non-ceiling close; b in 1..9"`, `training {set, n_F1, events_F1, n_F2, events_F2, cutoff_date, tickers_sha256, break_fields_sha256 (82 × (ticker, b, close_b, lower_b, volume_b) ham metin), data_version_sha256, sessions_file_sha256}`, `structural_zero_rule: {name: "D10_STRUCTURAL_ZERO", margin: "0.10", tick_table: ...}` (gösterim sabiti; parametre değil), `spec_document {path, sha256}`.

## 5. Karşılaştırıcılar ve birincil hücre

Hepsi eşleşik fark (model − karşılaştırılan; negatif = model iyi), Brier **kırpmasız** (Faz 7C kalıbı; karşılaştırıcı tam 0/1 verebilir), aynı fold'lar/arzlar, aylık blok bootstrap (backtest: SPEC_DEVIATIONS C7, blok = ilk işlem ayı, 4000, `random.Random(20260921)`; canlı: SPEC_SCORING §8). Dil SPEC_SCORING §8.

**5.1 Asıl karşılaştırıcı: ürünün kırılma akşamı cevabı [KARAR].** `PRODUCT_BREAK_FLOOR`: tavan yolu durum-2 karışımından türetilen taban olasılığı.
```
atoms(h) = conditional_after_break(hücreler(kesim), limit yolu(P), t = L, kapanış(D_1..D_b))["D_h"] atomları   # (r, w), S kısmı yok
eşik_F1  = Lo(close_b) / P − 1                                   # D_{b+1}'de mümkün en düşük getiri = taban
P_ürün(F1) = Σ { w : r ≤ eşik_F1 + 1e-12 },  h = b + 1
eşik_F2  = Lo(Lo(close_b)) / P − 1 ;  P_ürün(F2) = Σ { w : r_(h = b + 2) ≤ eşik_F2 + 1e-12 }
```
- Hücreler ve limit yolu `ceiling_path_v0`'ınkidir; durum-2'de S kısmı düştüğünden çıktı seri modelinden bağımsızdır (`ceiling_path_v0`, `@INF`, `pb_ceiling_path_v0` aynı sayıyı verir; f3 gerekmez) → her arz için tanımlıdır. Canlıda ürün, **listeleme öncesi dondurulmuş kayıttaki** hücreleri gösterir; backtest'te bunun karşılığı hücrelerin kesim **D_1(k)** (test arzının ilk işlem günü = Faz 4 fold kesimi) ile kurulmasıdır: `predict_path.build_cells(units, cutoff = D_1(k))` (H14 kalıbı; `cells_max_session_date < D_1(k) ≤ T_k`; kesişen 87 fold'da Faz 4 ledger'ının hücre sayılarıyla birebir). Kırılma akşamına kadar biriken ek gözlemler **verilmez** (ürün o akşam onları görmez). `POST_BREAK_INSUFFICIENT` ise çift düşer (sayılır). Canlıda arzın birincil listeleme-öncesi kaydındaki `ceiling_path_v0` (yoksa `ceiling_path_v0@INF`) `limit_path` ve dondurulmuş hücreleriyle; kayıt yoksa `NOT_AVAILABLE`.
- Bu, ürünün gösterdiği D_{b+1} q10'unun olasılık karşılığıdır; "ürün o akşam ne der"in sayısal tanımı budur. F2 eşiği için not: Lo∘Lo düzeyine iki taban olmadan inmek adım yuvarlaması yüzünden sınırda mümkün olabilir; eşik tanımı yine de budur (karşılaştırıcı, etiket değil).
- Backtest'te ayrıca `ceiling_path_v0`'ın **koşulsuz** ve j = L durum-1 görünümleri karşılaştırıcı DEĞİLDİR (kırılma bilgisini içermez).

**5.2 Hücreler.**

| Öncelik | Metrik | Karşılaştırılan | Fold kümesi |
|---|---|---|---|
| **BİRİNCİL** | F1 Brier | `PRODUCT_BREAK_FLOOR` (P_ürün(F1)) | yakın dönem (ilk işlem ≥ 2024-01-01) |
| ilan edilmiş ikincil | F1 Brier | `break_floor_v0@ZERO` (fold eğitim oranı) | yakın dönem |
| ilan edilmiş ikincil | F2 Brier | `PRODUCT_BREAK_FLOOR` (P_ürün(F2)); `@ZERO` | yakın dönem |
| ilan edilmiş ikincil | F1 Brier | kırılma türüne koşullu oran: `base_floor_by_type` = fold eğitiminde `b_floor` sınıfına göre oran (2 hücreli tablo) | yakın dönem — "özelliklerden lojistiğin payı" |
| bilgi | `PRODUCT_BREAK_FLOOR − @ZERO` (ürün tek orandan kötü mü) | | yakın dönem |
| keşif | bütün fold'lar; 2023 fold'ları; b = 1 / 2 ≤ b ≤ 9 kırılımı; `b_floor` sınıflarına göre kalibrasyon; yıl | | hüküm yok |

Birincil hücrenin gerekçesi: K2 — ürün bugün bu akşam bir cevap gösteriyor; yeni model önce onu geçmelidir. `@ZERO` hücresi, ürün karşılaştırıcısının bu hedefte zayıf olması yüzünden **öne çıkan kuralının zorunlu ikinci ayağıdır** (§8): ürünü geçip tek oranı geçemeyen model öne çıkarılmaz.

## 6. ÖNCEDEN YAZILMIŞ BEKLENTİ

Bu bölüm 2026-10-01'de, bu model için hiçbir kod ve skor yokken yazıldı; sonradan değiştirilmez. Sayılar maruziyet tablosundan, `profil_kirilma.txt`'nin tek değişkenli sayılarından ve MODELS.md'deki Faz 5/7C hücre genişliklerinden **mekanikle** türetildi; hiçbir yeni skor hesaplanmadı. Birim: Brier farkı (kesir); negatif = model iyi.

**Türetme [ÇIKARIM].** Taban kırılmasında ertesi gün taban oranı a = 19/35 = 0.54 [MARUZ]; taban üstü kırılmada b ≈ 0.08 (≥ 2 ardışık taban 2/35'ten üst sınır; ÇIKARIM). Sınıf payları 35/82 ve 47/82; havuz oranı ≈ 0.28. Tek oran Brier ≈ 0.197; iki sınıflı mükemmel kalibrasyon ≈ 0.146 (ideal kazanç −0.051). Walk-forward: erken fold'larda küçük eğitim (13…30 satır), L2 büzmesi, ZERO seçimi → ideal kazancın %60–80'i: **−0.030…−0.045**. Ürün karşılaştırıcısı: taban kırılmasında P_ürün ≈ 0.30 (B m = 2 hücresinde çift taban payı ≈ 20/67), taban üstünde ≈ 0.35–0.50 (eşik daha gevşek) → Brier ≈ (35·(0.248 + 0.058) + 47·(0.074 + 0.116))/82 ≈ 0.24 → ürün tek orandan ≈ +0.04 kötü; model − ürün ≈ −0.08. Yakın dönem alt kümesi (69 fold, 22 ay bloğu) için aralık yarı genişliği Faz 7C emsalinde 0.02–0.04; ürün farkında atom gürültüsü nedeniyle 0.05–0.06.

| Hücre | Karşılaştırılan | Beklenen fark | Aralık | Aralık 0'ı | Gerekçe (kısa) |
|---|---|---|---|---|---|
| **F1 Brier (BİRİNCİL)** | `PRODUCT_BREAK_FLOOR` | **−0.080** | **[−0.140, −0.020]** | **dışlaması olası** | ürün ters yönlü; türetme yukarıda |
| F1 Brier | `@ZERO` | −0.040 | [−0.080, 0.000] | dışlaması olası, garanti değil (alt uç ≤ 0) | ideal −0.051 × büzme |
| F1 Brier | `base_floor_by_type` | −0.005 | [−0.025, +0.015] | içerir | lojistiğin 2 hücreli tabloya eklediği yalnız el değiştirme |
| F2 Brier | `PRODUCT_BREAK_FLOOR` | −0.050 | [−0.110, +0.010] | içerir ya da negatif dışlar | F2 olayı daha seyrek; ürün eşiği de daha sıkı |
| F2 Brier | `@ZERO` | −0.030 | [−0.070, +0.010] | içerir | 18/32 vs 2/27 güçlü ama olay ≈ 20 |
| bilgi: `PRODUCT − @ZERO` (F1) | — | +0.040 | [0.000, +0.090] | pozitif dışlar ya da içerir (alt uç ≥ 0) | ürün tek orandan kötü |
| Kalibrasyon | ort(p_F1) − gözlenen F1 oranı | \|Δ\| ≤ 0.06 | — | — | lojistik sabit; yakın dönem oranı 2023'ten düşük olabilir |
| Katsayı işareti | β_floor (F1) | > 0; nihai fit ve ZERO olmayan fold'ların ≥ %90'ında | — | — | mekanizma |
| Katsayı işareti | β_turn (F1) | < 0 (düşük güven) | — | — | karşı-mekanizma var |
| Seçilen C | nihai fit F1 | 0.1–1 en olası; ZERO olası değil | — | — | 2 özellik, ≈ 23 olay |
| Seçilen C | fold'lar F1 | ZERO payı ≤ %20 (yakın dönem FIT_OK fold'ları) | — | — | erken fold'lar küçük |
| n | F1 birincil eşleşik (yakın dönem) | 60–69 | — | — | 69 fold − `POST_BREAK_INSUFFICIENT` − `INSUFFICIENT_TRAINING_HISTORY` |
| n | F2 (yakın dönem) | 55–65 | — | — | b = 9 düşer |

Hangi hücrede kazanç en olası: **F1 − ürün**, sonra **F1 − `@ZERO`**. En az olası: `base_floor_by_type`'a karşı (lojistik yalnız ikinci özelliği ekler).

**Başarısızlık tanımları (backtest'te de canlıda da aynı sözcüklerle):**
- (a) **"basit kuraldan ayırt edilemiyor":** yakın dönem F1 − `@ZERO` aralığı 0'ı içeriyor → model yine dondurulur; kart bunu yazar; **öne çıkarılmaz** (§8 k1).
- (b) **"zarar veriyor":** birincil aralık tamamen 0'ın üstünde → dondurulur; kartta "ürünün cevabından kötü".
- (c) **"özellikler bilgi eklemiyor":** nihai fit'te F1 başlığı C = ZERO ya da yakın dönem FIT_OK fold'larının ≥ %50'sinde ZERO.
- (d) **Kalibrasyon:** |ort(p_F1) − gözlenen| > 0.15 (n ≥ 30) → "düzey kayması" notu.
- (e) **Canlı (n ≥ 30):** birincil aralık üst ucu ≥ 0 → "ayırt edilemiyor" / tamamen 0'ın üstünde → "geçemiyor"; `@ZERO` hücresi aynı. n < 30 hüküm yok; n < 10 satır tablosu.
- Başarı sayılacak (yalnız canlı, n ≥ 30): birincil VE `@ZERO` aralıklarının ikisi de 0'ı negatif tarafta dışlıyor. Backtest'te aynı olursa yalnız "backtest'te geçiyor (tasarıma maruz)".

**Her durumda:** v0 bu şartnameyle dondurulur; tutmayan beklenti adıyla MODELS.md'ye yazılır. **Beklentiden çok iyi** (tanım: birincil fark < −0.160, ya da birincil aralığın üst ucu < −0.080, ya da F1 − `@ZERO` farkı < −0.090) → dondurmadan önce Fable'ın bu şartnameden bağımsız sıfırdan yeniden üretimi ledger'larla |Δ| ≤ 1e-9 eşleşmelidir (Faz 4/5/7C kalıbı; yol zaten planda, eşik eşleşme şartını bağlar).

**Rejim dışı okuma (önceden; §11):** canlı dönem fon krizi rejiminde başladı (BIST100 Eylül 2026 −%16,65; NETGL D1 = krizin ilk günü). Beklenti: kriz penceresinde gözlenen taban oranı eğitim oranının üstünde → ort(p_F1) < gözlenen (model tabanı **az** tahmin eder). `regime_tags = FON_KRIZI_2026` (D1 ≥ 2026-09-16) satırları ayrı kırılımda ("yetersiz örnek" etiketiyle) gösterilir, n'den düşülmez, model girdisi olmaz.

## 7. Backtest planı (Opus için)

**7.1 Kırılma tablosu.** `borsai/post_break.py: build_break_table(sessions_csv, train)` SESSIONS dosyasını arz başına seans sırasıyla okur: `ceiling_close_k` (thb_raw_close == thm_raw_upper_limit), L, b; b ≤ 9 ise D_b alanları (`thb_raw_open/high/low/close/volume/trade_count`, `thm_raw_reference_price/upper_limit/lower_limit`, `session_type`, `security_trading_status`, `target_session_date`) ve **yalnız etiket için** D_{b+1} (ve b ≤ 8 için D_{b+2}) `thb_raw_close`, `thm_raw_lower_limit`, `target_session_date`. **Yükleyici beyaz listesi:** D_b'den sonraki satırlarda yalnız bu üç alan okunur (erişim sayacı testi, H20 kalıbı). Kabul [ÖLÇTÜM §1–§2]: 82 satır; b dağılımı §1.2; `b_floor` toplam 35 (31 + 4); L = 10: 14; b = 10: 3.

**7.2 Plan [KARAR].** `PLAN_BREAK_H99 = H99_BREAK_WALK_FORWARD_E_CUTOFF_B_LE_9_MIN10ROWS_5EV_5NE`:
- Test birimi: b ≤ 9 olan her arz k; kesim **T_k = E_b(k)** = D_b(k)'nin tarihi (kırılma akşamı; o günün bülteni o akşam yayımlanır, test arzının kendi D_b alanları girdidir).
- Eğitim satırı j (F1): ancak `date(D_{b_j + 1}) < T_k` (kesin önce; aynı gün dışarıda); F2: `date(D_{b_j + 2}) < T_k`. Aynı gün listelenen ya da aynı gün kırılan arzlar birbirini eğitmez.
- Skorlanabilirlik: eğitimde ≥ 10 satır, ≥ 5 olay, ≥ 5 olay-dışı; değilse `INSUFFICIENT_TRAINING_HISTORY`. Azınlık < 2 → `fallback_C` (V1.6 politikası).
- Ön işleme fold içinde (kırpma, μ, σ yalnız eğitim satırlarından; iç CV'de her bölmede yeniden). `b_floor` σ = 0 → düşer.
- Her fold: iç LOOCV → C → nihai → test arzı için p_F1, p_F2 (b = 9: F2 `TARGET_UNDEFINED`), `@ZERO` oranı, `base_floor_by_type`, `PRODUCT_BREAK_FLOOR` (hücreler `build_cells(units, cutoff = D_1(k))` — ürünün listeleme öncesi kaydının karşılığı, §5.1; limit yolu `limit_path(P)`, gözlenen kapanışlar D_1..D_b SESSIONS'tan — bu okuma yalnız karşılaştırıcı içindir; H27 kalıbı), gerçekleşen y_F1, y_F2.
- **Yakın dönem hücresi:** ilk işlem ≥ 2024-01-01 fold'ları (beklenen 69 [ÖLÇTÜM §1]; 2023: 13 keşif). Blok = ilk işlem ayı (Faz 7 kalıbı; 22–25 ay).
- **Sızıntı noktaları ve testleri:** (i) D_b'den sonraki satırlarda beyaz liste dışı sütun erişimi → kırmızı; (ii) test arzının D_b alanları ön işleme istatistiklerini değiştirmez (duyarlılık testi); (iii) her fold'da `training_max_label_date < T_k` ve `cells_max_session_date < D_1(k)`; (iv) aynı gün kuralı sentetik testle; (v) etiket sütunları yalnız skor/etiket kodunda (grep testi); (vi) karşılaştırıcı hücreleri Faz 4 ledger'ının aynı kesimli fold'uyla sayı eşitliği (kesişen 87 fold'da `cells_n_*` birebir).
- **Ledger sütunları (sıra sabit):** `model_id, fold_id, ticker, first_trading_date, b, break_date (= T), training_n, training_events, training_nonevents, training_max_label_date, training_tickers_sha256, selected_C_F1, inner_table_F1 (JSON), selected_C_F2, inner_table_F2, columns, coef_floor_F1, coef_turn_F1, intercept_F1, coef_floor_F2, coef_turn_F2, intercept_F2, clip_p05, clip_p95, mean_floor, std_floor, mean_turn, std_turn, dropped, test_b_floor, test_b_turnover_ratio, test_b_turnover_clipped, test_floor_lock_allday, test_half_day, p_F1, p_F2, zero_F1, zero_F2, by_type_F1, product_F1, product_F2, product_status, cells_max_session_date, structural_zero_D10 (0/1; bilgi), realized_F1, realized_F2, status`. `status ∈ {FIT_OK, INSUFFICIENT_TRAINING_HISTORY, NOT_APPLICABLE, MODEL_NOT_FIT_SINGLE_CLASS, MODEL_NOT_FIT_DID_NOT_CONVERGE}`.
- **Metrik ve rapor:** §5.2 hücreleri; `docs/MODELS.md` "Faz 8: kırılma akşamı" bölümü (`report_faz8.py`, `OPERATIONAL_RULES_FAZ8` sonuç görülmeden kodda; §6 tablosu satır satır tuttu/tutmadı; Faz 5 H16 ve 7C T6 kuralları aynen: fark aralığı kapalı, "(nokta ≈)" değerlendirilmez, konum "aralık içinde / altında — beklentiden çok iyi / üstünde"); `experiments/log.jsonl`'a `kind: backtest` (`spec_sha256` kanonik sözlük + `spec_document_sha256` bu dosya; `sessions_file_sha256`; `path_cells_source`); duyarlılıklar (`kind: sensitivity`, model değil): `__sens_floor_only`, `__sens_turnover_only`, `__sens_with_group_Z`.
- `ScaleMixError`: hücreler `scale = backtest_break`; koşulsuz/koşullu tavan ölçekleriyle birleştiren çağrı hata verir.

**7.3 Dondurma sırası.** Backtest → MODELS.md → Fable yeniden üretim (|Δ| ≤ 1e-9; "çok iyi" tetiklense de tetiklenmese de) → `python -m borsai.freeze --post-break break_floor_v0 break_floor_v0@ZERO` temiz ağaçta → `models/INDEX_POST_BREAK.json` (yeni; `borsai.model_index/1`) → commit → push → push kanıtı. `models/INDEX.json`, `INDEX_POST_D1.json` ve 28 model dosyası değişmez. Bu commit `commit_frozen(m)`'dir.

## 8. Uygulama "öne çıkan" kuralı (önceden yazılı) [KARAR]

Kart: "Kırılma akşamı (yarın taban mı?)". Üç durum, yalnız iki teraziyle (yakın dönem backtest'i ve canlı sicil); eski dönem (2020–23 kohortu, kasa) **hiçbir aşamada kullanılmaz** ve bu modelin eski dönem testi **yapılmaz** (proje sahibi kararı, 1 Ekim).

1. **Aşama 1 — canlı n_scored < 30:** `break_floor_v0`'ın p_F1'i kartta **öne çıkarılır ancak** (k1) yakın dönem backtest'inde F1 − `PRODUCT_BREAK_FLOOR` aralığının üst ucu < 0 **VE** F1 − `@ZERO` aralığının üst ucu < 0. Etiket zorunlu: **"ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = k"**. k1 sağlanmıyorsa kart modeli ikincil satırda, `@ZERO` oranını ve ürün türevini yan yana gösterir; başlıkta "basit kuraldan ayırt edilemiyor (backtest)".
   - n_scored < 10: canlı bölümünde yalnız satır tablosu (arz, b, tür, p_F1, gerçekleşen, `@ZERO`, ürün); 10 ≤ n < 30: hücreler + "yetersiz örnek".
2. **Aşama 2 — canlı n_scored ≥ 30 (beklenen ≈ 12 ay; ayda ≈ 2.5 kırılma akşamı):** öne çıkarma yalnız canlı hücrelere göre: (k2) canlı F1 − ürün üst ucu < 0 **VE** canlı F1 − `@ZERO` üst ucu < 0 → öne çıkar, etiket "canlı sicil (prospektif, n = k; makine sıralı n_m / LIVE n_l)". Değilse ikincil satıra iner; kart hükmü yazar ("ayırt edilemiyor" ya da "geçemiyor"). Backtest etiketi bu aşamada öne çıkarma için **kullanılmaz** (yalnız bilgi satırı).
3. Her durumda kartta: `D10_STRUCTURAL_ZERO` rozeti (kural; §2.4), ürünün mevcut p_up(D10) satırı, rejim uyarısı (§11), `BAND_RULE_MISMATCH` varsa rozet gizli ve uyarı.
4. KARARLAR K4 aynen: model listeden kalkmaz; `@ZERO` satırı her zaman görünür; terfi yok.

## 9. Canlı kayıt aşaması `POST_BREAK` — makine sıralı [KARAR]

**9.1 Seçim: (a) makine sıralı; (b) gece kaydı v0'da yok.**

| Ölçüt | (a) Makine sıralı | (b) Gece kaydı (POST_D1 kalıbı) |
|---|---|---|
| Akşam yükü | **0** (kayıt yok; skorlama istenen zamanda) | her kırılma akşamı Claude: outcomes update + freeze + commit; proje sahibi: push + push_proof **T_open'dan önce** (ayda 2–3 akşam; bugünkü 7 kaydın hepsi geç yazıldı, POST_D1 kaydı hiç yazılmadı: `registry/post_d1/` boş) |
| Model tarafı kanıt | aynı: `commit_frozen(m)` D_b'den sonraki ilk bülten commit'inin atası + push kanıtı | aynı |
| Girdi tarafı kanıt | girdiler **yalnız** sha-pinli resmi bültenler (tarih kuralıyla seçilir) + `registry/inputs` (PIT alanı); insan hiçbir değer girmez → `inputs_pit_ok` yapısal | aynı girdiler; ek olarak kaydın push zamanı |
| Kalan kanal | predict kodunun sonradan değişmesi → altın vektör pini (dondurmada), `code_version` ve `borsai_source_sha256` makine kayıtta; **seçim** → skorlayıcı bütün FROZEN arzları sayar, satır yazılmayan arz yok | aynı + insanın kayıt yazmamayı seçmesi (SKIPPED satırı görünür) |
| Sınıf | `MACHINE_SEQUENCED` (yeni ad; LIVE değil) | LIVE / LATE_RECORD |
| Altyapı | skorlama bloğu + makine kayıt yazıcı (eski kohort `registry/oot/post_d1/` kalıbı birebir) | yeni kayıt şeması, sihirbaz, T_open akışı, iptal kuralı (≈ +2 oturum) |

**Karar:** (a). Gerekçe: `LATE_RECORD`'ın tek açık kanalı "girdi toplayanın sonucu biliyor olması"dır (SPEC_SCORING §5); bu aşamada girdi toplayan yoktur. Kanıt gücü, projenin zaten canlı teraziye saydığı LATE_RECORD'a eşit ya da ondan güçlüdür; akşam yükü ise bugünkü sicilin en zayıf halkasıdır. (b) ileride **aynı model_id ile** yükseltme olarak eklenebilir (kayıt push'u < T_open(D_b) ise satır LIVE olur; skor tanımı değişmez; §9.3 formülü bunu şimdiden içerir).

**9.2 Ad, şema, yol, dizin.**
- Aşama `POST_BREAK` ("D_b sonrası"); model dizini `models/INDEX_POST_BREAK.json`; makine kayıtları `registry/post_break/<TICKER>/machine_<UTC>_<kısa-sha>.json`, şema `borsai.post_break_machine_record/1`, append-only, `exposure_class = MACHINE_SEQUENCED`:
```
schema_version, record_type = "MACHINE", record_stage = "POST_BREAK", exposure_class, ticker, produced_at_utc (bilgi; kanıt değil),
code {git_head, borsai_dirty, borsai_source_sha256, predict_break_sha256},
inputs_ref {file: registry/inputs/<T>.json, sha256, shares_offered {value, source_published_at}, ipo_price_tl, inputs_pit_ok},
streak {L, b, break_date, sessions [ {h, date, thb {file, sha256}, thm {file, sha256}, close_raw, upper_limit_raw, ceiling_close} for h = 1..b ]},
break_day {h = b, session_date, half_day, halt_flag, fields_raw {open, high, low, close, volume, turnover, aof, trade_count, halt,
           special_trade_volume, special_trade_turnover, reference_price, upper_limit, lower_limit}, b_floor, band_ratio, warnings[]},
features {b_floor, b_turnover_ratio (Decimal metin), b_turnover_ln, clipped, z {...}},
models_index {path, sha256, model_ids}, models [ {model_id, file, params_sha256, spec_sha256, status ∈ {PREDICTED, REFUSED, NOT_APPLICABLE},
           refused, not_applicable, output {F1 {p_floor}, F2 {p_floor} | null, warnings}} ],
comparators {PRODUCT_BREAK_FLOOR {source_record, source_model_id, F1, F2, status}, base_floor_by_type: null (canlıda yok)},
structural_zero_D10 {min10, P, impossible, k_b, r_b, band_rule_ok},
t_open (D_b'yi izleyen resmi seans 09:40, bilgi), summary
```
- **Bekçi:** kayıt D_b'den sonraki hiçbir seansın alanını, bülten adını ya da sha'sını taşımaz (`registry.post_d1_record_problems` genelleştirilir: `record_problems_through(rec, manifest, last_day = D_b)`); h > b sonuç anahtarı hiçbir yerde; `registry/post_break/` dosyaları `sequence_guard`'ın korunan dizinlerine girmez (sonuçtan sonra yazılır) ama `sequence_violations` INDEX_POST_BREAK model dosyalarını H5 kuralıyla denetler.
- Girdi: D_1..D_b bültenleri yerel pinli dosyalardan (`outcomes.local_bulletin`), `MANIFEST.csv` sha eşitliği; eksik bülten → satır `BULLETIN_NOT_PINNED` (kayıt yazılmaz; `outcomes update` sonra yeniden).

**9.3 Zaman ve sınıf kuralı.**
```
outcome_ingest_commit_break(a) = min( data/raw/bist/ altına tarihi > D_b(a) olan ilk THB/THM'yi ekleyen commit,
                                      data/outcomes/<a>.csv'ye h ≥ b + 1 dolu satırı (OK | NA_LIMIT) ilk yazan commit )
model_prospective_break(m, a)  = is_ancestor(commit_frozen(m), outcome_ingest_commit_break(a)) AND push_proof(commit_frozen(m)) var
T_open_break(a)                = registry.t_open(D_b(a), takvim)            # D_b'yi izleyen resmi seans 09:40:00 Europe/Istanbul (aynı fonksiyon)
record_live_break(a)           = (isteğe bağlı insan kaydı var) AND push_proof(commit_record).created_at < T_open_break(a)   # v0'da hep False
inputs_pit_ok_break(a)         = inputs_ref.inputs_pit_ok (shares_offered PIT) AND bekçi temiz AND her bülten sha MANIFEST'e eşit

class_break(m, a) = LIVE               if model_prospective_break AND record_live_break AND inputs_pit_ok_break
                  = MACHINE_SEQUENCED  if model_prospective_break AND NOT record_live_break AND inputs_pit_ok_break
                  = RETRO              otherwise
```
- **Ölçek `live_break`:** satırlar LIVE ∪ MACHINE_SEQUENCED; her hücre ve sayaç `n_live / n_machine` kırılımıyla; RETRO `retro_info` (bilgi). Hiçbir ölçekle (canlı listeleme öncesi, POST_D1 koşullu, backtest) toplanmaz; `merge_scales` reddeder. Bugünkü 7 arz (NETGL dahil) → RETRO.
- Birincil makine satırı: aynı arz için birden çok makine kaydı (kod sürümü değişmiş) olabilir; skorlanan, **INDEX_POST_BREAK sha'sı ve bülten sha'ları eşit en erken** kayıttır; sonrakiler parite denetimidir (|Δ| ≤ 1e-12; aşım `ScoringError`).
- **Payda (`scores_break.json` `denominator`):** `ipos.csv`'de FROZEN her arz için bir satır: `RETRO` (model prospektif değil) → `STREAK_PENDING` (b henüz oluşmadı / h = b bekleniyor) → `NOT_SCORABLE_STREAK_NA` → `NOT_APPLICABLE_NO_BREAK` (L = 10) → `NOT_APPLICABLE_B10` → `BULLETIN_NOT_PINNED` → `INPUTS_NOT_AVAILABLE` (registry/inputs yok) → `CALENDAR_NOT_AVAILABLE` → satır (sınıf). Sayaçlar `n_scored / n_refused / n_target_unavailable / n_target_label_na / n_pending / n_not_applicable_* / n_retro / n_live / n_machine`. Özdeşlik testi.
- Skor hücreleri: §5.2 (F1 − ürün birincil; F1 − `@ZERO`; F2 ikisi; `base_floor_by_type` canlıda yok — eğitim oranları dondurulmuş JSON'dan sabit: `@ZERO` = dondurulmuş eğitim oranı, `by_type` = dondurulmuş sınıf oranları JSON'a yazılır ve karşılaştırıcı olur). Kalibrasyon satırı ve rejim kırılımı `descriptive`.

**9.4 CLAUDE.md kural 1'e önerilen ek (proje sahibi onaylar; bu belge CLAUDE.md'ye dokunmaz).**
> POST_BREAK (kırılma akşamı) aşamasının kaydı makine sıralıdır: tahmin, dondurulmuş model JSON'u ile D_b'ye kadarki sha-pinli resmi bültenlerden ve listeleme öncesi girdi dosyasından skorlama anında deterministik üretilir, `registry/post_break/` altına append-only yazılır ve insan değer girmez. Bir arz bu aşamanın modeli için ancak modelin JSON'u, D_b'den sonraki ilk bülteni ya da h ≥ b + 1 sonucunu repoya sokan commit'in atası ve push kanıtlı ise prospektiftir; bu satırlar `MACHINE_SEQUENCED` sınıfıyla ayrı ölçekte (`live_break`) skorlanır, LIVE ile toplanmaz, kırılımı her zaman görünür. T_open'dan önce push kanıtlı bir insan kaydı varsa satır LIVE olur.

**9.5 b = 1 akşamı (D1 tavan değil).** Tek akış: D1 bülteni iner (`outcomes update --through D_1`), `post_d1_hazard_v0` için kayıt akışı L ≥ 1'de (POST_D1_AKISI.md), `break_floor_v0` makine satırı skorlamada; ikisi aynı akşam birbirini dışlar (`ceiling_close_D1`). İki kayıt sorusu makine yoluyla ortadan kalkar.

**9.6 `borsai/` değişiklik listesi ve oturum tahmini.**

| Parça | İş | Oturum |
|---|---|---|
| `borsai/post_break.py` (numpy) | kırılma tablosu + beyaz listeli yükleyici; plan; fit (Faz 7C Logit yolu); `@ZERO`, `by_type`; ürün karşılaştırıcısı (`predict_path.build_cells`, `limit_path`, `mixture_atoms`, `lower_limit`); ledger; metrikler; günlük | A |
| `borsai/predict_break.py` (stdlib) | `evaluate_break_day(fields_raw, shares_offered)` (retler, uyarılar, `b_floor`, `b_turnover`), `predict_break(params, features)`, `structural_zero_d10(close_b, b, P)`, `product_break_floor(path_params, path_output, L, closes)` | A |
| `borsai/preprocess.py` | `BREAK_V0_RECIPE`; eski tarifler bayt-eşit | A |
| `borsai/specs.py` | `POST_BREAK_MODEL_SPECS` (`break_floor_v0`, `@ZERO`), `FAZ8_MODEL_IDS`, `PLAN_BREAK_H99`, `SPEC_DOCUMENTS_FAZ8` (bu dosya + `KARARLAR.md`), `model_kind → "post_break"` | A |
| `borsai/freeze.py` | `freeze_post_break` (INDEX_POST_BREAK), `run_model` bu türü listeleme öncesi kayıtta çalıştırmaz; makine kayıt yazıcı `write_post_break_machine_record` (eski kohort `post_d1` yazıcısı kalıbı) | A / S |
| `borsai/registry.py` | `POST_BREAK_DIR`, `record_problems_through(rec, manifest, last_day)` (post_d1 bekçisinin genellemesi; post_d1 çağrısı `last_day = D_1` ile davranış aynı, test) | A |
| `borsai/scoring.py` | `outcome_ingest_commit_after(git, ticker, day)` (post_d1 için `day = D_1` ile bit-eşit; refactor), `class_break`, `build_break_scores` → `scores/scores_break.json` (`borsai.scores_break/1`), `docs/SCORES.md` §8, `sequence_violations` INDEX_POST_BREAK | S |
| `borsai/outcomes.py` | değişmez (`OUTCOME_COLUMNS` aynı; alt limit `ThmRow.lower`'dan zaten okunur) | — |
| `borsai/report_faz8.py` | MODELS.md bölümü, `OPERATIONAL_RULES_FAZ8` | A/B |
| `tests/` | `test_faz8_break.py` (kabul testleri §13), `test_outcome_guard.py` (post_break bekçisi), `test_experiment_log.py` (sensitivity türleri), `test_scoring.py` (ölçek, payda özdeşliği) | A, S |
| `app/` | EK 5: Rust `predict_break` + altın vektörler (`PINNED_POST_BREAK_MODEL_IDS`), kart (§10), `scores_break.json` okuyucu; bu görevlerde değişmez (`build_embed` yeni dizini EK 5'e kadar yok sayar) | 2 |

Toplam: A 1, B 1, Fable 1, dondurma 1, S 1–2, EK 5 2 → **7–8**.

## 10. Uygulama etkisi (kısa; EK 5)

- Sonuç ve sicil ekranlarında resmi yol AFTER_BREAK durumundaysa (b ≤ 9) tavan kartının altında **"Kırılma akşamı"** kartı: "Yarın (D_{b+1}) taban kapanış olasılığı = %k" (`break_floor_v0`), altında "iki gün üst üste taban = %k₂" (b ≤ 8), yan yana `@ZERO` oranı ve ürün türevi (`PRODUCT_BREAK_FLOOR`), kırılma türü rozeti (taban / düşüş / yükseliş-yatay), `D10_STRUCTURAL_ZERO` rozeti ya da "k_b = …, kalan r_b = …" satırı, ürünün mevcut p_up(D10)'u. Öne çıkarma §8.
- Senaryo ekranında kırılma günü alanları elle girilebilir (THB alanları); resmi değerler yalnız makine kaydından (U38 kalıbı: uygulama tahmini resmi hücreye yazmaz).
- Doğruluk sekmesi: dördüncü bağımsız bölüm **"Kırılma akşamı sicili (makine sıralı)"**: `scores_break.json` kartı, hücreler, `n_live / n_machine`, satır tablosu (n < 10), rejim kırılımı. Üç mevcut ölçekle toplanmaz; `scalesNote` dörde çıkar.
- İzinli sözcükler SPEC_APP §4; "sinyal", "al/sat" yok. Yeni çıktı türü `p_floor` (uygulama `prediction_of_cell` benzeri okuyucusuna yeni ad).
- Rust portu: lojistik iki başlık (`fall` portuyla aynı yol), `lower_limit` zinciri (mevcut `path` crate), ürün türevi (`conditional_after_break` atomlarından eşik toplamı). Altın vektörler: sentetik kırılma günü satırları + H99 82 satır.

## 11. Ret ve uyarılar

| Kod | Tür | Koşul |
|---|---|---|
| `B_LIMIT_NA` | RET | D_b THM alt limiti yok/≤ 0 |
| `B_VOLUME_INVALID` | RET | hacim boş/≤ 0 iken sözleşme > 0 |
| `B_FIELD_INVALID` | RET | açılış/en yüksek/en düşük yok ya da ≤ 0 |
| `INPUT_SHARES_OFFERED` | RET | payda yok/≤ 0/sayı değil |
| `NOT_APPLICABLE_B10`, `NOT_APPLICABLE_NO_BREAK` | kapsam dışı (ret değil) | b = 10; L = 10 |
| `TARGET_UNDEFINED_F2` | başlık yok | b = 9 |
| `STREAK_PENDING` | kayıt yazılmaz | b henüz oluşmadı (seri sürüyor, h < 10) |
| `NOT_SCORABLE_STREAK_NA` | satır skorlanmaz | bir seansta üst limit NA, L belirsiz |
| `TARGET_LABEL_NA` | satır skorlanmaz | D_{b+1} (ya da D_{b+2}) alt limiti NA |
| `BULLETIN_NOT_PINNED` | kayıt yazılmaz | D_1..D_b bülteni yerelde/MANIFEST'te yok |
| `INPUTS_NOT_AVAILABLE` | kayıt yazılmaz | `registry/inputs/<T>.json` yok |
| `WARN_B_HALF_DAY`, `WARN_B_INTRADAY_HALT`, `WARN_B_SPECIAL_TRADES`, `WARN_B_FLOOR_LOCK_ALLDAY`, `B_TURNOVER_CLIPPED_TO_TRAINING_P05_P95`, `OUT_OF_TRAINING_RANGE` | uyarı | tahmin üretilir |
| `BAND_RULE_MISMATCH` | uyarı + rozet gizli + `regime_tags: BAND_CHANGED` | `lower_limit_b / reference_b ∉ [0.9, 0.9020]` ya da üst limit için [1.098, 1.1] dışı |
| `REGIME_WARNING: FON_KRIZI_2026` | kart uyarısı (metin; model girdisi değil) | D_1 ≥ 2026-09-16 (bitiş: proje sahibi kararıyla; varsayılan açık). Metin: "Bu arzın ilk seansları Eylül 2026 fon krizi penceresine düşüyor; eğitim kümesinde (2023-09…2026-08) böyle bir stres yok. Beklenti (önceden yazıldı): model tabanı az tahmin eder." |
| `PARAMS_INVALID` / `SCHEMA_UNSUPPORTED` | hata | JSON şeması, INDEX sha uyuşmazlığı |

## 12. Maruziyet

1. **Orkestratör tablosu** (başta, aynen) — kırılma türü × {≥ 2 ardışık taban, D10 ≤ arz, ort. R10}; L = 0 ve L = 10 sayıları; 35 taban kırılmasının 19'unda ertesi gün taban. Hipotez bu tablodan doğdu; H99 yalnız ön eleme.
2. **Bu şartnamenin profili** (`ekler/profil_kirilma.txt`, tek değişkenli, b'den sonrası okunmadı): L/b dağılımları; kırılma türü sayımları (b'ye ve yıla göre); kırılma günü limit eşitlikleri (taban kapanış 31/64, dokunma 35/64, gün boyu kilit 7/64, tavandan açılış 16/64); bant konumu kutuları; el değiştirme, hacim şoku, sözleşme, açılış/kapanış getirileri **kırılma türüne göre alt kümelerde** (tür girdidir); yastık aritmetiği (imkânsız 16/82, hepsi b ≥ 7; mümkün 66); seri günleri özetleri. Özellik seçimi (taban kapanış, el değiştirme) bu profilden **sonra** yazıldı → tasarıma maruz (mekanik gerekçe ayrıca var; karşı-olgusal duyarlılık bilinmiyor). Hiçbir sonuç (D_{b+1}.., R_h, Y_h) ile birleştirme yapılmadı.
3. **`experiments/log.jsonl` (2 142 satır: backtest 71, sensitivity 16, conditional_eval 1, exploration 2 054):** kırılma günü alanını özellik olarak kullanan koşu **0**; kırılma sonrasıyla ilgili olanlar yalnız `ceiling_path_v0` ailesi (hücre tabanlı, kovaryatsız) ve duyarlılıkları (`__sens_nmin5/20`, `__sens_single_group`, `__sens_nearest_only`, `__sens_v0_ref`); Faz 7C'nin 2 054 keşif varyantı yalnız listeleme öncesi özelliklerdir.
4. **Faz 4 tavan yolu hücreleri (SPEC_CEILING_PATH_V0 §3, MODELS.md Faz 4):** B/Z × m hücre büyüklükleri (B m = 1..9: 67, 64, 60, 54, 48, 40, 28, 15, 11; Z 18), m = 1 hücresinin kuantilleri (p10 = p25 ≈ −0.0997, medyan −0.095; 36/85 tam taban), m = 2..9 medyanları (−0.129 … −0.166), m = 6 yayılımı; D2–D10 kendi kümesi tabloları (koşulsuz). Bunlar kırılma **günü** getiri dağılımıdır (bu şartnamenin özelliği değil, karşılaştırıcısının malzemesi); ertesi gün taban bilgisi içermez.
5. **MODELS.md Faz 5 / 7C hücreleri** (aralık genişlikleri için), **NETGL raporu** (D4 taban kırılması + 6 ardışık taban; canlı sonuç; NETGL bu model için RETRO), **araştırma notu** (Çin %85,8 taban sürekliliği, özet düzeyi; VBTS 3 vaka; yastık tablosu).
6. **Görmedim:** `registry/oot/`, `data/outcomes_oot/`, `scores/scores_oot.json`, `docs/SCORES_OOT.md`; `data/outcomes/*.csv` (NETGL'nin yolu yalnız raporda görüldü); `scores/scores.json` içeriği; Faz 1B/4/5/7C altın ledger'larının değer sütunları; `tests/`; eski repo. Hiçbir fit, hiçbir walk-forward, hiçbir özellik–sonuç hesabı yapılmadı.
7. **Kasa/kohort kodu:** hiçbir kasa dosyası açılmadı; bu belgede ve eklerde bülten adı kalıbı (`th?YYYYMMDD`) ve kasa kodu yoktur (betikle denetlenmeli: kabul testi 14).

## 13. Kabul testleri (Opus için, kanıtlanabilir) ve sözde kod

1. **Kırılma tablosu:** 82 satır (b ≤ 9); b dağılımı 18/11/4/13/12/8/6/6/4; L = 10: 14; b = 10: 3; `b_floor` = 1 toplam 35 (2 ≤ b ≤ 9: 31; b = 1: 4); kırılma günü yarım gün 1, durdurma 0; referans_b == kapanış_{b−1} 67/67; `Lo(referans_b) == alt limit_b` 85/85 (`profil_kirilma.txt` §1–§3, §7 ile birebir).
2. **Özellik tanımı:** `b_floor` Decimal ham metin ("10.12" vs "10.120" → 1; "10.1200000000000000001" → 0; float mutasyonu kırmızı); `b_turnover` oranının H99 kantilleri profil betiğinin `q` yöntemiyle |Δ| ≤ 1e-9 ve `{:.4g}` basımı §4 "hepsi" satırına eşit (0.06236 / 0.1134 / 0.8542 / 1.632 / 2.228 / 2.897 / 3.219); kırpma ln ölçeğinde Type-7.
3. **Yükleyici sızıntısı:** D_b'den sonraki satırlarda erişilen anahtarlar tam olarak {ticker, session_number, target_session_date, thb_raw_close, thm_raw_lower_limit} (erişim sayaçlı DictReader, H20); test arzının D_b alanı değiştirilince kendi fold'unun ön işlemesi aynı, sonraki fold'larınki farklı.
4. **Plan:** fold sayısı 82 (F1), yakın dönem 69, 2023 13; her fold'da `training_max_label_date < T` ve `cells_max_session_date < D_1(k)`; aynı gün sentetik örneği dışarıda; `INSUFFICIENT_TRAINING_HISTORY` sayısı raporlanır; F2 fold'ları b ≤ 8 (78).
5. **Fit yolu:** `_fit_logit` V1.6 ızgarası ve aday başına politika (monkeypatch sayacı > 0); `@ZERO` = eğitim oranı Fraction ile bit-eşit; V1.5/V1.6/PB/7C altın ledger'ları ve 16 eski altın dosya bayt-eşit; `gen_golden --check` yeşil.
6. **Ürün karşılaştırıcısı:** sentetik hücrelerle (a) bütün atomlar çift tabanda → P_ürün(F1) = 1; (b) hiç atom eşik altında değil → 0; (c) `conditional_after_break` çıktısıyla aynı atomlar (ikinci karışım kodu yok; `mixture_atoms` çağrılır); kesişen 87 fold'da hücre sayıları Faz 4 ledger'ının `cells_n_*` sütunlarıyla birebir; `POST_BREAK_INSUFFICIENT` sayısı raporlanır.
7. **Yastık kuralı:** 82 kırılma akşamında imkânsız 16 (hepsi b ≥ 7; b = 7: 6, 8: 6, 9: 4); yaklaşık kural k_b ≥ r_b ile adım zinciri 82/82 aynı; sentetik: kapanış = P × 0.9^(10 − b) tam sınırda → mümkün; adım yuvarlaması sentetik örnekte farkı yakalar.
8. **Ret/uyarı/kapsam:** alt limit boş → `B_LIMIT_NA`; hacim 0 + sözleşme > 0 → `B_VOLUME_INVALID`; b = 10 → `not_applicable B10`; L = 10 → `NO_BREAK`; b = 9 → F2 `TARGET_UNDEFINED_F2`, F1 dolu; en yüksek == alt limit → `WARN_B_FLOOR_LOCK_ALLDAY`; `lower/reference = 0.89` → `BAND_RULE_MISMATCH` ve rozet gizli; `shares_offered` PIT değil → tahmin var, sınıf RETRO.
9. **JSON ↔ stdlib predict paritesi:** 82 eğitim satırında numpy nihai model ile `predict_break` |Δ| ≤ 1e-12; stdlib import listesi Faz 1A K2 kalıbı.
10. **Etiket kuralları:** sentetik aralıklarla §6 satırlarının tuttu/tutmadı ve "çok iyi" tetikleri (fark −0.17 → tetik; üst uç −0.079 → tetik yok; `@ZERO` farkı −0.095 → tetik); "dışlaması olası" kesin kısmı alt uç ≤ 0.
11. **Sınıf (geçici git deposu):** (a) model → D_b bülteni → D_{b+1} bülteni ⇒ MACHINE_SEQUENCED; (b) D_{b+1} bülteni modelden önce ⇒ RETRO; (c) push kanıtı yok ⇒ RETRO; (d) `shares_offered` PIT değil ⇒ RETRO; (e) insan kaydı push kanıtı < T_open ⇒ LIVE (formül; v0'da üretici yok); (f) `outcome_ingest_commit_after(day = D_1)` post_d1'in mevcut fonksiyonuyla bit-eşit sonuç (refactor testi); (g) makine kayıt bekçisi: h > b anahtarı ya da D_b sonrası bülten sha'sı → kırmızı; post_d1 bekçisi `last_day = D_1` ile aynı davranış (mevcut testler yeşil).
12. **Payda özdeşliği:** `scores_break.json` satır sayısı = Σ sayaçlar; bugünkü 7 arz RETRO (`retro_info`), hiçbir n'e girmez; NETGL retro satırında b = 4, `b_floor = 1`.
13. **Ölçek:** `live_break` hücrelerini başka ölçekle birleştiren çağrı `ScaleMixError`; SCORES.md'de "geçiyor" yalnız n ≥ 30 ve aralık 0'ı dışlarsa; backtest etiketi "backtest'te geçiyor (tasarıma maruz)".
14. **Hijyen:** `docs/specs_faz8/` ve yeni dosyalarda bülten adı kalıbı ve kasa kodu yok (regex testi); `docs/specs*` (Faz 1–7C) bayt-eşit; `models/INDEX.json`, `INDEX_POST_D1.json` bayt-eşit; 2026-08-19 sonrası veri eğitime girmez.
15. **Günlük:** backtest satırında `spec_document_sha256` = bu dosyanın sha256'sı; üç duyarlılık `kind: sensitivity`; kart varyant sayacı bunları sayar.
16. **Uygulama (EK 5 ile):** Rust `predict_break` altın vektörlerle |Δ| ≤ 1e-12; resmi hücre yalnız makine kaydından; kart öne çıkarma kuralı sentetik skor dosyalarıyla üç durumda doğru (k1 var/yok, n ≥ 30 k2 var/yok).

**Sözde kod**
```
# ---------- kırılma tablosu (H99) ----------
def break_table(sessions, train):
    for t in tickers:
        L = 0; rows = by_session(t)                       # artan h
        for h in 1..10:
            r = rows[h]                                   # yalnız close/upper okunur (seri için)
            if Decimal(r.close) == Decimal(r.upper): L += 1; continue
            b = h; break
        else: yield Unit(t, L=10, b=None); continue       # NO_BREAK
        if b == 10: yield Unit(t, L=9, b=10); continue    # B10
        f = fields(rows[b])                               # D_b ham alanları (beyaz liste tam)
        y1 = label(rows[b+1]); y2 = label(rows[b+2]) if b <= 8 else None   # yalnız close/lower/date okunur
        yield Unit(t, L, b, E_b = rows[b].date, f, y1, y1_date = rows[b+1].date, y2, y2_date, P, shares)

def label(r): lo = Decimal(r.lower);  return None if lo <= 0 else int(Decimal(r.close) == lo)

# ---------- özellikler (fit ve tahmin aynı yol; stdlib) ----------
def evaluate_break_day(f, shares):
    lo = Decimal(f.lower_limit); 
    if lo <= 0: refuse(B_LIMIT_NA)
    vol = Decimal(f.volume); tc = Decimal(f.trade_count)
    if vol <= 0 and tc > 0: refuse(B_VOLUME_INVALID)
    if Decimal(shares) <= 0: refuse(INPUT_SHARES_OFFERED)
    floor = int(Decimal(f.close) == lo)
    warn_if(Decimal(f.high) == lo, WARN_B_FLOOR_LOCK_ALLDAY)
    band = Decimal(f.lower_limit) / Decimal(f.reference_price); warn_if(not (0.9 <= band <= 0.9020), BAND_RULE_MISMATCH)
    return {"b_floor": floor, "b_turnover": float(ln(vol / Decimal(shares)))}

def predict_break(params, feats, b):
    z = params.preprocessing.transform(feats)             # kırpma + z; clipped işareti
    out = {"F1": {"p_floor": sigmoid(a1 + β1·z)}}
    out["F2"] = None if b >= 9 else {"p_floor": sigmoid(a2 + β2·z)}
    return out

def structural_zero_d10(close_b, b, P):
    x = close_b
    for _ in range(10 − b): x = lower_limit(x)             # predict_path.lower_limit (Decimal)
    k = ln(float(close_b / P)) / ln(1/0.9)
    return {"min10": x, "impossible": x > P, "k_b": k, "r_b": 10 − b}

def product_break_floor(path_params, path_output, L, closes):      # closes = D_1..D_b
    cond = conditional_after_break(path_params, path_output, t=L, observed_closes=closes)
    P = Decimal(path_output.limit_path.ipo_price); cb = Decimal(closes[-1])
    thr1 = float(lower_limit(cb) / P − 1); thr2 = float(lower_limit(lower_limit(cb)) / P − 1)
    a1 = atoms(cond, h = L + 2); a2 = atoms(cond, h = L + 3)       # mixture_atoms ile aynı atomlar (dışa açılır)
    return {"F1": sum(w for r, w in a1 if r <= thr1 + 1e-12), "F2": None if L + 3 > 10 else sum(w for r, w in a2 if r <= thr2 + 1e-12)}

# ---------- backtest fold ----------
for k in units_with_break:                                # b ≤ 9
    T = k.E_b
    train1 = [j for j in units if j.y1 is not None and j.y1_date < T]
    train2 = [j for j in units if j.y2 is not None and j.y2_date < T]
    if not enough(train1): ledger(INSUFFICIENT_TRAINING_HISTORY); continue
    head1 = fit_logit_head(train1, BREAK_V0_RECIPE, V1_6_GRID)      # iç LOOCV; ön işleme bölme içinde
    head2 = fit_logit_head(train2, ...) if k.b <= 8 and enough(train2) else None
    cells = build_cells(all_units_as_path_units, cutoff = k.D_1)   # Faz 4 yükleyicisi, ürünün listeleme öncesi kaydının karşılığı; cells_max_session_date < D_1(k)
    prod  = product_break_floor(template_with(cells), limit_path(k.P), k.L, k.closes_1_to_b)
    ledger(p_F1 = head1.predict(k), p_F2, zero = rate(train1), by_type = rate(train1 | b_floor == k.b_floor), prod, realized = (k.y1, k.y2))
metrics: eşleşik Brier farkları (yakın dönem: first_trading_date ≥ 2024-01-01), blok bootstrap (C7), §6 etiketleri, MODELS.md, log.jsonl

# ---------- canlı (makine sıralı) ----------
def break_row(ticker):
    L, b, sessions = streak_from_outcomes_and_bulletins(ticker)    # outcomes csv ceiling_close; THM alt limiti pinli zip'ten
    if b is None: return STREAK_PENDING / NO_BREAK;  if b == 10: return B10
    inputs = registry/inputs/<ticker>.json; pit = inputs_pit_problems(inputs) == []
    feats = evaluate_break_day(fields_raw(sessions[b]), inputs.shares_offered)
    pred = predict_break(frozen, feats, b); prod = product_break_floor(primary_path_record(ticker), ...)
    rec = write_machine_record(...)                                 # registry/post_break/<T>/machine_*.json, append-only
    ingest = outcome_ingest_commit_after(git, ticker, day = sessions[b].date)
    klass = LIVE if human_record_before(t_open(sessions[b].date)) and pit else MACHINE_SEQUENCED if prospective(frozen, ingest) and pit else RETRO
    realized = labels from outcomes csv h = b+1, b+2 (OK satırları; lower limit pinli THM'den)
    return row(klass, pred, prod, zero = frozen.training_rate, realized)
```

## 14. Açık sorular (proje sahibine; en çok 5; her birinde öneri)

1. **Birincil hedef.** Şartname "ertesi seans taban kapanışı"nı seçti; "D10 ≤ arz" için yeni model "dur". Proje sahibi D10'u birincil istiyorsa bu şartnamenin cevabı "dur"dur ve uygulama yapılmaz. **Öneri:** ertesi seans taban (yazıldığı gibi); D10 kartta yastık kuralı + mevcut ürün.
2. **Makine sıralı sınıfın canlı terazide yeri.** Şartname `MACHINE_SEQUENCED` satırlarını ayrı ölçekte (`live_break`) skorlar ve n_scored'a sayar; CLAUDE.md kural 1'e §9.4 cümlesi eklenir. Alternatif: yalnız insan kaydı (b yolu) sayılsın → akşam yükü geri gelir ve bugünkü sicile göre n büyük olasılıkla 0 kalır. **Öneri:** §9.4 metni kabul; (b) ileride yükseltme.
3. **L = 0 (b = 1) kapsamı.** Dahil (18/82 H99). Alternatif: yalnız L ≥ 1 ("tavan bozulunca" lafzı). **Öneri:** dahil — aynı mekanizma, aynı alanlar; Z/B kırılımı keşifte raporlanır; dışlanırsa olay bütçesi 2 parametre için sınıra iner.
4. **Rejim uyarısının bitişi.** `FON_KRIZI_2026` (D1 ≥ 2026-09-16) kart uyarısı ne zaman kalkar? **Öneri:** proje sahibi tarih verene kadar açık; satırlar `regime_tags` ile ayrı kırılımda; model girdisi hiçbir zaman olmaz; kaldırma kararı `KARARLAR.md`'ye tarihle yazılır.
5. **Bant varsayımının doğrulanması.** Rev. 54 (21.09.2026) prosedürü ±%10 ve ilk gün baz fiyat kuralını değiştirdiyse yastık kuralı ve ürün karşılaştırıcısının eşiği geçersizdir (`BAND_RULE_MISMATCH` zaten yakalar). **Öneri:** dondurmadan önce orkestratör iki PDF'in farkını doğrular; değiştiyse §2.4 ve §5.1 sabitleri KARARLAR'da yeni değerle yazılır (model özellikleri etkilenmez: taban etiketi THM eşitliğidir).

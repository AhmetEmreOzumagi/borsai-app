# SPEC_CEILING_PATH_V0 — tavan yolu modelleri (`ceiling_path_v0`, `ceiling_path_v0@INF`, `pb_ceiling_path_v0`)

Görev: BORSAI_FAZ4_FABLE_CEILING_PATH_SPEC_20260922. Yazım: 2026-09-22, Fable. Kod yok, git komutu yok, skor yok. Uygulayıcı: Opus (Claude Code). Bu belge `docs/specs_faz4/` altındadır; `docs/specs/` değişmemiştir.

## Özet (≤ 10 satır)

1. Üç yeni model_id; hiçbiri yeni hazard fit etmez. Seri bileşeni S_k, dondurulmuş `ceiling_hazard_v0` (ana), `ceiling_hazard_v0@INF` (sıfır model, MECHANICS_BASE) ve `pb_ceiling_v0` (talep toplama öncesi) JSON'larından **parametre sha'sıyla aynen** alınır.
2. Limit yolu C_h: arz fiyatından, borsaistanbul.com'daki fiyat adımı tablosu ve "üst limit aşağı adıma yuvarlanır" kuralıyla deterministik. H99'da 424 tavan-günü kapanışının 424'ünü birebir üretir (`ekler/m4_cikti.txt` §12); `1.1^h` kullanılmaz.
3. Kırılma sonrası bileşen: kovaryatsız, **ampirik kuantil hücreleri** G(g, m); g ∈ {Z: D1 tavan değil, B: seri ≥ 1 günde kırıldı}, m = son limit-yolu gününden bu yana geçen seans. Parametrik serbest parametre **0** (bütçe ≤ 2). Küçük hücre için deterministik havuzlama merdiveni, N_MIN = 10.
4. R_h'nin öngörü dağılımı: S_h ağırlıklı C_h atomu + her t < h için P(L = t) ağırlıklı hücre atomları. Nokta = karışımın **MEDYANI** (MAE için; şimdi yazıldı, değişmez). `p_up_h` = P(R_h > 0). Kuantiller %10/%50/%90. h = 1..10.
5. Ret: ana model f3 yoksa RET (mirası). Sıfır model ve PB varyantı f3 istemez.
6. Karşılaştırma SPEC_SCORING §7 ile, eşleşik: getiri → `base_always_ceiling`, `base_train_median`, `v1_5_h99`, sıfır model; p_up → `base_rate`, `base_last10_rate`, `v1_5_h99`, sıfır model. **Birincil hücre: D5 getiri MAE, `base_train_median`'a karşı.**
7. Önceden yazılmış beklenti (§6): D1'de `base_always_ceiling` ile BERABERE (aralık 0'ı içerir; çoğu fold bit-eşit). Kazanç en olası D5 MAE'de ve D3 p_up Brier'inde; D10'da V1.5'e karşı beklenmez.
8. Koşullu güncelleme (§7): S_k / S_j ve koşullu karışım; dondurulmuş kayıt + resmi THM'den deterministik; canlı skorlaması j başına ayrı, koşulsuzla asla toplanmaz.
9. Backtest: `ceiling_hazard_v0` ve `@INF` fold ledger'larındaki S_k yeniden kullanılır; yalnız hücreler her fold'da walk-forward kurulur (seans tarihi < T). Aralıklar SPEC_DEVIATIONS C7.
10. Geriye dönük sonuç tasarıma maruzdur (§10). Asıl ölçüm prospektif; ilk 7 arz (CITAS…NETGL) bu modeller için RETRO'dur.

İşaretler: **[ÖLÇTÜM]** = bu oturumda H99 dosyasından ya da kural metninden (`ekler/m4_cikti.txt`, `ekler/kural_metni_borsaistanbul_20260922.md`); **[ÇIKARIM]** = yorum. Hiçbir model fit edilmedi, hiçbir walk-forward skoru hesaplanmadı, özellik–sonuç ilişkisine bakılmadı.

---

## 1. Modeller ve kimlikler

| model_id | Seri bileşeni S_k (dondurulmuş, aynen) | Kırılma sonrası bileşen | Eşleme | Girdi / ret | Plan (backtest) |
|---|---|---|---|---|---|
| `ceiling_path_v0` (ana) | `models/ceiling_hazard_v0.json` (sha256 `caa4dc867a9f…`, INDEX'teki tam değer) | §3 hücreleri, kesim T | §4 | V1.5 girdileri; f3 yoksa **RET** `F3_MISSING` (mirası) | `ceiling_hazard_v0` ledger'ının 87 fold'u |
| `ceiling_path_v0@INF` (sıfır model, MECHANICS_BASE) | `models/ceiling_hazard_v0@INF.json` (`c5ac8085fd76…`); yalnız gün-grubu sabitleri | aynı hücreler, aynı kesim | aynı | girdi istemez, ret etmez | `@INF` ledger'ının aynı 87 fold'u |
| `pb_ceiling_path_v0` (PB varyantı) | `models/pb_ceiling_v0.json` (`7fb7a41e48ea…`) | aynı hücreler, kesim **B(k)** (ilk talep toplama günü) | aynı | 8 PB alanı; PB ret kuralları (SPEC_PB_V0 §5); f3 istemez | `pb_ceiling_v0` ledger'ının 87 fold'u |

- `algorithm`: `CEILING_PATH_MIXTURE_EQ_V0` (üçü de). `schema_version`: `borsai.model/1`. `borsai/freeze.py: model_kind` bu algoritmayı `ceiling_path` türüne bağlar; tahmin `borsai/predict_path.py` (yalnız stdlib; `borsai/predict_hazard.py`'yi çağırır).
- Seri modeli JSON'un içine **birebir kopya** olarak gömülür (`survival_model`), `survival_model_sha256` = INDEX'teki `sha256`; test bunu sınar. Böylece `predict(params, inputs)` tek dosyayla çalışır ve S_k, dondurulmuş modelin `predict_hazard.predict` çıktısına bit-eşittir.
- **Neden yeni hazard yok** [ÇIKARIM]: `ceiling_hazard_v0` dondurulmuş ve sonuçtan önce push edilmiş; RPS'te basit kuralları aralık 0'ı dışlayarak geçiyor (MODELS.md). Aynı 99 arzda ikinci bir hazard varyantı (F1'in {1,2,3,≥4} gruplaması, yalnız log f3) çatallanan yol açar ve bu görevin konusu değildir. Değişiklik istenirse yeni model_id + ayrı şartname.
- **PB varyantı neden alındı** [ÇIKARIM]: uygulama f3 açıklanmadan önce de getiri ve p_up göstermek istiyor (SPEC_PB_V0 §9 gerekçesi). Maliyet: aynı kodun üçüncü çağrısı; yeni parametre yok. PB için ayrı bir @INF yolu **açılmaz** (en çok 3 kimlik); PB varyantı `pb_v0` ile ve bilgi amaçlı `ceiling_path_v0@INF` ile karşılaştırılır (§5).
- Yeni serbest parametre sayısı: **0**. Miras alınan parametreler: ana 6 (`ceiling_hazard_v0`), sıfır 3, PB 5. Tasarım sabitleri (parametre değil, şartnamede yazılı): marj 0.10, fiyat adımı tablosu, D1 baz fiyat yuvarlaması, N_MIN = 10, hücre tanımı, havuzlama merdiveni, kuantil kuralı.
- CLAUDE.md kural 5: bu şartnamedeki herhangi bir sabit, hücre tanımı, kesim ya da eşleme değişirse yeni model_id.

## 2. Limit yolu C_h

Tanım: C_h = D1..Dh'nin hepsi tavan kapanırsa D_h'nin resmi kapanışı; ρ_h = C_h / P − 1 (P = resmi kesin arz fiyatı, Decimal).

**Kural metni** (borsaistanbul.com, Pay Piyasası → Piyasa İşleyişi; erişim 2026-09-22; alıntı ve sayfa sha256'sı `ekler/kural_metni_borsaistanbul_20260922.md`):
- Baz fiyat = bir önceki işlem gününün kapanış fiyatı. Fiyat marjı: "yeni bir duyuru yapılana kadar" Yıldız Pazar ve Ana Pazar'da **%10**. (Aynı sayfada yeni pazar yapısı için %20/%15 genel esası da yazılıdır; uygulanmıyor. Bkz. §11 soru 2.)
- "Fiyat limitleri hesaplanırken yuvarlama işlemi içeri doğru yapılacaktır: Üst fiyat limiti bulunurken yuvarlama aşağı adıma, alt fiyat limiti bulunurken yuvarlama yukarı adıma yapılacaktır."
- Fiyat adımı tablosu (paylar): [0.01, 20) → 0.01; [20, 50) → 0.02; [50, 100) → 0.05; [100, 250) → 0.10; [250, 500) → 0.25; [500, 1000) → 0.50; [1000, 2500) → 1.00; ≥ 2500 → 2.50.

**Seçilen yöntem: deterministik yuvarlama (`1.1^h` DEĞİL).** Hepsi Decimal:
```
adim(x)      = yukarıdaki tabloda x'in düştüğü aralığın adımı          # x: yuvarlanacak değerin KENDİ seviyesi
U(b)         = floor(b × 1.10 / adim(b × 1.10)) × adim(b × 1.10)       # üst limit; aşağı adıma
Lo(b)        = ceil (b × 0.90 / adim(b × 0.90)) × adim(b × 0.90)       # alt limit; yukarı adıma (yalnız test/uygulama bilgisi)
snap(P)      = round_half_up(P / adim(P)) × adim(P)                    # D1 baz fiyatı: arz fiyatı adıma oturtulur
C_0 = P;  b_1 = snap(P);  C_1 = U(b_1);  C_k = U(C_{k−1}) (k ≥ 2);  ρ_k = C_k / P − 1
```
- [ÖLÇTÜM `m4_cikti.txt` §2–§3, §11–§12]: 990 seansta üst limit / referans ∈ [1.09604, 1.1] (tam 1.1 yalnız 209 seans). Adımı, yuvarlanacak değerin kendi seviyesinden alıp aşağı yuvarlamak üst limiti **990/990**, alt limiti yukarı yuvarlamak **990/990** seansta birebir üretir; adımı referans fiyatın seviyesinden almak 931/990. Referans(D_k) = kapanış(D_{k−1}) 891/891. D1 referansı 95/99 arzda arz fiyatına eşit; 4 arzda (BORLS 25.29→25.30, AVPGY 55.08→55.10, ARTMS 25.35→25.36, LILAK 37.39→37.40) arz fiyatının adıma yuvarlanmış hali; dördü de HALF_UP ve CEIL ile tutar, HALF_EVEN ve FLOOR ile tutmaz. Seçim: **HALF_UP** (§11 soru 1).
- [ÖLÇTÜM §12] Bu yolla C_h, seri ≥ h olan her arzda gerçekleşen kapanışa **Decimal-eşit: h = 1..10 için 81/81, 70/70, 66/66, 53/53, 41/41, 33/33, 27/27, 21/21, 17/17, 14/14** (toplam 424/424).
- Hata payı, `1.1^h` seçilseydi [ÖLÇTÜM §4, §13]: ρ_h − (1.1^h − 1) medyanı h = 1: 0.0000, h = 3: −0.0008, h = 5: −0.0019, h = 10: −0.0077; 99 arzda h = 10 için en küçük −0.0537 (düşük fiyatlı arzda adım etkisi büyür). Yani `1.1^h` D10'da sistematik olarak yaklaşık 0.8 puan fazla tahmin ederdi; deterministik yol sıfır hata verir.
- Sınır notu: `borsai/horizons.py` fiziksel sınırı 1.1^h − 1 alır; snap(P) > P olan arzlarda ρ_1, 0.1'i bir adım aşabilir (LILAK 0.10029). Bu model için etkin üst sınır **ρ_h^max = 1.1^h × snap(P) / P − 1** olarak tanımlanır (§4, §9-4); atomlar kırpılmaz, sınır test edilir.
- Uygulama uyarıları: arz fiyatı adım ızgarasında değilse `IPO_PRICE_NOT_ON_TICK_GRID` uyarısı (snap uygulanır, değer gösterilir). Marj sabiti (0.10) ve adım tablosu JSON'da yazılıdır; canlıda D1 THM üst limiti C_1'e eşit değilse skorlama satırına `limit_path_mismatch = 1` düşer (§7).

## 3. Kırılma sonrası bileşen

**Yol bağımlılığı.** L = t < h ise R_h = (C_t / P) · (1 + G) − 1; G = kapanış(D_h) / kapanış(D_t) − 1 = son limit-yolu gününden D_h'ye getiri. t = 0 için C_0 = P ve G = R_h'nin kendisi.

**Gruplar (g) ve geçen seans (m = h − t):**
- **Z** (t = 0): D1 tavan kapanmadı; fiyat ilk gün serbest oluştu. m = h ∈ 1..10.
- **B** (1 ≤ t ≤ 9): seri t gün sürdü, D_{t+1}'de kırıldı. m = h − t ∈ 1..9. t'ye göre ayrıca bölünmez.
- Gerekçe [ÇIKARIM + ÖLÇTÜM §6]: mekanik olarak Z'de baz fiyat arz fiyatıdır ve satıcı baskısı ilk gün emilmiştir; B'de kırılma günü bir limit yolundan düşüştür. Ölçüm bunu doğrular: m = 1'de Z medyanı −0.0011 (18 arzın 8'i arz fiyatının üstünde), B medyanı −0.0949 (67 gözlemin çoğu alt limitte; §8'de m = 1'de 36/85 taban). B içinde t = 1 / t = 2,3 / t ≥ 4 için m = 1 medyanları −0.089 / −0.0995 / −0.094 → t'ye göre bölmek bilgi katmaz, hücreleri küçültür.

**Hücre gözlemleri (eğitim; walk-forward).** Kesim T (ana ve sıfır model: test arzının ilk işlem günü; PB varyantı: ilk talep toplama günü B(k)). Aday arz j (99 arzın hepsi; f3 şartı YOK, bileşen kovaryatsız), L_j = t < 10:
```
for m in 1..(10 − t):
    if session_date(j, t + m) >= T: break          # kesin öncelik; ilk geçmeyen seansta durulur
    base = P_j if t == 0 else close(j, D_t)         # resmi THB kapanışı, Decimal
    G = float(Decimal(close(j, D_{t+m})) / base − 1)
    hücre[g(t)][m].append((G, j.ticker))
```
- Seri 10 gün sürmüş arzlar (L = 10) ve kesimde hâlâ seride olan arzlar hücreye girmez (kırılma gözlenmemiş). Kırılma gözlenmişse (D_{t+1} < T) t bilinir; sonraki her seans yalnız kendi tarihi < T ise girer.
- Hücre listeleri (değer, ticker) sırasıyla artan saklanır; her gözlem eşit ağırlıklı.
- [ÖLÇTÜM §6, §14] Tam kohortta hücre büyüklükleri: Z m = 1..10: 18, 18, …, 18 (aynı 18 arz); B m = 1..9: 67, 64, 60, 54, 48, 40, 28, 15, 11. Tavan planının ilk skorlanabilir fold'unda (EKOS, T = 2023-11-21): Z hepsi 0, B = [6, 6, 5, 4, 3, 2, 0, 0, 0]; Z hücreleri ilk 31 skorlanabilir fold'da 5'in altında (ilk L = 0 arz geç geliyor); B[1] 87 fold'un hepsinde ≥ 5, 7'sinde < 10; B toplamı her skorlanabilir fold'da ≥ 20.

**Havuzlama merdiveni (deterministik; hedef hücre (g, m), N_MIN = 10):**
1. Kendi hücresi. n ≥ N_MIN ise dur.
2. Diğer grubun aynı m hücresi eklenir ((Z, m) ↔ (B, m); Z için m = 10'da B'de karşılık yok, atlanır). n ≥ N_MIN ise dur.
3. m − 1, m + 1, m − 2, m + 2, … sırasıyla (geçerli aralıkta), her adımda İKİ grubun o m hücresi eklenir; n ≥ N_MIN olunca durulur.
4. Bütün hücreler tükenip n < N_MIN kalırsa: fold/tahmin durumu `POST_BREAK_INSUFFICIENT` (S_k ve P_L yine üretilir; getiri/p_up/kuantil üretilmez). [ÖLÇTÜM §14] Tavan planının 87 skorlanabilir fold'unda B toplamı ≥ 20 olduğundan bu durum backtest'te beklenmez (test 9-8).
- Havuzlanmış değerler dönüştürülmez; yalnız hedef m'nin fiziksel sınırına kırpılır: G ← min(max(G, 0.9^m − 1), 1.1^m − 1). Kendi hücresinde kırpma hiç tetiklenmez [ÖLÇTÜM §7: 567 gözlemde sınır dışı 0].
- Sonuçta hücrenin `pooled` bayrağı, kullanılan (g, m') listesi ve n'i ledger'a ve JSON'a yazılır.
- Gerekçe [ÇIKARIM]: aynı m önce (aynı fiziksel sınır, aynı geçen süre); komşu m sonra (medyanlar m ≥ 2'de yavaş değişir: B m = 2..9 medyanları −0.129 … −0.166). Erken fold'larda Z boşken t = 0 atomları B'den gelir; bu p_up_1'i erken fold'larda düşük tahmin ettirir (Z'de G > 0 payı 8/18, B m = 1'de p90 ≈ +0.008); bilinçli ve raporlanan bir taviz.

**Dağılım biçimi: ampirik (kuantil tabanlı), parametrik değil.** Gerekçe [ÖLÇTÜM §6, §8]: kırılma günü dağılımı alt limitte kütle noktalı (m = 1: p10 = p25 ≈ −0.0997, medyan −0.095, p75 −0.039, p90 +0.008; 36/85 tam taban); büyük m'de iki modlu ve sağa uzun kuyruklu (m = 6: p25 −0.24, p75 +0.10, p90 +0.38). Normal/lognormal konum-ölçek modeli bu biçimi 2 parametreyle temsil edemez; MAE için gereken medyan ve Brier için gereken P(G > eşik) sıra istatistikleridir ve ampirik dağılımdan doğrudan gelir. Parametrik serbest parametre 0 ⇒ F1 §2.3 bütçesi (≤ 2) sağlanır; bileşenin esnekliği hücre sayısındadır (2 grup × ≤ 10 m) ve bu havuzlama kuralıyla sınırlanır. Kovaryat yok.

**Fiziksel sınırlar:** her atom r için 0.9^h − 1 ≤ r ≤ ρ_h^max (§2). Kanıt [ÇIKARIM]: C_t ≤ 1.1^t · snap(P) ve G ≤ 1.1^m − 1 ⇒ r ≤ 1.1^h · snap(P)/P − 1; C_t ≥ P ve G ≥ 0.9^m − 1 ⇒ r ≥ 0.9^m − 1 ≥ 0.9^h − 1.

## 4. Eşleme ve çıktılar

Girdi: S_1..S_10 (dondurulmuş seri modeli çıktısı), P, hücreler. Türetilenler (`borsai/survival.py: p_streak`): P(L = 0) = 1 − S_1; P(L = t) = S_t − S_{t+1} (1 ≤ t ≤ 9); P(L = 10) = S_10.

**R_h'nin öngörü dağılımı (h = 1..10), ayrık atom listesi:**
```
atoms(h) = [(ρ_h, S_h)]                                             # limit yolu atomu
         + [ ((C_t/P)·(1 + v) − 1,  P(L = t) / n_cell(g(t), h − t))   # t = 1..h−1, v ∈ hücre(B, h − t)
         + [ (v,                    P(L = 0) / n_cell(Z, h))            # t = 0, v ∈ hücre(Z, h)
```
Ağırlık toplamı S_h + Σ_{t<h} P(L = t) = 1 (test). Bütün aritmetik binary64; C_t/P Decimal'den bir kez float'a.

**Kuantil kuralı (deterministik):** atomlar (r, sonra ekleme sırası) ile artan sıralanır; kümülatif ağırlık F; Q(q) = F ≥ q − 1e-12 sağlayan ilk atomun r'si (alt kuantil). Çıktılar:
- `return` = **Q(0.5) (medyan) — birincil nokta tahmini, MAE ile skorlanır; şimdi yazıldı, sonradan değiştirilmez.** Ortalama Σ w·r yalnız `mean` alanında, ikincil gösterim.
- `p_up` = Σ{w : r > 0} (kesin >; Y_h = 1[kapanış > arz] ile aynı). ρ_h > 0 daima; t = 0 atomlarında v = 0 (kapanış = arz) yukarı sayılmaz.
- `q10`, `q50` (= return), `q90`; `limit_path_return` = ρ_h; `S_h`; `p_limit_path` = S_h (aynı); `n_post_break` = kullanılan hücre n'leri ve `pooled` bayrakları.
- Tutarlılık (kendiliğinden; test): return ≤ ρ_h; S_h ≥ 0.5 ⇒ return = ρ_h (limit atomu tek başına yarıyı geçer); S_h → 1 ⇒ bütün kuantiller = ρ_h ve p_up → 1; p_up ∈ [0, 1]; p_up ≥ S_h.

**JSON tahmin çıktısı (`predict_path.predict(params, inputs)`)**, `predict_hazard` çıktısıyla uyumlu alanlar + yeni alanlar:
```
{"model_id", "refused": None | {code, field, reason}, "warnings": [...], "clipped",
 "hazard": [10], "S": [10], "P_L": [11], "P_close_ceiling": [10],      # gömülü seri modelinden aynen
 "limit_path": {"ipo_price": "…", "snapped_ipo_price": "…", "tick": "…", "C": ["…"×10], "rho": [10]},
 "D1": {"return": …, "p_up": …, "mean": …, "q10": …, "q50": …, "q90": …, "limit_path_return": …, "S_h": …,
        "post_break": {"cells": [{"group": "Z"|"B", "m": …, "n": …, "pooled": bool, "sources": [[g, m'], …]}], "status": "OK"|"POST_BREAK_INSUFFICIENT"}},
 "D2": {...}, …, "D10": {...}}
```
- `D1`, `D3`, `D5`, `D10` anahtarlarında `return` ve `p_up` bulunması `borsai/scoring.py: prediction_of_cell`'in ufuk-tabanlı yoluyla uyumludur (yeniden hesap yok; kayıt değeri skorlanır).
- Ret: ana model f3 yoksa `F3_MISSING` (gömülü seri modelinin reddi aynen geçer; `refused` doludur, diğer alanlar None). Girdi aralık dışı/kırpma uyarıları seri modelinden geçer. PB varyantında PB ret kodları. Sıfır model ret etmez.
- Model JSON ek alanları: `survival_model` (gömülü kopya), `survival_model_sha256`, `survival_model_id`, `limit_path: {margin: "0.10", tick_table: [...], upper_rounding: "FLOOR_TO_TICK_AT_LIMIT_LEVEL", d1_base: "HALF_UP_TO_TICK", rule_source: {url, accessed, page_sha256}}`, `post_break: {N_MIN: 10, groups: ["Z","B"], cells: {"Z": {"1": [[G, ticker], …], …}, "B": {…}}, cutoff_date: "2026-08-19", n_ipo: 99, ipos_sha256}`, `quantile_rule`, `horizons: {"D1".."D10": {"return": {"kind": "mixture_median"}, "p_up": {"kind": "mixture_p_up"}}}`, `training` (hücreler: `H99_ALL_ROWS`, n = 99, kesim 2026-08-19; `survival_training`: gömülü modelinki), `spec_document{path, sha256}`.

## 5. Karşılaştırmalar

Hepsi SPEC_SCORING §7 ile: eşleşik fark = model − karşılaştırılan, aynı arzlar (ikisinin de skorlandığı), negatif = model iyi; aralık §8 (backtest'te SPEC_DEVIATIONS C7: ilk işlem ayı blokları, 4000 tekrar, `random.Random(20260921)`; p_up Brier'i Faz 1A/1B tablolarıyla aynı [0.01, 0.99] kırpmasıyla). Eşleştirme anahtarı (ticker, ufuk).

| Model | Çıktı | Karşılaştırılan | Kaynak (backtest) | Beklenen eşleşik n (D1/D3/D5/D10) |
|---|---|---|---|---|
| `ceiling_path_v0` | R_h MAE | `base_always_ceiling`, `base_train_median` | Faz 1A altın ledger'ları (PLAN_V15), `rule_return` | 87/86/85/85 [ÖLÇTÜM: tavan fold'ları ∩ V1.5 fold'ları] |
| | | `v1_5_h99` | Faz 1A altın ledger'ı, `ridge_prediction` (kırpılmamış, legacy ile aynı) | 87/86/85/85 |
| | | `ceiling_path_v0@INF` | aynı plan | 87/87/87/87 |
| | p_up Brier | `base_rate`, `base_last10_rate` | Faz 1A altın ledger'ları, `rule_p_up` | 87/86/85/85 |
| | | `v1_5_h99` | `logit_probability`, yalnız Logit FIT_OK fold'ları | ≈ 78/78/79/79 |
| | | `ceiling_path_v0@INF` | aynı plan | 87 |
| `ceiling_path_v0@INF` | MAE, Brier | `base_train_median`, `base_always_ceiling`, `base_rate`, `base_last10_rate` | Faz 1A ledger'ları | 87/86/85/85 |
| `pb_ceiling_path_v0` | MAE, Brier | `pb_v0`; PB planı kuralları (`base_train_median__pb`, `base_always_ceiling__pb`, `base_rate__pb`, `base_last10_rate__pb`) | Faz 1B altın ledger'ları (PLAN_PB) | ≈ 87 (D10 ≈ 84) |
| | bilgi amaçlı | `ceiling_path_v0`, `ceiling_path_v0@INF` (kesimleri farklı) | aynı test arzları | ≈ 85 |

**Önceden ilan edilen TEK birincil hücre: `ceiling_path_v0`, D5 getiri MAE, `base_train_median`'a karşı.** Gerekçe [ÇIKARIM]: D5, ortalama S_5 ≈ 0.43 ile karışım medyanının ilk kez limit atomundan çıkıp özelliklere göre değiştiği ufuktur (D1–D3'te medyan hemen her arzda ρ_h'dir; D10'da limit atomu küçüktür ve hücre yayılımı büyüktür); V1.5'in de en güçlü ve önceden ilan edilmiş hücresi D5 MAE–medyandır, bu yüzden doğrudan karşılaştırılabilir. Diğer bütün hücreler "keşif" etiketiyle gösterilir. Sıfır modele karşı D5 MAE hücresi, "katkı mekanik mi" sorusunun adlandırılmış keşif hücresidir (§6 başarısızlık tanımı), birincil değildir.

## 6. ÖNCEDEN YAZILMIŞ BEKLENTİ

Bu bölüm 2026-09-22'de, bu modeller için hiçbir kod ve skor yokken yazıldı; sonradan değiştirilmez. Sayılar MODELS.md'deki DİĞER modellerin backtest tablolarından (V1.5, pb_v0, ceiling_hazard_v0) ve H99 tanımlayıcı ölçümlerinden mekanikle türetildi; bu modellerin skoru hesaplanmadı. Backtest H99 üzerinde ve tasarıma maruzdur; kanıt değeri düşüktür. Birim: getiri farkı puan (0.030 = 3 puan); Brier farkı ham.

**D1 (beraberlik, açıkça):** Tavan olasılığı ~0.82 iken MAE için en iyi nokta tahmin limitin kendisidir; S_1 ≥ 0.5 olan her arzda karışım medyanı = ρ_1 = `base_always_ceiling`'in tahmini (adım yuvarlaması dışında aynı). **Yeni model D1 MAE'de `base_always_ceiling` ile BERABERE kalır; aralık 0'ı içerir; fold'ların ≥ 80/87'sinde fark bit-eşit 0 ya da |fark| < 0.001.** "D1'de kazanç beklenmiyordu" cümlesi bu satıra dayanarak kullanılabilir. D1 p_up'ı taban oranından ayırt edilemez.

| Ufuk | Çıktı | Karşılaştırılan | Beklenen fark (model − karş.) | Aralık 0'ı | Gerekçe (kısa) |
|---|---|---|---|---|---|
| D1 | MAE | `base_always_ceiling` | 0.000 … +0.005 | içerir (beraberlik) | medyan = ρ_1 |
| D1 | MAE | `base_train_median` | 0.000 … +0.005 | içerir | medyan kuralı D1'de ≈ 0.1 |
| D1 | MAE | `v1_5_h99` | −0.007 … −0.002 | dışlayabilir (negatif) | V1.5'in D1 farkı +0.0046 [+0.0015, +0.0080] aynen devralınır; modelleme kazancı DEĞİL |
| D1 | MAE | sıfır model | \|fark\| < 0.001 | içerir | ikisinde de medyan = ρ_1 |
| D1 | Brier | `base_rate` | −0.005 … +0.005 | içerir | p_up_1 ≈ S_1 + (1 − S_1)·0.44 ≈ 0.90 ≈ taban oranı |
| D1 | Brier | `base_last10_rate` | −0.010 … +0.002 | içerir | |
| D1 | Brier | `v1_5_h99` | −0.002 … +0.010 | içerir | |
| D1 | Brier | sıfır model | \|fark\| < 0.003 | içerir | |
| D3 | MAE | `base_always_ceiling` | −0.020 … +0.005 | içerir | S_3 ort. ≈ 0.70; medyan çoğu arzda ρ_3; S_3 < 0.5 arzlarda düşer |
| D3 | MAE | `base_train_median` | −0.020 … +0.005 | içerir | |
| D3 | MAE | `v1_5_h99` | −0.010 … +0.020 | içerir | V1.5 D3 MAE 0.120, tavan kuralı 0.136 |
| D3 | MAE | sıfır model | −0.015 … 0.000 | içerir | |
| D3 | Brier | `base_rate` | −0.040 … −0.005 | büyük olasılıkla içerir | p_up_3 ≈ 0.42 + 0.58·S_3; S_3 ayrımı RPS'te güçlü |
| D3 | Brier | `base_last10_rate` | −0.040 … −0.005 | büyük olasılıkla içerir | |
| D3 | Brier | `v1_5_h99` | −0.010 … +0.030 | içerir | V1.5 D3 Brier 0.149 |
| D3 | Brier | sıfır model | −0.025 … 0.000 | içerir | |
| D5 | MAE | `base_train_median` **(BİRİNCİL)** | **−0.090 … −0.020** | **dışlaması olası, garanti değil** | medyan kuralı 0.306; karışım medyanı S_5'e göre 0.2–0.6 arasında ayrışır |
| D5 | MAE | `base_always_ceiling` | −0.110 … −0.040 | dışlaması olası | tavan kuralı 0.333 |
| D5 | MAE | `v1_5_h99` | −0.020 … +0.050 | içerir | V1.5 D5 MAE 0.222; aynı bilgi (f1–f3) farklı yolla |
| D5 | MAE | sıfır model | −0.050 … −0.005 | içerir | özellik ayrımının getiriye taşınan payı |
| D5 | Brier | `base_rate` | −0.030 … 0.000 | içerir | p_up_5 ≈ 0.62 + 0.38·S_5 |
| D5 | Brier | `base_last10_rate` | −0.035 … −0.005 | içerir | |
| D5 | Brier | `v1_5_h99` | 0.000 … +0.040 | içerir | |
| D5 | Brier | sıfır model | −0.020 … +0.005 | içerir | |
| D10 | MAE | `base_train_median` | −0.100 … −0.010 | büyük olasılıkla içerir | medyan kuralı 0.564; hücre yayılımı büyük (sd 0.19–0.31) |
| D10 | MAE | `base_always_ceiling` | −0.750 … −0.550 | dışlar (negatif) | tavan kuralı 1.195 (bilgi değeri düşük) |
| D10 | MAE | `v1_5_h99` | −0.020 … +0.100 | içerir | V1.5 D10 MAE 0.448; kazanç BEKLENMEZ |
| D10 | MAE | sıfır model | −0.050 … +0.010 | içerir | S_10 ayrımı küçük |
| D10 | Brier | `base_rate` | −0.020 … +0.010 | içerir | p_up_10 ≈ 0.66 + 0.34·S_10 |
| D10 | Brier | `base_last10_rate` | −0.070 … −0.020 | dışlayabilir | son-10 kuralı D10'da zayıf (0.305) |
| D10 | Brier | `v1_5_h99` | +0.010 … +0.060 | içerir ya da pozitif dışlar | V1.5 D10 Brier 0.188 daha iyi |
| D10 | Brier | sıfır model | −0.010 … +0.005 | içerir | |
| `@INF` | D5 MAE | `base_train_median` | −0.040 … +0.010 | içerir | yalnız mekanik: fold içinde arzlar arası ayrım yok |
| `@INF` | D10 MAE | `base_train_median` | −0.060 … +0.020 | içerir | |
| `pb_ceiling_path_v0` | D5 MAE | `pb_v0` | −0.040 … +0.030 | içerir | pb_v0 D5 MAE 0.275 |
| `pb_ceiling_path_v0` | D5 MAE | `ceiling_path_v0` (bilgi) | +0.000 … +0.050 | içerir ya da pozitif dışlar | talep katının değeri |

Hangi ufukta kazanç en olası: **D5 getiri MAE** (medyan/tavan kurallarına karşı) ve **D3 p_up Brier** (taban oranlarına karşı). En az olası: D1 her hücre (beraberlik); D10 MAE ve Brier'de V1.5'e karşı (V1.5 D10'da güçlü, bu modelin D10'u hücre gürültüsüne bağlı).

**Başarısızlık tanımları (backtest'te de canlıda da aynı sözcüklerle):**
- (a) **Yalnız mekanik:** ana model − sıfır model, {D3, D5, D10} × {MAE, Brier} altı hücrenin hepsinde aralık 0'ı içeriyor VE noktasal fark ≥ −0.005 → "özellik bilgisi getiriye taşınmıyor; katkı yalnız mekaniktir". Model listede kalır; kart bunu yazar.
- (b) **Mekanik eşleme katmıyor:** sıfır model − `base_train_median` D5 VE D10 MAE'de aralık tamamen 0'ın üstünde → "limit yolu + kırılma sonrası karışım medyan kuralından kötü".
- (c) **Eşleme hatası:** ana model − `base_always_ceiling` D1 MAE'de aralık tamamen 0'ın üstünde (D1 beraberliği bozulmuş) → kod/eşleme incelemesi; model yine dondurulur, MODELS.md'ye yazılır.
- (d) **Kalibrasyon:** |ortalama p_up_3 − gözlenen Y_3 oranı| > 0.15.
- (e) Prospektif (n ≥ 30): birincil hücre aralığı 0'ı pozitif tarafta dışlıyor → "geçemiyor".
Ara durum (aralık 0'ı içeriyor): "ayırt edilemiyor"; n < 30 hüküm yok; n < 10 yalnız satır tablosu (SPEC_SCORING §8).

**Her durumda ne yapılacak:**
- Beklenti tuttu ya da tutmadı: **v0 bu şartnameyle dondurulur**; tutmayan parça adıyla MODELS.md'ye yazılır. Sonuca bakıp hücre/eşik/gruplama değiştirmek = yeni model_id + deney günlüğü satırı.
- **Beklentiden çok iyi** (tanım: birincil hücrede fark < −0.120 ya da aralığın üst ucu < −0.060; ya da herhangi bir D3/D5/D10 hücresinde fark, yukarıdaki aralığın alt ucundan 0.03'ten fazla aşağıda): dondurmadan önce **farklı elle sıfırdan yeniden üretim** (ilk uygulamayı görmeyen ayrı oturum, yalnız bu şartnameyle; ledger'lar |Δ| ≤ 1e-9 ile eşleşmeli). Eşleşmezse fark giderilene kadar dondurma yok.
- Başarısızlık (a)/(b): dondurma yine yapılır (mekanik gösterim ve koşullu güncelleme ürünü için S gerekli); uygulama getiri/p_up sütununda "basit kural daha iyi ya da ayırt edilemiyor" yazar.

## 7. Koşullu güncelleme: "bugün tavan gitti, yarın ne olur"

Ürün özelliği; aynı şartnamede tanımı ve skorlaması. Girdi: dondurulmuş kayıt (S_1..S_10, hücreler, C yolu, P) + resmi THB/THM'den gözlenen seans dizisi. Deterministik; yeni dondurma gerekmez; hiçbir şey yeniden fit edilmez.

**Durumlar (resmi THM tavan etiketleriyle, SPEC_SCORING §3):**
1. **Seri j. günde hâlâ sürüyor** (D1..Dj tavan, j ≥ 1): 
   - P(L ≥ k | L ≥ j) = S_k / S_j, k = j+1..10. P(L = t | L ≥ j) = (S_t − S_{t+1}) / S_j (j ≤ t ≤ 9), P(L = 10 | L ≥ j) = S_10 / S_j.
   - h ≤ j: R_h gerçekleşmiştir, tahmin gösterilmez (gerçekleşen değer gösterilir). h > j: koşullu karışım = [(ρ_h, S_h/S_j)] + t = j..h−1 için hücre(B, h − t) atomları ağırlık P(L = t | L ≥ j)/n_cell; medyan, p_up, kuantiller §4 kuralıyla. C_t yerine gözlenen kapanış(D_t) kullanılır (t ≤ j için gözlenmiştir; t > j için deterministik C_t); gözlenen kapanış C_t'den farklıysa `limit_path_mismatch = 1`.
   - j = 0 = koşulsuz kayıt (kimlik testi).
2. **Seri t. günde kırıldı** (L = t bilinir, D_{t+1} gözlendi): S kısmı düşer; h > t için R_h atomları (kapanış(D_t)/P)·(1 + v) − 1, v ∈ hücre(g(t), h − t), ağırlık 1/n. Kırılmadan sonra gözlenen ek seanslar (D_{t+2}, …) bu v0'da ayrıca koşullanmaz (hücreler son limit-yolu gününe göre tanımlıdır); ekranda "kırılma sonrası, D_t'ye koşullu" yazılır (§11 soru 5).
3. `ceiling_hazard_v0`, `ceiling_hazard_v0@INF`, `pb_ceiling_v0` ve KM kuralları için yalnız durum 1'in S kısmı geçerlidir (getiri eşlemesi yok); bu modeller zaten dondurulmuştur, kayıtlarındaki S vektörü kullanılır.

**Canlı skorlama tanımı (SPEC_SCORING'e ek; kod Faz 2B/2C'de):**
- Skorlanan çift (a, j), j = 1..9: arz a'nın dondurulmuş kaydı var, resmi THM'den L_a ≥ j biliniyor (D1..Dj tavan etiketi 1) ve D_{j+1}..D_10 sonuçları girmiş (eksik ufuk → `TARGET_UNAVAILABLE`, tüm modeller için aynı anda düşer). Payda: `registry/ipos.csv`'de FROZEN olup L ≥ j olan her arz; j başına `n_scored / n_refused / n_skipped / n_target_unavailable`.
- Sınıf: (a, j) çifti, dayandığı kaydın (model, a) sınıfını AYNEN miras alır (LIVE / LATE_RECORD / RETRO); j'ye göre yeniden sınıflanmaz.
- Metrikler, j başına ayrı:
  - **Koşullu RPS_j** = (1/(10 − j)) Σ_{k=j+1..10} (S_k/S_j − 1[L ≥ k])². Birincil.
  - **Koşullu Brier**: k = j + 1 ("yarın") ve k = 10 ("sonuna kadar"); j = 9'da tek hücre.
  - İkincil (yalnız `ceiling_path_*`/`pb_ceiling_path_*`): koşullu p_up Brier ve koşullu medyanın MAE'si, h ∈ {3, 5, 10}, yalnız h > j.
- Kurallar (aynı j, aynı arzlar): koşullu KM (`base_km_expanding`, `base_km_last10` kayıt değerlerinden S^KM_k / S^KM_j), koşullu `@INF` (S^INF_k / S^INF_j), koşullu her-zaman-tavan (1). Getiri/p_up ikincilleri için: koşullu sıfır model yolu (`ceiling_path_v0@INF`'in koşullu karışımı) ve koşulsuz `base_train_median`/`base_rate` (yalnız referans; "koşulsuz" etiketiyle).
- Aralık: SPEC_SCORING §8 (aylık blok = D_1 ayı, 4000, seed, n ≥ 10 ve ≥ 6 blok). Küçük-n dili §8 ile aynı: j başına n < 10 → yalnız satır tablosu; 10 ≤ n < 30 → "yetersiz örnek"; n ≥ 30 → hüküm.
- **Birleştirme yasağı:** farklı j'ler toplanmaz; koşullu hücreler koşulsuz RPS/MAE/Brier ile hiçbir tabloda toplanmaz ya da ortalanmaz (aynı arz birden çok j'de bulunur; bağımlı). `ScaleMixError` mantığı bu tablolara da uygulanır.
- Bu tanım canlıda ilk koşullu metrik gösteriminden (n ≥ 10) önce yazılmıştır; bugünkü 7 arzda metrik üretilmez.
- Backtest tarafı (bilgi, keşif, tasarıma maruz): H99'da mevcut tavan ledger'larından j = 1..9 için koşullu RPS ve Brier hesaplanabilir; yeni model değildir, `experiments/log.jsonl`'a `kind: conditional_eval` satırıyla düşer; MODELS.md'de ayrı, "koşullu (keşif)" başlıklı tablo.

## 8. Backtest planı (Opus için)

- Plan kimlikleri: `H99_CEILING_PATH_T_CUTOFF_REUSE_CEILING_LEDGER` (ana ve sıfır model), `H99_PB_CEILING_PATH_B_CUTOFF_REUSE_PB_CEILING_LEDGER` (PB varyantı).
- **S_k yeniden kullanımı, yeniden fit yok:** her fold için S_1..S_10 doğrudan `tests/reference/macos_golden_faz1b/ceiling_hazard_v0_fold_ledger.csv` (ledger sha256 `976b4dcea981…`), `ceiling_hazard_v0@INF_fold_ledger.csv` (`90b610463de4…`) ve `pb_ceiling_v0_fold_ledger.csv` (`c92ce859ac67…`) satırlarından okunur (`fold_id` = `CEILING|TICKER` vb., `status = FIT_OK`, `S_1..S_10`). Fold kümesi ve sırası bu ledger'larınkidir (87 / 87 / 87). Kaynak ledger'ın sha256'sı ve fold_id'si yeni ledger'a yazılır. FIT_OK olmayan satır → `SURVIVAL_NOT_AVAILABLE` (beklenmez).
- Kesim T = kaynak ledger'ın `prediction_date`'i (ana/sıfır: ilk işlem günü; PB: B(k)). Hücreler her fold'da §3 kuralıyla, 99 arzın hepsinden, yalnız seans tarihi < T olan gözlemlerle kurulur (`borsai/data.py`'deki seans tarihleri; kapanışlar SESSIONS dosyasından Decimal olarak okunur; bu okuma yalnız hücre kurulumu içindir).
- Her fold, h = 1..10 için §4 çıktıları; gerçekleşen R_h (h ∈ {1,3,5,10}, `training_table.csv`), Y_h, L.
- Metrikler: §5 tablosu; SPEC_SCORING §7 ve SPEC_DEVIATIONS C7 (blok = ilk işlem ayı, 4000 tekrar, `random.Random(20260921)`, aralık sıralı dağılımın 100. ve 3899. elemanı; Brier [0.01, 0.99]). Ek: p_up kalibrasyonu (ort. p_up_h vs gözlenen Y_h oranı), medyan-AE, yön isabeti (hep-yukarı ile yan yana), h = 2, 4, 6..9 için de MAE (yalnız bilgi; kural yok).
- Her koşu `experiments/log.jsonl`'a `run_backtest` ile düşer (kural 4): `model_id`, `plan_id`, `spec_sha256` (kanonik şartname sözlüğü), `spec_document` ve `spec_document_sha256` (bu dosya), `survival_ledger_sha256`, `ledger_sha256`, `folds_scorable`, metrikler (ufuk başına n, MAE, MedAE, Brier), `data_version_sha256`, `context` (`faz4_acceptance_run`, `faz4_golden`). Altın ledger'lar `tests/reference/macos_golden_faz4/` altına; regresyon testi bayt eşitliğiyle.
- **Fold ledger sütunları:** `model_id, fold_id, ticker, first_trading_date, prediction_date, survival_model_id, survival_ledger_sha256, survival_fold_status, S_1..S_10, P_L_0..P_L_10, ipo_price, snapped_ipo_price, tick, C_1..C_10, rho_1..rho_10, cells_n_Z_1..cells_n_Z_10, cells_n_B_1..cells_n_B_9, cells_max_session_date, cells_ipos_sha256, status, ` ve h = 1..10 için `D{h}_return, D{h}_mean, D{h}_p_up, D{h}_q10, D{h}_q90, D{h}_post_break_status, D{h}_pooled_cells (JSON), D{h}_n_atoms`, ve `realized_R_D1, realized_R_D3, realized_R_D5, realized_R_D10, realized_Y_D1..D10, realized_L`.
- Karşılaştırma ledger'ları yeniden koşulmaz: Faz 1A/1B altın ledger'larından (ticker, ufuk) ile eşlenir; eşleşik n her hücrede raporlanır.
- Nihai dondurma: hücreler 99 arzın tamamından, kesim 2026-08-19 (sonuç seansları ≤ 2026-08-19); seri modeli JSON'ları gömülür. `models/INDEX.json`'a sona eklenir (Faz 1B bekçisi ilk 7 kaydı ve Faz 1A dosyalarını değişmemiş ister). Faz 1 modellerinin dosyaları, altın ledger'ları ve `docs/specs/` DEĞİŞMEZ.

## 9. Kabul testleri (Opus için, kanıtlanabilir)

1. **Fiyat adımı ve limit:** H99 SESSIONS'ın 990 satırında U(referans) = üst limit 990/990, Lo(referans) = alt limit 990/990 (Decimal eşitliği). Adım tablosu sınır değerleri: adim(19.999) = 0.01, adim(20) = 0.02, adim(2500) = 2.50.
2. **Limit yolu:** 99 arzda C_h (h = 1..10) = seri ≥ h olan her arzın resmi kapanışı: 81/70/66/53/41/33/27/21/17/14 eşit, 0 farklı. snap: BORLS 25.29 → 25.30, AVPGY 55.08 → 55.10, ARTMS 25.35 → 25.36, LILAK 37.39 → 37.40; diğer 95 arzda snap(P) = P.
3. **Hücre sayımı (tam kohort, kesim yok):** Z m = 1..10 hepsi 18; B m = 1..9 = 67, 64, 60, 54, 48, 40, 28, 15, 11; toplam 567 gözlem; sınır dışı 0; m = 1'de B'de tam taban 36/85 (Z + B) ve tavan 0.
4. **Tutarlılık (rastgele 1000 S vektörü + 99 eğitim satırı):** ağırlık toplamı = 1 (|Δ| ≤ 1e-12); return ≤ ρ_h; S_h ≥ 0.5 ⇒ return = ρ_h; S ≡ 1 ⇒ q10 = q50 = q90 = ρ_h ve p_up = 1; p_up ∈ [0, 1] ve p_up ≥ S_h; q10 ≤ q50 ≤ q90; her atom ∈ [0.9^h − 1, ρ_h^max].
5. **Sıfır model:** `ceiling_path_v0@INF`'in S'i, `ceiling_hazard_v0@INF.json`'un `predict_hazard` çıktısına bit-eşit; γ kapalı biçim (SPEC_CEILING_V0 §13-5). Gömülü kopyaların sha256'sı INDEX ile eşit (üç model).
6. **Predict paritesi:** 97 (ana), 97 (sıfır), 99 (PB) eğitim arzında backtest kodunun nihai-dondurma hesabı ile stdlib `predict_path.predict` |Δ| ≤ 1e-9 (return, p_up, q10, q90, mean; her h). `predict_path` import listesi stdlib + `borsai.predict_hazard`/`features`/`survival` (numpy/sklearn yok; mevcut K2 testi kalıbı).
7. **Koşullu formül (sentetik):** j = 0 ⇒ koşulsuzla bit-eşit; S_k/S_j, hazard'lardan Π_{d=j+1..k}(1 − h_d) ile |Δ| ≤ 1e-12; koşullu ağırlıklar toplamı 1; h ≤ j için tahmin üretilmez; durum 2'de S kısmı yok ve ağırlık toplamı 1; koşullu RPS_j, S ≡ 1[L ≥ k] için 0; her-zaman-tavan ve L = j için 1.
8. **Walk-forward sızıntı:** her fold'da `cells_max_session_date` < T; T ve sonrası tarihli hiçbir seans hücrede yok (sentetik: T'den 2 seans önce kırılmış arz tam 1 gözlemle girer); PB planında < B(k). Hiçbir fold `POST_BREAK_INSUFFICIENT` değil (87/87); ilk fold EKOS'ta B = [6, 6, 5, 4, 3, 2, 0, 0, 0], Z = 0 ve havuzlama merdiveni (B,1) için {(B,1),(Z,1),(B,2),(Z,2)} → n = 12 verir.
9. **Havuzlama determinizmi:** aynı girdi iki kez aynı hücre listesi; kırpma yalnız havuzlanmış gözlemlerde; N_MIN = 10 sabiti JSON'da.
10. **Fold kümesi:** yeni ledger'ların fold_id/ticker dizisi kaynak tavan ledger'larınkiyle birebir; `survival_ledger_sha256` doğru.
11. **Ret/uyarı:** ana model f3 = None → `F3_MISSING`, diğer alanlar None; sıfır model aynı girdiyle tahmin verir; PB varyantı PB alanı eksikse `PB_FIELD_MISSING`; arz fiyatı 25.29 → `IPO_PRICE_NOT_ON_TICK_GRID` uyarısı ve snap = 25.30.
12. **Deney günlüğü ve bekçiler:** her koşu bir satır ekler; `docs/specs/` dosya sayısı 11 ve git durumu temiz kalır; Faz 1A/1B altın ledger'ları ve model dosyaları bayt-eşit; 2026-08-19 sonrası veri yok.
13. **Kayıt uyumu:** `freeze.build_record` yeni modeller için hücre üretir; `scoring.prediction_of_cell` D1/D3/D5/D10 `return`/`p_up`'ı okur; kural 1 gereği kayıt, üç yeni modelin çıktısını ve parametre sha'larını içerir.

## 10. Maruziyet

**Gördüm (bu oturum):**
- `docs/MODELS.md`'nin tamamı: V1.5, `v1_6_h99`, `v1_5_market20_v0`, `pb_v0`, `ceiling_hazard_v0`, `pb_ceiling_v0` backtest tabloları (eşleşik farklar, aralıklar, kalibrasyon, λ dağılımları, nihai katsayılar). §6'daki sayılar bunlardan türetildi.
- Eski repodan F1 belgesi (`BORSAI_V3_TARGET_REVIEW_20260907_F1.md`) tamamı; yalnız modelleme içeriği (§1 S1, §2 S2, MECHANICS_BASE, önceden yazılan D1 beklentisi) alındı; N_A kapıları, merdiven, M0/M1/M2, permütasyon, τ, çeyrek blok, B = 10 000, %90 aralık, maruziyet sınıf tabloları ALINMADI.
- `docs/specs/` (CEILING, SCORING, PB tamamı), `docs/DATA.md`, `DATA_NOTES.md`, `SPEC_DEVIATIONS.md`, `experiments/README.md`, `models/ceiling_hazard_v0.json`, `@INF.json`, `pb_ceiling_v0.json`, `INDEX.json` (γ, β, r, sha'lar), `borsai/survival.py`, `predict_hazard.py`, `horizons.py`, `rules.py`, `data.py`, `metrics.py`, `predict.py` (baş), `freeze.py` (model_kind, build_record), `backtest.py` (ledger sütunları), `report_faz1b.py` (OPERATIONAL_RULES), `specs.py` (baş), `tests/test_faz1b_guardrails.py`, `test_guardrails.py`; `borsai/scoring.py` ve `outcomes.py`'nin yalnız fonksiyon/sabit adları (grep; Faz 2B kodu, veri değil).
- Altın ledger'lar: `ceiling_hazard_v0` ve `@INF` ledger'larının başlığı ve ilk satırı (EKOS S vektörü), fold sayıları ve ticker kesişimleri; `base_train_median` ve `v1_5_h99` ledger'larının başlıkları. Değer okuması yalnız EKOS satırı.
- H99 tanımlayıcı ölçümler (`ekler/m4_kirilma_sonrasi.py` → `m4_cikti.txt`): L dağılımı, üst limit/referans oranı, adım/yuvarlama uyumu, C_h eşitliği, L = t < h sayıları, kırılma sonrası getirinin m ve gruba göre konum/yayılımı, taban/tavan sayıları, Y_h oranları L ≥ h / L < h gruplarında, fold başına hücre büyüklükleri. Bunlar sonuç (kapanış) verisidir; H99 zaten tasarıma maruzdu. Grup ayrımı (Z/B), N_MIN ve havuzlama sırası bu ölçümler görüldükten sonra seçildi → **tasarıma maruz** (mekanik gerekçesi ayrıca vardır ama karşı-olgusal duyarlılık BİLİNMİYOR).
- borsaistanbul.com: yalnız Pay Piyasası "Piyasa İşleyişi" sayfası (kural metni; sha256 ekte). Ana sayfanın bağlantı listesinde 2026-09-22 tarihli bir duyuru başlığı görüldü ("yukarı adım kuralı" — açığa satış kuralı; fiyat marjıyla ilgisiz, içeriği açılmadı). Fiyat/bülten verisi indirilmedi.

**Görmedim:** `data/outcomes/`, `data/raw/bist/`, `scores/`, `docs/SCORES.md` (dizinler listelenmedi, açılmadı); eski repoda replay, `artifacts/outcomes|live_forecast|evaluation|predictions`, `BorsAi_External_Archive/`, kökteki realized/evaluation dosyaları (yalnız kök dizin adları `ls` ile görüldü, açılmadı); 2026-08-06 sonrası listelenen 7 arzın hiçbir gerçekleşen değeri. `docs/prompts/FAZ2B_*`, `FAZ3_*` okunmadı. Önerilen modellerin ve sıfır modelin hiçbir skoru hesaplanmadı; basit kurallarla karşılaştırılmadı.

**Yanlışlıkla görülen:** yok.

## 11. Açık sorular (proje sahibine; en çok 5)

1. **D1 baz fiyat yuvarlaması:** HALF_UP mı CEIL mi? Dört H99 örneği ikisiyle de tutar; kural metninde halka arz için açık hüküm yok. **Öneri:** HALF_UP (kural metnindeki "en yakın" dilinin uzantısı), uyarıyla; ilk çelişen canlı örnekte yeni model_id değil, `limit_path_mismatch` satırı (§2, §7) — çünkü C yolu skorlanan tahmini yalnız adım payı kadar etkiler.
2. **Fiyat marjı rejimi:** sayfa yeni pazar yapısında %20/%15 esasını yazıyor ama %10 "yeni duyuruya kadar" sürüyor. Marj değişirse ne olur? **Öneri:** marj JSON'da yazılı sabit (0.10); rejim değişikliği = yeni model_id (kural 5) ve o tarihten sonra listelenen arzlarda eski modelin kartında "marj rejimi değişti" uyarısı; THM üst limiti ile C_1 karşılaştırması bunu otomatik yakalar.
3. **Hücre evreni 99 mu 97 mi?** Bileşen kovaryatsız; ALBTN ve ENDAE (ikisi L = 0) Z grubunu 16'dan 18'e çıkarır. **Öneri:** 99 (yazıldığı gibi); tavan planı test kümesi yine f3 dolu 87 fold.
4. **Birincil hücre:** D5 MAE–`base_train_median` mı, yoksa "ana − sıfır model D5 MAE" (F1'in MECHANICS_BASE mantığı) mı? **Öneri:** yazıldığı gibi D5 MAE–medyan (V1.5/pb ile aynı çizgi, prospektif n'de daha çözünür); sıfır modele karşı hücre adlandırılmış keşif ve başarısızlık (a) tanımı.
5. **Kırılma sonrası izleme:** durum 2'de kırılmadan sonraki gözlenen seanslara (D_{t+2}…) koşullanma v0'da yok. **Öneri:** v0 böyle dondurulsun; "kırılma sonrası izleme" ayrı bir ürün şartnamesi olsun (hücreler o zaman "son gözlenen kapanışa göre m" ile yeniden tanımlanır → yeni model_id).

## 12. Sözde kod

```
TICKS = [(20,0.01),(50,0.02),(100,0.05),(250,0.10),(500,0.25),(1000,0.50),(2500,1.00),(None,2.50)]   # Decimal
def tick(x): return first s for (lim,s) in TICKS if lim is None or x < lim
def U(b):  y = b*Decimal("1.1"); s = tick(y); return (y/s).to_integral(ROUND_FLOOR)*s
def snap(P): s = tick(P); return (P/s).to_integral(ROUND_HALF_UP)*s
def limit_path(P): C=[]; b=snap(P)
    for k in 1..10: b = U(b); C.append(b)
    return C, [float(c/P - 1) for c in C]

def build_cells(ipos, cutoff):                      # ipos: 99 arz; kapanışlar Decimal
    cells = {("Z",m): [] for m in 1..10} | {("B",m): [] for m in 1..9}
    for j in ipos:
        t = j.L
        if t >= 10: continue
        base = j.P if t == 0 else j.close[t]
        for m in 1..(10-t):
            if j.session_date[t+m] >= cutoff: break
            cells[("Z" if t == 0 else "B", m)].append((float(j.close[t+m]/base - 1), j.ticker))
    return {k: sorted(v) for k,v in cells.items()}

def pooled(cells, g, m, N_MIN=10):                  # merdiven §3; her adım bir hücre GRUBU, adım sonunda kontrol
    steps = [[(g,m)], [(other(g),m)]] + [[(gg,mm) for gg in ("Z","B") if valid(gg,mm)] for d in 1..9 for mm in (m-d, m+d)]
    out=[]; used=[]
    for step in steps:
        for key in step:
            if key in cells and cells[key]: out += cells[key]; used.append(key)
        if len(out) >= N_MIN: break
    if len(out) < N_MIN: return None, used
    lo, hi = 0.9**m - 1, 1.1**m - 1
    return [(min(max(v,lo),hi), tk) for v,tk in out], used     # kırpma yalnız havuzda etkili

def mixture(S, P, C, rho, cells, h):
    PL = p_streak(S)                                 # borsai.survival
    atoms = [(rho[h-1], S[h-1])]
    for t in range(0, h):
        vals, used = pooled(cells, "Z" if t == 0 else "B", h - t)
        if vals is None: return POST_BREAK_INSUFFICIENT
        scale = 1.0 if t == 0 else float(C[t-1] / P)
        atoms += [((scale*(1+v) - 1) if t else v, PL[t]/len(vals)) for v,_ in vals]
    atoms.sort(key=lambda a: a[0])                   # kararlı sıralama
    def Q(q): cum=0
        for r,w in atoms: cum += w; if cum >= q - 1e-12: return r
    return {"return": Q(.5), "q10": Q(.1), "q50": Q(.5), "q90": Q(.9),
            "p_up": sum(w for r,w in atoms if r > 0), "mean": sum(r*w for r,w in atoms), "limit_path_return": rho[h-1], "S_h": S[h-1]}

def predict(params, inputs):                        # stdlib
    surv = predict_hazard.predict(params["survival_model"], inputs)
    if surv["refused"]: return {..., "refused": surv["refused"]}
    P = Decimal(inputs["ipo_price_tl"]); C, rho = limit_path(P)
    cells = {(g,int(m)): [(v,tk) for v,tk in lst] for g in ("Z","B") for m,lst in params["post_break"]["cells"][g].items()}
    return {**surv, "limit_path": {...}, **{f"D{h}": mixture(surv["S"], P, C, rho, cells, h) for h in 1..10}}

def conditional(record, j, observed_closes):        # §7 durum 1; j = 0 -> koşulsuz
    S = record.S; Sc = [S[k-1]/S[j-1] for k in j+1..10]  ...  # ağırlıklar (S_t − S_{t+1})/S_j, t ≥ j; S_10/S_j
    # h > j için atomlar: (rho_h, S_h/S_j) + t=j..h-1: hücre(B, h−t), ölçek = observed_close[t]/P (t ≤ j) ya da C_t/P
```

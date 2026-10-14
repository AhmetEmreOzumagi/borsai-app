# SPEC_POST_D1_V0 — ilk gün sonrası güncelleme modeli (`post_d1_hazard_v0`)

Görev: BORSAI_FAZ5_FABLE_POST_D1_SPEC_20260924. Yazım: 2026-09-24, Fable. Uygulayıcı: Opus (Claude Code); sonra Fable sıfırdan yeniden üretim; sonra dondurma. Bu belge `docs/specs_faz5/` altındadır; `docs/specs/` ve `docs/specs_faz4/` değişmemiştir.

**Beyan (K3):** Bu şartname yazılırken hiçbir model fit edilmedi, hiçbir walk-forward ya da canlı skor hesaplanmadı ve **özellik–sonuç ilişkisine bakılmadı**. Bakılanlar: (a) D1 alanlarının TEK DEĞİŞKENLİ profili (`ekler/m5_d1_profil.py` → `ekler/profil_d1.txt`; yalnız 1. seans alanları, `ceiling_close_D1` yalnız L ≥ 1 alt kümesini seçmek için); (b) `docs/MODELS.md`'deki karşılaştırıcı başarımı (koşullu keşif tablosu, j = 1); (c) `docs/specs/SPEC_CEILING_V0.md` §2'nin yayımlı risk/olay tablosu; (d) borsaistanbul.com kural metinleri (`ekler/kural_metni_borsaistanbul_20260924.md`). Maruziyetin tamamı §10'dadır.

İşaretler: **[ÖLÇTÜM]** = bu oturumda dosyadan/komuttan; **[ÇIKARIM]** = yorum; **[KARAR]** = bu şartnamenin bağlayıcı kararı. Görev metnindeki 12 madde → bölüm eşlemesi: 1→§1, 2→§2, 3→§3, 4→§4, 5→§5, 6→§6, 7→§7, 8→§8, 9→§9, 10→§10, 11→§11 + §12, 12→§13.

## Özet (≤ 10 satır)

1. Soru: "Bugün (D1) tavan gitti; yarın ve sonrası ne olur?" Bugünkü cevap, dondurulmuş `ceiling_hazard_v0` kaydının koşullu güncellemesidir: P(L ≥ k | L ≥ 1) = S_k / S_1 (SPEC_CEILING_PATH_V0 §7). Bu, D1'in NASIL geçtiğini kullanmaz. Yeni model bunu D1'in resmi THB/THM bülteninden iki özellikle günceller.
2. Kapsam: yalnız D1'i tavanda kapatan arzlar (L ≥ 1; H99'da 81, karşılaştırıcının skorlanabilir fold'larında 71). Çıktı: S_k | (L ≥ 1, D1 bilgisi), k = 2..10; "yarın bozulur mu" = 1 − S_2/S_1 = h_2. D1 hedefi bu modelde hiç skorlanmaz.
3. Özellikler (2): `d1_lock` = 1[en düşük == üst limit] (gün boyu tek fiyat; Decimal, ham metin; H99'da 70/81), `d1_turnover` = ln(D1 hacmi / arz edilen pay) (el değiştirme; H99 medyanı 0.0042, kilitli/kilitsiz ayrışır). Beklenen işaretler hazard üzerinde: δ_lock < 0, δ_turn > 0.
4. Model: dondurulmuş `ceiling_hazard_v0`'ın doğrusal öngörücüsü SABİT OFSET; d = 2..10 günlerinin hazard'ına δ ∈ R² eklenir (h_1 değişmez). Yeni serbest parametre 2; L2, λ ızgarası SPEC_CEILING_V0 ile aynı, iç arz-bırak CV. λ = INF uç noktası karşılaştırıcının kendisidir (bit-eşit; ayrı sıfır model gerekmez).
5. **Birincil hücre:** koşullu RPS_1 (k = 2..10), `post_d1_hazard_v0` − `ceiling_hazard_v0` koşullu (S_k/S_1), aynı arzlar, aynı fold'lar. Kurallar: koşullu KM (iki), koşullu `@INF`, her-zaman-tavan. İkincil: koşullu Brier k = 2 ve k = 10.
6. Önceden yazılmış beklenti (§5): birincil fark −0.020 … +0.003 (nokta ≈ −0.008), aralık **büyük olasılıkla 0'ı içerir** ("ayırt edilemiyor"); kazanç en olası k = 2 Brier'inde (−0.025 … 0.000). Kurallara karşı karşılaştırıcının payı devralınır (dışlaması olası).
7. Canlı: yeni kayıt aşaması `POST_D1` (`registry/post_d1/<T>/`), girdisi D_1 tarihli resmi THB+THM bülteninin kendisi (sha256 pinli). Zaman kanıtı: push, D_1'i izleyen ilk resmi seans gününün **09:40:00 Europe/Istanbul** açılış emir toplama anından ÖNCE (kural metni Ek-9). Sınıf LIVE/LATE_RECORD/RETRO tarihlerden, yalnız h ≥ 2 hedefler.
8. Backtest: Faz 1B tavan fold planı (kesim T), test arzları L ≥ 1; ofset = o fold'un kendi `ceiling_hazard_v0` fit'i (ledger'la parite); D1 özelliği yalnız 1. seanstan; ön işleme fold içinde; kurallar aynı fold'dan. Beklenen n = 65–71.
9. Ret/uyarı: D1 tavan değil → `NOT_APPLICABLE_D1_NOT_CEILING` (ret değil, kapsam dışı); f3 yok → RET (miras); THM limiti yok → RET; yarım gün / gün içi durdurma → tahmin + uyarı.
10. **Backtest sonucu ne olursa olsun v0 bu şartnameyle dondurulur**; sonuca bakıp değişiklik = yeni model_id. Uygulama etkisi küçük (EK 3 gerekir): koşullu sekmeye "D1 sonrası" satırı ve POST_D1 kayıt akışı.

---

## 1. Kapsam ve çıktılar

**1.1 Kimlik [KARAR].** `model_id = post_d1_hazard_v0`; `algorithm = discrete_time_hazard_offset_logit_l2`; `stage = POST_D1`; `parent_model_id = ceiling_hazard_v0` (parametre dosyası `models/ceiling_hazard_v0.json`, sha256 `caa4dc867a9f…` INDEX'ten; JSON'a tam sha yazılır ve `freeze` sırasında INDEX ile denetlenir). Şartnamedeki herhangi bir şey (özellik, dönüşüm, ızgara, gün kümesi, fold kuralı, ofset kaynağı) değişirse yeni `model_id` (CLAUDE.md kural 5).

**1.2 Hangi arzlar.** Model yalnız **D1'i resmi tavanda kapatan** arzlarda tanımlıdır: `ceiling_close_D1 = 1` (SPEC_SCORING §3: `Decimal(KAPANIS) == Decimal(UST LIMIT)`, D_1'in THM'sinden). D1 tavan kapatmayan arzlar (H99'da 18/99) **v0'da kapsam dışıdır** [KARAR]: onlarda "seri" yoktur (L = 0), soru "yeniden tavana döner mi / getiri ne olur" sorusudur ve bugünkü ürün bunu `ceiling_path_v0`'ın kırılma-sonrası hücreleriyle (SPEC_CEILING_PATH_V0 §7 durum 2) zaten kapsar; ayrı bir model_id'nin işidir. Ayrıca kapsam dışı: talep katı (f3) olmayan arzlar (ofset modeli reddeder; §9) — PB tabanlı varyant açık soru 2.

**1.3 Çıktılar.** `predict(params, inputs)` standart hazard şemasını döndürür (SPEC_CEILING_V0 §8; `hazard[1..10]`, `S[1..10]`, `P_L[0..10]`, `P_close_ceiling[1..10]`), ancak:
- `hazard[1]` ve dolayısıyla `S[1]` **aynen ana modelden** gelir (D1 zaten gözlenmiştir; değer yalnız koşullu görünümde payda olarak kullanılır, hiçbir yerde skorlanmaz).
- `hazard[d]`, d = 2..10, D1 özellikleriyle güncellenmiştir. `S[k] = Π_{d≤k}(1 − hazard[d])`.
- **Birincil çıktı:** koşullu eğri `S_cond[k] = S[k]/S[1] = Π_{d=2..k}(1 − hazard[d])`, k = 2..10; `p_break_next = 1 − S_cond[2] = hazard[2]`; `P_L_cond[l] = P(L = l | L ≥ 1)`, l = 1..10. Bu görünüm var olan tek tanımdan üretilir: `borsai.predict_path.conditional_weights(S, j = 1)` (Python) ve `borsai_predict::survival::conditional(S, 1)` (Rust). **Bu yüzden yeni çıktı türü yoktur**: her koşullu okuyucu (uygulama §3g, Faz 2C skorlama) bu modeli `ceiling_hazard_v0` gibi okur.
- `P_close_ceiling[k]` ana modelin `reclose_rates`'i ile türetilir (ikincil; miras).
- **İkincil, türetilmiş (yeni parametre 0):** `path_conditional`: SPEC_CEILING_PATH_V0 §7 durum 1'in j = 1 koşullu karışımı, `ceiling_path_v0`'ın dondurulmuş hücreleri ve limit yoluyla, S yerine bu modelin S'iyle (`predict_path.conditional(params_path, output_with_S_post, j = 1, closes = [close(D_1)])`, tek tanım). h = 2..10 için koşullu medyan getiri, `p_up`, q10/q90. JSON'da `ceiling_path_v0` dosya sha'sı pinlenir. Kayıtta `ceiling_path_v0` çıktısı yoksa blok `null`. Skorlanır ama birincil hücreyi etkilemez (§4).

**1.4 Ne yapmaz.** j ≥ 2 için (D2 sonrası, D3 sonrası …) ayrı güncelleme yapmaz: v0 yalnız D1 bülteniyle çalışır; sonraki günler için ürün yine S_cond'un koşullu güncellemesini (S_cond[k]/S_cond[j]) gösterir (§8). "POST_Dj" genelleştirmesi yeni model_id'dir (açık soru 4).

## 2. Özellikler (2; sonuç görülmeden, mekanizmayla)

Kaynak: D_1 tarihli resmi THB (fiyat bülteni) ve THM (marj bülteni) dosyaları; bültenin ilgili satırı `<TICKER>.E`. Alan adları legacy toplayıcı ve arşiv eşlemesiyle aynıdır (`~/Desktop/Halka_Arz_Modeli/artifacts/ohlcv/pilot/BIST_BULLETIN_FIELD_MAPPING.md`; ad tabanlı, sıra tabanlı değil). Değerler ham metinden `Decimal(str)`; float'a girmez (SPEC_SCORING §1).

| Ad | Tanım | THB/THM alanı | Birim | Dönüşüm (eğitim kümesinden, arz düzeyinde) |
|---|---|---|---|---|
| `d1_lock` | 1[`Decimal(EN DUSUK FIYAT) == Decimal(UST LIMIT FIYATI)`], D_1 satırı | THB `EN DUSUK FIYAT`; THM `UST LIMIT FIYATI` | 0/1 | z-skor (ortalama, popülasyon std, ddof = 0). σ = 0 ise düşer (SPEC_CEILING_V0 §4 kuralı) |
| `d1_turnover` | ln(`TOPLAM ISLEM ADEDI` / `shares_offered`) | THB `TOPLAM ISLEM ADEDI` (pay adedi; 1 lot = 1 pay, Pay Piyasası Prosedürü 5.1.1); `shares_offered` = girdi belgesindeki satılan toplam pay (f1/f2'nin paydasıyla aynı alan; ek satış dahil olduğu arzlarda dahil, DATA_NOTES §4) | ln(pay/pay) | [p05, p95] kırpma (Type-7 doğrusal kantil, eğitim kümesinden; f3 ile aynı yöntem) → z-skor |

**Eşitlik ve yuvarlama kuralı [KARAR].** `d1_lock` ham metinlerin Decimal eşitliğidir (`thb_raw_low` ve `thm_raw_upper_limit`; "10.12" == "10.120" eşit; adım/yuvarlama uygulanmaz). Tavan etiketiyle aynı kural (SPEC_SCORING §3); düzeltilmiş (`low`, `upper_limit`) sütunlar kullanılmaz. Ek tutarlılık: kilit ⇒ açılış = en yüksek = kapanış = üst limit (H99'da 70/70 tutar, `profil_d1.txt` §2). Bu üç eşitlik ayrıca hesaplanır; biri tutmazsa `WARN_D1_LOCK_INCONSISTENT` uyarısı (bülten satırı elle incelenir; tahmin yine üretilir).

**Neden bu ikisi [ÇIKARIM, sonuç görülmeden].**
- Tavan mekaniği: fiyat üst limitteyken alış emirleri limit fiyatta kuyruk oluşturur; işlem ancak bir satıcı kuyruğa vurunca olur. `d1_lock = 1` demek, D1 boyunca kuyruk hiç tükenmedi, tek bir işlem bile limitin altında olmadı demektir: karşılanmamış talebin doğrudan, bültenden okunabilen ölçüsü. `d1_lock = 0` (D1 tavanda kapandı ama gün içinde düştü) demek, kuyruk en az bir kez tükendi ve fiyat geri çıktı: talep fazlası kırılgan. Beklenti: δ_lock < 0 (kilitlide sonraki günlerin hazard'ı düşük). Gün içi en düşük seviyenin büyüklüğü (`dip`) H99'da yalnız 11 arzda sıfırdan farklı (`profil_d1.txt` §3): sürekli değişkenin eğimi 11 gözlemle tanımlanamaz; ikili gösterge yeterli ve bütçeyi korur.
- El değiştirme: kilitli bir günde hacim tümüyle satıcıların kararıdır (alıcı kuyruğu sonsuz gibi davranır). `hacim / arz edilen pay`, tahsisat alanların ne kadarının ilk gün +%10'a satmayı seçtiğinin doğrudan örneklemidir; satmaya hazır elden çıkarıcıların (flipper) dağılımına dair D1'de edinilebilen tek nicel bilgidir. Beklenti: δ_turn > 0 (ilk gün çok satan kohort sonraki günlerde de satar; seri erken kırılır). Karşı-mekanizma: yüksek D1 hacmi "kuyruk çok satışı emdi ve yine de kilitli kaldı" diye de okunabilir (talep derinliği → δ_turn < 0). İkisi de a priori savunulabilir; bu yüzden işaret beklentisi §5'te düşük güvenle yazılır ve **işaret bir başarı ölçütü değildir**. Kilit ve el değiştirme güçlü ilişkilidir (H99: kilitli medyan 0.0028, kilitsiz 0.53); L2 cezası ortak λ ile ikisini birlikte büzer.
- Alınmayanlar: sözleşme sayısı (hacimle ln ölçeğinde neredeyse aynı bilgi; `profil_d1.txt` §3), AOF'nin limite uzaklığı (kilitli günde tam sıfır; kilit göstergesiyle örtüşür: 71/81 vs 70/81), gün içi aralık (`dip`; yukarıda), TL ciro (hacim × fiyat; arz büyüklüğü f1 ile karışır), özel işlem bildirimi hacmi (H99'un 99 D1'inde |AOF×hacim − ciro|/ciro ≤ 1e-3: fiilen yok).

**Eksik / işlemsiz / durdurma hâlleri.**

| Durum | Davranış |
|---|---|
| D_1 satırında `TOPLAM SOZLESME SAYISI = 0` ya da `KAPANIS FIYATI ≤ 0` | O gün `traded` değildir (SPEC_SCORING §2); D_1 henüz oluşmamıştır; model çağrılmaz (POST_D1 kaydı yazılamaz: `D1_NOT_TRADED`) |
| THM satırı yok / üst limit boş ya da ≤ 0 (`NA_LIMIT`) | RET `REFUSED_D1_LIMIT_NA` (tavan etiketi de NA; SPEC_SCORING §3) |
| `ceiling_close_D1 = 0` | `NOT_APPLICABLE_D1_NOT_CEILING`: ret değil, kapsam dışı; kayıtta hücre `status = NOT_APPLICABLE`; hiçbir n'e girmez, ayrı sayılır |
| `TOPLAM ISLEM ADEDI` boş/≤ 0 iken sözleşme > 0 | Veri tutarsızlığı: RET `REFUSED_D1_VOLUME_INVALID` (bülten satırı elle incelenir) |
| `shares_offered` yok / ≤ 0 / sayı değil | Etiketli RET `REFUSED_INPUT_SHARES_OFFERED` (çıplak exception yok) |
| f3 (talep katı) yok | RET `REFUSED_F3_MISSING` — ana modelin mirası (ofset hesaplanamaz) |
| D1 yarım gün (`half_day = 1`) | Tahmin üretilir; `WARN_D1_HALF_DAY` (el değiştirme kısa seansta ölçülmüştür; H99'da örnek yok, `profil_d1.txt` §1) |
| D1'de gün içi geçici durdurma (`GECICI DURDURMA = 1`, sözleşme > 0) | Tahmin üretilir; `WARN_D1_INTRADAY_HALT` (H99'da örnek yok) |
| `OZEL ISLEM BILDIRIMI ISLEM ADEDI > 0` | Hacim DÜZELTİLMEZ (resmi toplam kullanılır); `WARN_D1_SPECIAL_TRADES` bilgi uyarısı, ham değerler kayda yazılır |
| `d1_turnover` eğitim p05/p95 dışında | Kırpılır, `clipped: true` + uyarı (f3 kuralı) |
| Özellik eğitim min/max dışında | Tahmin + `OUT_OF_TRAINING_RANGE` uyarısı (`feature_ranges`) |

## 3. Model sınıfı ve parametre bütçesi

**3.1 Model [KARAR].** Arz i, gün d ∈ 2..10, x_i = (f1, f2, f3), w_i = (d1_lock, d1_turnover):

```
η^base_d(x) = γ^base_{g(d)} + β^base · z^base(x)          # dondurulmuş ceiling_hazard_v0: γ, β, ön işleme AYNEN (ofset, sabit)
logit h_d(x, w) = η^base_d(x) + δ · u(w),   d = 2..10       # δ ∈ R², u = z-skorlu (d1_lock, d1_turnover)
h_1(x)          = sigmoid(η^base_1(x))                     # değişmez
```
- Gün grupları, γ, β, ön işleme (`V1_3_STEPS_F1_F2_F3_IPO_LEVEL_NO_IMPUTATION_NO_F5`) ana modelden; bu modelde **yeniden fit edilmez, yeniden merkezlenmez**. Ofset SPEC_CEILING_V0 §5 ile aynı sayısal yolda hesaplanır (`predict_hazard.predict` ile parite testi: h_1 bit-eşit).
- Yeni kesişim yok: u eğitim ortalamasında sıfır olduğundan, ortalama D1 profilinde model = karşılaştırıcı. δ, d = 2..10'un hepsinde ortak (orantılı etki); gün-grubu etkileşimi yok (bütçe).
- Pseudo-satır yok [KARAR]: ofset sabit ve sonlu λ'da L2 cezası δ'yı sınırlar; ayrışma (separation) −∞'a gidemez. λ = INF: δ ≡ 0 (kapalı biçim: karşılaştırıcı).
- Amaç: `J(δ) = −Σ_r [e_r ln h_r + (1 − e_r) ln(1 − h_r)] + (λ/2)‖δ‖²`, r = eğitim arzlarının d ≥ 2 PP satırları (SPEC_CEILING_V0 §2 tanımı: satır ancak d − 1 ≤ L_i ise; event = 1[L_i = d − 1]). Çözücü: SPEC_CEILING_V0 §5'in Newton–Raphson'ı (2 boyut; ∇ ≤ 1e-10, ≤ 100 yineleme, adım yarılama, SPEC_DEVIATIONS A2 kabul kuralı). Yakınsamama → `MODEL_NOT_FIT_DID_NOT_CONVERGE`.
- Izgara ve seçim: λ ∈ {0.1, 1, 3, 10, 30, 100, 300, 1000, INF}; iç "bir arzı dışarıda bırak" CV: eğitimdeki her arz j için j'nin BÜTÜN d ≥ 2 satırları dışarıda, D1 ön işlemesi (p05/p95, μ, σ) kalanlardan yeniden, ofset değişmez; j'nin satırlarında log-kayıp (h [1e-12, 1 − 1e-12] kırpılı); skor(λ) = toplam nll / toplam satır; en küçük skor, bit-eşit eşitlikte **en büyük λ**. Yakınsamayan aday o fold için ızgaradan çıkar; INF her zaman kalır.

**3.2 Neden ofset, neden refit değil [ÇIKARIM].** Soru "D1 bilgisi bugünkü koşullu güncellemeye bir şey katıyor mu?"dur. Ofset tasarımında δ = 0 karşılaştırıcının kendisidir; fark yalnız D1 bilgisine atfedilir. γ/β'yı L ≥ 1 alt kümesinde yeniden fit etmek (6 + 2 parametre) hem bütçeyi aşar hem farkı "yeniden fit" ile "D1 bilgisi" arasında bölünemez kılar. Ofsetin kendisi eğitim kümesinde in-sample kalibredir; δ yalnız artık (residual) hazard'ı öğrenir.

**3.3 Bütçe [ÖLÇTÜM, yayımlı tablodan türetildi; yeniden sayılmadı].** SPEC_CEILING_V0 §2 tablosu: d = 2..10 risk 81 + 70 + 66 + 53 + 41 + 33 + 27 + 21 + 17 = **409 satır**, olay 11 + 4 + 13 + 12 + 8 + 6 + 6 + 4 + 3 = **67**, sağ kalım 342. f3'ü dolu kümede aynı (ALBTN ve ENDAE L = 0, d ≥ 2 satırı yok: 506 − 97 = 409; 83 − 16 = 67). 2 parametre → **33.5 olay/parametre** (10–15 kuralının çok üstünde). Azınlık sınıfı `d1_lock = 0`: 11/81 arz (`profil_d1.txt`); bu sınıfın d ≥ 2 satır/olay sayısı BİLİNMİYOR (bakılmadı) — δ_lock'un belirsizliği bu 11 arzla sınırlıdır, L2 bunu büzer. Bütçe ≤ 2 gerekçesi: tek bilgi kaynağı (bir bülten satırı), 67 olay, ve karşılaştırıcıya karşı çözünürlük ~0.03 (§5); üçüncü özellik (sözleşme sayısı) hacimle örtüşür.

**3.4 Sıfır/kovaryatsız eşdeğer model gerekli mi? [KARAR] Hayır.** Bu modelin λ = INF ucu, `ceiling_hazard_v0`'ın koşullu görünümüyle **bit-eşittir** (aynı ofset, δ = 0). O görünüm zaten karşılaştırıcı olarak kayıtlıdır ve skorlanır (Faz 2C j = 1 bloğu). Ayrı bir `post_d1_hazard_v0@INF` kaydı aynı sayıların ikinci kopyası olurdu; yerine kabul testi 5 (INF paritesi, |Δ| ≤ 1e-12) zorunludur. Nihai fit'te λ = INF seçilirse model yine dondurulur ve kartı "D1 bilgisi eklemiyor; karşılaştırıcıyla özdeş" yazar (§5 başarısızlık b).

**3.5 Eğitim (dondurma).** Küme `H99_F3_PRESENT_L_GE_1`: `data/training_table.csv`'de f3 dolu VE `ceiling_close_D1 = 1` olan arzlar (beklenen 81; kabul testi 1). Kesim 2026-08-19. Ofset `models/ceiling_hazard_v0.json`'dan. D1 alanları `data/raw/…_canonical_bist_session_outcomes.csv`'nin `session_number == 1` satırlarından (`thb_raw_low`, `thb_raw_volume`, `thm_raw_upper_limit`; ayrıca tutarlılık için `thb_raw_open/high/close`); 2..10. seansların fiyat/hacim sütunları HİÇ okunmaz (yalnız `target_session_date`, sansür için). `shares_offered` training_table'dan.

Model JSON ek alanları: `stage: "POST_D1"`, `parent: {model_id, file, sha256, gamma, beta, preprocessing_id}` (kopya + sha), `delta: {d1_lock, d1_turnover}`, `lambda`, `lambda_score_table`, `d1_preprocessing: {clip: {d1_turnover: {p05, p95}}, mean, std, dropped}`, `feature_ranges` (iki D1 özelliği + miras f1–f3), `training: {set: "H99_F3_PRESENT_L_GE_1", n_ipo, n_pp_rows (d ≥ 2), n_events, n_survivals, cutoff_date, tickers_sha256, d1_fields_sha256 (kullanılan 81 × 4 ham metin), data_version_sha256, sessions_file_sha256}`, `path_secondary: {model_id: "ceiling_path_v0", sha256}`, `spec_sha256` (bu dosya).

## 4. Karşılaştırmalar ve birincil hücre

Hepsi **koşullu ölçekte, j = 1**, aynı arzlar (L ≥ 1, iki tarafın da skorlandığı), aynı fold'lar (backtest) ya da aynı kayıt sınıfı (canlı). Fark = model − karşılaştırılan; negatif = model iyi. Koşullu metrikler SPEC_CEILING_PATH_V0 §7'nin ve Faz 2C'nin ORTAK fonksiyonlarıdır (`predict_path.conditional_rps`, `conditional_brier`); ikinci tanım yazılmaz.

| Öncelik | Metrik | Karşılaştırılan | Not |
|---|---|---|---|
| **BİRİNCİL** | Koşullu RPS_1 = (1/9) Σ_{k=2..10} (S_cond[k] − 1[L ≥ k])² | `ceiling_hazard_v0` koşullu: S_k/S_1 aynı fold ledger'ından (backtest) / aynı arzın birincil listeleme-öncesi kaydından (canlı) | Tek önceden ilan edilmiş hücre (çoklu karşılaştırmaya karşı) |
| kural | Koşullu RPS_1 | `base_km_expanding` koşullu (S^KM_k / S^KM_1), `base_km_last10` koşullu, `ceiling_hazard_v0@INF` koşullu, `base_always_ceiling` (S_cond ≡ 1) | SPEC_CEILING_PATH_V0 §7 kural listesi |
| ikincil | Koşullu Brier k = 2 ("yarın": (h_2 − 1[L ≥ 2])²) ve k = 10 ("sonuna kadar") | aynı beş karşılaştırılan | |
| ikincil | Kalibrasyon: ort(h_2) ile gözlenen D2 kırılma oranı; ort(S_cond[k]) ile gözlenen oran, k = 2, 3, 5, 10 | — | |
| ikincil (yalnız `path_conditional` varsa) | h ∈ {3, 5, 10}, h > 1: koşullu medyan getiri MAE, koşullu p_up Brier | `ceiling_path_v0`'ın kendi j = 1 koşullu karışımı | Yeni parametre yok; yalnız S farkının getiriye taşınan payı |
| keşif | Koşullu Brier k = 3..9; fold başına λ; δ işaretleri | | "keşif" etiketiyle |

Birincil hücrenin gerekçesi: yeni model basit kuralları geçse bile karşılaştırıcıyı (bugün üründe olan) geçmiyorsa ürüne bir şey katmaz (görev metni). Aralık: backtest'te SPEC_DEVIATIONS C7 yöntemi (MODELS.md ile aynı: D_1 ayı blokları, 4000 tekrar, `random.Random(20260921)`; Brier/RPS kırpmasız); canlıda SPEC_SCORING §8 (n ≥ 10 ve ≥ 6 blok). Hüküm dili SPEC_SCORING §8: "geçiyor" yalnız aralık 0'ı dışlarsa; n < 30 hüküm yok; n < 10 satır tablosu.

## 5. ÖNCEDEN YAZILMIŞ BEKLENTİ

Bu bölüm 2026-09-24'te, bu model için hiçbir kod ve skor yokken yazıldı; sonradan değiştirilmez. Sayılar `docs/MODELS.md` "Koşullu güncelleme (keşif): H99, j = 1" tablosundan (karşılaştırıcının bilinen başarımı), SPEC_CEILING_V0 §2 marjinal hazard tablosundan ve `profil_d1.txt`'nin tek değişkenli sayılarından **mekanikle** türetildi; hiçbir özellik–sonuç ilişkisi ölçülmedi.

**Karşılaştırıcının bilinen başarımı [ÖLÇTÜM, MODELS.md]:** j = 1, n = 71: RPS_1 = 0.1706; Brier k = 2: 0.1277; Brier k = 10: 0.1370. Fark (karşılaştırıcı − kural): vs `@INF` koşullu −0.0301 [−0.0592, −0.0004]; vs `base_km_expanding` −0.0362 [−0.0687, −0.0031]; vs `base_km_last10` −0.0408 [−0.0735, −0.0073]; vs her-zaman-tavan −0.3912 [−0.4904, −0.2744]. Brier k = 2 farkları: −0.0138 / −0.0128 / −0.0399 / −0.0272. **Aralık yarı genişliği n = 71'de ≈ 0.03** (RPS) ve ≈ 0.01–0.02 (Brier k = 2): bu ölçeğin çözünürlüğüdür.

**Mekanik türetme [ÇIKARIM].** D2 marjinal hazard'ı 11/81 = 0.136 (SPEC_CEILING_V0 §2). Kilit oranı 70/81 = 0.864 (`profil_d1.txt`). Kilit göstergesi D2 hazard'ını iki sınıfa ayırırsa, sınıf hazard'ları h_2|kilit = a, h_2|kilitsiz = b, 0.864a + 0.136b = 0.136 kısıtıyla (varsayımsal; ölçülmedi):
- Güçlü ayrım (a = 0.06, b = 0.62): mükemmel kalibre iki-sınıf Brier_2 = 0.864·0.06·0.94 + 0.136·0.62·0.38 = 0.081; sabit-oran Brier_2 = 0.136·0.864 = 0.1175 → ideal kazanç −0.036.
- Ilımlı ayrım (a = 0.10, b = 0.36): Brier_2 = 0.864·0.09 + 0.136·0.23 = 0.109 → ideal kazanç −0.008.
- Walk-forward'da 11 kilitsiz arz, L2 büzmesi ve erken fold'larda INF seçimi ideal kazancın ancak üçte biri – yarısını bırakır. k ≥ 4 için ana modelin g3 sabiti baskındır; D1 bilgisinin etkisi S_k'ya çarpımsal taşınır ama k büyüdükçe sönümlenir.

| Hücre | Karşılaştırılan | Beklenen fark (model − karş.) | Aralık 0'ı | Gerekçe (kısa) |
|---|---|---|---|---|
| **RPS_1 (BİRİNCİL)** | `ceiling_hazard_v0` koşullu | **−0.020 … +0.003 (nokta ≈ −0.008)** | **büyük olasılıkla içerir** → "ayırt edilemiyor" | k = 2'deki kazanç 9 ufka bölünür; çözünürlük 0.03 |
| RPS_1 | `ceiling_hazard_v0@INF` koşullu | −0.055 … −0.015 | dışlaması olası | karşılaştırıcının −0.030'u + kendi payı |
| RPS_1 | `base_km_expanding` koşullu | −0.060 … −0.020 | dışlaması olası | karşılaştırıcı −0.036 [−0.069, −0.003] |
| RPS_1 | `base_km_last10` koşullu | −0.065 … −0.025 | dışlaması olası | karşılaştırıcı −0.041 |
| RPS_1 | her-zaman-tavan | −0.42 … −0.36 | dışlar | karşılaştırıcı −0.39 |
| Brier k = 2 | `ceiling_hazard_v0` koşullu | −0.025 … 0.000 (nokta ≈ −0.010) | içerir ya da negatif dışlar; **kazanç en olası bu hücrede** | yukarıdaki türetme |
| Brier k = 2 | `@INF` koşullu | −0.040 … −0.010 | dışlayabilir | karşılaştırıcı −0.014 [−0.030, −0.000] |
| Brier k = 2 | `base_km_last10` koşullu | −0.065 … −0.030 | dışlar (olası) | karşılaştırıcı −0.040 [−0.061, −0.020] |
| Brier k = 10 | `ceiling_hazard_v0` koşullu | −0.006 … +0.006 | içerir | D1 bilgisi 10. güne taşınmaz; S_10 ayrımı küçük |
| Brier k = 3 (keşif) | `ceiling_hazard_v0` koşullu | −0.020 … +0.003 | içerir | g2 grubu (d = 2, 3) aynı ofset sabiti |
| `path_conditional` h = 5 MAE | `ceiling_path_v0` koşullu (j = 1) | −0.015 … +0.005 | içerir | yalnız S farkının medyana taşınan payı |
| `path_conditional` h = 3 p_up Brier | `ceiling_path_v0` koşullu | −0.015 … +0.005 | içerir | |
| Kalibrasyon | ort(h_2) − gözlenen D2 kırılma oranı | \|Δ\| ≤ 0.05 | — | ofset in-sample kalibre; u merkezli |
| λ | nihai fit | 10–100 en olası; INF olası | — | 2 parametre, 67 olay; INF'in iç-CV skoru yakın |
| λ | fold'lar | erken fold'larda INF; fold'ların %20–50'sinde INF | — | küçük eğitim kümesi |
| δ_lock işareti | nihai fit ve λ < INF fold'ları | < 0 (fold'ların ≥ %80'inde) | — | mekanizma (§2) |
| δ_turn işareti | nihai fit | > 0 (düşük güven; ters çıkabilir) | — | karşı-mekanizma var (§2) |
| n (fold) | — | 65–71 | — | karşılaştırıcının 71'i; erken fold'lar d ≥ 2 eşiğinde düşebilir |

Hangi hücrede kazanç en olası: **Brier k = 2** ("yarın bozulur mu"); sonra RPS_1. En az olası: Brier k = 10 ve `path_conditional` h = 10 (beklenmez).

**Başarısızlık tanımları (backtest'te de canlıda da aynı sözcüklerle):**
- (a) **D1 bilgisi zarar veriyor:** birincil hücre aralığı tamamen 0'ın üstünde → "D1 sonrası model karşılaştırıcıdan kötü"; model yine dondurulur, kart bunu yazar, ürün koşullu sekmede karşılaştırıcıyı birincil gösterir.
- (b) **D1 bilgisi eklemiyor:** nihai fit'te λ = INF, ya da fold'ların ≥ %80'inde INF → "özellikler bilgi eklemiyor; model karşılaştırıcıyla özdeş"; dondurulur (kart yazar); uygulama ayrı satır göstermez.
- (c) **Kalibrasyon:** |ort(h_2) − gözlenen D2 kırılma oranı| > 0.10 (n ≥ 30) → "kalibrasyon bozuk" notu.
- (d) **Parite hatası:** INF ucu karşılaştırıcıya bit-eşit değil ya da h_1 ana modelle bit-eşit değil → kod incelemesi; giderilmeden dondurma yok (kabul testi 5).
- (e) **Prospektif (n ≥ 30):** birincil aralık 0'ı pozitif tarafta dışlıyor → "geçemiyor". Aralık 0'ı içeriyor → "ayırt edilemiyor". n < 30 hüküm yok; n < 10 satır tablosu.
- Başarı sayılacak (yalnız prospektif, n ≥ 30): birincil hücre aralığı 0'ı negatif tarafta dışlıyor. Backtest'te aynı olursa yalnız "backtest'te geçiyor (tasarıma maruz)" yazılır.

**Her durumda:** v0 bu şartnameyle dondurulur; tutmayan beklenti adıyla MODELS.md'ye yazılır. **Beklentiden çok iyi** (tanım: birincil fark < −0.040, ya da aralığın üst ucu < −0.020, ya da Brier k = 2 farkı < −0.040) → dondurmadan önce Fable'ın sıfırdan yeniden üretimi bu şartnameden bağımsız oturumda yapılır ve ledger'lar |Δ| ≤ 1e-9 ile eşleşmelidir (Faz 4 kalıbı). Bu yol görev planında zaten vardır; "çok iyi" durumu onu zorunlu eşleşme eşiğine bağlar. Beklenti tuttuğunda da yeniden üretim yapılır (görev metni), eşik aynıdır.

## 6. Backtest planı (Opus için)

**6.1 Plan kimliği [KARAR].** `PLAN_POST_D1 = H99_POST_D1_PP_WALK_FORWARD_T_CUTOFF_F3_PRESENT_L_GE_1_MIN10IPO_5EV_5SV`. Fold kümesi Faz 1B `PLAN_CEILING`'in fold'larıdır (test arzı k, f3 dolu, kesim T = `first_trading_date(k)`; aday eğitim arzı j: `first_trading_date(j) < T`; (j, d) satırı ancak `target_session_date(j, d) < T`), şu ek kurallarla:
1. **Test arzı** L_k ≥ 1 (`ceiling_close_D1 = 1`). Diğerleri `NOT_APPLICABLE` satırı (skorlanmaz, sayılır).
2. **Ofset** = o fold'un kendi `ceiling_hazard_v0` fit'i: `hazard.fit_training_set` aynı eğitim kümesi ve `PLAN_CEILING` kesimiyle yeniden koşulur (deterministik); γ, β, seçilen λ Faz 1B altın ledger'ının (`tests/reference/macos_golden_faz1b/ceiling_hazard_v0_fold_ledger.csv`) aynı fold satırıyla |Δ| ≤ 1e-9 eşleşmelidir (kabul testi 3). Ledger'daki `hazard_1..10` test arzı için ofset paritesi. Ledger `FIT_OK` değilse fold `SURVIVAL_NOT_AVAILABLE`.
3. **δ eğitim kümesi**: PLAN_CEILING eğitim satırlarından d ≥ 2 olanlar (L ≥ 1 arzlara aittir; L = 0 arzın d ≥ 2 satırı yoktur). D1 özellikleri bu arzların 1. seans alanlarından; d ≥ 2 satırı olan her eğitim arzının D1 tarihi zorunlu olarak < T'dir (D2 tarihi < T), yani D1 bülteni kesimden önce yayımlanmıştır (test: her eğitim arzında `target_session_date(j, 1) < T`).
4. **Skorlanabilirlik**: δ eğitim kümesinde ≥ 10 arz, ≥ 5 olay, ≥ 5 sağ kalım; değilse `INSUFFICIENT_TRAINING_HISTORY`. `d1_lock` eğitimde σ = 0 ise o fold'da düşer (katsayı 0, `dropped` listesi); fold yine skorlanır.
5. **Ön işleme fold içinde**: `d1_turnover` p05/p95 (Type-7) ve z-skor μ/σ, `d1_lock` μ/σ yalnız δ eğitim arzlarından, arz düzeyinde; iç CV'de her j için yeniden.
6. Her fold: iç CV → λ → nihai δ → test arzı için h_1 (ofset, ledger'la eşit), h_2..10, S, S_cond, P_L_cond; `path_conditional` yalnız `ceiling_path_v0` fold ledger'ı (`H99_CEILING_PATH_T_CUTOFF_REUSE_CEILING_LEDGER`) aynı fold'da `OK` ise, o fold'un hücreleriyle (SPEC_CEILING_PATH_V0 §8 walk-forward hücreleri) ve bu modelin S'iyle.
7. **Sızıntı noktaları (test edilir):** (i) SESSIONS dosyasından yalnız `session_number == 1` satırlarının fiyat/hacim sütunları okunur (yükleyici sütun beyaz listesi; 2..10 için yalnız `target_session_date`); (ii) test arzının D1 alanları yalnız tahminde, hiçbir zaman eğitimde/ön işlemede; (iii) her fold'da `training_max_session_date < T`; (iv) `realized_L` ve `ceiling_close_Dk` yalnız etiket/skor için; (v) kurallar ve karşılaştırıcı aynı fold_id'nin Faz 1B ledger satırından (yeniden koşulmaz; `evaluated` sha'ları günlüğe); (vi) aynı gün listelenen arzlar birbirini eğitmez (kesin `<`).
8. **Ledger sütunları** (sıra sabit): `model_id, fold_id, ticker, first_trading_date, prediction_date (= D_1 tarihi), training_n_ipo, training_n_pp_rows, training_n_events, training_n_survivals, training_max_session_date, training_tickers_sha256, training_pp_sha256, parent_fold_status, parent_gamma_g1, parent_gamma_g2, parent_gamma_g3, parent_beta_f1, parent_beta_f2, parent_beta_f3, parent_selected_lambda, parent_ledger_row_sha256, selected_lambda, lambda_score_table, n_lambda_not_converged, columns, delta_d1_lock, delta_d1_turnover, d1_clip_p05, d1_clip_p95, d1_mean_lock, d1_std_lock, d1_mean_turnover, d1_std_turnover, solver_iterations, solver_grad_max, test_d1_lock, test_d1_turnover_ratio, test_d1_turnover_clipped, hazard_1..hazard_10, S_1..S_10, S_cond_2..S_cond_10, path_cond_status, path_cond_h3_median, path_cond_h3_p_up, path_cond_h5_median, path_cond_h5_p_up, path_cond_h10_median, path_cond_h10_p_up, realized_L, status`. `status ∈ {FIT_OK, INSUFFICIENT_TRAINING_HISTORY, SURVIVAL_NOT_AVAILABLE, NOT_APPLICABLE, MODEL_NOT_FIT_DID_NOT_CONVERGE}`.
9. **Metrikler ve rapor:** koşullu RPS_1, Brier k = 2, k = 10 (ortak fonksiyonlar); eşleşik fark + aralık (SPEC_DEVIATIONS C7, MODELS.md yöntemi) + n + kazanç/kayıp/eşitlik; `docs/MODELS.md`'ye yeni "Faz 5: D1 sonrası güncelleme" bölümü (koşullu ölçek; koşulsuz tablolarla toplanmaz; §5 tablosu satır satır "tuttu / tutmadı" ile); `experiments/log.jsonl`'a `kind: backtest` satırı (`spec_sha256` = bu dosya; `survival_ledger` = Faz 1B tavan ledger sha'sı; kural 4).
10. `ScaleMixError`: bu modelin hücreleri `scale = backtest_conditional`; koşulsuz ölçekle birleştiren çağrı hata verir.

**6.2 Dondurma sırası.** Backtest → MODELS.md → (Fable yeniden üretim, |Δ| ≤ 1e-9) → `python -m borsai.freeze --models post_d1_hazard_v0` temiz ağaçta → `models/INDEX.json` sonuna ekleme (ilk 19 kayıt değişmez) → commit → push → push kanıtı. Freeze **ön koşul**: `models/ceiling_hazard_v0.json` sha'sı INDEX'le eşit ve `ceiling_path_v0.json` sha'sı eşit. Bu modelin canlı sınıfı için `commit_frozen(m)` bu commit'tir.

## 7. Canlı kayıt aşaması `POST_D1` ve zaman kanıtı (SPEC_SCORING'e ek; `docs/specs/` değişmez, ek bu dizinde durur)

**7.1 Neden yeni aşama.** SPEC_SCORING §5 `record_live = push(kayıt) < D_1`; D1 bülteni D_1 akşamı yayımlandığından POST_D1 kaydı o kurala göre her zaman LATE olurdu. Aşamanın kendi zaman sınırı D2'nin ilk fiyat bilgisidir.

**7.2 Kural metninden zaman noktaları [ÖLÇTÜM, `ekler/kural_metni_borsaistanbul_20260924.md`].**
- Pay Piyasası Prosedürü Ek-9 (tam ve yarım gün): Açılış emir toplama **09:40 – 09:55**, açılış fiyatı 09:55(+), sürekli işlem 10:00 – 18:00 (yarım gün 12:30), kapanış 18:00 – 18:10 (yarım gün 12:30 – 12:40).
- Bülten yayım saati kural metninde yok. Ölçüm (MANIFEST `http_last_modified`, 33 THB): D_1 günü **18:25 – 18:40** Istanbul; THM ertesi sabah 08:01 – 08:03 (Ek-10 seans akışı: marj yayını 07:00). [ÇIKARIM] THB aynı akşam kullanılabilir; pencere ≈ 15 saat (hafta sonu/tatilde daha uzun).
- D2'nin THM'si (D2 üst limiti) D1 kapanışından deterministiktir (marj kuralı); bilgi taşımaz ve kayda ALINMAZ.

**7.3 Tanımlar [KARAR].**
- `D2_cal(a)` = resmi takvimde (SPEC_SCORING §2 `official_sessions`, ilan dışı kapanışlar düşülmüş) D_1(a)'dan sonraki ilk seans günü. Payın o gün gerçekten işlem görüp görmediğine (durdurma) bakılmaz: sınır takvimden.
- `T_open(a)` = `D2_cal(a)` + **09:40:00 Europe/Istanbul** (Ek-9 "Emir Toplama Süreci 09:40"; BYF istisnası paylara uygulanmaz). Bu andan itibaren D2 emir defteri (teorik açılış fiyatı/miktarı) piyasaya görünür; D2'ye dair ilk bilgi budur.
- `record_live_post_d1(m, a)` = `push_proof(commit_record).created_at` (Istanbul'a çevrilmiş) **< T_open(a)**. Push kanıtı SPEC_SCORING §5 / `borsai.push_proof` ile aynı (GitHub commit status `created_at`; torun commit kanıtı geçerli). Yerel saat kullanılmaz.
- `outcome_ingest_commit_post_d1(a)` = `data/raw/bist/` altına tarihi **> D_1(a)** olan ilk THB ya da THM dosyasını ekleyen commit ile `data/outcomes/<a>.csv`'ye h ≥ 2 için `status = OK` satırı ilk yazan commit'in en erkeni. (Bekçi: h ≥ 2 OK satırı, o tarihli bülten commit'inden önce olamaz.)
- `model_prospective_post_d1(m, a)` = `is_ancestor(commit_frozen(m), outcome_ingest_commit_post_d1(a))` VE `push_proof(commit_frozen(m))` var.
- `inputs_pit_ok_post_d1(rec)` = (i) kaydın dayandığı listeleme-öncesi birincil kaydın `inputs_pit_ok`'u (SPEC_SCORING §5) VE (ii) kayıttaki her bülten atfının tarihi tam olarak D_1(a) VE (iii) her atfın sha256'sı `data/raw/bist/MANIFEST.csv`'deki pinli değere ve dosyaya eşit VE (iv) kayıtta D_1 dışında hiçbir seansın alanı yok (şema testi: `d1` bloğu dışında fiyat/hacim alanı yok).

```
class_post_d1(m, a) = LIVE         if model_prospective_post_d1 AND record_live_post_d1
                    = LATE_RECORD  if model_prospective_post_d1 AND NOT record_live_post_d1 AND inputs_pit_ok_post_d1
                    = RETRO        otherwise
```
Yalnız **h ≥ 2 hedefler** (k = 2..10 koşullu; `path_conditional` için h ∈ {3, 5, 10}) skorlanır; D1 hedefi POST_D1 modellerinde hiçbir zaman skorlanmaz (kod: bu modeller `kind = post_d1`; `_need_names` D1'i içermez). H99'un 99 arzı bu model için RETRO'dur (kayıt yok; yalnız backtest).

**7.4 Kayıt dosyası [KARAR].** Dizin `registry/post_d1/<TICKER>/<UTC-zaman>_<kısa-sha>.json` (`registry/records/` DEĞİL: `tests/test_outcome_guard.py::test_registry_carries_no_outcome_fields` o dizinde sonuç alanı yasaklar ve haklıdır; POST_D1 kaydı tanımı gereği D1 alanı taşır. Bekçi şöyle genişler: `registry/post_d1/` altında yalnız `d1` bloğunda ve yalnız D_1 tarihli alanlar; h ≥ 2 anahtarı ya da D_1 dışı bülten sha'sı → kırmızı). Şema `borsai.post_d1_record/1`:

```
schema_version, record_type ∈ {PREDICTION, CANCELLATION}, record_stage = "POST_D1", ticker,
recorded_at_utc, recorded_at_istanbul, recorded_at_basis (LOCAL_CLOCK_SELF_REPORTED …), code {git_head, borsai_dirty, borsai_source_sha256},
base_record {file (registry/records/<T>/…json), sha256, model_inputs_sha256, selected_by = "SPEC_SCORING_6_PRIMARY_ceiling_hazard_v0_AT_POST_D1_TIME"},
d1 {session_date, session_h = 1, half_day, halt_flag,
    thb {file (data/raw/bist/thb/YYYY/th?YYYYMMDD1.zip), sha256, url, http_last_modified, downloaded_at, internal_filename},
    thm {aynı alanlar},
    fields_raw {open, high, low, close, volume, turnover, aof, trade_count, halt, special_trade_volume, special_trade_turnover,
                reference_price, upper_limit, lower_limit}   # ham metin, Decimal'e çevrilmeden
    ceiling_close_D1 (0/1), lock_consistency {open_at_U, high_at_U, close_at_U}},
d1_features {d1_lock, d1_turnover_ratio (Decimal metin), d1_turnover_ln, clipped, z {d1_lock, d1_turnover}, warnings[]},
models_index {path, sha256, model_ids}, models [ { model_id, stage, file, params_sha256, spec_sha256, algorithm, kind = "post_d1",
        status ∈ {PREDICTED, REFUSED, NOT_APPLICABLE}, refusal, output (standart hazard şeması + conditional_j1 {S_cond, p_break_next, P_L_cond} + path_conditional | null) } ],
comparators_conditional { ceiling_hazard_v0, ceiling_hazard_v0@INF, base_km_expanding, base_km_last10, base_always_ceiling:
        {record_cell_sha256, S (kopya), S_cond (conditional_weights ile), source = "base_record"} },
summary {n_models, n_predicted, n_refused, n_not_applicable}
```
- `base_record`: POST_D1 anında D_1 bilindiğinden SPEC_SCORING §6 seçimi kesindir: `ceiling_hazard_v0` için birincil kayıt (D_1'den önce push kanıtlı, f3'lü en son; yoksa en erken LATE adayı). **Modelin f1–f3 girdileri bu kaydın `model_inputs`'undan** alınır (girdi belgesi yeniden okunmaz) → ofset, karşılaştırıcının S'iyle bit-eşit. Uygun kayıt yoksa POST_D1 kaydı YAZILMAZ; payda satırı `SKIPPED_POST_D1: NO_PRE_LISTING_RECORD`.
- `comparators_conditional` değerleri kayıttan kopyadır (kural 1: kuralların değeri kayıtta); skorlama Faz 2C'nin j = 1 bloğunu kullanır (tek tanım), kopya ile |Δ| ≤ 1e-12 parite denetlenir.
- Aynı arza listeleme-öncesi (PB, talep katlı) kayıtlarla birlikte var olur; onlar değişmez. Aynı arz için birden çok POST_D1 kaydı olabilir (ör. bülten yeniden indirildi); **birincil POST_D1 kaydı** = `T_open`'dan önce push kanıtlı en erken kayıt, yoksa `inputs_pit_ok_post_d1` olan en erken kayıt (`select_primary_post_d1`). Aynı `base_record` sha + aynı iki bülten sha + aynı INDEX sha ikinci kayıt → `DUPLICATE_RECORD`.
- İptal: `record_type = CANCELLATION` aynı dizinde; **`T_open`'dan itibaren iptal yapılamaz** (SPEC_SCORING §6'nın D_1 kuralının aşama karşılığı).
- Yazım akışı: `python -m borsai.outcomes update --through <D_1>` (D_1 bültenlerini indirir, `sequence_guard` sağlanmış olmalı; `data/outcomes/<T>.csv` h = 1 OK, h ≥ 2 PENDING) → commit → `python -m borsai.freeze --post-d1 <TICKER>` → commit → push → `python -m borsai.push_proof <sha>` (proje sahibi). `sequence_guard`, `registry/post_d1/` altındaki commit edilmemiş dosyaları da engeller.

**7.5 Payda ve sayaçlar.** `registry/ipos.csv`'de `FROZEN` olan her arz için POST_D1 aşaması satırı: `ceiling_close_D1 = 1` ise POST_D1 kaydı beklenir (yoksa `SKIPPED_POST_D1: NO_POST_D1_RECORD`, nedeniyle); `ceiling_close_D1 = 0` → `NOT_APPLICABLE`; D1 etiketi NA → `NOT_SCORABLE_D1_LABEL_NA`. j = 1 koşullu bloğunda bu model için `n_scored / n_refused / n_skipped / n_not_applicable / n_target_unavailable / n_live / n_late`. Bugünkü 7 arz: model dondurulduğunda hepsinin D2+ sonuçları repoda olacağından (NETGL dahil) hepsi RETRO → `retro_info` satırı, hiçbir n'e girmez (Faz 4 F16 kalıbı).

**7.6 `borsai/outcomes.py` ve `registry` değişiklikleri (yalnız ana hatlar).**
- `THB_COLUMNS` eki: `open: "ACILIS FIYATI"`, `high: "EN YUKSEK FIYAT"`, `low: "EN DUSUK FIYAT"`, `volume: "TOPLAM ISLEM ADEDI"`, `turnover: "TOPLAM ISLEM HACMI"`, `aof: "A.O.F"`, `special_volume: "OZEL ISLEM BILDIRIMI ISLEM ADEDI"`, `special_turnover: "OZEL ISLEM BILDIRIMI ISLEM HACMI"` (adlar arşiv eşlemesinden; Opus 2026 THB başlığıyla birebir doğrular, `REQUIRED` listesi genişler). `ThbRow` bu ham alanları taşır. `OUTCOME_COLUMNS` **değişmez** (v0'da sonuç CSV'sine sütun eklenmez; D1 alanları kayıtta ve pinli bültende yaşar).
- `registry.py`: `POST_D1_DIR = registry/post_d1`, `select_primary_post_d1`, `t_open(d1, calendar)`.
- `freeze.py`: `build_post_d1_record`, `--post-d1`; `model_kind` → `"post_d1"`; `run_model` yeni tür.
- `scoring.py`: `pair_class_post_d1`, `outcome_ingest_commit_post_d1`, j = 1 koşullu bloğuna POST_D1 model satırı; `_need_names("post_d1")` = k = 2..10 etiketleri (+ h ∈ {3, 5, 10} getiri, `path_conditional` varsa).
- `tests/test_outcome_guard.py`: `registry/post_d1/` istisnası (yalnız `d1` bloğu, yalnız D_1 tarihli sha'lar); h ≥ 2 OK satırı bülten commit'inden önce olamaz.

## 8. Uygulama etkisi (yalnız ana hatlar)

- **Yeni çıktı türü yok**: standart hazard şeması + var olan koşullu görünüm (j = 1). Uygulama koşullu sekmesinde (SPEC_APP §3g) resmi j ≥ 1 ve `registry/post_d1/<T>/` birincil kaydı varsa "**D1 sonrası (post_d1_hazard_v0)**" satırı/eğrisi karşılaştırıcının yanında; j ≥ 2 seçilince aynı satır S_cond[k]/S_cond[j] ile güncellenir (aynı Rust `conditional`). Kayıt yoksa satır yok ("D1 sonrası kayıt yok").
- Rust portu: ofset + 2 katsayı (`predict_post_d1`), altın vektörler (Python `gen_golden.py` eki), parite |Δ| ≤ 1e-12; `PINNED_MODEL_IDS` 19 → 20.
- Doğruluk paneli: j = 1 koşullu bloğunda ek model satırı; küçük-n kuralları aynen; koşulsuzla toplanmaz.
- Sicil ekranı: `registry/post_d1/` okuyucusu (`borsai.post_d1_record/1`), aşama etiketi, `T_open` ve push kanıtı karşılaştırması görünür.
- **EK 3 gerekir** (kısa): "D1 sonrası kayıt" akışı (outcomes güncelle → kayıt → commit/push komut bloğu), gösterim kuralları, U-testleri. Uygulama THB/THM indirmez, etiket üretmez (mevcut rol ayrımı).

## 9. Ret ve uyarılar (özet; ayrıntı §2 tablosu)

| Kod | Tür | Koşul |
|---|---|---|
| `F3_MISSING` | RET (miras) | talep katı yok; ofset yok |
| `REFUSED_D1_LIMIT_NA` | RET | D_1 THM satırı/üst limiti yok |
| `REFUSED_D1_VOLUME_INVALID` | RET | hacim boş/≤ 0 iken sözleşme > 0 |
| `REFUSED_INPUT_SHARES_OFFERED` | RET | payda yok/≤ 0 |
| `NOT_APPLICABLE_D1_NOT_CEILING` | kapsam dışı (ret değil) | `ceiling_close_D1 = 0` |
| `D1_NOT_TRADED` | kayıt yazılmaz | D_1 oluşmamış (tam gün durdurma ⇒ D_1 kayar; SPEC_SCORING §2) |
| `WARN_D1_HALF_DAY`, `WARN_D1_INTRADAY_HALT`, `WARN_D1_SPECIAL_TRADES`, `WARN_D1_LOCK_INCONSISTENT`, `D1_TURNOVER_CLIPPED_TO_TRAINING_P05_P95`, `OUT_OF_TRAINING_RANGE` | uyarı | tahmin üretilir |
| `PARAMS_INVALID` / `SCHEMA_UNSUPPORTED` | hata (kayıt yazılmaz) | JSON şeması, parent sha uyuşmazlığı |

Ana model mirası: f1/f2 hesaplanamıyorsa etiketli hata; f3 p05/p95 dışı kırpma ve `clipped`; `feature_ranges` uyarıları aynen.

## 10. Maruziyet

**H99'da bu arzlar üzerinde denenmiş varyantlar [ÖLÇTÜM, `experiments/log.jsonl`, 64 satır]:** `kind: backtest` 58 (19 kayıtlı model + kural koşuları; aynı veri sürümü sayacı 19, MODELS.md F10), `sensitivity` 5 (Faz 4 duyarlılık), `conditional_eval` 1 (j = 1..9 koşullu keşif; bu şartnamenin karşılaştırıcı sayılarının kaynağı). Tavan ailesi koşuları: `ceiling_hazard_v0` 2, `@INF` 2, `base_km_expanding` 4, `base_km_last10` 4, `base_always_ceiling` 8, `pb_ceiling_v0(@INF)` 2 + 2, tavan yolu 3 × 2. D1 işlem alanını özellik olarak kullanan koşu: **0**.

**Arşivde D1 alanlarının önceki kullanımı (`~/Desktop/Halka_Arz_Modeli`, tarandı):**
- `FIRST10_OHLCV` (pilot 3 arz, FULL20 20 arz, 2026-08-12…14): THB/THM'den D1–D10 açılış/yüksek/düşük/kapanış/hacim/ciro/AOF/sözleşme toplandı; yalnız veri toplama ve QA (audit metni: "No returns, limit-event counts, feature selection, outcome analysis, model fitting … was performed"). Özellik olarak kullanılmadı.
- V1–V1.5 ön kayıtları listeleme-sonrası fiyat/hacmi özellik olarak açıkça YASAKLAR (V1.1 §10 "Using post-first-trade prices, volumes, ceiling series … as features").
- `Agents.md` / "Yeni Metin Belgesi.md": betimleyici metrik listesi ("Gün içi fiyat aralığı %", "İlk gün hacmine göre hacim şoku"); hiç uygulanmadı, model girmedi.
- `config/live_forecast.toml [live_forecast.model_live_v0]` (LIVE_V0 EOD_NEXT_DAY): aynı gün kapanış verisinden ertesi gün için **elle yazılmış kural** (`limit_near_threshold_daily_change_pct = 9.5`, `limit_near_probability = 0.85`, `limit_base_probability = 0.03` …); fit edilmemiş; en yakın emsal. Sonuçlarına bakılmadı.
- `artifacts/modeling/historical99_market_sector_microstructure_stage_a/…/ticker_market_microstructure_diagnostic.csv`: H99'da arz başına `volume_path_json`, `aof_path_json`, `close_at_official_upper_limit_exact_json` vb. taşıyan **post hoc açıklayıcı teşhis** ("POST_HOC_EXPLANATORY_DIAGNOSTIC_ONLY"). Yalnız başlık ve ilk iki satır (AGROT, AHSGY) görüldü; içerik ve bulguları okunmadı. **Not:** bu dosya H99'da D1–D10 hacim yollarına bakmış bir çalışmanın varlığını gösterir; bu şartnamenin tasarımı ona dayanmıyor ama H99'un bu yönden de tasarıma maruz olduğu kayda geçer.
- Karar defteri (`DECISION_LEDGER.csv`) ve model spec JSON'ları: D1 hacim/AOF özelliği yok (KARCL D9 OHLC örneği yalnız veri doğrulama notu).

**Bu şartnamenin kendi maruziyeti:**
- Gördüm: `profil_d1.txt` (tek değişkenli; **ek olarak** `ceiling_close_D1 = 0` alt kümesinin profili de basıldı — D1 alanlarını D1 etiketiyle ilişkilendirir; D1 etiketi bu modelde girdi koşuludur, skorlanan hedef değildir; h ≥ 2 hiçbir sonuca bakılmadı); MODELS.md koşullu keşif tabloları (j = 1..9, karşılaştırıcı sayıları; beklenti için gerekli); SPEC_CEILING_V0 §2 tablosu; `models/ceiling_hazard_v0.json` ve `@INF` parametreleri; `experiments/log.jsonl` `conditional_eval` satırının j = 1..3 blokları; Faz 1B tavan ledger'ının başlığı ve EKOS satırının kimlik/λ sütunları; `data/outcomes/NETGL.csv`'nin **ilk iki satırı** (D1 ve D2 kapanış/limit; canlı sonuç — istemeden, şema için açıldı; NETGL bu model için zaten RETRO'dur); `registry/records/NETGL/…json`'un `ceiling_hazard_v0` çıktısı; `data/raw/bist/MANIFEST.csv` zaman damgaları (içerik değil); `registry/ipos.csv`; borsaistanbul.com kural metinleri (üç kaynak, `ekler/`).
- Görmedim: `scores/`, `docs/SCORES.md`, diğer 6 arzın `data/outcomes/` dosyaları, bülten içerikleri, `tests/reference` ledger'larının S/realized sütunları (EKOS satırında da yalnız kimlik sütunları), arşivin `artifacts/live_forecast|evaluation|predictions` sonuçları, paralel oturumun (Faz 2C) `borsai/`/`scores/` değişiklikleri (yalnız SPEC_DEVIATIONS'ın G bölümü başlığının varlığı bildirildi, okunmadı).
- Hesaplanmadı: hiçbir fit, hiçbir walk-forward skoru, hiçbir özellik–L/R_h/Y_h ilişkisi, kilitli/kilitsiz alt kümelerin sonuçları.

## 11. Kabul testleri (Opus için, kanıtlanabilir)

1. **Eğitim kümesi ve PP sayımı:** f3 dolu ve `ceiling_close_D1 = 1` arz sayısı 81; d ≥ 2 PP satırı 409, olay 67, sağ kalım 342; `d1_lock = 1` 70/81; H99 D1'lerinin 99'u tam gün, 0 durdurma, 99/99 sözleşme > 0.
2. **Özellik tanımı:** `d1_lock` ham metin Decimal eşitliğinden (sentetik "10.12" vs "10.120" → 1; "10.11" → 0); kilitli 70 arzda açılış = yüksek = kapanış = limit (0 aykırı); `d1_turnover` = ln(volume/shares_offered) H99'da `profil_d1.txt` §3'ün p05/p50/p95 değerleriyle 1e-9 içinde (0.0009841 / 0.004202 / 0.5402 oran); `shares_offered` f1/f2 ile aynı alan.
3. **Ofset paritesi:** her skorlanabilir fold'da yeniden koşulan `ceiling_hazard_v0` fold fit'inin γ(3), β(3), λ'sı Faz 1B altın ledger satırıyla |Δ| ≤ 1e-9; test arzı için `hazard_1..10` ledger'la |Δ| ≤ 1e-9; nihai fit'te ofset `models/ceiling_hazard_v0.json` ile `predict_hazard.predict` çıktısına **bit-eşit** (h_1 birebir).
4. **Fold kümesi:** fold_id/ticker dizisi Faz 1B tavan ledger'ının L ≥ 1 test arzlarına eşit (beklenen 71; `NOT_APPLICABLE` 16 = 87 − 71); `INSUFFICIENT_TRAINING_HISTORY` sayısı raporlanır; her fold'da `training_max_session_date < T` ve her eğitim arzında `target_session_date(j, 1) < T`.
5. **INF paritesi:** λ = INF ile fit edilen model (δ = 0) H99 eğitim arzlarında ve rastgele 1000 girdide `ceiling_hazard_v0`'ın `conditional_weights(S, 1)` çıktısına |Δ| ≤ 1e-12; `S_cond[k] = Π_{d=2..k}(1 − h_d)` ile |Δ| ≤ 1e-12; `P_L_cond` toplamı 1.
6. **Çözücü:** sentetik ofsetli veride (λ > 0) `scipy.optimize.minimize(BFGS)` çözümüyle |Δ| ≤ 1e-6, max|∇| ≤ 1e-10; λ = 1e9 ile ‖δ‖ ≤ 1e-6 ve S_cond INF ucuyla |Δ| ≤ 1e-6 (γ, β dokunulmadı: bit-eşit).
7. **Seçim kuralı:** iki λ'nın skoru eşitlenmiş sentetik tabloda büyük olan; INF ızgarada; yakınsamayan aday çıkarılır, INF kalır.
8. **Sızıntı (yükleyici):** SESSIONS okuyucusu 2..10. seanslar için fiyat/hacim sütunlarına erişirse test kırmızı (sütun beyaz listesi ya da erişim sayacı); test arzının D1 alanı ön işleme istatistiklerini değiştirmiyor (test arzını değiştirip μ/σ/p05/p95'in aynı kaldığı sınanır).
9. **Ret/uyarı/kapsam:** f3 = None → `F3_MISSING`; üst limit boş → `REFUSED_D1_LIMIT_NA`; `ceiling_close_D1 = 0` → `NOT_APPLICABLE_D1_NOT_CEILING` (refused değil, status NOT_APPLICABLE); `half_day = 1` → tahmin + `WARN_D1_HALF_DAY`; özel işlem hacmi > 0 → uyarı, hacim değişmez; p95 üstü el değiştirme → kırpma işareti.
10. **JSON ↔ predict paritesi:** 81 eğitim arzında numpy nihai model ile stdlib `predict_post_d1` |Δ| ≤ 1e-12 (hazard, S, S_cond, P_L_cond); stdlib import listesi Faz 1A K2 kalıbı (numpy/sklearn yok).
11. **`path_conditional`:** `predict_path.conditional` ile tek tanım (ikinci karışım kodu yok); S ≡ ana modelin S'i verildiğinde `ceiling_path_v0`'ın j = 1 koşullu çıktısına bit-eşit; blok `null` olduğunda skor satırı `TARGET_UNAVAILABLE` değil `NOT_PRODUCED`.
12. **Koşullu metrikler:** `conditional_rps(S, 1, L)` ve `conditional_brier` çağrılır (monkeypatch sayacı > 0; ikinci tanım yok); sentetik S ≡ 1[L ≥ k] → RPS_1 = 0; S ≡ 1 ve L = 1 → 1.
13. **POST_D1 kayıt ve sınıf (geçici git deposu):** (a) model → D1 bülteni+sonuç(h = 1) → kayıt + kanıt < T_open → D2 bülteni ⇒ LIVE; (b) kanıt ≥ T_open ⇒ LATE_RECORD; (c) D2 bülteni modelden önce ⇒ RETRO; (d) kayıtta D_1 dışı tarihli bülten sha'sı ⇒ `inputs_pit_ok_post_d1` yanlış ⇒ RETRO ve bekçi kırmızı; (e) `base_record` yok ⇒ kayıt yazılmaz, `SKIPPED_POST_D1`; (f) T_open sonrası iptal ⇒ hata; (g) yarım gün D2_cal'da da T_open 09:40; (h) D2_cal ilan dışı kapanış olsa da sınır aynı; (i) `comparators_conditional` kopyası Faz 2C j = 1 satırıyla |Δ| ≤ 1e-12; (j) `T_open` hesabı Ek-9 sabitinden (`09:40:00+03:00`), yerel saat kullanılmaz (test, sistem saatini değiştirmeden zaman damgalarını enjekte eder).
14. **Bekçiler:** `registry/records/`, `registry/inputs/`, `ipos.csv` sonuç alanı taşımaz (mevcut test aynen); `registry/post_d1/` yalnız `d1` bloğunda D_1 alanı; `data/outcomes` h ≥ 2 OK satırı ilgili bülten commit'inden önce değil; `docs/specs/` 11 dosya ve temiz; `docs/specs_faz4/` bayt-eşit; `models/INDEX.json` ilk 19 kayıt bayt-eşit; Faz 1A/1B/4 altın ledger'ları bayt-eşit; 2026-08-19 sonrası veri eğitime girmez.
15. **Deney günlüğü ve rapor:** backtest koşusu `experiments/log.jsonl`'a `kind: backtest`, `spec_sha256` = bu dosyanın sha256'sı, `survival_ledger_sha256` = Faz 1B tavan ledger'ı; MODELS.md "Faz 5" bölümü §5 tablosunun her satırı için "tuttu / tutmadı" satırı üretir (`OPERATIONAL_RULES_FAZ5`, sonuç görülmeden koda yazılmış).
16. **Uygulama (EK 3 ile):** Rust `predict_post_d1` altın vektörlerle |Δ| ≤ 1e-12; koşullu sekme resmi j = 0'da D1 sonrası satırı göstermez; resmi kayıt yalnız `registry/post_d1/` birincil kaydından okunur (Rust tahmini çağrılmaz; U38 kalıbı).

## 12. Sözde kod

```
# ---------- veri (H99) ----------
def d1_fields(sessions_csv, ticker):                       # yalnız session_number == 1 satırı
    r = row(sessions_csv, ticker, session_number=1)
    return {"low": r.thb_raw_low, "open": r.thb_raw_open, "high": r.thb_raw_high, "close": r.thb_raw_close,
            "volume": r.thb_raw_volume, "upper": r.thm_raw_upper_limit}      # ham metin

def d1_features(fields, shares_offered):
    U = Decimal(fields["upper"]); low = Decimal(fields["low"]); vol = Decimal(fields["volume"])
    if U <= 0: refuse(REFUSED_D1_LIMIT_NA)
    if vol <= 0: refuse(REFUSED_D1_VOLUME_INVALID)
    if Decimal(shares_offered) <= 0: refuse(REFUSED_INPUT_SHARES_OFFERED)
    lock = int(low == U)
    warn_if(lock and not (Decimal(fields["open"]) == U == Decimal(fields["high"]) == Decimal(fields["close"])), WARN_D1_LOCK_INCONSISTENT)
    return {"d1_lock": lock, "d1_turnover": float(ln(vol / Decimal(shares_offered)))}   # ln 60 haneli Decimal → binary64

def pp_rows_post_d1(units, cutoff):                          # SPEC_CEILING_V0 §2/§12 build_pp, d ≥ 2 süzgeci
    return [r for r in sv.pp_table(units, cutoff) if r.day >= 2]

# ---------- ofset ----------
def offset(parent_fit, prep_parent, x):                      # parent_fit: fold'un ceiling_hazard_v0 fit'i ya da dondurulmuş JSON
    z = prep_parent.transform(x)                              # V1_3 adımları: ln f1, f3 kırpma, z-skor (aynen)
    lin = dot(parent_fit.beta, z)
    return [parent_fit.gamma[g(d)] + lin for d in 1..10]       # η_1..η_10

# ---------- fit ----------
def prep_d1(train_feats):                                     # arz düzeyinde
    p05, p95 = quantile_type7([f.d1_turnover], .05, .95)
    clipped = [{lock: f.d1_lock, turn: clip(f.d1_turnover, p05, p95)} for f in train_feats]
    mean, std = mean(clipped), pop_std(clipped)               # std == 0 → sütun düşer
    return Prep(p05, p95, mean, std, dropped)

def fit_delta(rows, eta, u, lam):                             # rows: (ticker, d, event); eta[ticker][d]; u[ticker]: z-vektör
    if lam == INF: return zeros(len(columns))
    J(δ) = -Σ_r [e ln h + (1-e) ln(1-h)] + lam/2 ‖δ‖²,  h = sigmoid(eta[t][d] + δ·u[t])
    return newton(J, δ0 = 0, tol=1e-10, max_iter=100, halving=30)   # SPEC_CEILING_V0 §5, SPEC_DEVIATIONS A2

def select_lambda(train_ipos, rows, eta, feats):
    for lam in GRID:
        nll = 0; m = 0
        for j in train_ipos:
            prep = prep_d1(feats - {j}); u = prep.transform(feats - {j}); δ = fit_delta(rows - rows(j), eta, u, lam)
            for r in rows(j): nll += -log_clip(p(event_r | eta[j][r.d] + δ·prep.transform(feats[j]))); m += 1
        score[lam] = nll / m
    return argmin(score, tie -> max lam)

# ---------- tahmin (stdlib) ----------
def predict_post_d1(params, inputs, d1):
    base = predict_hazard.predict(params.parent, inputs)          # RET'ler (F3_MISSING …) aynen döner
    if base.refused: return base
    if d1.ceiling_close_D1 == 0: return not_applicable(NOT_APPLICABLE_D1_NOT_CEILING)
    w = d1_features(d1.fields_raw, inputs.shares_offered)         # uyarılar toplanır
    u = params.d1_preprocessing.transform(w)                      # kırpma + z; clipped işareti
    eta = logit(base.hazard)                                      # ana modelin doğrusal öngörücüsü (bit-eşit)
    hazard = [base.hazard[1]] + [sigmoid(eta[d] + dot(params.delta, u)) for d in 2..10]
    S = survival(hazard); S_cond, P_L_cond = conditional_weights(S, 1)
    out = {hazard, S, P_L: p_streak(S), P_close_ceiling: p_close(S, parent.reclose_rates), conditional_j1: {S_cond, p_break_next: hazard[2], P_L_cond}}
    out.path_conditional = predict_path.conditional(params_path, {**path_output, "S": S}, j=1, closes=[d1.close]) if path_output else None
    return out

# ---------- backtest fold ----------
for fold in plan_ceiling_folds(dataset, PLAN_CEILING):              # Faz 1B fold'ları
    if L[fold.test] < 1: ledger(NOT_APPLICABLE); continue
    parent = hazard.fit_training_set(fold.training, cutoff=fold.T)    # ledger ile |Δ| ≤ 1e-9 (test 3)
    rows = pp_rows_post_d1(fold.training, fold.T)                     # d ≥ 2
    if not (n_ipo(rows) >= 10 and events(rows) >= 5 and survivals(rows) >= 5): ledger(INSUFFICIENT_TRAINING_HISTORY); continue
    feats = {j: d1_features(d1_fields(SESSIONS, j), shares_offered[j]) for j in ipos(rows)}   # D1(j) < T garantili
    eta = {j: offset(parent.fit, parent.prepared.prep, x[j]) for j in ipos(rows)}
    lam = select_lambda(ipos(rows), rows, eta, feats); prep = prep_d1(feats); δ = fit_delta(rows, eta, prep.transform(feats), lam)
    ledger(predict(test) with parent, prep, δ; S_cond; path_conditional from ceiling_path_v0 fold cells if OK; realized_L)
metrics = conditional_rps / conditional_brier (ortak fonksiyonlar) → eşleşik farklar → MODELS.md, log.jsonl

# ---------- canlı sınıf ----------
def t_open(d1, calendar): return datetime(calendar.next_session_after(d1), 09:40, tz=Europe/Istanbul)
def class_post_d1(git, model_file, record, ticker, d1):
    m_commit = git.added_commit(model_file); m_proof = earliest_proof(m_commit)
    oc = min(first_commit_adding_bulletin_dated_after(d1), first_commit_with_ok_row_h_ge_2(ticker))
    prospective = m_commit and m_proof and git.is_ancestor(m_commit, oc)
    live = proof(record.commit).created_at_istanbul < t_open(d1, calendar)
    pit = base_record_pit_ok(record) and all(b.date == d1 and b.sha256 == manifest[b.date, b.kind] for b in record.d1.bulletins) and no_non_d1_fields(record)
    return LIVE if prospective and live else LATE_RECORD if prospective and pit else RETRO
```

## 13. Açık sorular (proje sahibine; en çok 5)

1. **Zaman sınırı 09:40 mı, 07:00 mı?** Şartname `T_open` = D2_cal 09:40 (ilk D2 emir defteri bilgisi) diyor. Daha muhafazakâr seçenek: marj yayını 07:00 (Ek-10) — D2 THM'si D1 kapanışından deterministik olduğu için bilgi taşımaz, bu yüzden 09:40 seçildi. **Öneri:** 09:40; kayıt zamanı ayrıca görünür olduğundan sonradan daha sıkı bir alt sınır raporda uygulanabilir (sınıf değişmez, ek sütun).
2. **PB/f3'süz varyant:** talep katı olmayan arzlarda (VEYAS gibi) POST_D1 güncellemesi yok. `pb_ceiling_v0` ofsetiyle `pb_post_d1_hazard_v0` ayrı bir model_id olarak Faz 5B'de mi? **Öneri:** evet, ama v0 dondurulup canlı n birikmeden değil.
3. **D1 tavan kapatmayanlar:** v0 kapsam dışı (§1.2). İstenirse "kırılma sonrası D1 bilgisiyle yeniden tavan" ayrı bir şartname. **Öneri:** ertelensin; `ceiling_path_v0` durum 2 yeterli.
4. **POST_Dj genelleştirmesi (j ≥ 2):** her gün için bülten kaydı ve zaman kanıtı akışı ağırdır; v0 yalnız D1. **Öneri:** v0 canlı n ≥ 10 olana kadar açılmasın; açılırsa aynı ofset tasarımı, özellik "son kilitli gün sayısı" gibi tek özellik, yeni model_id.
5. **`path_conditional` ikincil çıktısı:** yeni parametre yok ama `ceiling_path_v0`'a bağımlılık ekler (sha pin). Kayıt boyutu ve Rust portu büyür. **Öneri:** v0'da kalsın (skorlanır, birincil değil); Opus uygulanamaz bulursa blok `null` bırakılır ve SPEC_DEVIATIONS'a yazılır — modelin birincil çıktısı ve dondurması bundan etkilenmez.

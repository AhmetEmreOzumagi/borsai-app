# TASK_ID: BORSAI_FAZ4_FABLE_CEILING_PATH_SPEC_20260922

Model: Fable · yüksek.
- Klasörler: ~/Desktop/BorsAi. Ek dizin ~/Desktop/Halka_Arz_Modeli (arşiv, salt okunur).
- Ağ: yalnız borsaistanbul.com'daki KURAL metinleri (fiyat adımı tablosu, fiyat marjı esasları). Fiyat ya da bülten verisi indirilmez.
- Git: HİÇBİR git komutu çalıştırılmaz. Paralel bir oturum (Faz 2B) repoda commit atıyor.
- Yazma: yalnız `docs/specs_faz4/` altına. Kod yok, commit yok, push/tag/amend yok.

## Bağlam

**Güçlü ve zayıf yanımız (geçmiş veri testi, H99 walk-forward, `docs/MODELS.md`).**
- Tavan serisi modeli `ceiling_hazard_v0` basit kuralları açık farkla geçiyor: RPS farkı −0.0496 [−0.0751, −0.0219]. Yapısı: ayrık zamanlı hazard; gün grupları {1}, {2,3}, {4..10}; girdiler f1, f2, f3.
- Buna karşılık getiri ve olasılık çıktıları zayıf:
  - V1.5 D1 getiri MAE'sinde `base_always_ceiling`'e yeniliyor.
  - P(kapanış > arz) hiçbir ufukta taban oranından ayırt edilemiyor.

**Bu görevin amacı.** Güçlü tavan modelini getiriye ve P(kapanış > arz)'a taşıyan yeni model hattının şartnamesini yazmak. Fikir:
- Seri h. güne ulaştıysa D_h getirisi limit yoludur.
- Seri t < h'de kırıldıysa bir kırılma sonrası bileşen gerekir.
- R_h ve Y_h bu karışımdan deterministik bir eşlemeyle üretilir.
- Kovaryatsız bir sıfır model (MECHANICS_BASE) zorunludur.

**Hazır tasarım.** Bu yapıyı sen 7 Eylül'de eski repoda tasarlamıştın: `~/Desktop/Halka_Arz_Modeli/artifacts/governance/reviews/BORSAI_V3_TARGET_REVIEW_20260907_F1.md`.
- Modelleme içeriğini girdi olarak al: §1 S1 model sınıfı, §2 S2 parametre bütçesi, MECHANICS_BASE, önceden yazılan beklenti.
- ESKİ YÖNETİŞİM aygıtını ALMA: N_A kapıları, preregistration merdivenleri, M0/M1/M2 terfi dili, permütasyon testi, τ eşikleri, çeyrek bloklar, B = 10 000, %90 aralık, maruziyet sınıfı tabloları.
- Bu repoda çıkarımı ve gösterimi yalnız `docs/specs/SPEC_SCORING.md` belirler: aylık blok, 4000 tekrar, %95, küçük-n kuralları.

**Dondurulmuş bileşeni yeniden kullan.** Varsayılan ve önerilen yol şu: yeni model seri bileşeni için dondurulmuş `ceiling_hazard_v0`'ın S_k'sini parametre sha'sıyla AYNEN kullanır. Yeni hazard tasarlanmaz.
- Neden: o bileşen zaten dondurulmuş ve sonuçtan önce push edilmiş. Yeni bir hazard varyantı aynı 99 arzda çatallanan yol açar.
- F1'deki {1,2,3,≥4} gruplaması ya da yalnız log f3 bu yüzden bu görevin konusu değildir.
- Yeni hazard şart diyorsan gerekçesini yaz. O zaman ayrı bir model_id olur.

**Neden şimdi ve hızlı.** Faz 2B şu an 2026-08-06 sonrası 7 arzın resmi sonuçlarını repoya alıyor. Yeni model bu 7 arz için RETRO olacak; bu normal. Hızlı dondurulursa bir sonraki arzları canlı yakalar.

ÖNCE OKU:
- CLAUDE.md
- docs/specs/SPEC_CEILING_V0.md (tamamı)
- docs/specs/SPEC_SCORING.md (tamamı; §2, §3, §7, §8 bağlayıcı)
- docs/specs/SPEC_PB_V0.md (§ PB tavan kısmı)
- docs/MODELS.md; docs/DATA.md; docs/DATA_NOTES.md
- models/ceiling_hazard_v0.json, ceiling_hazard_v0@INF.json, pb_ceiling_v0.json
- borsai/survival.py, predict_hazard.py, horizons.py (fiziksel sınırlar), rules.py
- data/training_table.csv
- data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv (H99'un 990 seansı: kapanış, referans, üst ve alt limit)
- Eski repodan: F1 belgesi. Gerekirse F1'in atıf yaptığı şartname metinleri (V1_1_PREREGISTRATION §4.6 gibi).

## Okuma sınırları (sızıntı)

YASAK:
- Bu repoda: `data/outcomes/`, `data/raw/bist/`, `scores/`, `docs/SCORES.md`. Bunlar Faz 2B'nin ürettiği post-2026-08-06 sonuçları.
- Eski repoda: 2026-08-06'dan sonra listelenen arzların (CITAS, VEYAS, TKNKA, KPEKS, INTET, BKRGY, NETGL) gerçekleşen değerlerini içerebilecek her dosya:
  - replay dosyaları
  - `artifacts/outcomes/`, `artifacts/live_forecast/`, `artifacts/evaluation/`, `artifacts/predictions/`
  - `BorsAi_External_Archive/` altında 2026-08-19 sonrası tarihli her şey
  - kökteki realized/evaluation dosyaları
- Yanlışlıkla bir şey görürsen şartnamenin "Maruziyet" bölümüne yaz.

SERBEST (H99, zaten tasarıma maruz):
- H99 üzerinde TANIMLAYICI ölçümler. Örnekler:
  - kırılma günü dağılımı
  - kırılmadan sonra gün sayısına göre gözlem sayısı
  - kırılma sonrası getirinin konum ve yayılımı
  - üst limit / referans oranının dağılımı
  - L = t < h durumlarının sayıları
- Ölçüm betiği ve çıktısı `docs/specs_faz4/ekler/` altına konur (d3fabad'daki m1/m2/m3 gibi).

YASAK (beklenti yazılmadan önce ve bu görev boyunca):
- Önerdiğin modelin ya da sıfır modelin H99 walk-forward skorunu hesaplamak.
- Onu basit kurallarla karşılaştırmak.
- Beklentiyi skor hesaplayarak "kalibre etmek".
- Beklenti, tanımlayıcı ölçümlerden ve mekanikten türetilir.

## Yazılacak: `docs/specs_faz4/SPEC_CEILING_PATH_V0.md` ve gerekirse `docs/specs_faz4/ekler/`

Şartname, Opus'un (Claude Code) sormadan kodlayabileceği kesinlikte olmalı. Şu bölümleri kapsar:

**1. Modeller ve kimlikler.** En çok 3 yeni model_id; adları sen kesinleştir.
- Ana model (öneri `ceiling_path_v0`): dondurulmuş `ceiling_hazard_v0` S_k + kırılma sonrası bileşen + eşleme.
- Sıfır model / MECHANICS_BASE (öneri `ceiling_path_v0@INF`): dondurulmuş `ceiling_hazard_v0@INF` S_k (yalnız gün sabitleri) + aynı kırılma sonrası bileşen + aynı eşleme.
- İsteğe bağlı PB varyantı: `pb_ceiling_v0` S_k ile. Uygulamada talep sonucu açıklanmadan önce getiri tahmini verebilmek için. Almazsan gerekçesini yaz.

**2. Limit yolu C_h.** C_h, D1..Dh'nin hepsi tavan kapanırsa D_h kapanışıdır.
- Gerçek üst limit fiyat adımı yuvarlamasına bağlı. Oran H99'da 1.09604…1.1; bkz. SPEC_SCORING §3, "fiyat adımı notu".
- Seçenekler: `1.1^h`, ya da arz fiyatından resmi fiyat adımı tablosuyla deterministik yuvarlama.
- Birini seç. Tanımlayıcı ölçümle hata payını göster. Kural metnini borsaistanbul.com'dan kaynakla.

**3. Kırılma sonrası bileşen.** Yol bağımlılığı: L = t < h ise R_h = C_t · (1 + kırılma sonrası getiri, D_t'den D_h'ye) − 1.
- t = 0 (D1 tavan değil) ayrı bir durum olabilir; sen karar ver.
- n küçük. Parametre bütçesi F1 §2.3'e göre: en çok 2 parametre, kovaryatsız ya da gerekçeli en çok 1 kovaryat.
- Dağılım biçimi: ampirik, parametrik ya da kuantil tabanlı; gerekçeli seçim.
- Günlük ±%10 marjdan gelen fiziksel sınırlar korunur.
- Walk-forward kuralı: fold T'de yalnız seans tarihi < T olan kırılma sonrası gözlemler kullanılır (SPEC_CEILING_V0'daki reclose oranlarının kuralı gibi).

**4. Eşleme ve çıktılar.** h ∈ {1, 3, 5, 10}; uygulama için 1..10'un hepsi önerilir.
- R_h'nin öngörü dağılımı (karışım).
- Nokta tahmini:
  - MAE ile skorlandığı için birincil nokta = karışımın MEDYANI. Bu şimdi yazılır, sonradan değiştirilmez.
  - Ortalama yalnız ikincil gösterimdir.
- `p_up_h` = P(R_h > 0).
- Kuantiller (ör. %10/%50/%90) uygulamada gösterilecek.
- JSON çıktı şeması: `predict_hazard` çıktısıyla uyumlu alanlar + yeni alanlar.
- Ret kuralları: f3 yoksa ana model ret (girdisinden miras). Sıfır model f3 istemez.

**5. Karşılaştırmalar.** Aynı arzlarda, eşleşik, SPEC_SCORING §7 ile.
- Getiri: `base_always_ceiling`, `base_train_median`, `v1_5_h99`, ve ana model için sıfır modeli.
- p_up: `base_rate`, `base_last10_rate`, `v1_5_h99`, ve sıfır model.
- Önceden ilan edilmiş TEK birincil hücre ve gerekçesi. Diğer hücreler "keşif".

**6. ÖNCEDEN YAZILMIŞ BEKLENTİ.** Bu bölüm, kod ya da skor yokken yazılır ve sonradan değiştirilmez.
- **D1:** Tavan olasılığı ~0.82 iken MAE açısından en iyi nokta tahmin zaten limitin kendisi. Yeni model D1 MAE'de `base_always_ceiling` ile büyük olasılıkla BERABERE kalır; aralık 0'ı içerir. Bunu açıkça yaz. "D1'de kazanç beklenmiyordu" cümlesi ancak burada önceden yazılmışsa kullanılabilir.
- **D3, D5, D10 getiri MAE'si ve p_up Brier'i:** Beklenen fark aralıklarını SAYI olarak yaz; `base_train_median`'a, `base_rate`'e, `v1_5_h99`'a ve sıfır modele karşı ayrı ayrı. Hangi ufukta kazanç en olası, hangisinde değil, gerekçesiyle.
- **Başarısızlık tanımı:** hangi sonuç "bu model bir şey katmıyor" demek olur. Örnek: ana model sıfır modelden ayırt edilemiyorsa katkı yalnız mekaniktir.
- Beklentinin tuttuğu ya da tutmadığı her durumda ne yapılacağı. Beklentiden çok iyi çıkarsa dondurmadan önce farklı elle sıfırdan yeniden üretim yapılır (proje kuralı).

**7. Koşullu güncelleme: "bugün tavan gitti, yarın ne olur".** Bu bir ürün özelliği; aynı şartnamede tanımı ve skorlaması yapılır.
- Dondurulmuş S vektöründen: P(L ≥ k | L ≥ j) = S_k / S_j, k > j.
- Yeni modelden ayrıca: L ≥ j koşulunda R_h'nin koşullu dağılımı ve p_up.
- Güncelleme deterministik, girdisi dondurulmuş kayıt ve resmi THM'den gözlenen seri. Yeni dondurma gerekmez.
- Canlı skorlama tanımı (SPEC_SCORING'e ek):
  - Hangi (arz, j) çiftleri skorlanır: gözlenen seri j'ye ulaşmış olmalı ve j'ye ulaşıldığı resmi THM'den bilinmeli.
  - Metrikler: k = j+1..10 üzerinde koşullu RPS; seçilen k'lerde Brier.
  - Kurallar: koşullu KM ve koşullu @INF.
  - Sınıf, dayandığı kaydın sınıfını miras alır.
  - j başına n raporlanır. Koşulsuz skorlarla ASLA birleştirilmez ya da toplanmaz.
  - Küçük-n kuralları §8'deki gibi.
- `ceiling_hazard_v0` ve `pb_ceiling_v0` için de geçerlidir; bu modeller zaten dondurulmuş.
- Bu tanımın canlıda ilk metrik gösteriminden (n ≥ 10) önce yazılmış olması yeterli. Bugünkü 7 arzda metrik zaten üretilmiyor.

**8. Backtest planı (Opus için)**
- `ceiling_hazard_v0` ve `@INF` fold ledger'larındaki S_k'ler yeniden kullanılır; yeniden fit yapılmaz.
- Kırılma sonrası bileşen her fold'da walk-forward fit edilir.
- Metrikler: SPEC_SCORING §7 ve SPEC_DEVIATIONS C7 kuralları (backtest aralığı `random.Random(20260921)`, 4000 tekrar, aylık blok).
- Her koşu `experiments/log.jsonl`'a yazılır.
- Fold ledger sütunları tanımlanır.

**9. Kabul testleri (Opus için, kanıtlanabilir)**
- Tutarlılık: medyan ≤ C_h; p_up ∈ [0, 1]; S_h → 1 iken medyan = C_h.
- Sıfır modelde S = KM.
- predict paritesi |Δ| ≤ 1e-9.
- Koşullu formül için sentetik testler.
- Walk-forward sızıntı testi: fold T'de T ve sonrası tarihli seans kullanılmaz.

**10. Maruziyet:** ne gördün (MODELS.md backtest sonuçları, F1, tanımlayıcı ölçümler) ve ne görmedin.

**11. Açık sorular (proje sahibine):** en çok 5, her biri için önerin.

## Kurallar
- Mevcut hiçbir dosyayı değiştirme.
- `docs/specs/` altına YAZMA. Faz 1 bekçi testi o dizinin dosya sayısını ve git durumunu sabit tutuyor; yazarsan 2B'nin testleri kırmızıya döner.
- Metinde tarihli THB/THM dosya adı kalıbı (thb/thm + 8 hane tarih) yazma. Bekçi testi bunları tarar.
- Ekler betikleri yalnız stdlib (ya da numpy) kullanır ve yalnız H99 dosyalarını okur.
- Rapor ve şartname Türkçe.

## Teslim (rapor)
- `docs/specs_faz4/` altındaki dosyalar ve sha256'ları (`shasum -a 256`).
- 10 satırlık özet.
- §6 beklenti tablosunun birebir kopyası.
- Birincil hücre.
- Model_id listesi ve toplam serbest parametre sayısı.
- Açık sorular ve önerilerin.

## Kabul kapısı
- K1 Yalnız `docs/specs_faz4/` altında yeni dosyalar var. Hiçbir git komutu çalıştırılmadı.
- K2 §6 beklentisi sayısal, D1 beraberliği açıkça yazılı, birincil hücre tek.
- K3 Kırılma sonrası bileşen ≤ 2 parametre. Dondurulmuş hazard yeniden kullanılıyor ya da ayrılık gerekçeli.
- K4 Koşullu güncellemenin tanımı ve canlı skorlaması yazılı.
- K5 Yasak dosyalar okunmadı; maruziyet bölümü dolu.

# TASK_ID: BORSAI_FAZ3_FABLE_APP_SPEC_20260922

Model: Fable · yüksek.
- Çalışma klasörü: ~/Desktop/BorsAi.
- Ağ: gerekmez. Tauri/Rust belgelerine bakmak serbest.
- Kod yazmazsın, commit atmazsın. Yalnız `docs/app/` altına yazarsın.
- push/tag/amend yok.

## Bağlam

**Proje sahibinin hedefi.** Halka arz modellerini gömülü çalıştıran bir masaüstü uygulaması:
- Kullanıcı girdilere kendi sayılarını girer (senaryo).
- Bütün modeller yan yana görünür.
- Her modelin doğruluğu teknik olarak gösterilir: n, MAE/Brier/RPS, basit kurala göre fark + aralık.
- İleride ücretli bir ürün olabilir. Şimdilik yalnız proje sahibinin Mac'inde çalışacak (macOS arm64).

**Modeller.**
- `models/INDEX.json`'da 16 model var. Tahmin kodu `borsai/predict*.py`: saf ve yalnız stdlib.
- En değerli çıktı `ceiling_hazard_v0`: tavan serisi S_k, P_L ve P_close_ceiling. Backtest'te basit kuralları açık farkla geçiyor; ayrıntı `docs/MODELS.md`'de.

**Resmi sicil.**
- Akış: `registry/inputs/<T>.json` → `python -m borsai.freeze` → kayıt → commit + push → push kanıtı.
- Skorları Faz 2B üretecek: `scores/scores.json`. Şeması `docs/prompts/FAZ2B_OUTCOMES_SCORING.md` adım 2'de.
- Uygulama skor hesaplamaz, yalnız gösterir.

**Paralel çalışma.** Faz 2B şu an başka bir oturumda çalışıyor ve `borsai/`, `tests/`, `data/`, `scores/` yollarına commit atıyor. O yollara dokunma. Git'i yalnız okuma komutlarıyla ve `GIT_OPTIONAL_LOCKS=0` önekiyle kullan.

**Sonrası.** Bu şartnameye göre Opus (Claude Code) `app/` altında uygulamayı yazacak, sonra sen uygunluk denetimi yapacaksın. Bu yüzden şartname, uygulayıcının sormadan kodlayabileceği kadar kesin olmalı. Kabul testleri kanıtlanabilir olmalı.

ÖNCE OKU:
- CLAUDE.md
- docs/specs/SPEC_SCORING.md. §7–§8'deki gösterim kuralları uygulama için bağlayıcı; §9 sonundaki rol ayrımını da oku.
- docs/specs/SPEC_CEILING_V0.md, SPEC_PB_V0.md, SPEC_MARKET20_V0.md, SPEC_V1_6.md: çıktılar, ret kodları, uyarılar.
- borsai/predict.py, predict_hazard.py, predict_pb.py, predict_market20.py, features.py, horizons.py, survival.py
- models/INDEX.json; en az v1_5_h99.json, ceiling_hazard_v0.json, pb_v0.json
- borsai/freeze.py, borsai/registry.py
- Girdi ve kayıt biçimi: registry/inputs/NETGL.json, registry/inputs/VEYAS.json (f3 yok) ve registry/records/NETGL/*.json
- docs/MODELS.md
- docs/DATA_NOTES.md §5 (f3 tanımı karışıklığı)
- docs/ENV.md (gerekecek araçlar)

## Yazılacak: `docs/app/SPEC_APP.md` (gerekirse `docs/app/ekler/`)

Şartname şu bölümleri kapsar:

**1. Mimari**
- Tauri 2 önerilir. Ön uç için sade TypeScript; ağır bir çerçeve gerekiyorsa gerekçesini yaz.
- `predict`'in TEK uygulaması nerede olacak? Öneri Rust. Alternatifleri (Python sidecar, WASM) kısaca tartış, birini seç ve gerekçesini yaz.
- Python ile parite yöntemi:
  - Python'dan üretilen altın vektörler: her model için en az 200 girdi; uç durumlar ve ret yolları dahil.
  - `cargo test` ile |Δ| ≤ 1e-9.
  - Ret ve uyarı kodları birebir aynı.

**2. Veri sözleşmeleri**
- **Model JSON'ları:** uygulamaya gömülür, salt okunur. Açılışta sha256'ları INDEX'teki değerlerle doğrulanır.
- **Girdi belgesi:** `borsai.inputs/1` ile uyumlu.
- **Skorlar:** `scores.json` yalnız okunur.
- **Kişisel kayıtlar:** uygulama verisinde JSON; silinebilir. Sicile ve skorlara asla girmez.
- **Şema sürümleri:** uyumsuz sürümde uygulamanın ne yapacağı tanımlanır.

**3. Ekranlar ve akışlar.** Her biri için alanlar, durumlar, boş ve hata hâlleri.
- **a. Girdi formu**
  - Alan listesi: tanım, birim, kaynak ipucu (hangi KAP/SPK belgesi), zorunlu mu isteğe bağlı mı.
  - Talep toplama öncesi (PB) ve sonrası aşamalar.
  - f3'ün tam tanımı.
  - XU100 f6 nasıl elde edilir: uygulama ağa çıkacak mı, yoksa kullanıcı mı girecek? Karar ver.
- **b. Sonuç ekranı**
  - Bütün modeller yan yana; kullanıcı modelleri gösterip gizleyebilir.
  - D1/D3/D5/D10 getiri, % ve fiyat olarak.
  - P(kapanış > arz).
  - Tavan serisi:
    - S_k eğrisi
    - P(L = k), yani "tavan k'ıncı günden sonra bozulur"
    - beklenen ve medyan L
    - P_close_ceiling
  - Ret hücreleri "ret + neden" olarak gösterilir.
  - Uyarılar: eğitim aralığı dışı, f4 = 0, fiziksel sınır kırpması, pb4.
- **c. Senaryo modu:** kullanıcının kendi değerleri. Sicile girmez ve resmi kayıttan görsel olarak açıkça ayrılır.
- **d. Doğruluk paneli.** SPEC_SCORING §8 birebir uygulanır:
  - iki terazi ayrı başlık ve renkle gösterilir;
  - n < 10'da yalnız satır tablosu;
  - 10 ≤ n < 30'da "yetersiz örnek";
  - "geçiyor" yalnız aralık 0'ı dışlıyorsa;
  - isabet oranı hiçbir zaman tek başına gösterilmez;
  - her metrik basit kuralın yanında, fark + aralık + n ile;
  - önceden ilan edilmiş birincil hücre vurgulanır;
  - model kartı ve rejim uyarısı.
- **e. Resmi "dondur" akışı**
  - Düğme → girdi belgesi (`registry/inputs/<T>.json`) → kayıt.
  - Kayıt yazıcı tek kaynak olarak Python `borsai.freeze` mu kalır, yoksa Rust mu? Gerekçeli karar ver.
  - Kullanıcıya commit + push talimatı ve push kanıtı komutu gösterilir.
  - "İlk işlem gününden önce" uyarısı.
  - Aynı arza ikinci kayıt: önce PB, sonra talep katlı. Bu, 2B düzeltmesinden sonra serbest.
  - İptal akışı.
  - Resmi sicil repoda kalır, uygulama verisinde değil.
- **f. Kişisel kayıtlar:** listele, sil, dışa aktar.

**4. Dil ve üslup**
- Arayüz Türkçe.
- "Tahmin" ve "olasılık" dili kullanılır.
- Tek satırlık "yatırım tavsiyesi değildir" yer tutucusu. Hukuki metin değil.

**5. Kabul testleri (U1…Un).** Her biri otomatik ya da elle kanıtlanabilir olmalı:
- parite;
- ret ve uyarı kodları;
- gösterim kuralları: n = 7'lik örnek `scores.json` ile satır tablosu çıkar, metrik çıkmaz;
- dondur akışı uçtan uca (geçici bir repoda);
- kişisel kayıtların sicile sızmaması.

**6. Kurulum ve çalıştırma**
- Gereken araçlar: Rust, Node, Tauri CLI. Xcode CLT zaten kurulu.
- Claude Code'un çalıştıracağı kurulum komutları.
- `app/` dizin düzeni; derleme ve çalıştırma.
- macOS imzası kişisel kullanımda ertelenir.

**7. Aşamalar.** Uygulayıcı için sıralı teslimler ve her birinin kabul kapısı. Örnek sıra:
- predict + parite
- ekranlar
- dondur akışı
- doğruluk paneli

**8. Açık konular**
- Dağıtımdan önce BIST veri lisansı ve SPK çerçevesi: tek paragraf, karar değil.
- Yeni model_id'lerin uygulamaya eklenmesi (INDEX'ten okuma) ve yeniden eğitim.

## Kurallar
- Kod yazma, commit atma. Yalnız `docs/app/` altına yaz.
- `docs/specs/` altına YAZMA: Faz 1 bekçi testi o dizindeki dosya sayısını sabit tutuyor.
- Mevcut hiçbir dosyayı değiştirme.
- Metinde tarihli THB/THM dosya adı yazma (ör. thb + tarih). Bekçi testi bunları tarar.
- Model davranışını değiştiren hiçbir şey önerme: f3 yokken tahmin uydurmak, kırpmayı ya da ret kurallarını değiştirmek gibi. `predict`'in tanımı Python'dakidir.
- Belirsizlikleri SPEC_APP içinde "Açık sorular (proje sahibine)" başlığı altında yaz; her birine önerini ekle.
- Rapor Türkçe.

## Teslim (rapor)
- `docs/app/` altındaki dosyaların listesi ve sha256'ları.
- 10 satırlık özet: mimari kararlar ve nedenleri.
- Proje sahibine açık sorular (en çok 5), her biri için önerin.
- Uygulayıcı için aşama başına tahmini iş büyüklüğü.

## Kabul kapısı
- K1 Yalnız `docs/app/` altında yeni dosyalar var. `GIT_OPTIONAL_LOCKS=0 git status --porcelain` çıktısı raporda; `docs/app/` dışındaki satırlar 2B oturumuna aittir.
- K2 SPEC_SCORING §8'deki her gösterim kuralı SPEC_APP'te bir kabul testine bağlı.
- K3 Parite yöntemi ve toleransı sayısal olarak tanımlı.
- K4 Dondur akışı resmi sicili repoda tutuyor ve kişisel kayıtların sicile giremeyeceği bir testle gösteriliyor.

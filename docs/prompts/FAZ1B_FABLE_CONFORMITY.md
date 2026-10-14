# TASK_ID: BORSAI_FAZ1B_FABLE_CONFORMITY_20260922

Model: Fable, akıl yürütme yüksek. Çalışma klasörü ~/Desktop/BorsAi. Ağ yok. Salt okur; tek yazma izni docs/fable_conformity_20260922/. git'te yalnız okuma komutları, GIT_OPTIONAL_LOCKS=0 ile (log, show, diff, cat-file); status, add, commit YOK.

## Bağlam

docs/specs/ altındaki şartnameleri sen yazdın (commit d3fabad). Opus bunları koda döktü, backtest'ten geçirdi ve dondurdu (commit b09cab5, HENÜZ PUSH EDİLMEDİ). Push, modellerin sonuçlardan önce dondurulduğunun zaman kanıtı olacak. Push'tan sonra 2026-08-19 sonrası THB/THM verisi indirilecek ve 7 arz bu modeller için prospektif örneklem olacak. Bu yüzden push'tan ÖNCE senin uygunluk denetimin gerekiyor: şartnameyi yazan el kodu denetliyor.

## Dikkat: sonuç beklentinden iyi

`ceiling_hazard_v0` için §11'de backtest RPS farkını (model − en iyi KM kuralı) −0.005 … −0.02 olarak ve aralığın büyük olasılıkla 0'ı içereceği şeklinde yazmıştın. Gerçekleşen: −0.0496 [−0.0751, −0.0219], ayrıca @INF'e karşı −0.0503 (docs/MODELS.md). Bu ya iyi haber ya da bir sızıntı ya da hata. Önceliğin bunu ayırt etmek.

## Sorular

1. **Sızıntı denetimi (en önemli).** Kendi bağımsız script'inle (/tmp altında; BorsAi/.venv'deki numpy/scipy/sklearn kullanılabilir; borsai/ paketini İMPORT ETME), `ceiling_hazard_v0` için en az 3 fold'u sıfırdan yeniden üret: biri erken, biri orta, biri geç.
   - Eğitim kişi-dönem satırları yalnız seansı < T olanlar mı; test arzı dışarıda mı; sağ-sansür doğru mu?
   - Ön işleme istatistikleri fold içinde mi hesaplanıyor?
   - λ seçimi yalnız eğitim içi CV ile mi yapılıyor?
   - S_k değerleri borsai ledger'ıyla örtüşüyor mu?
   - KM kuralları aynı eğitim kümesinden mi?

   Aynı kontrolü `pb_ceiling_v0` (kesim B) için en az 1 fold'da, ayrıca `pb_v0` ve `v1_5_market20_v0` için birer fold'da yap. market20'de f6'nın yalnız S0 < ref kayıtlarını gördüğünü doğrula.

2. **Uygunluk.** Her model için şartname ↔ kod karşılaştırması: özellikler, ön işleme, model sınıfı, ızgara, seçim kuralı ve eşitlik kuralı, fold planı ve min-eğitim kuralları, ret/uyarı kuralları, dondurulmuş JSON'un içeriği (parametre sayısı, eğitim kümesi, kesim). Şartnamedeki kabul testlerinin testlerde gerçekten var olup olmadığını ve doğru şeyi sınayıp sınamadığını kontrol et.

3. **Sapmalar.** docs/SPEC_DEVIATIONS.md'deki her maddeye hüküm ver: KABUL / DÜZELT / YENİ KİMLİK. Özellikle C2'ye (KM dondurması 99, model 97) ve B1–B2'ye (market20 rol ayrımı) bak.

4. **predict paritesi.** Her yeni model için dondurulmuş JSON'dan stdlib predict çıktısı ile fit tarafının çıktısı eşit mi? En az 5 girdi vektörü, uç durumlar dahil. Ret kuralları çalışıyor mu (f3 yok; PB alan eksik; fiyat aralığı; f6 yok)?

5. **Beklenti tablosu.** docs/MODELS.md'deki "tuttu / tutmadı" hükümleri şartnamedeki metne ve OPERATIONAL_RULES'a göre doğru mu uygulanmış?

## Hüküm biçimi

Her model için tek satır:

| Hüküm | Anlamı |
|---|---|
| **PUSH_OK** | Olduğu gibi dondurulabilir. |
| **FIX_BEFORE_PUSH** | Şartnameden sapan bir hata var. Kesin düzeltme tarifi dosya:satır ile verilir. Şartname kimliği tanımladığı için düzeltme aynı model_id ile push'tan önce yapılır. |
| **NEW_ID_OR_DROP** | Tasarım sorunu var. Model bu turda dondurulmaz; gerekçe yazılır. |

## Kurallar

- Hiçbir dosyayı değiştirme. Tek yazma izni: docs/fable_conformity_20260922/ (AUDIT.md ve ekler/).
- Her iddiaya kanıt: dosya:satır ya da komut + çıktı. Ölçtüğünü ve çıkarımını ayrı işaretle.
- 2026-08-19 sonrası hiçbir veri indirme ya da okuma yok.

## Teslim

AUDIT.md: en başta model başına hüküm tablosu ve 10 satırlık özet; sonra soru 1–5 sırasıyla. Her bulguya önem derecesi: KRİTİK / ÖNEMLİ / KÜÇÜK.

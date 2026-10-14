# TASK_ID: BORSAI_FAZ1_FABLE_MODEL_SPECS_20260921

Model: Fable, akıl yürütme yüksek. Çalışma klasörü ~/Desktop/BorsAi, ek dizin ~/Desktop/Halka_Arz_Modeli (arşiv). Ağ yok. Salt okur; tek yazma izni docs/specs/.

## Bağlam

Senin denetimin (~/Desktop/Halka_Arz_Modeli/docs/fable_audit_20260921/AUDIT.md) plana işlendi. Yeni repo hazır (CLAUDE.md, data/training_table.csv, docs/DATA*.md).

Aynı anda aynı klasörde bir Opus oturumu model çekirdeğini kuruyor ve V1.5'i taşıyor (docs/prompts/FAZ1A_V1_5_PORT.md). Onun dosyalarına dokunma. git'te yalnız okuma komutları kullan (log, show, cat-file); status, add ve commit YOK.

Sıra kuralı gereği aşağıdaki modellerin JSON'ları, 2026-08-19 sonrası THB/THM verisi repoya girmeden ÖNCE dondurulacak. O zaman 2026-08-06 sonrası listelenen 7 arz (CITAS, VEYAS, TKNKA, KPEKS, INTET, BKRGY, NETGL) ve sonraki her arz, bu modeller için gerçek prospektif örneklem olur. Kodlamayı ve dondurmayı Faz 1B'de Opus yapacak. Senin işin şartnameleri yazmak; yazan el ile tasarlayan el ayrı olacak.

## İstenen şartnameler (her biri docs/specs/ altında ayrı bir .md)

1. **SPEC_CEILING_V0.md: tavan modeli v0.** AUDIT §3b'deki önerin: ayrık zamanlı hazard, yalnız listeleme öncesi bilgi, ≤ 3 paylaşılan katsayı, gün sabitleri (gruplamayı sen belirle ve gerekçelendir). Çıktılar: P(seri ≥ k), k = 1..10. Tutarlılık kendiliğinden gelmeli. P(Dk'de tavan kapanışı) ayrı bir çıktı olacaksa nasıl türetileceğini yaz; türetilmeyecekse neden. İstersen beklenen getiriye eşleme; opsiyonel, ama yapılacaksa kuralı şimdi yaz.
2. **SPEC_PB_V0.md: talep toplama öncesi model.** f3 (talep katı) henüz yokken tahmin verebilen model; kullanıcı arzı talep toplamadan önce görmek isteyecek. PB kanıt CSV'si (data/raw) ve pb1–pb4. V1.5'in f3'süz kullanımının yerini alır.
3. **SPEC_MARKET20_V0.md: piyasa modeli**, takvim sonu hatası düzeltilmiş. Önemli: XU100 bir SONUÇ değil, tahmin anındaki GİRDİ. 2026-08-19 sonrası tahminler için XU100 verisi gerekecek. Bunun resmi kaynaktan nasıl alınacağını ve sıra kuralıyla nasıl bağdaştığını yaz: sıra kuralı arz sonuçları içindir, girdi verisi için değil. Yine de bir sınır varsa belirt.
4. **SPEC_V1_6.md:** V1.5 aynen, yalnız ızgara genişletilmiş (AUDIT §1.2-e). Izgara değerlerini şimdi sabitle; "yalnız sabit terim" uç noktası dahil.
5. **SPEC_SCORING.md: Faz 2 skorlama tanımları** (CLAUDE.md kural 6: tanımlar ilk skorlamadan önce kodda olmalı):
   - D_h tanımı: yarım gün, işlem durdurma, tatil.
   - Tavan etiketi: THM üst limitiyle Decimal eşitliği.
   - Prospektif/retrospektif ayrımının tarihlerden hesaplanması (kural 3).
   - "Atlandı" satırları (kural 2).
   - Legacy dondurmaların rolleri: NETGL = git+push kanıtlı; TKNKA = v1_5_full20; BKRGY/INTET'te birincil = POST_BOOKBUILD; f3'süz olanlar = geçersiz kullanım.
   - Metrikler, blok bootstrap aralıkları ve küçük-n gösterim kuralları (AUDIT §3d).

## Her model şartnamesinde bulunacaklar

- model_id.
- Tam özellik tanımları ve kaynak sütunları (data/training_table.csv ya da data/raw).
- Ön işleme; model sınıfı; ızgara ve seçim yöntemi.
- Parametre bütçesi ve gerekçesi (azınlık sınıfı sayıları).
- Eksik veri davranışı: ret mi, uyarı mı.
- Walk-forward planı (V1.5 ile aynı fold kuralı mı, farkı ne).
- Aynı fold'larda karşılaştırılacak basit kurallar.
- **Sonuç görülmeden yazılan beklenti:** hangi ufukta ne bekliyorsun, neyi başarı sayacaksın, neyi başarısızlık sayacaksın. Backtest H99 üzerinde ve tasarım H99 görülerek yapıldığı için geriye dönük sonuçların "tasarıma maruz" olduğunu açıkça yaz. Asıl ölçüm prospektiftir.
- Opus'un koda dökebileceği kesinlikte sözde kod.
- Kabul testleri: kodun şartnameye uyduğunu gösterecek somut testler.

## Kurallar

- Salt okur. Tek yazma izni: docs/specs/. Kod yazma; hesap gerekiyorsa /tmp altında salt okur script.
- Her sayıya kanıt (dosya:satır ya da komut + çıktı). Ölçtüğünü ve çıkarımını ayrı işaretle.
- Şartnameler kısa ve uygulanabilir olsun. Her dosyanın başında 10 satırı geçmeyen bir özet.

## Teslim

docs/specs/ altındaki dosyaların listesi, her birinin tek cümlelik özeti ve Opus'un Faz 1B'de dikkat etmesi gereken en önemli üç nokta.

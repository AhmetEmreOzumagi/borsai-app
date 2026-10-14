# FAZ9_KITAP_AUDIT_ORTAK — Kılavuz denetimlerinin ortak kuralları

Bu dosya dört denetim görevinin ortak kısmıdır. Görevler:
- `FAZ9_KITAP_AUDIT_1_VERI.md`
- `FAZ9_KITAP_AUDIT_2_ONCESI.md`
- `FAZ9_KITAP_AUDIT_3_SONRASI.md`
- `FAZ9_KITAP_AUDIT_4_UYGULAMA.md`

Her görev dosyasındaki `<n>` ve `<AD>` o görevin numarası ve adıdır.

## Ne denetleniyor, neden

- Orkestratör ve yardımcı ajanları 7 Ekim 2026'da repoya bakarak projenin tamamını anlatan bir kılavuz yazdı: `docs/fable_kitap_audit/kitap/01..10_*.md` (121 bin kelime, HEAD `ee3796d`). Önce `docs/fable_kitap_audit/README.md`'yi oku.
- Proje sahibinin sorusu: **"Yaptığımız bir hata var mı?"**
- **Kılavuz birincil kaynak değildir.** Kanıt yalnız şunlardır:
  - repodaki dosyalar;
  - git geçmişi;
  - senin hesapladığın sayılar.

  Kılavuzu bir iddia listesi olarak kullan ve her iddiayı kaynağına karşı ölç. Her alt bölümün sonundaki "Kaynak dosyalar" satırı başlangıç noktasıdır. O yolların gerçekten var olup olmadığı da denetimin parçasıdır.
- **Üç bulgu türü:**
  - **[P] Proje hatası.** Kod, veri, şartname, test ya da proje belgesi (`docs/*.md`) yanlış ya da birbiriyle çelişiyor. Örnekler:
    - formül kodda şartnameden farklı;
    - eğitime gelecekten bilgi sızıyor;
    - bir sayı belgede bir değer, koddan hesaplanınca başka;
    - bir test iddia ettiği şeyi sınamıyor;
    - CLAUDE.md "kodla zorlanır" diyor ama kural zorlanmıyor.
  - **[K] Kılavuz hatası.** Repo doğru ama kılavuz yanlış ya da eksik anlatıyor.
  - **[B] Belirsiz.** Ölçülemedi ya da yorum gerektiriyor. Nedeni yazılır.
- **Önem dereceleri:**
  - **KRİTİK:** bir doğruluk rakamını, bir tahmini, bir kaydın sınıfını ya da bir kuralın uygulanmasını değiştirir.
  - **ORTA:** yanlış ama sonuca dokunmaz. Örnek: yanlış belge sayısı, yanıltıcı ad ya da metin.
  - **DÜŞÜK:** yazım hatası ya da eksik açıklama.
- **Asıl değer [P] bulgularındadır.** [K] bulgularını kısa yaz, bir satır yeter. Kılavuzu düzeltmek bu görevlerin işi değil.

## Kurallar

- **Model:** Fable · yüksek.
- **Ağ yok.** TÜİK, KAP ya da BIST'e gitme. Eski kohort ve kasa arzları için hiçbir sonuç arama.
- **Git:**
  - Yalnız okuma komutları çalıştır, hepsini `GIT_OPTIONAL_LOCKS=0` önekiyle.
  - Sonda tek commit atılır, yalnız görev dosyandaki yollarla.
  - push, tag ve amend yok.
  - `index.lock` hatası alırsan 10 saniye bekle ve yeniden dene. Kilidi silme.
- **Paralel çalışma.** Dört denetim aynı anda koşabilir. Diğer denetimlerin dosyaları çalışma ağacında görünebilir ya da commit'lenebilir (`docs/fable_kitap_audit/` altındaki diğer raporlar, `docs/prompts/FAZ9_KITAP_AUDIT_*`). Bu beklenen bir durum; o dosyalara dokunma.
- **Yazma izinleri:**
  - Yazabileceğin yerler yalnız kendi raporun (`docs/fable_kitap_audit/AUDIT_<n>_<AD>.md`) ve `docs/fable_kitap_audit/ekler/<n>/` (en çok 3 MB).
  - Geçici işler `/tmp/borsai_kitap_audit_<n>/` altında yapılır ve sonda silinir.
  - Repoda başka hiçbir dosya oluşturulmaz ya da değiştirilmez.
  - **Bulduğun hatayı düzeltme, yalnız raporla.**
- **Koruma.** Başta ve sonda aşağıdaki iki komutu çalıştır. Çıktıları `ekler/<n>/koruma_once.txt` ve `koruma_sonra.txt` dosyalarına yaz.
  ```
  GIT_OPTIONAL_LOCKS=0 git rev-parse HEAD:borsai HEAD:data HEAD:models HEAD:registry HEAD:scores HEAD:app HEAD:tests HEAD:legacy HEAD:CLAUDE.md
  GIT_OPTIONAL_LOCKS=0 git status --porcelain --untracked-files=all -- borsai data models registry scores app tests legacy experiments CLAUDE.md
  ```
  Birinci komutun çıktısı iki ölçümde aynı olmalı. HEAD diğer denetimlerin commit'leriyle ilerleyebilir, ama bu dokuz sha değişmemeli. İkinci komutun çıktısı iki ölçümde de boş olmalı.
- **Testler.**
  - Tam test koşusu yapma. `ee3796d`'de testler yeşildi: pytest 952, cargo 164, vitest 376 (`docs/app/ui_fix_test_runs.txt`).
  - Bir iddiayı sınamak için tek bir test dosyası ya da tek bir test koşabilirsin (`.venv/bin/pytest -q tests/x.py::test_y`).
  - Bir ağaç temizliği bekçisi, diğer denetimlerin izlenmeyen dosyaları yüzünden kırmızı olursa bunu proje hatası sayma.
- **Mutasyon ya da deneme gerekirse** asıl repoda yapma. Klonda çalış: `git clone --local . /tmp/borsai_kitap_audit_<n>/clone`. `.venv`'i klona bağla ve bağı klonun `.git/info/exclude` dosyasına yaz.
- **Hijyen.**
  - Kasa (SEALED) kodlarını yalnız bellekte bir küme olarak tut. Rapora ve eklere kod yazma, yalnız sayı yaz.
  - Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı olmayacak.
  - Rapor ve eklerin sonunda bu iki sayımı yap ve yaz. İkisi de 0 olmalı.
- **Ölçmeden hüküm yok.**
  - Her [P] ve [K] bulgusu için şunları yaz: kılavuzdaki yeri (dosya ve § numarası), repodaki kanıtı (dosya:satır ya da komut ve çıktısı), beklenen değeri ve gerçek değeri.
  - "Doğrulandı" diyebilmek için bakmış olmalısın. Bakmadıklarını "Bakılmayanlar" listesine yaz.
  - Kendi ölçtüğünü **[ÖLÇTÜM]**, yorumunu **[ÇIKARIM]** diye işaretle.
- **Beklenenden çok iyi ya da çok kötü bir sayı** görürsen kökünü ölç, tahmin etme.
- **Düzeltme önerisi.** CLAUDE.md kural 5'e göre yaz:
  - Kodu var olan şartnameye uydurmak aynı model_id ile yapılır.
  - Şartnameyi, özelliği ya da veriyi değiştirmek yeni model_id gerektirir.

## Rapor biçimi

Dosya: `docs/fable_kitap_audit/AUDIT_<n>_<AD>.md`

1. **İlk satır:** `KITAP_AUDIT_<n>: [P] <x> kritik, <y> orta, <z> düşük; [K] <k>; [B] <b>`
2. **Özet.** Proje sahibi için sade Türkçe, en çok 10 satır. En önemli üç şey önce gelir.
3. **Bulgular tablosu.** Sütunlar:
   - no;
   - tür;
   - önem;
   - kılavuzdaki yer;
   - kısa tanım;
   - kanıt;
   - öneri (düzeltme kodda mı belgede mi; yeni model_id gerekir mi).
4. **Bölüm bölüm kontrol listesi.** Her § için kontrol edilen iddia sayısı, tutan ve tutmayan.
5. **Bağımsız yeniden hesaplananlar.** Kendin hesapladığın her kilit sayı için betik yolu, kendi sonucun ve repodaki değer.
6. **Bakılmayanlar** ve nedenleri.
7. **Proje sahibine açık sorular** (en çok 3).
8. **Koruma ve hijyen sayımları.**

## Teslim (sohbete, kısa)

- Commit sha'sı ve konusu.
- Raporun ilk satırı.
- KRİTİK bulguların her biri için tek satır.

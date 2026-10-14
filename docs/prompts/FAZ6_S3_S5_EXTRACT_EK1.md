# EK1 — BORSAI_FAZ6_S3_S5_EXTRACT_20260925: Takvim C kapanışları için bülten kanıtı

Yazan: orkestratör, 2026-09-25 ~14:00 (İstanbul). Ana görevin T6 kuralı doğru çalıştı: prob 5 XU100-boşluk gününün hepsinde THB zip'i buldu (Şubat 2023 günleri ~30 KB; 2023-04-24 ~107 KB, olağan boyut).

**Kök neden.** Prob kuralı "bülten yayımlanmışsa o gün seanstır" varsayıyordu. Bu varsayım altyapı görevinde yazıldı, orkestratörün görev metninde de sorgulanmadan kaldı. Yayımlanmış bülten işlem olduğunu göstermez: piyasanın kapalı olduğu bir günde de içinde işlem olmayan bir bülten yayımlanabilir. Doğru ölçüt, o gün işlem yapılıp yapılmadığıdır. Bu, bülten açılarak ve yalnız toplam sayılarla (üye satırı basılmadan) makineyle ölçülür.

**Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** Bu ek hiçbir modeli, girdiyi ya da S2 kaydını değiştirmez. Sonuç takvimi SPEC_SCORING §2'deki "resmi seans" tanımına uydurulur. Bu düzeltme, hiçbir sonuç repoya girmeden yapılıyor.

## Kararlar
- **K1.** Takvim C dosyası (`data/raw/pay_calendar_c_20200101_20230921.csv`) ve `market20` sabitleri (`XU100_GAP_CLOSURES` dahil) DEĞİŞMEZ. Bunlar f6'nın takvimidir; S2 kayıtları onlarla donmuştur.
- **K2. Sonuç takvimi.** `outcomes_oot.load_calendar_oot` = Takvim C seansları ∪ kanıt dosyasında `TRADING_SESSION` olan günler ∪ H99 takvimi ∪ Faz 2A uzatması. İlan dışı kapanışlar eskisi gibi düşülür. Yarım günler değişmez.
- **K3. Kanıt dosyası** (yeni, pinli): `data/raw/pay_calendar_c_bulletin_evidence_20200101_20230921.csv`.
  - Kapsam: Takvim C'nin **hafta içi bütün tam kapanışları** (orkestratör ölçümü: 42 gün; 37 tatil tablosu + 5 XU100 boşluğu; hafta içi XU100 boşluğu sayısıyla aynı, AUDIT §4).
  - Her gün için THB HEAD. 200 dönen günün THB zip'i karantinaya indirilir (`fetch_quarantine`). Makine şunları sayar: toplam satır, `.E` satırı, `TOPLAM SOZLESME SAYISI` > 0 olan `.E` satırı. Hiçbir satır, kod ya da fiyat yazılmaz, basılmaz.
  - Sütunlar: `date, source ∈ {HOLIDAY_TABLE, XU100_GAP}, thb_head_status, thb_sha256, thb_bytes, n_rows, n_equity_rows, n_equity_rows_traded, decision, checked_at_istanbul`. 404 günlerinde sha/bayt/sayı sütunları boş.
- **K4. Önceden yazılmış karar kuralı:**
  - HEAD 404 → `NOT_PUBLISHED` (kapanış doğrulandı).
  - HEAD 200 ve `n_equity_rows_traded = 0` → `PUBLISHED_NO_TRADING` (kapanış doğrulandı; sonuç takviminde kapalı kalır).
  - HEAD 200 ve `n_equity_rows_traded ≥ 50` → `TRADING_SESSION` (sonuç takviminde seans olur).
  - `n_equity_rows_traded` 1–49 arasındaysa ya da HEAD başka bir kod dönerse → DUR. Yalnız sayıları rapora yaz.
- **K5. Prob.** `check_xu100_gap_closures` genişletilir ya da yerine yenisi gelir. Kanıt dosyası varken Takvim C'nin her hafta içi kapanışını kanıta karşı denetler; şu durumlarda `CalendarConflict` verir:
  - kanıtta satırı yok;
  - `NOT_PUBLISHED` ama HEAD 200;
  - `PUBLISHED_*` ya da `TRADING_SESSION` ama HEAD 404;
  - karantinadaki zip'in sha'sı kanıttaki pinle eşit değil.
  
  Kanıt dosyası yoksa prob bugünkü gibi davranır (5 gün; yayımlanmışsa DUR).
- **K6. f6 ve S2 kayıtları.** Kayıt iptali yok, yeniden kayıt yok. Bir gün `TRADING_SESSION` çıkarsa, f6 penceresi o günü kesen üyelerde f6, "20 XU100 gözlemi" üzerinden hesaplanmış olur (o gün pinli XU100 serisinde yok). SPEC_DEVIATIONS'a yazılır; S6'da bilgi olarak sayılır. Orkestratörün yalnız takvimden ölçtükleri:
  - 2023-04-24'ü kesen pencereler: f6 5 üye (açık kümede 1), D_1…D_10 3 üye (açık kümede 2).
  - Şubat günlerini kesen pencereler: f6 1 üye (açık kümede 1), D_1…D_10 1 üye (açık kümede 0).
  - İlk işlem günü bu 5 günden birine düşen üye yok.
- **K7.** T5 bağımsız betiği de aynı sonuç takvimini kullanır (Takvim C + `TRADING_SESSION` günleri; kanıt dosyasını kendisi okur).

## İzinli izlenmeyen
Bu EK dosyası. Başka bir şey varsa DUR.

## Adımlar
- **E0.** HEAD `1c0803e`, ağaç temiz (bu dosya hariç).
- **E1. Kod (commit E1):**
  - `python -m borsai.outcomes_oot calendar-evidence` alt komutu: önce `download_gate`; yalnız Takvim C hafta içi tam kapanışları; `--pace`; karantina.
  - Dosya yoksa yazar. Varsa ve içerik aynıysa `UNCHANGED`; farklıysa DUR. `checked_at` karşılaştırmaya girmez; ilk yazım korunur.
  - K2 ve K5.
  - Sentetik testler:
    - işlemsiz zip → `PUBLISHED_NO_TRADING`; işlemli zip → `TRADING_SESSION`; 1–49 → hata; 404 → `NOT_PUBLISHED`;
    - prob uyuşmazlıklarının her biri → `CalendarConflict`;
    - `load_calendar_oot` `TRADING_SESSION` gününü seans sayar, `PUBLISHED_NO_TRADING` gününü saymaz;
    - kanıt dosyası yokken eski davranış.
  - Mutasyon (her yeni kural için en az bir): eşik 50 → 1, `TRADING_SESSION` takvime eklenmez, prob kanıtı atlar. Çıktı `docs/faz6/ekler/s3_s5_mutasyon_ek1.txt`.
  - SPEC_DEVIATIONS I34… (K1–K7). Tam pytest + test.sh yeşil → commit E1.
- **E2. Kanıt (commit E2):** `.venv/bin/python -m borsai.outcomes_oot calendar-evidence`. Beklenen:
  - 42 satır: `HOLIDAY_TABLE` 37, `XU100_GAP` 5.
  - Her satırda K4'e göre bir karar; DUR durumu yok.
  - Karar sayıları ve 5 XU100-boşluk gününün kararları rapora (günler tarihle yazılabilir; bunlar piyasa günleri, üye değil).
  
  Temizlik yolu (`test_guardrails.py::test_legacy_and_data_have_no_working_tree_changes` ve yalnız bu dosya yüzünden kırmızı olan diğerleri) → commit E2 (yalnız kanıt dosyası) → deselect'siz tam koşu yeşil.
- **E3.** Ana görevin Bölüm A'sına **adım 2'den** (prob) devam et. Prob yeşil olmalı. Sonra S3a → S3b → RA. RA raporuna bir "EK1" bölümü ekle: E1/E2 hash'leri, kanıt karar sayıları, `TRADING_SESSION` günlerinin listesi, K6 etkilenen üye sayıları (açık/toplam, kod yok), mutasyon.
- Push bloğu değişmez: `push_proof <S3a> <S3b>`. E1 ve E2 aynı push'la gider.

## Commit'ler
```
git add borsai/outcomes_oot.py tests/test_faz6_oot.py docs/SPEC_DEVIATIONS.md docs/faz6/ekler/s3_s5_mutasyon_ek1.txt docs/prompts/FAZ6_S3_S5_EXTRACT_EK1.md
git commit -m "BORSAI_FAZ6_CAL_C_EVIDENCE_CODE: outcome calendar from bulletin evidence (trading vs published-no-trading), probe checks every Calendar C weekday closure" -- borsai/outcomes_oot.py tests/test_faz6_oot.py docs/SPEC_DEVIATIONS.md docs/faz6/ekler/s3_s5_mutasyon_ek1.txt docs/prompts/FAZ6_S3_S5_EXTRACT_EK1.md
git add data/raw/pay_calendar_c_bulletin_evidence_20200101_20230921.csv
git commit -m "BORSAI_FAZ6_CAL_C_EVIDENCE: bulletin evidence for Calendar C weekday closures (aggregate counts only)" -- data/raw/pay_calendar_c_bulletin_evidence_20200101_20230921.csv
```
Diğer bütün kurallar ana görevdeki gibidir: yalnız sayılar, SEALED yok, `thb`/`thm` + 8 haneli tarih kalıbı metinde yok, `git add -A` yok.

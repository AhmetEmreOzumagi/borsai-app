# TASK_ID: BORSAI_FAZ3_FABLE_APP_AUDIT_20260923

Model: Fable · yüksek. Klasör: ~/Desktop/BorsAi. Ağ gerekmez (node_modules ve cargo önbelleği hazır; indirme gerekirse DUR).
- Git: yalnız okuma komutları ve her zaman `GIT_OPTIONAL_LOCKS=0` öneki. Sonda tek commit, yalnız kendi yollarınla.
- Yazma: YALNIZ `docs/fable_app_audit/` (AUDIT.md ve `ekler/`). Geçici işler `/tmp/borsai_app_audit/` altında: klonlar, mutasyon kopyaları, büyük çıktılar. `ekler/` toplamı ≤ 2 MB.
- `app/` altında hiçbir dosyayı değiştirme. Bulgular düzeltme tarifidir; düzeltmeyi sonra Opus yapar.

## Bağlam
- Uygulama şartnamelerini sen yazdın:
  - `docs/app/SPEC_APP.md` (EK 1 dahil): `52e1567`
  - `docs/app/SPEC_APP_EK2.md` (Faz 4): `c89ff5a`
  - Proje sahibi kararı "beyan yalnız etiket" (§3g, U52): `cf90da2`
- Uygulama Opus'a ait:
  - `50c62da` aşama 0 · `0b67f5d` aşama 1 · `5606772` aşama 2 · `a41f183` + `2a7cf0c` aşama 3
  - `50e6af9` U52 · `4c44bcc` P1 · `510f890` P2 · `0341bc6` aşama 4 · `8fa0bf5` aşama 5
- Şartname sonrası bağlayıcı eklemeler görev dosyalarında. Bunları da şartname say; SPEC_APP ile çelişen varsa bulgudur:
  - `docs/prompts/FAZ3_APP_STAGE3.md`, `FAZ3_APP_P1.md`, `FAZ3_APP_P2.md`
  - `FAZ3_APP_STAGE4.md`: "şartname yazıldıktan sonra eklenen alanlar" ve iki bütünlük kuralı
  - `FAZ3_APP_STAGE5.md`: G1–G6, özellikle G1 bant tablosu
- Uygulama kişisel kullanımda (`/Applications/BorsAi.app`). İlk gerçek arzın dondurulması yakında bu uygulamadan yapılabilir.
- **Denetimin asıl sorusu:** uygulama resmi sicile, skora ya da kullanıcının resmi sanacağı bir sayıya yanlış bir şey sokabilir mi?
- **Neden ağırlık testlerin içinde:** U28 testi aşama 3'ten 5'e kadar öncesi/sonrası sha listesini hiç karşılaştırmıyordu (`let _ = scen_before;`, `app/src-tauri/tests/e2e.rs`). Aşama 5'te düzeldi. "Test var" ile "test doğru şeyi sınıyor" aynı şey değil.

ÖNCE OKU:
- CLAUDE.md
- docs/app/SPEC_APP.md (tamamı), docs/app/SPEC_APP_EK2.md (tamamı)
- docs/specs/SPEC_SCORING.md §5–§9; docs/specs_faz4/SPEC_CEILING_PATH_V0.md §5, §7
- Yukarıdaki görev dosyaları
- app/ kodu ve testleri. Kod, yeniden üretimde kaynak olarak KULLANILMAZ; yalnız denetlenir.

## Adımlar
0. Taban:
   - `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -3`, `git status --porcelain`
   - İzinli izlenmeyen dosya yalnız `docs/prompts/FAZ3_FABLE_APP_AUDIT.md`. Başka bir şey varsa DUR.
1. **Tam koşu (ölç).** Aşağıdakileri çalıştır. Her birinin test sayısı, süresi ve son satırları `ekler/test_runs.txt`'ye:
   - `bash app/scripts/test.sh`
   - `bash app/tests/e2e_freeze_tmp_repo.sh`
   - `bash app/tests/e2e_personal_isolation.sh`
   - `.venv/bin/pytest -q`

   Asıl repoda `git status --porcelain` koşudan önce ve sonra aynı olmalı. `registry/`, `data/`, `scores/` sha listeleri de önce ve sonra aynı olmalı.
2. **U-tablosu (U1–U52).** Her U için tek satır: şartname cümlesi (kısa) · test dosyası:fonksiyon · test gerçekten bunu sınıyor mu (EVET / KISMEN / HAYIR + neden) · sonuç.
   - Sadece adın varlığına bakma; assert'leri oku.
   - Boş geçen, koşulsuz atlanan (`BORSAI_REPO` yoksa atla gibi), sabit beklentiyle kendini doğrulayan ya da hesaplanıp kullanılmayan değişkenler bulgudur.
   - STAGE5'teki A5-1…A5-7 de aynı tabloya.
   - K1–K4 (`docs/prompts/FAZ3_FABLE_APP_SPEC.md` satır 142–145) için ayrı hüküm.
3. **Mutasyon denetimi.** `git clone --local` ile `/tmp/borsai_app_audit/` altına klon aç. Her mutasyonu ayrı uygula, ilgili testi koş, testin KIRMIZI olduğunu göster, geri al. En az şunlar:
   - (a) bir altın vektörde tek bir sayının son hanesi (U2 kırmızı mı)
   - (b) Rust'ta bir ridge katsayısının okunuşu ya da bir kırpma sınırı (golden kırmızı mı)
   - (c) `scores.json` fixture'ında n = 7 iken `live.cells` dolu (U24)
   - (d) `verdict = "geçiyor"` iken ci95 0'ı içeriyor (U24)
   - (e) ön uçta bir koşullu hesap komutuna beyanlı j'nin geçirilmesi (U52)
   - (f) git beyaz listesine `commit` eklenmesi (U32)
   - (g) senaryo yol bekçisinin kaldırılması (U27, tekli ve toplu dışa aktarma)
   - (h) bant fonksiyonunda Sicil ekranının `mode-scenario` döndürmesi (A5-1/A5-2)
   - (i) resmi görünümde `predict_all` çağrılması (U38)

   Kırmızı olmayan her mutasyon ÖNEMLİ ya da KRİTİK bulgudur. Klonda derleme ayrı `CARGO_TARGET_DIR` ister; süreyi raporla.
4. **Bağımsız parite örneklemi.** `borsai`'yi import eden kendi betiğinle (`/tmp` altında; altın dosyaları üreten `gen_golden.py`'yi KULLANMA), altın dosyalarda OLMAYAN en az 50 rastgele girdi üret. Bunları uygulamanın Rust yoluyla karşılaştır.
   - Rust yolu: klonda geçici bir test ya da mevcut `records_parity` düzeneği; asıl `app/`'e yazma.
   - 19 model, §1.3 kuralları, tolerans 1e-9.
   - Uç girdiler dahil: f3 yok, PB alanı eksik, eğitim aralığı dışı, kırpma sınırı.
   - Ayrıca asıl `registry/records/**` altındaki 7 resmi kaydın Rust ile paritesi (U6/U50) yeniden: kaç kayıt × kaç model, maks |Δ|.
5. **Değişmezler (kodu oku, gerekirse klonda dene).** Her biri için hüküm ve kanıt:
   - Uygulama skor hesaplamaz: TS ve Rust'ta bootstrap/ortalama/aralık üretimi yok; doğruluk panelindeki her sayı dosyadan.
   - İki terazi hiçbir yerde toplanmaz, ortalanmaz, tek hükümde birleşmez; koşullu skorlar koşulsuzla birleşmez.
   - "geçiyor" yalnız `verdict` alanından; n < 10'da hiçbir metrik ya da hüküm yok.
   - Beyan kuralı (U52 ve genel ilke): resmi olmayan girdiden (beyan, senaryo, elle f6, "varsayımsal j") türetilmiş hiçbir sayı resmi görünen bir yerde yok. Bu genel ilke, Sicil ve Doğruluk ekranlarının tamamında ve bantta ayrıca aranır.
   - Dondur akışı:
     - Asıl repoda yalnız kullanıcının bilerek çalıştırdığı `freeze` yazar.
     - Uygulama commit ya da push çalıştırmaz.
     - Kişisel kayıt `registry/` altına hiçbir yoldan düşemez. Denenecek yollar: sembolik bağ, `..`, büyük/küçük harf, `app_data_dir`'in repo altına ayarlanması.
   - Resmi görünüm yalnız kayıttan okur; kayıt INDEX'ten eskiyse eksik modeller uydurulmaz.
   - `scores.json` bütünlük denetimi fail-closed; sürüm uyumsuzluğunda kısmi gösterim yok.
   - Bant kuralı G1: hiçbir resmi ya da doğruluk görünümünde SENARYO yok; senaryo ekranlarında her zaman var.
6. **Ekran kontrolü.** `app/docs/screens/` altından en az 8 görüntüye bak: 04, 11b, 15, 16, 22, 25, 25c, 26. Gördüğün, şartnameyle ve README tablosundaki iddiayla uyuşuyor mu? Uyuşmayanları listele.
7. **identifier önerisi** (HANDOFF açık karar 3): `tr.borsai.app` kalsın mı?
   - Tauri'nin uyarısının macOS'ta gerçek bir sorun yaratıp yaratmadığını kanıtla ya da çürüt.
   - Değişirse kişisel kayıtların taşınma tarifini yaz.
   - Karar vermezsin; öneri yazarsın.
8. AUDIT.md ve commit.

## Hüküm biçimi
AUDIT.md'nin en başında:
- Genel hüküm, üç seçenekten biri:
  - **UYGUN**: gerçek arz dondurmasında uygulama kullanılabilir.
  - **DÜZELTMEYLE UYGUN**: listedeki düzeltmeler önce yapılmalı.
  - **UYGUN DEĞİL**: dondurma Python'dan yapılmalı; neden.
- 10 satırlık özet.
- Bulgu tablosu: # · önem (KRİTİK / ÖNEMLİ / KÜÇÜK) · alan · kanıt (dosya:satır ya da komut + çıktı) · düzeltme tarifi (dosya:satır, beklenen test).

KRİTİK: resmi sicile, skora ya da resmi görünen bir sayıya yanlış bilgi girebilir, ya da bir değişmez testsiz kırılabilir.

Sonra adım 1–7 sırasıyla. Ölçtüğünü **[ÖLÇTÜM]**, çıkarımını **[ÇIKARIM]** diye işaretle.

## Kurallar
- `app/`, `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `docs/` (kendi dizinin hariç), `tests/` salt okunur.
- Kişinin gerçek uygulama verisine (`~/Library/Application Support/tr.borsai.app/`) yazma, oradaki dosyaları açma. Testler için `BORSAI_DATA_DIR` ya da geçici dizin kullan.
- Dondur sihirbazını ya da `borsai.freeze`'i asıl repoda ÇALIŞTIRMA; yalnız klonda.
- `npm run tauri dev` ve `app/scripts/screens.sh` çalıştırma (pencere açar).
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma (`tests/test_outcome_guard.py`).
- `git add -A` yok. Commit:
  ```
  git add docs/fable_app_audit docs/prompts/FAZ3_FABLE_APP_AUDIT.md
  git commit -m "<mesaj>" -- docs/fable_app_audit docs/prompts/FAZ3_FABLE_APP_AUDIT.md
  ```
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Mesaj: `BORSAI_FAZ3_FABLE_APP_AUDIT: app conformity audit against SPEC_APP, EK2 and stage task decisions (U1-U52, mutation, parity sample)`
- Rapor Türkçe.

## Teslim (rapor)
- Commit hash'i ve `git show --stat`.
- Genel hüküm ve KRİTİK/ÖNEMLİ bulguların tek satırlık listesi.
- Test sayıları (cargo, vitest, e2e iki betik, pytest) ve süreler.
- Mutasyon tablosu: mutasyon · test · kırmızı mı.
- Parite örneklemi: girdi sayısı × model, maks |Δ|, uyuşmazlık sayısı; resmi kayıt paritesi.
- identifier önerisi (tek paragraf).

## Kabul kapısı
- K1 U-tablosu 52 + 7 satır eksiksiz; her satırda test dosyası:fonksiyon ve EVET/KISMEN/HAYIR.
- K2 En az 9 mutasyon koşuldu; her birinin sonucu komut çıktısıyla.
- K3 Parite örneklemi ≥ 50 yeni girdi × 19 model; `gen_golden.py` kullanılmadı.
- K4 Tam koşu sayıları ölçülmüş; asıl repoda `registry/`, `data/`, `scores/` değişmemiş, `git status` koşu öncesiyle aynı.
- K5 Commit yalnız `docs/fable_app_audit/` ve bu görev dosyası.

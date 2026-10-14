# TASK_ID: BORSAI_FAZ7_VERIFY_PROSPECTUS_20260925

Model: Opus 5.5 · yüksek. Klasör: ~/Desktop/BorsAi (yalnız okuma) ve `~/Desktop/BorsAi_codex/` (okuma + `verified_faz7/` altına yazma).
- **Ağ: açık** (KAP, SPK, Borsa İstanbul). Resmi kaynak önceliklidir.
- **Repoya HİÇBİR ŞEY yazılmaz, commit yok.** Bütün çıktılar `~/Desktop/BorsAi_codex/verified_faz7/` altına. Repo git'i yalnız okuma komutlarıyla ve `GIT_OPTIONAL_LOCKS=0` önekiyle.
- Paralel: bir Opus oturumu repoda `docs/prompts/FAZ7_HAZARD_V1_IMPL.md`'yi koşuyor ve commit atıyor. Ona dokunma.

## Bağlam
- 2020-01-01…2023-09-21 arasında listelenen 135 arzlık eski kohort için "düşenler" (hangi arzlar ilk günlerde düşüyor) keşfine aday özellikler gerekiyor. Mevcut `registry/oot/candidate_features/<T>.json` dosyalarında şu 7 alan 135/135 boş: `distribution_method`, `price_stability_planned`, `price_stability_days`, `issuer_lockup_days`, `shareholder_lockup_days`, `sector`, `participation_index_eligible`.
- Codex + GPT-6 Astra bunları izahname ve TSSD'den çıkardı: `~/Desktop/BorsAi_codex/BORSAI_FAZ7_CODEX_PROSPECTUS_B1…B4_20260925.json` (görevler `docs/prompts/FAZ7_CODEX_PROSPECTUS_B*.md`; alan tanımları orada). Codex'in betikleri ve indirmeleri `scripts/`, `sources/` altında olabilir.
- **Orkestratörün ölçtüğü Codex kapsaması** (OK / 135):

  | Alan | OK / 135 |
  |---|---|
  | `distribution_method` | 85 |
  | `price_stability_planned` | 99 |
  | `price_stability_days` | 93 |
  | `issuer_lockup_days` | 76 |
  | `shareholder_lockup_days` | 83 |
  | `sector` | 89 |
  | `participation_index_eligible` | 7 |

  Bütün arzlar PARTIAL. B4'te (2023) sektör 8/37 ve dağıtım yöntemi 17/37 zayıf.
- **Bu görevin iki işi:** (1) Codex'in her OK değerini resmi belgede **doğrulamak**; (2) boşları **doldurmak**. Önem sırası: dağıtım yöntemi, fiyat istikrarı (planlı mı, süre) > satmama taahhütleri > sektör > katılım endeksi uygunluğu.
- Aynı alanlar H99 için eski repo ana tablosunda var (`data/raw/HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv`: `distribution_method`, `price_stability_planned`, `price_stability_days`, `issuer_lockup_days`, `shareholder_lockup_days`, `sector`). **Değer biçimini ve kategori adlarını H99 tablosuyla uyumlu tut** (ör. dağıtım yöntemi kategorileri; sektör adlandırması). Bu tabloyu yalnız biçim için oku; H99 arzlarına başka bir amaçla bakma. Eşleme kuralını raporda yaz.

## SONUÇ KÖRLÜĞÜ (kesin kural)
- Bu 135 şirketin **ilk işlem gününden sonraki hiçbir fiyat, getiri, tavan/taban, hacim ya da performans bilgisine bakma, yazma, özetleme.** THB/THM bültenleri indirilmez. Haber, forum, aracı kurum performans raporu ve fiyat sayfası açılmaz.
- İzahnamenin finansal tablo ve değerleme bölümleri bu görevin kaynağı değildir.
- KAP listelerinde listeleme sonrası bildirim başlıkları istemeden görülürse `verified_faz7/EXPOSURE.md`'ye yaz (ticker + ne görüldü, değer yazmadan). Codex'in 8 `exposure_log` satırını da oraya aynen taşı.
- Belge yayın zamanı (KAP sunucu zamanı) ilk işlem gününden (İstanbul) ÖNCE olmalı; değilse o belge kaynak olamaz.

## Çıktı düzeni
```
~/Desktop/BorsAi_codex/verified_faz7/
  candidate_features_faz7/<T>.json    # yalnız 7 alan; kayıt biçimi registry/oot/candidate_features/<T>.json'daki gibi
  source_docs/<T>/MANIFEST.json       # her belge: url, tür (IZAHNAME/TSSD/…), kap_notice_id, published_at, accessed_at, sha256, bytes, pages
  source_docs/<T>/<id>_*.pdf          # resmi kaynaktan YENİDEN indirilmiş belgeler (repoya alınmayacak; bkz. not)
  REPORT.md, EXPOSURE.md, coverage.csv, verification_log.jsonl
```
- Her alan kaydı şunları taşır: `value`, `unit`, `status` (VERIFIED / CORRECTED / FILLED / MISSING), `source_url`, `source_type`, `kap_notice_id`, `published_at`, `source_sha256`, `page`, `quote` (belgeden birebir), `ocr` (true/false), `provenance` (`CODEX_VERIFIED` / `CODEX_CORRECTED` / `CLAUDE_VERIFIER_FILLED`), `note`. MISSING ise `missing_reason` ve bakılan yerler.
- **Not (repo boyutu):** izahnameler büyük. Repoya daha sonra yalnız `candidate_features_faz7/*.json` ve `source_docs/<T>/MANIFEST.json` (URL + sha + yayın zamanı + sayfa) alınacak; PDF'ler repo dışında kalır ve gerektiğinde URL'den yeniden indirilip sha ile eşlenir. Bu yüzden her belgenin URL'si ve sha256'sı eksiksiz olmalı.

## Adımlar
0. Codex JSON'larını ve görev dosyalarını oku. `docs/specs_faz6/ekler/evren_listesi.csv` (135 MEMBER) ile ticker/tarih eşleşmesini göster.
1. **Doğrulama:** Codex'in her OK değeri için belgeyi resmi URL'den yeniden indir; Codex'in yerel kopyası varsa sha'yı karşılaştır. sha256'yı pinle, değeri metinde bul (metin katmanı yoksa OCR), KAP yayın zamanını doğrula. Sonuç VERIFIED, CORRECTED ya da UNVERIFIABLE (UNVERIFIABLE değer kullanılmaz, MISSING'e düşer).
2. **Doldurma:** önce TSSD (kısa, hızlı), sonra izahname. KAP'ta şirketin listeleme öncesi bildirimleri, dar tarih pencereleri (SPK onayı ile ilk işlem günü arası). Borsada satış arzlarında dağıtım yöntemi "borsada satış" olarak yazılabilir, ama kaynağı alıntılanır.
3. **Denetim:**
   - `coverage.csv` (ticker × alan: VERIFIED / CORRECTED / FILLED / MISSING).
   - Rastgele 10 arzda (`random.Random(20260925)`) bütün alanları baştan ikinci kez kontrol et.
   - Her dosya kendi içinde tam olmalı (yarım dosya bırakma).
4. **`REPORT.md`:**
   - alan başına kapsama (Codex önce / sonra);
   - Codex doğruluk oranı (VERIFIED / CORRECTED / UNVERIFIABLE);
   - kategori eşleme kuralları (H99 ile uyum);
   - kalan boşlukların nedenleri;
   - maruziyet (sayı ve satırlar);
   - toplam belge sayısı ve boyutu;
   - süre ve istek sayısı.
   
   Hangi arzın kasada olduğunu bilmiyorsun ve bilmeye çalışma.

## Tek oturumda bitmezse
Yapılan kısmı yaz; `REPORT.md`'de kalan listeyi ver.

## Kurallar
- Resmi olmayan kaynak değer kaynağı olamaz. Şirket ya da aracı kurum sitesindeki kopya yalnız KAP'ta yoksa ve `secondary: true` ile kullanılabilir.
- Tahmin, türetme, ortalama ya da ilişki analizi YOK. Özellik–sonuç ilişkisine bakma.
- Repo içinde hiçbir dosya değişmez (`git status` önce/sonra aynı; paralel oturumun kendi değişiklikleri hariç).
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- KAP API'sinde istekler arasında 3–4 s bekle, 429'da geri çekil.
- Rapor Türkçe.

## Kabul kapısı
- **K1** 135 ticker için `candidate_features_faz7/<T>.json` var; her alan bir durum taşıyor.
- **K2** Her dolu değer resmi, pinlenmiş, listeleme öncesi yayımlanmış bir belgede birebir bulunuyor.
- **K3** Kapsama ve Codex doğruluk oranı raporlandı; boşlukların nedenleri yazılı.
- **K4** Sonuç körlüğü korundu; `EXPOSURE.md` var.
- **K5** Repoda hiçbir dosya değişmedi.

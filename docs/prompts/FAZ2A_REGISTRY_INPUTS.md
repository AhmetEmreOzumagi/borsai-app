# TASK_ID: BORSAI_FAZ2A_REGISTRY_INPUTS_20260922

Model: Opus 5, akıl yürütme yüksek/Extra. Çalışma klasörü ~/Desktop/BorsAi; ek dizin ~/Desktop/Halka_Arz_Modeli (arşiv, salt okunur). push/tag/amend yok.

## Bağlam

Faz 1 modelleri dondurulup push edildi: model commit'leri 5fa849d (Faz 1A) ve b09cab5 (Faz 1B), uzak depoda HEAD 1869da6. Fable denetimi: docs/fable_conformity_20260922/AUDIT.md, bütün modeller PUSH_OK.

Bu task Faz 2'nin ilk yarısıdır:
- Tahmin sicili ve payda kurulur.
- 2026-08-07'den bu yana listelenen arzların listeleme öncesi girdileri resmi belgelerden toplanır.
- Bu arzlar için bütün kayıtlı modellerin tahmin kayıtları üretilir.

**Bu task'ta hiçbir arzın gerçekleşen sonucu (THB/THM, fiyat, getiri) repoya GİRMEZ ve okunmaz.** Tahmin kayıtlarının commit'i, sonuç verisinin commit'inin atası olmalı (SPEC_SCORING §5). Sonuçlar Faz 2B'de, bu commit push edildikten sonra gelir.

ÖNCE OKU: CLAUDE.md; docs/specs/SPEC_SCORING.md (tamamı; özellikle §4, §5, §6); docs/specs/SPEC_MARKET20_V0.md §5–§6 (canlı f6 ve XU100 güncellemesi); docs/MODELS.md; models/INDEX.json; borsai/predict*.py; registry/legacy_frozen/ ve docs/PROVENANCE.md §3.

## Adımlar

### 1. Push kanıtı (önce bu)

- Eski repodaki `scripts/modeling/emit_true_live_push_proof.py` yöntemini `borsai/push_proof.py`'ye taşı. Yöntem: GitHub commit status API ile sunucu zaman damgası (`created_at`). Kimlik doğrulama `gh` CLI (`gh api`) ya da `GH_TOKEN` ile.
- Şu commit'ler için kanıt üret ve `registry/push_proofs/<sha>.json` olarak yaz:
  - 5fa849d
  - b09cab5
  - 1869da6
- Kimlik doğrulama yoksa (`gh auth status` başarısız ve `GH_TOKEN` yok): bu adımı atla, kodu ve testini yaz, raporda proje sahibinin çalıştıracağı tek komutu ver. Diğer adımlara devam et.

### 2. Payda: registry/ipos.csv (SPEC_SCORING §4)

- Sütunlar ve status değerleri şartnamedeki gibi.
- Bilinen 7 arz: CITAS, VEYAS, TKNKA, KPEKS, INTET, BKRGY, NETGL.
- 2026-08-07'den bugüne kadar Borsa İstanbul Pay Piyasası'nda halka arzla ilk kez işlem görmeye başlayan BAŞKA pay var mı? Resmi kaynaklardan ara: SPK bültenleri ve KAP. Fiyat verisi olmadan: işlem görmeye başlama duyurusu, SPK onayı, talep toplama sonuç bildirimi. Bulduklarını ekle.
- ilk işlem tarihi (first_trading_date) resmi duyurudan alınır; kaynak kimliğiyle birlikte.
- Emin olamadığın kayıt varsa raporda listele.

### 3. Girdiler (listeleme öncesi resmi belgelerden)

Her arz için `registry/inputs/<TICKER>.json`. Alanlar:
- V1.5 ve tavan modelinin girdileri: ipo_price_tl, shares_offered (kesin satış), post_ipo_share_capital, capital_increase_shares, existing_share_sale_shares, total_demand_multiple (+ origin, filter_status), additional_sale_shares.
- PB modellerinin girdileri (SPEC_PB_V0; talep toplama öncesi planlanan yapı).
- Tarihler: bookbuilding tarihleri, first_trading_date.
- **Her alan için:** kaynak belge kimliği (KAP bildirim no / SPK belge), yayın zamanı, belgenin sha256'sı (inputs_pit_ok, SPEC_SCORING §5). Yayın zamanı ilk işlem gününden önce olmalı.

Kaynak sırası:
1. registry/legacy_frozen/ içindeki dondurma sözleşmeleri (NETGL, BKRGY, INTET, TKNKA).
2. Eski repodaki kaynak belgeler (inputs/prospective/<TICKER>/ vb.).
3. Gerekirse ağdan YALNIZ kap.org.tr ve spk.gov.tr'deki listeleme öncesi belgeler. İndirilen belgeler `registry/source_docs/<TICKER>/` altına, sha256'larıyla.

Eski repodaki CITAS/VEYAS/KPEKS replay dosyalarında gerçekleşen değerler var. Oradan yalnız GİRDİ alanlarını al; gerçekleşen alanları kopyalama, rapora yazma.

Bir alan resmi belgede yoksa boş bırak. Model o alanı istiyorsa hücresi "ret + neden" olur. Hiçbir modelin çalışamadığı arz için ipos.csv'ye SKIPPED / INPUTS_NOT_AVAILABLE yazılır. Tahmin etme, türetme, ikincil kaynaktan doldurma yok.

### 4. XU100 güncellemesi (SPEC_MARKET20_V0 §6)

- 2026-08-19 sonrası XU100 kapanışlarını resmi BIST uç noktasından indir. Eski pinli dosyayla aynı kaynak ve biçimde olmalı.
- Eski 9682 kaydın birebir örtüştüğünü doğrula.
- Yeni dosyayı `data/raw/` altına pinle ve PROVENANCE.md'ye ekle.
- XU100 bir arz sonucu değildir, sıra kuralının kapsamında değildir. Ama bu task'ta THB/THM ve pay fiyatı indirmek YASAK.

### 5. Kayıt yazıcı: borsai/freeze.py

`python -m borsai.freeze registry/inputs/<TICKER>.json` şunu üretir: `registry/records/<TICKER>/<UTC-zaman>_<kısa-sha>.json`.

İçerik (CLAUDE.md kural 1):
- Girdiler ve input_sha256.
- `models/INDEX.json`'daki kayıtlı TÜM modellerin çıktıları; ret edenler için ret kodu ve nedeni.
- Her modelin parametre sha256'sı.
- Kayıt zamanı, git HEAD, borsai kaynak sha'sı, schema_version.

Kurallar:
- Dosya yeniden yazılmaz. Aynı arz için ikinci kayıt ancak açık bir iptal kaydıyla yapılır.
- Birincil kayıt seçimi SPEC_SCORING §6'ya göre.
- Legacy dondurmalar (registry/legacy_frozen) sicile rolleriyle bağlanır, şartnamedeki gibi.

Kayıt yazıcı ileride masaüstü uygulamasının "dondur" düğmesi tarafından da kullanılacak. Arayüzü sade tut (girdi JSON → kayıt dosyası).

### 6. Kayıtlar

2. adımdaki her arz için kayıt yaz. Bunlar sınıf olarak büyük olasılıkla LATE_RECORD olacak; sınıf Faz 2B'de tarihlerden hesaplanır, burada etiketlenmez.

### 7. Testler

- Kayıt yazıcı: bütün modeller kayıtta; ret hücreleri; üzerine yazma reddi; iptal kaydı.
- ipos.csv şeması.
- inputs_pit_ok: her girdi alanında kaynak + yayın zamanı < ilk işlem günü.
- XU100 örtüşme testi.
- Push kanıtı dosya biçimi.
- Bir koruma testi: repoda 2026-08-19 sonrası THB/THM ya da post-08-06 arz sonuç değeri yok.
- Eski testlerin hepsi yeşil.

## Kurallar

- models/, tests/reference/, legacy/, docs/specs/ DEĞİŞMEZ.
- THB/THM, pay fiyatı ve getiri: indirme ve okuma YOK. Ağ yalnız kap.org.tr, spk.gov.tr ve XU100 uç noktası (borsaistanbul.com) için; ayrıca GitHub API (push kanıtı).
- Commit'e yalnız: borsai/, tests/, registry/, data/raw/ (XU100), docs/PROVENANCE.md, docs/prompts/FAZ2A_REGISTRY_INPUTS.md. `git add -A` YOK.
- Tek commit. Mesaj: "BORSAI_FAZ2A: prediction registry, IPO denominator, pre-listing inputs and records for all registered models (no outcomes)". Push yok.

## Teslim (rapor)

- Commit hash'i ve `git show --stat` özeti.
- Push kanıtları: hangi commit'ler, `created_at` değerleri; yapılamadıysa proje sahibinin çalıştıracağı komut.
- ipos.csv içeriği: her arz, ilk işlem tarihi, status.
- Arz × model tablosu: tahmin var mı, ret mi (ret kodu).
- Toplanamayan girdi alanları ve nedenleri.
- XU100: yeni kayıt sayısı, son tarih, örtüşme sonucu.
- Test sonuçları.
- Belirsizlikler ve verdiğin kararlar.

## Kabul kapısı

- K1 Repoda hiçbir post-08-06 arz sonucu ve 2026-08-19 sonrası THB/THM yok (tarama ile kanıt).
- K2 Her kayıt bütün kayıtlı modelleri içeriyor; her girdi alanı kaynak belge + yayın zamanıyla.
- K3 ipos.csv şartnameye uygun; bilinen 7 arzın hepsi içinde.
- K4 Testler yeşil; models/ ve golden ledger'lar değişmedi.
- K5 Push, tag, amend yok.

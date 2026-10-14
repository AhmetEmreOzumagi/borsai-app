# Görev: halka arz sonuç belgelerinden karar dosyası (decisions/<T>.json)

Çalışma dizini: `W=/private/tmp/claude-501/-Users-ahmet-Desktop-BorsAi/9acfa5c4-64b4-4bce-a540-5cecbabfcf80/scratchpad/w`
(her komutta `cd $W &&` ile başla). Yalnız bu dizinde çalış; **yalnız `decisions/` altına yaz.**

## Kesin kurallar
1. **Ağ YOK.** Web'e, KAP'a, arama motoruna gitme. Yalnız yerel `dossier/<T>.md` dosyasını ve araçları kullan.
2. **Sonuç körlüğü:** Bu şirketlerin ilk işlem günü sonrasına ait hiçbir fiyat/getiri/tavan/hacim bilgisi arama, yazma, tahmin etme. Belgeler zaten listeleme öncesidir.
3. **Uydurma yok, tahmin yok, ikincil kaynak yok.** Her değer, dosyada metni verilen resmi belgede birebir yazılı olmalı. Alıntıları (`quote`) belge metninden **harfi harfine** kopyala (satır sonları boşluk sayılır; kesme işaretleri ’ ' gibi karakterler aynı kalmalı). Emin değilsen `python3 qfind.py <T> <SOURCE_ID> '<regex>' [önek_uzunluğu]` ile metinde ara; çıktıdaki metni kopyala.
4. Değer biçimi: metin; binlik noktası atılır, ondalık virgül noktaya ("1.451.243.670" → "1451243670"; "26,3" → "26.3"). Yüzde işareti yazılmaz.
5. Her dosyayı yazdıktan sonra `python3 check_decision.py <T>` çalıştır; **OK** olana kadar düzelt. OK olmadan bırakma.
6. Örnek: `decisions/TRILC.json` (elle yazılmış, denetimden geçmiş). Aynı şemayı kullan.

## `source_id` biçimi
Dossier başlıklarındaki kimlikler: `KAP_<id>` (bildirimin kendisi), `KAP_<id>_EK<n>` (ek). SPK bülteni için `SPK` (bunu genellikle kullanmana gerek yok).

## Alanlar ve tanımlar
Hepsi `fields` altında; bulunamayan alan `{"value": null, "missing_reason": "<neden: hangi belgeye bakıldı, ne yok>"}`.

**total_demand_multiple** (toplam talep katı, f3 — en önemli alan)
- Belge toplam katı açıkça yazıyorsa ("toplam halka arz büyüklüğünün 26,3 katı", "toplamda 2,84 katı talep"): `origin: "SOURCE_REPORTED"` ("yaklaşık" deniyorsa `"SOURCE_REPORTED_APPROX"`), `quote` sayıyı içermeli.
- Kat yazılmıyor ama **aynı belgede** toplam talep ile arz edilen toplam **aynı birimde** (nominal/adet/lot ↔ nominal/adet/lot; ya da TL tutar ↔ TL tutar) yazılıysa: `origin: "CALCULATED_FROM_SOURCE_TOTALS"`, `numerator`, `numerator_quote`, `denominator`, `denominator_quote`; `value` = pay/payda, 10 ondalığa ROUND_HALF_UP, sondaki sıfırlar atılır (denetçi hesabı kontrol eder). Pay = bütün yatırımcı gruplarının toplam talebi (tablonun "Toplam" satırındaki talep sütunu ya da metindeki toplam talep). Payda = belgede yazan arz edilen toplam; `denominator_includes_additional_sale` true/false/null yaz.
- **Yapma:** grup katlarını birleştirme/ortalama alma; "talebi karşılanan" (dağıtılan) miktarı talep sayma; farklı belgelerden pay ve payda birleştirme; SPK yıllık tablosu ya da başka bir özet kullanma.
- Belge yalnız **alt/üst sınır** veriyorsa ("27 katın üzerinde", "X kattan fazla"): kesin kat değildir → `value: null`, `missing_reason: "BOUND_ONLY: ..."` ve alıntıyı `evidence` alanına yaz. Talep toplama sürerken verilen ara bilgi ("ilk gün itibarıyla ...") da kesin toplam değildir.
- Belge toplam katı açıkça yazıyorsa **her zaman** onu al (SOURCE_REPORTED); yeniden hesaplama yapma (paydası ek satışı içermese bile; `denominator_includes_additional_sale` ile işaretle).
- Hesaplıyorsan payda = belgede yazan **nihai gerçekleşen arz** nominali (satılan/dağıtılan toplam; ek satış kullanıldıysa dahil; arz eksik satıldıysa satılan miktar) — H99 kuralı. Planlanan/satışa sunulan farklıysa onunla hesaplanan değeri `note`'a yaz.
- `definition`: kısa metin (ör. "belgedeki toplam kat" ya da "TOPLAM_TALEP_NOMINALI_x / HALKA_ARZ_EDILEN_NOMINAL_PAY_y").
- Borsada satış (Borsa Birincil Piyasa) arzlarında sonuç bildirimi çoğunlukla yalnız dağıtımı verir; kat ya da toplam talep yoksa `value: null`, `missing_reason: "SALE_METHOD_ON_EXCHANGE_NO_BOOKBUILD_MULTIPLE: <belge> yalnız dağıtım/başvuru sayısı veriyor"`.
- Sonuç belgesi hiç yoksa: `missing_reason: "NO_RESULT_DOCUMENT_IN_WINDOW: ..."` ve üst düzeyde `"needs_search": true`.

**total_demand_filter_status**: `"UNFILTERED"` yalnız belge açıkça "filtrelenmemiş/filtre edilmemiş" diyorsa (alıntıyla); `"FILTERED"` yalnız belge katın filtrelenmiş talep olduğunu açıkça söylüyorsa (alıntıyla); aksi `"NOT_SPECIFIED"` (alıntısız, `source_id` f3'ün belgesi). Belge hem filtrelenmiş hem filtrelenmemiş toplam veriyorsa f3 için **filtrelenmemiş** olanı al, `UNFILTERED` yaz, filtrelenmişi `note`'a yaz. f3 null ise bu alan da null + `missing_reason: "f3 yok"`.

**ipo_size_tl**: yalnız belge gerçekleşen arzın TL tutarını açıkça yazıyorsa ("halka arz büyüklüğü 234.500.000 TL", "50.025.000 TL tutarlı ... payların"). Fiyat × pay HESAPLAMA.

**Genel:** toplama/çıkarma ile türetme YAPMA (ortakların tek tek tutarlarını toplamak, "satılan − taban" vb.); belgede tek sayı olarak yazılı değilse null. Tek istisna f3 oranı. `existing_share_sale_shares` ek satışı İÇERMEZ (H99: shares_offered = sermaye artırımı + ortak satışı + kullanılan ek satış); belge ortak satışını ek satış dahil tek sayı veriyorsa null + neden.

**capital_increase_shares / existing_share_sale_shares**: yalnız sonuç belgesi sermaye artırımı (yeni pay) ve ortak satışı (mevcut pay) nominalini ayrı ayrı açıkça yazıyorsa. Yazmıyorsa null + `missing_reason: "sonuç belgesinde ayrım yok"` (planlanan ayrımın taşınmasına ayrı kural karar verecek; sen taşıma yapma).

**additional_sale_shares** (kullanılan ek satış nominali): belge açıkça yazıyorsa değer; belge "ek satış yapılmamıştır/kullanılmamıştır" diyorsa "0"; belgedeki satılan toplam SPK satırındaki planlanan tabana (Bedelli + Mevcut Pay Satışı) eşitse "0" + `"zero_from_statement": true` + `note`; satılan toplam = taban + planlanan ek satış ise değer = ek satış nominali + `"derived": true, "formula": "satılan toplam − planlanan taban"` + alıntı satılan toplamı içersin. SPK satırında ek satış "-" ise ve belge toplamı tabana eşitse yine "0" (`zero_from_statement`). Belirsizse null.

**full_sale_statement**: belgenin arzın tamamının satıldığını / toplam satılan nominali söyleyen cümlesi `{"source_id", "quote"}`; yoksa `null`.
**additional_sale_usage_statement**: ek satışın kullanılıp kullanılmadığını gösteren cümle `{"source_id", "quote", "used": "NONE"|"FULL"|"PARTIAL"}`; yoksa `null`.

### Aday özellikler (model girdisi değil; aynı titizlik)
- **investor_count**: tek sayı; `semantic`: `"ALLOCATED_INVESTOR_COUNT"` (dağıtım yapılan / talebi karşılanan) tercih; yalnız talep eden sayısı varsa `"APPLICANT_COUNT"`. İkisi de varsa ALLOCATED'ı yaz, diğerini `note`'a.
- **investor_count_by_group**: `{"retail": "...", "domestic_institutional": "...", "foreign_institutional": "...", ...}` (belgede olan gruplar; yabancı bireysel vb. ek anahtarla: "foreign_retail", "unregistered"), `semantic` aynı; `quote` liste olabilir.
- **retail_demand_multiple / domestic_institutional_demand_multiple / foreign_institutional_demand_multiple**: grup başına belgede yazan kat (ya da aynı belgede o grubun talep ve tahsisat nominali yazılıysa `derived: true` + `formula`; hesap 10 ondalık).
- **distributed_by_group**: grup başına dağıtılan nominal (sözlük).
- **retail_allocation_pct / domestic_institutional_allocation_pct / foreign_institutional_allocation_pct**: gerçekleşen dağıtım oranı (%) — `semantic: "REALIZED_DISTRIBUTION_SHARE"`; yalnız planlanan tahsisat varsa `"PLANNED_ALLOCATION"`.
- **distribution_method**: belgedeki ifade (ör. "Eşit Dağıtım", "Oransal dağıtım", "bireysel yatırımcılara eşit dağıtım"); metin değer.
- **lead_broker**: halka arza aracılık eden / konsorsiyum lideri aracı kurum adı (belgede yazıldığı gibi).
- **price_stability_planned** ("true"/"false"), **price_stability_days**, **issuer_lockup_days**, **shareholder_lockup_days**: TSSD pencerelerinde açıkça varsa. Süre "1 yıl", "365 gün", "180 gün" vb. yazılabilir: gün yazılıysa sayı; "1 yıl" ise "365" + `"derived": true, "formula": "1 yıl = 365 gün"`.
- **sector**, **participation_index_eligible** ("true"/"false"): yalnız belgede açıkça varsa.
Candidate alanlarda da `source_id` + `quote` zorunlu.

## `codex_check`
Dossier'deki "Codex değerleri" listesinde durumu OK/PARTIAL olan ve değeri "BULUNAMADI" olmayan her alan için (yalnız şu alanlar: total_demand_multiple, ipo_size_tl, capital_increase_shares, existing_share_sale_shares, additional_sale_shares ve yukarıdaki aday alanlar):
`{"codex_value": "<Codex'in yazdığı>", "verdict": "FOUND_SAME" | "FOUND_DIFFERENT" | "NOT_FOUND_IN_DOCS" | "NOT_APPLICABLE", "note": "..."}`.
- FOUND_SAME: senin değerin Codex'inkiyle sayısal olarak aynı ve belgede var.
- FOUND_DIFFERENT: belgede başka değer yazıyor (senin değerin `fields`'ta; farkı `note`'a yaz).
- NOT_FOUND_IN_DOCS: Codex'in değeri eldeki belgelerde yok (Codex'in alıntısının belgede olup olmadığını qfind ile kontrol et).
- NOT_APPLICABLE: Codex'in değeri SPK/listeleme tablosundan (ör. planlanan ayrım) ve sonuç belgesi ayrım yazmıyor.

## Çıktı
`decisions/<T>.json`: `{"ticker", "reviewed_by", "result_docs_seen": [...], "fields": {...}, "codex_check": {...}, "notes": "...", "needs_search": false}`.
Bitince her ticker için tek satır özet ver: `T: f3=<değer|null (neden)> · ayrım=<var/yok> · denetim OK`.

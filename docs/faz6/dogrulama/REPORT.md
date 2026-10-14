# BORSAI_FAZ6_VERIFY_CODEX_INPUTS_20260924 — Rapor

Doğrulayıcı: Claude Code (Opus 5.5). Süre: 2026-09-24 20:05–22:05 (İstanbul). Repoya hiçbir şey yazılmadı; bütün çıktılar `~/Desktop/BorsAi_codex/verified/` altında.

## 0. Özet
- **135/135** `registry/oot/inputs/<T>.json` yazıldı; hepsi repo doğrulayıcısından geçiyor: `validate_inputs(doc) == []` ve `inputs_pit_problems(doc, root=verified, as_of=<ilk işlem günü>T00:00:00+03:00) == []` (135/135, `_tools/logs/validate_result.json`).
- Her dolu alanın değeri, resmi URL'den **yeniden indirilmiş**, sha256'sı pinlenmiş, ilk işlem gününden önce KAP'ta ya da SPK bülteninde yayımlanmış bir belgede **birebir alıntıyla** bulunuyor. Bağımsız denetim (`audit_outputs.py`): 135/135 girdi ve 135/135 aday dosyası sorunsuz (alıntı belgede, sha eşleşiyor, dosya MANIFEST'te, yayın < ilk işlem günü).
- **f3 (toplam talep katı): 72 → 130/135.** Kalan 5 boşluk 2020'nin borsada satış arzları (4'ü belgede kat/toplam talep yok, DNISI yalnız "27 katın üzerinde" alt sınırı veriyor).
- **Sermaye ayrımı: 135/135** (sermaye artırımı ve ortak satışı); 66/42'si sonuç belgesinde açıkça yazılı, gerisi DATA_NOTES §2 taşıma kuralıyla ya da SPK tablosundaki '-' ile.
- **PB planlanan yapı: ~61 → 133–135/135** (8 alanın 7'si 135/135, `planned_post_ipo_capital` 133/135). PB modelleri 112 arzda çalışabiliyor (12 saf ortak satışı → pb3 aralık reddi, 9 fiyat aralığı, 2 eksik alan).
- **Codex doğruluğu (girdi alanları):** Codex'in verdiği 1.702 değerin 1.675'i (%98,4) birebir doğrulandı; 17'si yalnız hassasiyet farkı (aynı pay/payda, 2 ondalığa yuvarlanmış), 8'i değer/tanım düzeltmesi, 2'si doğrulanamadı.
- Rastgele 10 arzda (tohum 20260924) 200 girdi alanı baştan ikinci kez kontrol edildi: **200/200 doğru**, düzeltme gerekmedi.
- Maruziyet: THB/THM hiç istenmedi; listeleme sonrası bildirim başlığı görülmedi; SPK bülteni kesitlerinde 28 üyenin listeleme sonrası kurumsal işlem satırları (fiyat/getiri değil) göründü → `EXPOSURE.md`.

## 1. Yöntem
1. **Evren eşleşmesi.** `docs/specs_faz6/ekler/evren_listesi.csv`'deki 135 MEMBER ile Codex'in 4 partisindeki 135 ticker birebir aynı; ilk işlem günleri 135/135 eşit. GMTAS `OUT_OF_SCOPE`, işlenmedi.
2. **KAP belge keşfi.** Her üyenin `[talep toplama başlangıcı − 7 gün, ilk işlem günü − 1]` penceresi `byCriteria` ile 3 günlük parçalarla (≤ 1.509 satır; 2.000 sınırına hiç yaklaşılmadı) sorgulandı; yanıt bellekte süzüldü (EXPOSURE §2). Seçilen roller: BIST "Payların İşlem Görmeye Başlaması" (listeleme), aracı kurum/şirket sonuç ÖDA'ları (+ekleri), TSSD (+ekleri). Codex'in andığı KAP kimlikleri de eklendi. İki sistematik boşluk bulunup kapatıldı: (a) "ilgili şirket" alanı boş yayımlanmış sonuç/TSSD bildirimleri unvanla eşleştirildi (11 ticker; OYYAT'ın tek sonuç belgesi böyle); (b) listeleme öncesi geçici kodla yayımlanmış belgeler (ENERY → "ENRYA"; A1CAP izahnamesi grup şirketi kodlarıyla) hedefli sorguyla bulundu.
3. **İndirme ve pin.** KAP bildirimi PDF'i (`api/BildirimPdf/<id>`), bildirim sayfası (yayın zamanı `publishDate` + ek listesi; eki olmayan bildirimde liste API zamanı), ekler (`api/file/download/<id>`, Java sarmalı açıldı; ham sarmalın sha'sı da MANIFEST'te). SPK bültenleri: 2020–2023'ün **299 bülteninin tamamı** SPK "geçmiş yıllara ait bültenler" sayfalarından (`?s=N` sayfalaması; ekteki dizin 2021-H2/2022-H1/2023-H1'de eksikti) indirildi.
4. **Metin.** Metin katmanı (pdfplumber); harf sayısı düşük sayfada Apple Vision OCR (doğru mod, tr-TR). Toplam 523 pinli belgenin 417'si metin katmanlı, 106'sı OCR (1 sayfası yüksek çözünürlüklü OCR: A1CAP izahnamesi s.83, imza/kaşe yüzünden).
5. **Değer çıkarma.** Listeleme alanları (fiyat, satılan nominal, sermaye, tarihler) ve SPK A.1 satırı programla; SPK sütunları sözcük x-koordinatlarından (120 satır otomatik, 15 satır sayfa görüntüsüyle elle; 133 satır `Yeni = Mevcut + Bedelli + Bedelsiz` özdeşliğini geçiyor, 2 istisna §7). Sonuç belgesi alanları (f3, filtre, arz büyüklüğü, ayrım, ek satış, aday özellikler) 6 alt ajan partisiyle; her karar dosyası `check_decision.py` ile denetlendi (her alıntı belge metninde birebir, değer alıntıda, hesaplanan katın aritmetiği, Codex kontrol listesi tam). Doğrulayıcı kural dışı türetmeleri (toplama/çıkarma) sonradan boşalttı (`postprocess.py`; 7 alan) ve 3 kararı düzeltti (GENIL: belgede yazan kat; MERCN: payda kuralı; DNISI: alt sınır → boş); ULUFA'da ek satış dahil ortak satışı boşaltıldı.
6. **Kurulum.** `build_outputs.py` her ticker için girdi JSON'u, aday özellik JSON'u, `source_docs/<T>/` (+`MANIFEST.json`) yazar; Codex değeriyle karşılaştırıp `provenance` koyar.

Kaynak belge adları: `KAP_<id>_bildirim.pdf`, `KAP_<id>_ek<n>.pdf`, `SPK_BULTEN_<yyyy>-<no>.pdf`. `MANIFEST.json`: `source_id, file, sha256, bytes, url, published_at, published_at_basis, accessed_at_utc, kind, text_layer` (+ ek adı, Java sarmalı sha'sı, bülten tarihi).

## 2. Alan başına kapsama (önce = Codex OK+PARTIAL; sonra = doğrulanmış dolu)

| Alan | Önce | Sonra | VERIFIED | CORRECTED değer (+yalnız hassasiyet) | FILLED | UNVERIFIABLE | MISSING |
|---|---|---|---|---|---|---|---|
| ipo_price_tl | 135 | 135 | 135 | – | – | – | – |
| shares_offered | 135 | 135 | 135 | – | – | – | – |
| post_ipo_share_capital | 134 | 135 | 134 | – | 1 | – | – |
| capital_increase_shares | 66 | 135 | 66 | – | 69 | – | – |
| existing_share_sale_shares | 59 | 135 | 56 | 3 | 76 | – | – |
| **total_demand_multiple (f3)** | **72** | **130** | 54 | 1 (+17) | 58 | – | 5 |
| total_demand_filter_status | 72 | 130 | 68 | 4 | 58 | – | 5 |
| additional_sale_shares | 76 | 132 | 74 | – | 58 | 2 | 1 |
| ipo_size_tl | 68 | 108 | 68 | – | 40 | – | 27 |
| ipo_price_try | 61 | 135 | 61 | – | 74 | – | – |
| planned_pre_ipo_capital | 57 | 135 | 57 | – | 78 | – | – |
| planned_post_ipo_capital | 57 | 133 | 57 | – | 76 | – | 2 |
| planned_capital_increase_shares | 61 | 135 | 61 | – | 74 | – | – |
| planned_existing_share_sale | 61 | 135 | 61 | – | 74 | – | – |
| planned_base_offer_shares | 61 | 135 | 61 | – | 74 | – | – |
| planned_additional_sale_ceiling | 61 | 135 | 61 | – | 74 | – | – |
| planned_max_offer_shares | 61 | 135 | 61 | – | 74 | – | – |
| first_trading_date / bookbuilding_start / _end | 135 | 135 | 135 | – | – | – | – |

Aday özellikler (`candidate_features/<T>.json`, model girdisi değil):

| Alan | Önce | Sonra | VERIFIED | CORRECTED | FILLED | UNVERIFIABLE | MISSING |
|---|---|---|---|---|---|---|---|
| investor_count | 66 | 135 | 37 | 29 | 69 | – | – |
| investor_count_by_group | 45 | 134 | 23 | 21 | 90 | 1 | – |
| retail / domestic_inst / foreign_inst demand_multiple | 37 / 39 / 20 | 86 / 85 / 55 | 37 / 39 / 19 | – | 49 / 46 / 36 | – / – / 1 | 49 / 50 / 79 |
| distributed_by_group | 45 | 134 | 43 | 1 | 90 | 1 | – |
| retail / domestic_inst / foreign_inst allocation_pct | 45 / 44 / 37 | 133 / 132 / 80 | 43 / 41 / 26 | – / 1 / 1 | 90 / 90 / 53 | 2 / 2 / 10 | – / 1 / 45 |
| distribution_method | 55 | 0 | – | – | – | 55 | 80 |
| lead_broker | 59 | 121 | 53 | – | 68 | 6 | 8 |
| price_stability_planned / _days, issuer_ / shareholder_lockup_days, sector, participation_index_eligible | 0 | 0 | – | – | – | – | 135 |
| market, sale_method | 135 | 135 | 135 | – | – | – | – |

Notlar: `investor_count` düzeltmelerinin tamamı tanım farkı (Codex başvuran sayısını, doğrulayıcı H99 tanımıyla **dağıtım yapılan** sayıyı yazdı; ikisi de belgede, diğeri `note`'ta). `distribution_method`: Codex'in 55 değeri ("Sabit Fiyatla Talep Toplama…") satış/fiyat belirleme yöntemidir, dağıtım yöntemi değildir; sonuç belgeleri dağıtım yöntemini adlandırmıyor → hepsi boş.

## 3. Codex doğruluk oranı
| Grup | Codex'in değer verdiği hücre | VERIFIED | CORRECTED (yalnız hassasiyet) | CORRECTED (değer/tanım) | UNVERIFIABLE |
|---|---|---|---|---|---|
| V1.5 alanları (9) | 817 | 790 (%96,7) | 17 | 8 | 2 |
| PB alanları (8) | 480 | 480 (%100) | – | – | – |
| Tarihler (3) | 405 | 405 (%100) | – | – | – |
| **Girdi toplamı** | **1.702** | **1.675 (%98,4)** | **17** | **8** | **2** |
| Aday özellikler | 762 | 631 (%82,8) | – | 53 | 78 |

Değer/tanım düzeltmeleri (girdi): filtre durumu 4 (FORTE, GRTRK, KTLEV: belge "filtre edilmemiş" diyor, Codex NOT_SPECIFIED; PCILT: Codex filtrelenmiş kabul edilen talebin katını (4,1) almış, belge filtrelenmemiş toplamı da yazıyor → 47.964.575 / 11.490.659); PCILT f3; ortak satışı 3 (TEZOL ve ULUFA'da Codex ek satışı ortak satışına katmış; PRDGS'de Codex tek ortağın ek satış payını yazmış); HTTBT arz büyüklüğü yalnız binlik ayırıcı biçimi (sayısal olarak aynı; VERIFIED sayıldı). Hassasiyet düzeltmeleri: 17 hesaplanmış f3'te Codex aynı pay/paydayı 2 ondalığa yuvarlamış; H99 emsali (`CALCULATED_FROM_SOURCE_TOTALS`) 10 ondalık. Doğrulanamayan 2: BRLSM ve PRDGS ek satış nominali belgede tek sayı olarak değil ortak başına yazılı (toplama türetme sayıldı, alan boş).
Codex'in yerel kopyaları: 124 PDF'in 124'ü yeniden indirilen belgeyle sha256 eşit. BIST listeleme bildirimleri: 135/135 evren listesindeki pinle sha256 eşit.

## 4. Model başına girdisi tam olan arz sayısı (repo kodu `borsai.features` ile hesaplandı)
| Model | Gerekli | Tam | Not |
|---|---|---|---|
| `v1_5_h99`, `v1_6_h99`, `v1_5_market20_v0` (f3 isteyen V1.5 ailesi) | fiyat, satılan pay, arz sonrası sermaye, sermaye artırımı, f3 | **130** | `compute_features` 135/135 hatasız; f3 5 arzda yok (RET F3_MISSING). 6 arzın f3'ü FILTERED (BRLSM, ENSRI, INVES, MAREN, MIATK, VBTYZ): eğitim modu NOT_SPECIFIED olduğundan `f3_filter_status_conflict` reddi tetiklenmez ama DATA_NOTES §5 anlamında farklı tanımdır. `v1_5_market20_v0` ayrıca f6 (XU100) ister — girdi dosyasında değil. |
| `ceiling_hazard_v0`, `ceiling_path_v0` (+@INF) | f1, f2, f3 | **130** | aynı 5 boşluk. Tavan yolu modellerinin dönem fiyat adımı uygulanabilirliği (şartname §7-R3) bu görevin konusu değil. |
| `pb_v0`, `pb_ceiling_v0`, `pb_ceiling_path_v0` | 8 planlanan alan + özdeşlikler + tek fiyat | **112** | `compute_pb_features` reddi: PB3_RANGE 12 (saf ortak satışı, planlanan sermaye artırımı 0: ARASE BASGZ DAPGM GWIND KLRHO KONKA KTSKR KZBGY MACKO MAKIM MTRKS TEZOL), PB_PRICE_RANGE 9 (ANGEN ARZUM AYDEM BIOEN HTTBT KLKIM KRVGD MERCN PENTA), PB_FIELD_MISSING 2 (AKFYE, PRDGS). |
| Kural tabanlı karşılaştırıcılar | ipo_price_tl | 135 | |

## 5. f3 ayrıntısı (K3)
- Kapsama: **130/135**. Yıla göre: 2020 3/8, 2021 52/52, 2022 38/38, 2023 37/37. Satış yöntemine göre: borsa dışı talep toplama 86/86, borsada satış 44/49.
- Köken: `SOURCE_REPORTED` 86, `SOURCE_REPORTED_APPROX` 4 ("yaklaşık"), `CALCULATED_FROM_SOURCE_TOTALS` 40 (aynı belgede toplam talep ve nihai gerçekleşen arz nominali yazılı; 10 ondalık ROUND_HALF_UP; alanda `numerator/denominator` alıntılarıyla, `derived: true`).
- Filtre durumu: NOT_SPECIFIED 67, UNFILTERED 57, FILTERED 6. Belge hem filtrelenmiş hem filtrelenmemiş toplam veriyorsa filtrelenmemiş olan alındı (PCILT). ENSRI'de "mükerrer başvuruların ayıklanması" FILTERED sayıldı.
- Payda: `denominator_includes_additional_sale` true 19, false 92, belirsiz 24. Kural: belge katı açıkça yazıyorsa **o değer** (paydası ek satış hariç olsa bile, ör. GENIL 6,7); hesaplanıyorsa payda = belgede yazan nihai gerçekleşen arz (ek satış dahil; eksik satışta satılan miktar — H99 `…_DIVIDED_BY_FINAL_OFFER_SHARES` emsali; MERCN'de dağıtılan 18.456.982). Diğer paydayla hesaplanan değer alanın `note`'unda.
- **5 boşluğun nedenleri:**
  - ARDYZ (KAP_816932), BAYRK (KAP_848583), ESEN (KAP_878967), FADE (KAP_864170): 2020 borsada satış; aracı kurum sonuç bildirimi yalnız dağıtım tablosu ve talebi karşılanan başvuru sayısı veriyor; toplam talep ya da kat yazılı değil (`SALE_METHOD_ON_EXCHANGE_NO_BOOKBUILD_MULTIPLE`). BIST'in KAP'taki birincil piyasa duyuruları yalnız satışın açılışı/devamıdır (sonuç duyurusu yok).
  - DNISI (KAP_872779): belge yalnız "27 katın üzerinde" diyor (ikinci talep günü itibarıyla, alt sınır) → `BOUND_ONLY`, değer girilmedi; alıntı `evidence` alanında.

## 6. Sermaye ayrımı ve ek satış
- `capital_increase_shares`: sonuç belgesinde açık 66; taşınan 68 (DATA_NOTES §2 `PLANNED_SPLIT_CARRIED_FULL_SUBSCRIPTION` 45; `…FULL_BASE_PLUS_STATED_ADDITIONAL_SALE` 21: taban tamamen satılmış + kullanılan ek satış belgede yazılı; `…PLUS_FULL_ADDITIONAL_SALE` 2: belge ek satışın tamamen kullanıldığını yazıyor); SPK Bedelli '-' (yeni pay yok) 1 (KTSKR, eksik satılmış saf ortak satışı).
- `existing_share_sale_shares`: açık 42; taşınan 92; SPK '-' 1. H99 tanımı: ek satış hariç (shares_offered = artırım + ortak satışı + kullanılan ek satış). Taşıma koşulları her alanın `carry_conditions`'ında alıntılarıyla.
- `additional_sale_shares`: 132 dolu (74 Codex'le aynı). "0" değerlerinin çoğu `zero_from_statement` (satılan = planlanan taban) ya da SPK '-'. Boş 3: BRLSM, CONSE, PRDGS (ek satış kullanıldı ama tek sayı olarak yazılı değil; toplama/çıkarma yapılmadı). Bu yüzden bu 3 arzda ayrım toplamı satılan paydan ek satış kadar küçük (tutarlı).
- Satılan nominal = ayrım toplamı denetimi: bu 3 arz dışında hepsi tutuyor.

## 7. PB (planlanan yapı) ayrıntısı
- 135/135 arzın SPK A.1 satırı bulundu (onay tarihindeki bülten; 2021-H2 için evren listesinde onay tarihi boş → unvan eşleşmesi). Bütün bülten tarihleri talep toplama başlangıcından önce (`pit_pb.ok` 135/135).
- `source_published_at` = bültenin basılı tarihi `T23:59:59+03:00` (gün sonu üst sınırı; `published_at_basis: SPK_BULTEN_BASILI_TARIH_GUN_SONU_UST_SINIR`). Neden: 2022'deki site göçü yüzünden eski bültenlerin URL ObjectId'si ve `Last-Modified` göç zamanını (2022/2025) gösteriyor. PIT denetimleri tarih düzeyinde yapıldığından yeterli; saat düzeyi kanıt gerekirse aynı yapı TSSD/izahnamede (KAP zamanlı) var.
- SPK tablosunda Ek Pay Satışı hücresi **boş** (tire yok) olan 5 arzda (HKTM, GRTRK, KTLEV, A1CAP, ENERY) `planned_additional_sale_ceiling = 0` onaylı izahnamenin §25.2.5 beyanından ("Ek satış işlemlerine ilişkin bilgi: Yoktur." / ENERY: "Ek satış planlanmamaktadır."), talep toplamadan önce KAP'ta yayımlanmış parçadan (H99 BESTE emsali). İzahname parçası kaynak olarak pinlendi.
- Boş 2: PRDGS (bültende "196.00.000" yazım hatası; talep öncesi başka belgede bulunamadı), AKFYE (Yeni Sermaye '-'; izahnamenin OCR metninde birebir alıntılanabilir beyan yok). Türetme yapılmadı.
- `ipo_price_try` fiyat aralıklı arzlarda belgedeki yazımla (ör. "8.50-9.90", "11.50 – 12.50") → PB modelleri `PB_PRICE_RANGE` reddi verir (şartname §4).

## 8. Kalan boşluklar ve nedenleri
| Alan | Boş | Neden |
|---|---|---|
| total_demand_multiple (+filtre) | 5 | §5 |
| ipo_size_tl | 27 | Sonuç belgesi gerçekleşen TL tutarı yazmıyor; fiyat × pay hesaplanmadı (`borsai.features` f1'de zaten fiyat × pay'a düşer): ADGYO ARDYZ ARZUM AYDEM BAYRK BIOEN BMSTL BYDNR CANTE CONSE DNISI EKSUN ESEN EUREN FADE GOKNR KLKIM KRPLS KRVGD NTGAZ OFSYM PENTA SELVA TARKM TEZOL UNLU YYLGD |
| planned_post_ipo_capital | 2 | §7 |
| additional_sale_shares | 3 | §6 |
| Aday: fiyat istikrarı, satmama taahhüdü (ihraççı/ortak), sektör, katılım endeksi uygunluğu | 135 | 2020–2023 TSSD'leri kısa biçim (3–10 sayfa, çoğu taranmış) ve bu bilgileri içermiyor; bilgi yalnız izahnamede (100–350 sayfa, çoğu taranmış, parça parça). Öncelik sırası gereği izahnameler toplu indirilip OCR edilmedi (yalnız 6 arzda §25.2.5 için tek parça). **Kalan iş** (§12). |
| Aday: distribution_method | 135 | Sonuç belgeleri dağıtım yöntemini adlandırmıyor (Codex'in 55 değeri satış yöntemi). İzahname §25.2.3'te var — kalan iş. |
| Aday: grup katları / yabancı kurumsal oran | 49–79 | Borsada satışlarda grup tahsisatı yok; bazı belgeler grup katı ya da yabancı grubu vermiyor. |
| Aday: lead_broker | 14 | Belge birden çok aracı kurum sayıp lider belirtmiyor ya da TSSD penceresinde yok. |

## 9. Doğrulayıcı notları
- Koşulan kontroller: `borsai.registry.validate_inputs` ve `inputs_pit_problems(root=verified, as_of=ilk işlem günü 00:00 İstanbul)`; 135/135 boş liste. Repo kodu değiştirilmedi; çağrı `PYTHONDONTWRITEBYTECODE=1` ile, repo dışından yapıldı.
- Uygulanamayan koşul: `SCOPE_START = 2026-08-07` yalnız `validate_ipos`'ta (ipos.csv); girdi doğrulayıcısında yok, bu yüzden etkilemedi. Eski kohort için `registry/oot/cohort_pre_h99.csv` doğrulaması (şartname §10) henüz kodda yok; bu görev ona dokunmadı.
- Girdi dosyalarında CITAS biçimine ek anahtarlar: dosya düzeyinde `cohort`, `sale_method`, `market` (+ INVES'te `notes`); alan düzeyinde `provenance`, `codex_value`, `codex_status`, `correction_kind`, `filled_by`, `carry_rule`, `carry_conditions`, `derived`, `formula`, `numerator(_quote)`, `denominator(_quote)`, `zero_from_statement`, `unit_expansion`, `pit_pb`, `checked_sources`, `evidence`. Doğrulayıcı bunları yok sayar. `regime_tags` ve `vault` şartname §4'e göre kohort dosyasından gelecek; bu görevde yazılmadı.
- Boş alanların `provenance`'ı: `MISSING` (Codex de bulamamış) ya da `CODEX_UNVERIFIABLE` (+`codex_value`).
- INVES: BIST bildiriminin yapılandırılmış "İşlem Görmeye Başlayacağı Tarih" alanı "01/03/2021" (yazım hatası); açıklama metni "01/03/2022 tarihinden itibaren" → açıklama cümlesi kaynak, not düşüldü.
- ESEN: sermaye "64 milyon TL" yazımıyla → `unit_expansion` notu.

## 10. Rastgele 10 arzda ikinci kontrol (tohum 20260924)
Seçim: `random.Random(20260924).sample(sorted(135 ticker), 10)` → AKFYE, EKSUN, AZTEK, PSGYO, KIMMR, MOBTL, RUBNS, KZGYO, MAKIM, IHAAS. Her birinin BIST bildirimi, SPK satırı ve sonuç belgesi metni doğrulayıcı tarafından baştan okundu, 20 girdi alanı tek tek karşılaştırıldı; aday özellikler (katılımcı sayıları, grup katları, dağıtım, oranlar, aracı kurum) belgeyle tarandı.
Sonuç: **200/200 girdi alanı doğru**, düzeltme yok. Gözlemler: AKFYE'de `planned_post_ipo_capital` kural gereği boş (§7); AZTEK'te "filtrelenmemiş" ifadesi yalnız grup katları için geçtiğinden toplam kat NOT_SPECIFIED; RUBNS'te aynı gün üç sürüm var, son düzeltme esas alınmış; PSGYO'da yabancı kurumsal grup katı aynı tablodan hesaplanmış (`derived`, aday alan).

## 11. Süre, istek sayısı, iş bölümü
- Süre: ~2 sa (20:05–22:05).
- İstekler (günlüklü, `_tools/logs/requests.jsonl`): **1.954** — KAP 1.543 (`byCriteria` 394, `BildirimPdf` 455, bildirim sayfası 339, ek indirme 355), SPK 411 (299 bülten + eksik dizinle başlatılıp durdurulan ilk koşunun ~100 yinelenen indirmesi + liste sayfaları). Durum: 200 × 1.944, 429 × 5 (geri çekilmeyle tekrarlandı), bağlantı sıfırlama × 4, zaman aşımı × 1. Ek olarak başlangıçta günlük dışı 6 deneme isteği (curl). KAP istekleri arası ≥ 3,5 s (dosya kilitli ortak zamanlayıcı), 429'da üstel geri çekilme.
- Alt ajanlar: 6 inceleme partisi + 1 gözden geçirme (toplam ~2,4 M alt ajan tokeni); hepsi ağsız, yalnız karar dosyası yazdı; her karar `check_decision.py` ile, sonra doğrulayıcının son işlemi ve 10 arzlık elle kontrolüyle denetlendi.

## 12. Kararlar gerektiren noktalar ve kalan iş
1. **Kalan iş (aday özellikler):** izahnamelerin §23–25 bölümlerini (fiyat istikrarı, satmama taahhütleri, dağıtım yöntemi, faaliyet/sektör) 135 arz için indirip OCR etmek. Tahmini yük: arz başına 1–3 parça × 50–110 sayfa OCR.
2. `ipo_price_tl` ve `shares_offered` için birincil kaynak BIST listeleme bildirimi alındı (şartname §4 sonuç bildirimini öne koyar). Gerekçe: tek şablon, KAP sunucu zamanı, 135/135 aynı biçim; değerler SPK fiyatı ve (ajanların Codex kontrolüyle) sonuç belgeleriyle tutarlı.
3. SPK bülteni yayın anı gün sonu üst sınırıyla yazıldı (§7). Onaylanırsa kalsın; saat düzeyi isteniyorsa TSSD/izahname KAP zamanı eklenebilir.
4. FILTERED f3'li 6 arz (§4) ve payda tanımı karışıklığı (DATA_NOTES §5) aynen H99'daki gibi alan düzeyinde işaretli; model bu farkı görmez.
5. `_tools/` repoya alınacak kopyanın parçası değildir (betikler, alt ajan karar dosyaları, istek ve sorgu günlükleri; denetim izi için).
6. `source_docs/` boyutu 196 MB (girdi kaynakları 142 MB, yalnız aday özelliklerin kaynağı 62 MB; en büyükleri §25.2.5 için pinlenen izahname parçaları, 2,7–4,9 MB). Repoya alırken aday kaynaklarının ayrı tutulması düşünülebilir.
7. SPK bülten kesitlerindeki listeleme sonrası kurumsal işlem satırları (EXPOSURE §3) sonuç bilgisi değildir; kasa üyeliğine etkisi orkestratörün kararı.

## 13. Kabul kapısı
- **K1** ✓ 135/135 `inputs/<T>.json`; doğrulayıcı temiz; eksik alanlar `null` + `missing_reason`.
- **K2** ✓ Her değer resmi, sha256 pinli, listeleme öncesi yayımlanmış belgede birebir alıntıyla; `provenance` her alanda dolu (bağımsız denetim 135/135).
- **K3** ✓ f3 kapsaması 130/135; 5 boşluğun her birinin nedeni §5'te ve alanın `missing_reason`'ında.
- **K4** ✓ THB/THM indirilmedi; `EXPOSURE.md` var (boş değil; §2–§3).
- **K5** ✓ Repoda bu görevden değişiklik yok: `git status` başlangıçtaki durumla aynı, farklar yalnız paralel oturumun commit'leri (23b6479 MANIFEST, 8e3a623 skorlar) — son kontrol bu raporun yazılmasından sonra yapıldı.

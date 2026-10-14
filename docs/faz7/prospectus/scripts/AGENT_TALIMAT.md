# Görev: izahname/TSSD'den 7 aday alan — karar dosyası `decisions/<T>.json`

Çalışma dizini: `W=/Users/ahmet/Desktop/BorsAi_codex/verified_faz7/_tools` — her komutu `cd $W/scripts && ...` ile çalıştır.
**Yalnız `$W/decisions/<T>.json` yaz.** Başka dosya oluşturma/değiştirme; repo (`~/Desktop/BorsAi`) ile hiç ilgilenme.

## Kesin kurallar
1. **Ağ YOK.** KAP'a, web'e, arama motoruna gitme; `curl`/`wget`/tarayıcı yok. Belgeler zaten indirildi ve metinleri çıkarıldı. Yalnız `dossier/<T>.md` ve aşağıdaki araçlar.
2. **Sonuç körlüğü:** Bu şirketlerin ilk işlem günü sonrasına ait hiçbir fiyat/getiri/tavan/taban/hacim bilgisini arama, yazma, tahmin etme. İzahnamenin finansal tablo ve değerleme (fiyat tespit) bölümleri bu görevin kaynağı değildir. Dossier'de "(ek: denetim/değerleme/hukukçu vb. — kaynak olarak kullanma)" işaretli belgeler (bağımsız denetim raporu, fiyat tespit/değerleme raporu, hukukçu raporu, esas sözleşme, iç yönerge, sorumluluk beyanı) değer kaynağı olamaz. Geçerli kaynaklar: izahname ana metni (İBD, SPAN, Özet, "İzahname 1-50" vb. parçalar), TSSD, Borsa İstanbul birincil piyasa duyurusu, izahnamenin taahhüt eki ("… tarafından verilen taahhütler") ve "Katılım Finans İlkeleri Bilgi Formu" eki.
3. **Uydurma, tahmin, türetme yok.** Her dolu değer, bu tickerın belgelerinden birinde birebir yazılı bir ifadeye dayanır. Alıntı (`quote`) **araçların bastığı normalize metinden harfi harfine** kopyalanır (OCR hataları dahil; düzeltme yapma). Alıntı, değerin dayandığı ifadeyi (ör. "30 gün", "1 (bir) yıl", "eşit dağıtım") içermeli.
4. Başka bir arzın bilgisini bu arza taşıma. Belgeler içinde başka şirketlere (ör. bağlı ortaklık, grup şirketi) ait ifadeleri ihraççınınki sanma.
5. Her dosyadan sonra `python3 check.py <T>` çalıştır; **OK** olana kadar düzelt.

## Araçlar
- `cat $W/dossier/<T>.md` — belgeler listesi (source_id, rol, KAP yayın zamanı, sayfa, OCR), Codex değerleri, alan başına otomatik aday pasajlar. Aday pasajlar eksik olabilir.
- `python3 qfind.py <T> '<regex>' [bağlam] [SOURCE_ID]` — bütün belgelerde (ya da tek belgede) büyük/küçük harf duyarsız arama; çıktıdaki metin denetçinin karşılaştırdığı metindir.
- `python3 page.py <T> <SOURCE_ID> <sayfa> [...]` — sayfanın tam normalize metni. Sayfa = PDF dosyasındaki 1 tabanlı sıra.
- `python3 check.py <T>` — denetçi.
- Bir sayfanın metni bozuk/boşsa (ör. yalnız damga, ters metin, "i.i" / "~" / "1" dolu harfler) ve o sayfada aradığın bölüm olmalıysa: `/Users/ahmet/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 reocr.py <T> <SOURCE_ID> <sayfa>` (yerel OCR, ağ yok) sonra `page.py` ile yeniden oku. Bazı sayfalarda metin katmanı zaten OCR ile değiştirildi; eski metin arka planda "alt_text" olarak durur, denetçi ikisini de kabul eder ama **yeni alıntıları güncel metinden** al.
- Örnek (elle yazılmış, denetimden geçmiş): `$W/decisions/ARDYZ.json`.

## Nereye bakılır
- 2020–2021 üç parçalı izahname: "İhraççı Bilgi Dokümanı" (faaliyet), "Sermaye Piyasası Aracı Notu" (SPAN: §5.1–5.2 tahsis ve dağıtım esasları, §6.5 fiyat istikrarı, §7.3 dolaşımdaki payın artırılmamasına ilişkin taahhütler a) ihraççı b) ortaklar c) SPK mevzuatı d) yetkili kuruluş), "Özet".
- Tek parçalı izahname (2021+; KAP'ta çok sayıda parça "İzahname 1-50", "İzahname 2.Bölüm"...): faaliyet §6 civarı ve Özet; halka arz bölümleri sonda (§23–§27: tahsis/dağıtım esasları, fiyat istikrarı, dolaşımdaki pay taahhütleri).
- TSSD: çoğu kısa (izahnameye atıf); uzun TSSD'lerde dağıtım esasları, fiyat istikrarı, satmama taahhütleri yazılı olabilir.
- `BIST_BIRINCIL` (Borsa İstanbul "Payların Borsa Birincil Piyasada Halka Arzı" duyurusu) Borsa'da satış arzlarında satış/dağıtım usulünü yazabilir.
- Belgeler çelişirse listeleme öncesi en son yayımlanan belgeyi esas al (ör. TSSD/izahname değişikliği), çelişkiyi `note`'a yaz.

## Alanlar ve H99 biçimi (değerler METİN)
**distribution_method** — yatırımcı gruplarına dağıtım yöntemi. Kanonik biçim (H99 ana tablosuyla uyumlu):
- Borsa'da satış, belge grup tahsisatı/dağıtımı olmadığını söylüyor ve eşit/oransal adlandırmıyor → `Borsa İstanbul Birincil Piyasa; yatırımcı grubu bazında tahsisat ve dağıtım yapılmadı`
- Borsa'da satış, grup tahsisatı yok, belge dağıtımın eşit (oransal) yapılacağını yazıyor → `Borsa'da satış; yatırımcı grubu tahsisatı yok; eşit dağıtım` (… `; oransal dağıtım`)
- Borsa'da satış ama gruplara tahsisat var → `Borsa'da satış; ` + aşağıdaki talep toplama biçimi (ör. `Borsa'da satış; yurt içi bireysele eşit; kurumsala oransal dağıtım`)
- Talep toplama (borsa dışı): `<eşit gruplar> eşit; <oransal gruplar> oransal dağıtım`, grup adları: `Yurt içi bireysel`, `çalışanlar` (ihraççı/grup çalışanları), `yüksek başvurulu` (yüksek başvurulu yurt içi bireysel), `kurumsal` (bütün kurumsal gruplar aynı yöntemdeyse; farklıysa `yurt içi kurumsal` / `yurt dışı kurumsal`). Örnekler: `Yurt içi bireysele eşit; kurumsala oransal dağıtım` · `Yurt içi bireysel ve çalışanlara eşit; kurumsala oransal dağıtım` · `Yurt içi bireysele eşit; yüksek başvurulu ve kurumsala oransal dağıtım` · `Tüm gruplara oransal dağıtım` · `Tüm gruplara eşit dağıtım`.
- Bir grubun dağıtımı ihraççı/yetkili kuruluş/halka arz eden ortak kararına (takdirine) bırakılmışsa o grup için `takdire bağlı` kullan: ör. `Yurt içi bireysele eşit; kurumsala takdire bağlı dağıtım` · `Yurt içi bireysel ve çalışanlara oransal; kurumsala takdire bağlı dağıtım`. Kimin takdiri olduğunu `note`'a yaz.
- Belge yalnız yurt içi bireysel grubun yöntemini yazıyorsa: `Yurt içi bireysel yatırımcılara eşit dağıtım` (oransal ise `… oransal dağıtım`).
- Kalıba uymayan yapı: aynı üslupta kısa metin + `note`'ta açıklama. `note`'a grup grup belgedeki ifadeyi yaz. Birden fazla cümle gerekiyorsa `extra_quotes` kullan.
- Satış yöntemini ("Sabit Fiyatla Talep Toplama") dağıtım yöntemi sanma; dağıtım yöntemi belgede yoksa ve grup tahsisatı da yoksa ilk kalıbı kullan; talep toplamada yöntem hiç yazmıyorsa `null`.

**price_stability_planned** — `TRUE` belge fiyat istikrarı işlemlerinin yapılabileceğini/planlandığını söylüyorsa; `FALSE` "Yoktur", "planlanmamaktadır" vb. diyorsa. Alıntı "Fiyat istikrarı işlemlerinin planlanıp planlanmadığı" başlığını ve cevabını içermeli (mümkünse).

**price_stability_days** — süre (gün, tam sayı). "30 gün" → `30`. Planlanmamışsa `0` (H99 biçimi) ve alıntı planlanmadığını gösteren cümle (planned ile aynı alıntı olabilir). "1 ay" gibi yazılmışsa ay × 30 ve `note`'a "belgede '1 ay'". Süre yazılmıyorsa `null`. Süre "iş günü" ise değer sayı ve alana `"unit": "iş günü"` ekle. Birim sözcüğü mühür altında kalıp OCR'da bozuksa (ör. "30 (otuz) g) inaür") ve sayı parantezli yazısıyla okunuyorsa değeri yaz, `note`'a "birim mühür altında" yaz (doğrulayıcı sayfa görüntüsünü kontrol edecek).

Halka arz teşvikleri / "Günlük Alım Emri Taahhüdü" (ortak ya da ihraççının borsada birkaç gün alım emri vermesi) fiyat istikrarı işlemi DEĞİLDİR; fiyat istikrarı başlığı "Yoktur" diyorsa `FALSE`, teşviki `note`'a yaz.

**issuer_lockup_days** — ihraççının (şirketin) kendi taahhüdünün süresi (bedelli sermaye artırımı yapmama / dolaşımdaki payı artırmama / pay satmama). "1 (bir) yıl" → `365`; "6 ay" → `180`; "2 yıl" → `730`; 12'nin katı ay yıl sayılır ("12 ay" → `365`, "24 ay" → `730`), diğer aylar ay × 30 ("18 ay" → `540`); gün yazılıysa aynen. Belge "a) İhraççı tarafından verilen taahhüt: Yoktur" diyorsa `0` + o alıntı. İhraççının farklı süreli birden fazla taahhüdü varsa **bedelli sermaye artırımı yapmama (dolaşımdaki payı yeni pay ihracıyla artırmama)** süresi esas alınır; diğerleri (kendi paylarını satmama, bedelsiz artırım, geri alım) `note`'a. Kapsam ve istisnalar `note`'a.

**shareholder_lockup_days** — mevcut ortakların pay satmama taahhütleri (gönüllü "b) Ortaklar tarafından verilen taahhütler" + mevzuat gereği "c) Sermaye piyasası mevzuatı kapsamında verilen taahhütler", ör. Pay Tebliği 8/1 "1 yıl halka arz fiyatının altında borsada satmama", 9/3 satışa hazır bekletilen paylar). **Yetkili kuruluş/aracı kurum (yüklenici) taahhütleri ortak taahhüdü DEĞİLDİR** — hariç. Değer = herhangi bir mevcut ortağın **borsada satış kısıtının ilk gevşediği gün**: `FIYAT_ALTI`/`MUTLAK` bileşenlerin en kısası, ancak aynı ortağın daha uzun ve en az o kadar sıkı (MUTLAK ≥ FIYAT_ALTI) bir kısıtı tarafından kapsanan bileşen hesaba girmez (ör. aynı ortakta MUTLAK 180 + MUTLAK 365 → 365; MUTLAK 540 + FIYAT_ALTI 365 → 540; MUTLAK 180 + FIYAT_ALTI 365 → 180); `DIGER` bileşenler (yalnız borsa dışı satış/virman/özel emir/rehin kısıtı) listede kalır ama değeri belirlemez. **i-SPK.128.21 (20/412) ilke kararı taahhütleri:** metin "borsada satışı da kapsayacak şekilde" ya da "borsada veya borsa dışında satmayacak" diyorsa borsada satışı da yasaklar → `MUTLAK` (başlangıç çoğu zaman izahname onay tarihi; `start`'a yaz); yalnız "borsa dışında satmama, virmanlamama, özel emir/toptan satış" diyorsa → `DIGER`. Zorunlu `components` listesi: her taahhüt için `{"who", "days", "type": "FIYAT_ALTI"|"MUTLAK"|"DIGER", "basis": "GONULLU"|"MEVZUAT ...", "start"}`. `type`: halka arz fiyatının altında satmama → `FIYAT_ALTI`; borsada hiç satmama / "dolaşımdaki pay miktarını (tedavülü) artıracak şekilde satmama" → `MUTLAK`; başka (ör. yalnız rehin/devir kısıtı) → `DIGER`. Değerin süre ifadesi alıntılarda görünmeli. Ortak taahhüdü hiç yoksa (b ve c "Yoktur") `0`. Ortağın halka arzda/teşvik kapsamında **sonradan aldığı** paylar için verdiği satmama beyanı mevcut paylara ilişkin değildir → `components`'e katma, `note`'a yaz. Taahhüt metninde süre yazmıyor ama aynı izahnamenin başka yerinde (ör. risk faktörleri, özet) o ortağın taahhüt süresi açıkça yazıyorsa oradan alıntıla.

**sector** — ihraççının ana faaliyet alanı, kısa Türkçe ifade, cümle başı büyük (H99 örnekleri: `Yenilenebilir enerji üretimi`, `Gayrimenkul yatırım ortaklığı`, `Hazır beton ve yapı malzemeleri`, `Elektronik bileşen dağıtımı`, `Gıda sanayi; un, bakliyat, irmik, bisküvi ve makarna üretimi`, `Demir-çelik üretimi`, `Turizm işletmeciliği`). Alıntı: ihraççının ana faaliyetini söyleyen cümle ("… ana faaliyet konusu … dır", "… alanında faaliyet göstermektedir"). Değer alıntının özeti olmalı; alıntıda olmayan bilgi ekleme.

**participation_index_eligible** — 2022 ortasından itibaren izahnamenin baş kısmındaki **Borsa İstanbul görüşü** şu tür bir cümle içerir: "Katılım Finans İlkeleri Bilgi Formu'nda … verilen bilgiler dikkate alındığında, Şirket paylarının … işlem görmeye başladığı tarihte BIST Katılım Tüm Endeksinde yer alma şartlarını sağladığının (ya da sağlamadığının) değerlendirildiği …". Bu, açık uygunluk beyanıdır: "sağladığı" → `TRUE`, "sağlamadığı" → `FALSE`; alıntı bu cümleyi (sonucu içeren kısmı) içermeli. Önce `qfind.py <T> 'Katılım Tüm Endeks|yer alma şartlarını|katılım endeks'` ile ara. Aksi hâlde: `TRUE` yalnız belge ihraççının/paylarının katılım endeksine, faizsiz finans (İslami finans) ilkelerine uygun olduğunu açıkça söylüyorsa (ör. uygunluk/icazet görüşü, "katılım endeksine dahil edilme kriterlerini karşılamaktadır"); `FALSE` yalnız açıkça uygun olmadığını söylüyorsa. Katılım bankalarından talep toplanması, aracı kurum adı vb. uygunluk beyanı DEĞİLDİR. Beyan yoksa `null`, `missing_reason: "belgede beyan yok ..."`. 2022 ve sonrası arzlarda izahname genellikle ekler listesinde "Katılım Finans İlkeleri Bilgi Formu"nu (ya da benzer adla) anar: form belge setinde varsa oku (formun sonucunu/uygunluk beyanını alıntıla; form yalnız soru-cevap tablosuysa ve açık "uygundur/uygun değildir" sonucu yoksa `null` + ne yazdığını `note`'a); form izahnamede anılıyor ama belge setinde yoksa `missing_reason`'a **"FORM_EKTE_YOK: <izahnamedeki ek adı/numarası>"** yaz (doğrulayıcı ayrıca indirecek).

## Karar dosyası şeması
```json
{"ticker": "T", "reviewed_by": "ajan-<ad>",
 "fields": {
   "<alan>": {"value": "metin", "source_id": "KAP_<id>_EK<n>", "page": 12, "quote": "birebir",
              "extra_quotes": [{"source_id": "...", "page": 13, "quote": "..."}],   // isteğe bağlı
              "components": [...],   // yalnız shareholder_lockup_days
              "note": "..."},
   "<alan>": {"value": null, "missing_reason": "neden; hangi belgelerde hangi aramalar", "looked_at": ["KAP_...", "..."]}
 },
 "codex_check": {"<alan>": {"codex_value": "...", "verdict": "FOUND_SAME|FOUND_DIFFERENT|NOT_FOUND_IN_DOCS", "note": "..."}},
 "notes": "..."}
```
7 alanın hepsi `fields` altında olmalı.

## `codex_check` (dossier'de status=OK olan her Codex alanı için zorunlu)
- `FOUND_SAME`: Codex'in değeri belgeyle çelişmiyor ve aynı kanonik değere/kategoriye eşleniyor (yalnız yazım/biçim farkı: `true`→`TRUE`; planlanmamışta `""`→`0`; "enerji üretimi" ≈ "Yenilenebilir enerji üretimi"; Codex dağıtım alanına satış yöntemini yazmış ama belge grup tahsisatı yok diyorsa Borsa'da satış kategorisi aynı).
- `FOUND_DIFFERENT`: belge başka bir değer söylüyor (ör. Codex 180, belge 365; Codex "oransal", belge bireysele "eşit"; sektör yanlış şirket/bağlı ortaklık). Senin değerin `fields`'ta; farkı `note`'a yaz.
- `NOT_FOUND_IN_DOCS`: Codex'in değerini destekleyen ifade belgelerde yok ve sen de değer bulamadın (ya da başka değer buldun ve Codex'inkinin dayanağı hiç yok). Codex'in alıntısını/sayfasını qfind ile ara.
Codex'in alıntıları çoğu zaman birebir değildir (kötü OCR ya da "…" kısaltma) — önemli olan değerin belgede doğrulanması.

## Çıktı
Her ticker için karar dosyası + `check.py` OK. Bitince her ticker için tek satır: `T: dm=<…> · ps=<TRUE/FALSE/null>/<gün> · iş=<gün> · ort=<gün> · sek=<…> · kat=<…> · codex FOUND_SAME a/b · OK`.

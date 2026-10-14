# 3. Veri: kaynaklar, etiketler ve özellikler

Bu bölüm BorsAi'nin veri katmanını baştan sona anlatır: hangi resmî kurumdan hangi dosya geliyor, dosya nasıl indirilip kilitleniyor, bir halka arzın "kaç gün tavan yaptığı" tam olarak nasıl hesaplanıyor, modele giren her sayı hangi formülle üretiliyor ve bunların hepsi hangi tabloda, hangi sırayla duruyor. Bölümdeki her sayı repodaki bir dosyadan ölçüldü; ölçemediğim şeyi "belirsiz" diye yazdım.

Önce bölüm boyunca geçecek birkaç terimi sade dille tanımlayayım:

| Terim | Anlamı |
|---|---|
| Halka arz (IPO) | Bir şirketin paylarını ilk kez borsada satışa sunması. |
| T, ilk işlem günü | Payın Borsa İstanbul'da ilk kez işlem gördüğü gün. Kodda `first_trading_date`. |
| Seans | Borsanın açık olduğu bir işlem günü. Hafta sonu ve resmî tatil seans değildir. |
| D_h | İlk işlem gününden başlayarak payın işlem gördüğü h'inci seans. D1 = ilk gün, D10 = onuncu seans. |
| Tavan | Bir payın o gün çıkabileceği en yüksek fiyat (üst limit). Kapanış bu fiyata eşitse "tavan kapattı" denir. |
| Taban | O gün inilebilecek en düşük fiyat (alt limit). |
| sha256 | Bir dosyanın içeriğinden hesaplanan 64 haneli parmak izi. Tek bayt değişse bile tamamen değişir. "Pinlemek" = bu parmak izini koda ya da bir manifest dosyasına yazıp her okumada yeniden denetlemek. |
| Decimal | Python'un ondalık sayı türü. `float` gibi ikili yuvarlama yapmaz; "10.12" metni tam olarak 10,12 kalır. |
| Nokta-zamanında (point-in-time, PIT) | Bir tahminde yalnız o tahmin anında gerçekten yayımlanmış bilgiyi kullanmak. Geleceği "sızdırmamak". |
| Kohort | Aynı kuralla seçilmiş arz grubu. Projenin ana eğitim kohortu H99'dur (99 arz). |
| Walk-forward | Geriye dönük testte her arzı yalnız ondan önce sonucu belli olmuş arzlarla eğitilmiş modelle tahmin etmek. |
| Fold | Walk-forward'daki tek bir "eğit, sonra bir arzı tahmin et" adımı. |

Kaynak dosyalar: `CLAUDE.md`, `docs/DATA.md`, `docs/specs/SPEC_SCORING.md`.

## 3.1 Veri katmanının ilkeleri

Veri katmanı birkaç sert kurala dayanır. Bunlar `CLAUDE.md`'de yazılıdır ve kodla zorlanır.

1. **Yalnız resmî kaynak.** Veri Borsa İstanbul (BIST), Kamuyu Aydınlatma Platformu (KAP), Sermaye Piyasası Kurulu (SPK) ve enflasyon için TÜİK'ten gelir. İkincil kaynak kullanılırsa etiketlenir. Sonuç (getiri, tavan) yalnız BIST'in resmî THB/THM bültenlerinden okunur (CLAUDE.md kural 6).
2. **Değer metin olarak taşınır.** Kaynaktaki sayı, kaynaktaki yazımıyla saklanır ve `Decimal("…")` ile okunur. `float`'a çevrilip geri yazılmaz. Örnek: `R_D3` 50 anlamlı haneli bir kesirdir; `ipo_price_tl` ise `76.6` gibi kısa yazılır.
3. **Her dosya sha256 ile kilitlidir.** Ham dosyanın parmak izi bir manifest ya da kod sabitinde durur. Okuyucu her seferinde parmak izini yeniden hesaplar; tutmazsa durur.
4. **Üretici yalnız kopyalar ve denetler.** Bir tutarsızlık görürse (ör. iki dosyada farklı ilk işlem günü) değeri düzeltmez, hata verip durur.
5. **Sıra kuralı.** 2026-08-19 sonrası THB/THM verisi ve 2026-08-06 sonrası listelenen arzların sonuçları, Faz 1 model dosyaları dondurulup commit edilmeden repoya alınamaz. Bu kesim tarihleri kodda `OUTCOME_CUTOFF = "2026-08-19"` ve `LISTING_CUTOFF = "2026-08-06"` olarak geçer.
6. **Veri sürümü değişirse model kimliği değişir.** Eğitim tablosunun ya da kaynak dosyalarının sha256'sı değişirse eski model "aynı model" sayılmaz; yeni `model_id` gerekir (CLAUDE.md kural 5).

Veri akışının kaba şeması şöyledir:

```
resmî kaynak (BIST, KAP, SPK, TÜİK)
   │  indir, ham baytları değiştirmeden sakla, sha256 yaz
   ▼
data/raw/…  ve  registry/source_docs/…      (ham ya da kanonik dosyalar)
   │  denetle + kopyala (düzeltme yok)
   ▼
data/training_table.csv, _v2.csv            (arz başına bir satır)
registry/inputs/<T>.json                    (yeni arzın listeleme öncesi girdileri)
data/outcomes/<T>.csv                       (yeni arzın D1–D10 sonucu)
   │  özellik formülleri (borsai/features.py, market20.py, tufe.py)
   ▼
ham özellikler f1…f6, f1r, pb1…pb4
   │  fold içi ön işleme (borsai/preprocess.py)
   ▼
z-skorlu matris  →  modeller
```

Kaynak dosyalar: `CLAUDE.md`, `docs/DATA.md`, `borsai/scoring.py` (satır 506–507), `borsai/outcomes.py` (`SEQUENCE_CUTOFF`).

## 3.2 Resmî kaynaklar ve indirme

### 3.2.1 BIST günlük bültenleri: THB ve THM

Borsa İstanbul her seans için iki günlük dosya yayımlar:

- **THB (fiyat bülteni):** o seansın bütün işlem kodları için açılış, en yüksek, en düşük, kapanış fiyatı, işlem adedi, hacim, sözleşme sayısı ve durum alanları.
- **THM (limit bülteni):** o seansın referans fiyatı, üst limit (tavan) ve alt limit (taban) fiyatı.

İki dosya da aynı URL kalıbıyla indirilir:

```
https://www.borsaistanbul.com/data/{thb|thm}/YYYY/MM/th?YYYYMMDD1.zip
```

Buradaki `?` THB için `b`, THM için `m` harfidir. Zip'in içinde tek bir CSV vardır; adı `th?YYYYMMDD1.csv` kalıbındadır. Kalıp `borsai/outcomes.py`'deki `source_url`, `internal_name` ve `local_path` fonksiyonlarında tek yerde tanımlıdır.

Dosya biçimi (`parse_archive_bytes`):

- Kodlama `cp1254` (Türkçe Windows kod sayfası). UTF-8 olarak okunamaz.
- Ayraç noktalı virgül (`;`).
- İki başlık satırı vardır: birincisi Türkçe, ikincisi İngilizce. Sütunlar sıra numarasıyla değil, Türkçe başlık adıyla bulunur.
- Zip'te tam olarak beklenen iç dosya adı olmalıdır; değilse hata.
- Her satırdaki `TARIH` alanı bültenin tarihine eşit olmalıdır.
- Aynı işlem kodu bir bültende iki kez geçerse o kod "çelişkili" (`SOURCE_CONFLICT`) işaretlenir ve okunmak istenirse hata verir.

Sütun sayıları bir biçim probu ile ölçüldü: THB 2019 sonunda 56 sütun, 2026'da 57 sütundur (fark sona eklenen `BIST KATILIM TUM ENDEKS`); THM her iki yılda 19 sütundur ve başlığı bayt bayt aynıdır. THM'de `FIYAT ADIMI` sütunu o gün geçerli fiyat adımı tablosunu taşır.

Projenin okuduğu sütunlar şunlardır (`REQUIRED`, `THB_COLUMNS`, `THM_COLUMNS`):

| Bülten | Türkçe başlık | Koddaki ad | Ne için |
|---|---|---|---|
| THB | `ISLEM  KODU` (iki boşluk) | anahtar | Payın işlem kodu, ör. `NETGL.E` |
| THB | `TARIH` | anahtar | Satır tarihi denetimi |
| THB | `KAPANIS FIYATI` | `close` | Getiri ve tavan etiketi |
| THB | `TOPLAM SOZLESME SAYISI` | `trade_count` | "İşlem gördü mü" testi |
| THB | `GECICI DURDURMA` | `halt` | Gün içi durdurma bayrağı |
| THB | `ACILIS FIYATI`, `EN YUKSEK FIYAT`, `EN DUSUK FIYAT`, `TOPLAM ISLEM ADEDI`, `TOPLAM ISLEM HACMI`, `A.O.F`, `OZEL ISLEM BILDIRIMI ISLEM ADEDI`, `OZEL ISLEM BILDIRIMI ISLEM HACMI` | `open` … `special_turnover` | D1 sonrası (POST_D1) modelin D1 alanları |
| THB | `BULTEN ADI`, `ENSTRUMAN GRUBU`, `PAZAR` | `name`, `group`, `market` | Yalnız tamlık denetimi |
| THM | `REFERANS FIYATI` | `reference` | Bilgi |
| THM | `UST LIMIT FIYATI` | `upper` | Tavan etiketi |
| THM | `ALT LIMIT FIYATI` | `lower` | Taban (kırılma modelleri) |

Yayın zamanı da manifestten okunabilir. Sunucunun `Last-Modified` başlığına göre THB seans bittikten sonra akşam (ör. 15:28 GMT = 18:28 İstanbul), THM ise sabah seans açılmadan önce (ör. 05:02 GMT = 08:02 İstanbul) yayımlanır. Yani THM o günün limitlerini önceden verir; THB o günün sonucunu sonradan verir.

**İndirme ve kilitleme.** İndirici `borsai/outcomes.py`'dir. Kurallar:

- Yalnız `www.borsaistanbul.com` adresine çıkılır; başka bir ev sahibi istenirse hata.
- HTTP 404 "henüz yayımlanmadı" ya da "o gün kapalı" demektir (`NotPublished`); yeniden denenmez. Diğer hatalarda en çok üç deneme yapılır. 100 bayttan kısa yanıt hata sayılır.
- Ham zip baytları hiç değiştirilmeden `data/raw/bist/<thb|thm>/YYYY/th?YYYYMMDD1.zip` yoluna yazılır. Dosya `xb` kipinde açılır: aynı adda dosya varsa yeniden yazılmaz. Yazmadan önce zip ayrıştırılır; ayrıştırılamıyorsa hiçbir şey yazılmaz.
- Her indirme `data/raw/bist/MANIFEST.csv`'ye bir satır ekler. Sütunlar: `date, kind, url, sha256, bytes, internal_filename, downloaded_at, http_last_modified`. `downloaded_at` yerel saattir ve kanıt sayılmaz; zaman kanıtı git push'tur.
- Yerelde dosya varsa önce manifestteki sha256 ile karşılaştırılır.
- H99 sonuç dosyasında sha256'sı zaten kayıtlı olan bir bülten (2023-09-22…2026-08-19 arası) başka baytlarla gelirse indirici `SourceChanged` ile durur. Bu, "BIST eski dosyayı sessizce değiştirdi mi" sorusunun bekçisidir.

Ölçülen manifest: 73 satır. THB 40 dosya (2026-08-06…2026-09-30), THM 33 dosya (2026-08-17…2026-09-30), toplam 15.414.084 bayt. 59 dosya 2026-09-22'de, 14 dosya (NETGL'in D4–D10'u için) 2026-09-30'da indirildi. THB'nin 2026-08-06'dan başlaması tamlık denetiminin tabanı içindir (§3.10). Bu salt okunur kopyada zip'lerin kendisi yoktur; yalnız manifest ve klasör yapısı vardır.

Eski kohort (2020–2023) bültenleri ayrı bir manifestte tutulur: `data/raw/bist/MANIFEST_OOT.csv`, 1.168 satır (584 THB + 584 THM), tarih aralığı 2020-02-06…2023-10-04. Bu zip'ler repoya hiç girmez; repo dışındaki bir karantina klasörüne indirilir (varsayılan `~/Desktop/BorsAi_quarantine`). Repoda yalnız manifest satırları ve ayıklanmış sonuçlar durur (§3.11).

Kaynak dosyalar: `borsai/outcomes.py`, `data/raw/bist/MANIFEST.csv`, `data/raw/bist/MANIFEST_OOT.csv`, `docs/specs/SPEC_SCORING.md` §1, `docs/specs_faz6/ekler/bulten_probu/bulten_bicim_probu.txt`, `docs/PROVENANCE.md` §10.

### 3.2.2 KAP

KAP, şirketlerin ve borsanın resmî duyuru platformudur. Projede üç tür KAP belgesi kullanılır:

- **Halka arz sonuçları bildirimi:** aracı kurumun yayımladığı, satılan pay adedi, talep katı ve dağıtım tablosunu içeren bildirim. Çoğu zaman asıl tablo ek PDF'tedir.
- **Payların işlem görmeye başlaması:** Borsa İstanbul'un ilk işlem gününü, baz fiyatı ve işlem görecek pay tutarını duyuran bildirimi.
- **Erteleme ya da başka bir duyuru:** ör. bir arzın talep toplama sırasında ertelendiğini bildiren duyuru.

İndirme ayrıntıları `docs/PROVENANCE.md` §8'dedir:

- Bildirim PDF'i `https://www.kap.org.tr/tr/api/BildirimPdf/<id>` adresinden gelir.
- Ek dosya `https://www.kap.org.tr/tr/api/file/download/<nesne kimliği>` adresinden gelir. Bu yanıt Java'nın `ObjectOutputStream(byte[])` sarmalıyla gelir: başta 27 baytlık bir başlık, sonra asıl PDF baytları. Repoda saklanan dosya sarmal çıkarılmış PDF'tir. Manifest iki parmak izini birden tutar: `sha256` (saklanan PDF) ve `download_sha256` (sarmallı ham yanıt).
- **Yayın zamanı** bildirim PDF'inin başlığındaki "KAP'ta yayınlanma tarihi ve saati" alanından alınır (İstanbul saati). KAP liste API'sindeki zaman bundan 1–4 saniye sonradır; o da `kap_api_publish_date` olarak saklanır.

Payda (§3.9) için KAP'ta bir de toplu tarama yapıldı: `registry/source_docs/_ENUMERATION/` altındaki ham `byCriteria` yanıtı "Payların İşlem Görmeye Başlaması" konusunda 2026-08-01…2026-09-22 aralığında 8 kayıt döndürür (QUICK ve yeni 7 arz).

Kaynak dosyalar: `registry/source_docs/*/MANIFEST.json`, `registry/source_docs/_ENUMERATION/ENUMERATION.json`, `docs/PROVENANCE.md` §8.

### 3.2.3 SPK bülteni

SPK haftalık bültenlerinde onaylanan ilk halka arzları "A.1 İlk Halka Arzlar" tablosunda listeler. Bu tablonun bir satırı şu sütunları taşır: Mevcut Sermaye, Yeni Sermaye, Bedelli (sermaye artırımıyla satılacak pay), Bedelsiz, Mevcut Pay Satışı (ortak satışı), Ek Pay Satışı, Satış Fiyatı. Tabloda "-" sıfır demektir.

Bu tablo, talep toplamadan önce **planlanan** arz yapısının resmî kaynağıdır. PB (talep toplama öncesi) modellerinin bütün girdileri buradan gelir (§3.6.4).

SPK PDF'i `https://spk.gov.tr/data/<24 haneli kimlik>/YYYY-NN.pdf` biçiminde bir adreste durur. Yayın zamanı, adresteki 24 haneli nesne kimliğinin ilk 4 baytından okunan sunucu oluşturma zamanıdır (`SPK_DATA_URL_OBJECTID_CREATION_TIME`). Bu zaman HTTP `Last-Modified` başlığı ve bültenin üzerindeki tarihle tutarlı olmalıdır.

Kaynak dosyalar: `registry/source_docs/NETGL/MANIFEST.json`, `registry/inputs/NETGL.json`, `docs/PROVENANCE.md` §8.

### 3.2.4 TÜİK

Reel (enflasyondan arındırılmış) arz büyüklüğü için TÜİK'in Tüketici Fiyat Endeksi (TÜFE) genel endeksi kullanılır. Seri 2025=100 temelindedir: 2025 yılının 12 aylık ortalaması 100'dür (dosyadan ölçtüm: 100,000000).

Dosyalar `data/raw/tuik/` altındadır:

- `tufe_degisim_oranlari_bulten_58290.xls`: TÜİK'in "Tüketici Fiyat Endeksi, Ağustos 2026" bülteninin (sayı 58290, yayım 2026-09-03 10:00) "Tüketici fiyat endeksi ve değişim oranları" tablosu, sha256 `6f7ee8e4…`, 58.368 bayt. Tablo 2005-01…2026-08'i verir. Komut satırı istemcisi TÜİK sunucusundan 403 aldığı için dosya tarayıcının bülten oturumunda indirildi; baytlar değiştirilmedi. Bu salt okunur kopyada `.xls` yoktur; yanındaki `.source.json` kanıt dosyası vardır (indirme bağlantısı, HTTP içerik türü, indirme zamanı).
- `tufe_bultenleri.csv`: her referans ayı için o ayın kendi bülteninin numarası, dönemi, yayım zamanı ve sayfa adresi (82 satır, 2019-11…2026-08).
- `tufe_genel_2025_100.csv`: modelin okuduğu dosya. Sütunlar `month, index, release_date, bulletin_id, source_url, source_sha256`. 82 satır, 2019-11…2026-08. `build_tufe_csv.py` bu dosyayı iki kaynaktan üretir (stdlib ile yazılmış bir `.xls` okuyucusu içerir); `--check` kipi bayt bayt aynı dosyanın yeniden üretildiğini sınar.

Önemli ayrıntı: 2025 ve öncesi aylar yayımlandıkları anda 2003=100 temelindeydi. Dosyadaki değerler TÜİK'in 2025=100'e zincirlediği seridir; `release_date` ise ayın kendi bülteninin tarihidir. Yeniden ölçekleme sabit bir çarpandır ve aylık değişim oranlarını korur (derleyici 259 ayda ±0,0051 içinde denetler). Bu yüzden reel büyüklüklerin sırası ve oranları T anındaki bilgiyle aynı kalır. Yayın günleri: 78 ay "izleyen ayın 3'ü ya da sonraki ilk iş günü" kuralına uyar; 4 ay bayram yüzünden daha geç yayımlandı (en geç ayın 5'i).

Kaynak dosyalar: `data/raw/tuik/*`, `borsai/tufe.py`, `docs/PROVENANCE.md` §11, `docs/SPEC_DEVIATIONS.md` J3.

### 3.2.5 XU100 grafik verisi

f6 özelliği (§3.6.2) BIST 100 endeksinin (XU100) günlük kapanışlarını kullanır. Kaynak BIST'in grafik uç noktasıdır:

```
https://www.borsaistanbul.com/graphic.php?veriTuru=endeks-graphic&indexCode=XU100
```

Yanıt bir JSON nesnesidir: `{"status": "success", "source": "api", "data": [...]}`. Her kayıt üç alan taşır: `indexName` (yalnız `XU100` olmalı), `clval` (kapanış değeri), `hisTs` (tarih, YYYY-MM-DD). Kayıtlar yeniden eskiye sıralıdır. Ayrıştırma `json.loads(..., parse_float=Decimal)` ile yapılır; değer hiç `float`'a uğramaz.

Repoda iki pinli dosya vardır:

| Dosya | Kayıt | Aralık | sha256 | Kullanım |
|---|---|---|---|---|
| `data/raw/official_bist_xu100_graphic_pinned_through_20260819.json` | 9.682 | 1986-01-31…2026-08-19 | `34859d7e…` | H99 eğitimi ve backtest |
| `data/raw/xu100/xu100_graphic_20260922.json` | 9.705 | 1986-01-31…2026-09-21 | `04637c91…` | canlı kayıt ve eski kohort |

Birinci dosya türetilmiştir: eski repodaki özgün dosyanın 9.684 kaydından 2026-08-19 sonrasına ait iki kayıt (2026-08-20 ve 2026-08-21) tek bir bayt aralığı olarak çıkarıldı; diğer her bayt aynıdır. İkinci dosya 2026-09-22'de aynı uç noktadan ham hâliyle alındı (579.614 bayt).

**Revizyon denetimi.** Yeni dosya eskisinin yerine geçmez; ikisi birlikte durur (`XU100_PINNED` sabiti). `market20.load_xu100_latest()` en yeni dosyayı okurken eski dosyanın her kaydının yeni dosyada Decimal olarak aynı değerle durduğunu sınar (`check_revision`). Bir eski kayıt değişmiş ya da silinmişse durur. Yalnız ekleme kabul edilir. Ölçüm: eski 9.682 kaydın hepsi yeni dosyada aynıdır; yeni dosyada 23 ek kayıt vardır (2026-08-20…2026-09-21).

XU100 bir arz sonucu değildir; sıra kuralının kapsamında değildir. Yine de iki sınır vardır: endeks için THB açılmaz (THB bütün payların fiyatını, yani yeni arzların sonucunu da taşır) ve XHARZ gibi halka arz endeksleri alınmaz (onlar sonucun doğrudan türevidir).

Kaynak dosyalar: `borsai/market20.py`, `docs/specs/SPEC_MARKET20_V0.md` §1, §4, `docs/PROVENANCE.md` §1 satır 11 ve §7.

### 3.2.6 Tatil tabloları

Seans takviminin kaynağı BIST'in her yıl yayımladığı "Pay Piyasası tatil tablosu" PDF'leridir. 2020–2026 için URL ve sha256'lar takvim dosyalarının satırlarında ve `market20.py`'deki `HOLIDAY_TABLES_2020_2023` sabitinde yazılıdır. PDF'lerin kendisi bu kopyada yoktur. Takvimler §3.4'te ayrıntılı anlatılıyor.

Kaynak dosyalar: `borsai/market20.py` (satır 56–100), takvim CSV'leri (`data/raw/` altında).

## 3.3 H99 kohortu

### 3.3.1 Nasıl seçildi

H99 ("Historical 99") modellerin üzerinde tasarlandığı ve eğitildiği ana kohorttur. Eski repo, QUICK'in ilk işlem gününden (2026-08-06) geriye doğru "son 100 halka arz"ı saymayı hedefledi ve bunların 99'unu doğrulanmış kanıtla bağlayabildi. Bu bilgi üyelik dosyasında sütun olarak durur:

| Sütun | Değer (99 satırın hepsinde aynı) |
|---|---|
| `historical_anchor` | `QUICK` |
| `historical_anchor_date` | `2026-08-06` |
| `original_target_universe_size` | `100` |
| `current_frozen_cohort_size` | `99` |
| `known_membership_gap_count` | `1` |
| `membership_gap_status` | `DEFERRED_RECONCILIATION` |

Eksik 100. üyenin kim olduğu **belirsizdir**. Dosya, yerine doğrulanmamış bir şirket konmadığını ve gelecekte 100'lü bir kohortun yeni bir sürüm olması gerektiğini açıkça yazar (`future_version_rule`).

Üyeler iki kaynaktan gelir (`membership_source`):

- `CANONICAL20_PROTECTED_INPUT`: 20 arz. Eski repodaki alan alan kanıtlı "kanonik 20" satırları değiştirilmeden alındı (QUICK, KARCL, MASFN, ALBTN, METEN, SARAE, SSAAT, ISVEA, EKIM, GOLDA, ORZAX, BETAE, EKDMR, AAGYO, MCARD, LXGYO, GENKM, SVGYO, EMPAE, ATATR). İlk işlem günleri 2026-02-19…2026-08-06 arasındadır; ama bu aralıktaki her arz kanonik 20'de değildir (ör. SOHOE, 2026-07-06, dış kanıt grubundadır). Üyelik sıra numarası (`membership_ordinal`) 1–20 bu gruba verilmiştir.
- `VERIFIED_FINAL_EXTERNAL_ACQUISITION_EVIDENCE`: 79 arz. Kanonik 20'de olmayan, ilk işlem günü QUICK'ten sonra olmayan, doğrulanmış tarihsel kanıtı bulunan arzlar.

Ölçülen kapsam:

- İlk işlem günleri 2023-09-22 (HATSN) … 2026-08-06 (QUICK).
- 99 arz, 96 farklı ilk işlem günü (2023-12-14, 2025-02-13 ve 2026-03-06'da ikişer arz başladı).
- Yıllara göre: 2023: 19, 2024: 33, 2025: 18, 2026: 29.
- H99'un 2023-09-22'de başlaması bir kural değişikliği değildir; yalnız "son 100" sayımının vardığı yerdir.

Kaynak dosyalar: `data/raw/HISTORICAL99_FROZEN_COHORT_V1_canonical_membership.csv`, `docs/prompts/FAZ6_FABLE_OLD_COHORT_SPEC.md` (satır 10), `docs/DATA.md`.

### 3.3.2 H99 kanonik dosyaları

Bütün H99 dosyaları `data/raw/` altındadır. Eski repodan 2026-09-21'de kopyalandılar. Dokuzunun satır sonları CRLF'den LF'ye çevrildi (her `\n` yeniden `\r\n` yapılırsa eski baytlar birebir geri gelir); UTF-8 BOM (dosya başındaki görünmez işaret) korundu. Bu yüzden okurken `encoding="utf-8-sig"` kullanılır.

| Kısa ad | Dosya (`data/raw/` altında) | Satır × sütun | Ne taşır |
|---|---|---|---|
| — | `HISTORICAL99_FROZEN_COHORT_V1_canonical_membership.csv` | 99 × 15 | Üyelik, sıra no, kaynak, boşluk bilgisi |
| MASTER | `HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv` | 99 × 38 | İşlem öncesi arz alanları |
| PROV | `HISTORICAL99_FROZEN_COHORT_V1_canonical_provenance.csv` | 99 × 22 | KAP kimlikleri, PIT durumu, kanıt dosyası |
| READY | `HISTORICAL99_FROZEN_COHORT_V1_canonical_feature_readiness.csv` | 99 × 23 | f1–f5'in ham değerleri ve formül metinleri |
| SESSIONS | `HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv` | 990 × 40 | Her arzın D1–D10 seansının THB/THM alanları |
| TARGETS | `HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_d1_d3_d5_d10_targets.csv` | 396 × 18 | D1/D3/D5/D10 getiri hedefleri |
| — | `HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_field_provenance.csv` | 11.880 × 15 | Seans alanı başına kaynak (990 seans × 12 alan) |
| Takvim A | `HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_pay_session_calendar.csv` | 1.063 × 11 | 2023-09-22…2026-08-19 her takvim günü |
| PB | `PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv` | 99 × 32 | Talep toplama öncesi planlanan yapı |

**MASTER'ın önemli alanları.** `ipo_price` (arz fiyatı, TL), `shares_offered` (satılan toplam pay), `capital_increase_shares` (sermaye artırımıyla satılan pay), `existing_share_sale` (ortak satışı), `additional_sale_shares` (kullanılan ek satış), `post_ipo_share_capital` (arz sonrası sermaye, pay adedi), `ipo_size_tl` (kaynakta bildirilen arz büyüklüğü), `total_demand_multiple` (toplam talep katı) ve onun kökeni (`…_origin`), tanım metni (`…_definition`) ve filtre durumu (`…_filter_status`). Eksik değer `DATA_NOT_FOUND` metniyle yazılır. 38 sütunun çoğu (yatırımcı sayısı, dağıtım yöntemi, kilit süreleri, sektör …) yalnız kanonik 20 için doludur: örneğin `distribution_method`, `lead_broker`, `sector` 79 satırda `DATA_NOT_FOUND`'dur. `data_completeness_status` 99 satırın hepsinde `PARTIAL`'dır.

**PROV'un önemli alanları.** `result_kap_id` (sonuç bildirimi), `first_trading_kap_id`, `point_in_time_status`. Bu son alan 20 satırda `PASS`, 79 satırda `UNKNOWN`'dır: kanonik 20 için girdinin arz anında yayımlandığı kanıtlıdır; diğer 79 için bu kanıt yoktur. 79'luk grup yine de eğitimde kullanılır (proje sahibinin kararı; `docs/DATA.md`). `conflict_status` 99'da `NO_CONFLICT`'tir. Bir arzda daha önceki bir sonuç bildirimi `SUPERSEDED_DO_NOT_CANONICALIZE` olarak işaretlenmiştir.

**SESSIONS'ın önemli alanları.** Her satır bir (arz, seans) çiftidir. `thb_raw_*` ve `thm_raw_*` sütunları bültendeki ham metni, `close`, `upper_limit` gibi sütunlar normalleştirilmiş değeri taşır; 990 satırın hepsinde ikisi aynıdır. Her satır bülten URL'sini, eski repodaki yerel yolunu, zip sha256'sını ve iç dosya adını da taşır. `security_trading_status` 990 satırın hepsinde `ACTIVE_NOT_SUSPENDED`'dır: H99'da hiç işlem durdurma yoktur. `session_type` 984 satırda `OPEN_FULL_DAY`, 6 satırda `OPEN_HALF_DAY`'dir.

**TARGETS'ın önemli alanları.** `horizon` (D1/D3/D5/D10), `target_session_date`, `ipo_price`, `official_close`, `target_return` (50 anlamlı haneli metin), `target_return_exact_numerator` ve `…_denominator` (kesin kesrin payı ve paydası), `above_ipo_flag` (0/1).

Kaynak dosyalar: yukarıdaki tablodaki dokuz dosya, `docs/PROVENANCE.md` §1, `docs/DATA.md`.

### 3.3.3 H99 verisindeki bilinen tuzaklar

`docs/DATA_NOTES.md` eski repodan gelen ve modele etki eden veri anlamı notlarını toplar. Önemlileri:

1. **f2'nin formülü ön kayıtta yazılı değildi.** Fiilen kullanılan tanım `shares_offered / post_ipo_share_capital × 100`'dür. READY dosyasındaki `f2_formula` sütunu da bunu söyler. Yeni kodda formül açıkça yazıldı (§3.6.1).
2. **Ek satış 6 arzda `shares_offered`'ın içindedir.** 93 arzda `shares_offered = capital_increase_shares + existing_share_sale` tutar. GLRMK, ARMGD, HOROZ, OZYSR, MEGMT ve BORLS'ta eşitlik ancak kullanılan ek satış eklenince tamamlanır. Bu 6 arzın f1 ve f2'si ek satışı içerir; f4'ün paydası büyür. `additional_sale_shares` 95 arzda doludur ve bunların 89'u sıfırdır; bilgi taşıyan yalnız 6 satır vardır. Dört arzda (KARCL, MASFN, ALBTN, METEN) bu alan `DATA_NOT_FOUND`'dur.
3. **f3 (talep katı) karışık tanımlıdır.** 97 dolu değerin kökeni: `SOURCE_REPORTED` 71, `CALCULATED_FROM_SOURCE_TOTALS` 16, `CALCULATED_FROM_PRIMARY_TOTALS` 8, `SOURCE_REPORTED_APPROX` 2. Filtre durumu: `NOT_SPECIFIED` 59, `UNFILTERED` 36, `NOT_APPLICABLE` 2 (f3 yok), `SOURCE_SEQUENCE_AMBIGUOUS` 1, `FILTERED_ACCEPTED_AFTER_DUPLICATE_SCREEN` 1. `total_demand_definition` sütununda 31 farklı metin vardır. f3 eksik olan iki arz ALBTN (`DATA_NOT_FOUND`) ve ENDAE'dir (`LEGITIMATE_SOURCE_MISSING`).
4. **NETGL'de sermaye artırımı / ortak satışı ayrımı arz öncesi belgeden taşındı.** NETGL'in `capital_increase_shares` değeri kesin sonuç bildiriminden değil, arz öncesi belgeden (SPK Bülteni 2026/56) alındı. Taşıma ancak üç koşul birlikte tutunca yapılır: resmî sonuç bildirimi planlanan arzın tamamının satıldığını söyler, nihai pay adedi planlananla aynıdır ve ek satışın kullanılmadığı resmî belgede yazılıdır. Taşınan değer `PLANNED_SPLIT_CARRIED_FULL_SUBSCRIPTION` bayrağını alır. Eski repodaki bir ölçüme göre (20 tarihsel arz) bu ayrım sonuç bildirimlerinde ayrı kalem olarak yalnız 6 arzda yayımlanıyordu (p = 0,30; 3 kısmi, 11 yok). Yani birçok satırda `capital_increase_shares` aslında planlanan değerdir.
5. **GOLDA dersi.** Eski bir raporda GOLDA'nın arz fiyatı 10,12 TL yazıyordu; resmî fiyat 9,20 TL'dir (KAP 1623769). 10,12 aslında D1 kapanışıdır: 9,20 × 1,1 = 10,12, yani tavan. Bu repoda doğrulandı: `ipo_price_tl` = 9.2, D1 `close` = 10.12, `ceiling_close_D1` = 1. Ders: bir sonuç değeri girdi alanına sızabilir ve tavan kapanışı arz fiyatı × 1,1'e eşit olduğu için göze batmaz. Değer her zaman birincil belgeden alınır.

Kaynak dosyalar: `docs/DATA_NOTES.md`, `data/raw/HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv`, `data/training_table.csv`.

## 3.4 Seans takvimi

### 3.4.1 Temel kavramlar

"Kaçıncı seans" sorusu takvime bağlıdır. Projede bir takvim günü şu sınıflardan birine girer:

- **Tam gün seans:** hafta içi ve tatil tablosunda yok. Seans sayılır.
- **Yarım gün seans:** tatil tablosunda "yarım gün seans yapılacaktır" yazan gün (genelde bayram arifesi). **Bir seans sayılır**; kapanış o günün resmî THB kapanışıdır.
- **Tam kapanış:** tatil tablosunda "seans yapılmayacaktır" yazan gün. Sayılmaz.
- **Hafta sonu:** sayılmaz.
- **İlan dışı kapanış:** tatil tablosunda olmadığı hâlde THB'nin hiç yayımlanmadığı hafta içi gün (ör. deprem kapanışı). Sayılmaz; kanıtıyla birlikte ayrı bir dosyaya yazılır.

Projede dört takvim dosyası vardır. Hepsi her takvim gününü tek tek listeler ve günler ardışık olmak zorundadır (kod bunu denetler).

| Takvim | Dosya | Aralık | Gün | Seans | Yarım gün | Kullanım |
|---|---|---|---|---|---|---|
| A | `HISTORICAL99_…_bist_pay_session_calendar.csv` | 2023-09-22…2026-08-19 | 1.063 | 728 | 6 | H99 sonuçları, canlı sonuç takvimi |
| B | `v2_market20_official_pay_calendar_evidence_r4.csv` | 2023-01-01…2026-08-19 | 1.327 | 910 | 8 | f6 (H99 eğitimi) |
| B uzatması | `pay_calendar_b_extension_20260820_20261231.csv` | 2026-08-20…2026-12-31 | 134 | 95 | 1 | canlı f6 ve canlı sonuçlar |
| C | `pay_calendar_c_20200101_20230921.csv` | 2020-01-01…2023-09-21 | 1.360 | 930 | 9 | eski kohort f6'sı ve sonuçları |

Kaynak dosyalar: dört takvim dosyası (`data/raw/` altında), `borsai/market20.py`, `borsai/outcomes.py` (`load_calendar`).

### 3.4.2 Takvim A

H99'un kendi oturum takvimidir. Sütunlar: `calendar_date, weekday, session_status, counts_as_official_session, used_by_historical99, calendar_evidence_year, calendar_source_url, calendar_source_path, calendar_source_sha256, session_semantics_version, notes`.

Ölçülen dağılım:

| `session_status` | Gün | `counts_as_official_session` |
|---|---|---|
| `OPEN_FULL_DAY` | 722 | `TRUE` |
| `OPEN_HALF_DAY` | 6 | `TRUE` |
| `OFFICIAL_FULL_CLOSURE` | 31 | `FALSE` |
| `WEEKEND_EXCLUDED` | 304 | `FALSE` |

Yarım günler: 2024-04-09, 2024-10-28, 2025-06-05, 2025-10-28, 2026-03-19, 2026-05-26. `used_by_historical99` 433 günde `TRUE`'dur; bu, SESSIONS dosyasındaki 433 farklı seans tarihine eşittir. Her satır o yılın tatil PDF'inin URL'sini ve sha256'sını taşır. `session_semantics_version` her satırda `BIST_PAY_NTH_OFFICIAL_OPEN_SESSION_V1`'dir; yani "D_n = n'inci resmî açık seans" tanımı.

Not: Takvim A seans sayarken `TRUE`/`FALSE` yazar; Takvim B ve C `YES`/`NO` yazar. Kod iki yazımı da tanır; sonuç takvimi yükleyicisi (`outcomes.load_calendar`) bu sütunda başka bir değer görürse durur.

Kaynak dosyalar: `data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_pay_session_calendar.csv`, `borsai/market20.py` (`load_calendar_a`).

### 3.4.3 Takvim B ve uzatması

Takvim B, f6'nın 20 seanslık penceresinin H99'un ilk arzlarında da dolabilmesi için 2023-01-01'den başlar. Sütunlar: `calendar_date, weekday_name, is_weekend, full_closure, half_day, counts_as_official_session, source_year, source_pdf, source_pdf_sha256, source_locator, verification_status`.

- 1.063 satırı (2023-09-22…2026-08-19) Takvim A ile birebir aynıdır (`VERIFIED_EXACT_MATCH_VS_R1_CANONICAL_CALENDAR`).
- 264 satırı (2023-01-01…2023-09-21) yalnız yeniden kurma kuralıyla doğrulanmıştır (`EXTENDS_BEYOND_R1_CANONICAL_RANGE_VERIFIED_BY_RECONSTRUCTION_RULE_ONLY`).
- `source_locator` her günün neden o sınıfta olduğunu yazar: tatil tablosundan harfi harfine kapanış (`OFFICIAL_FULL_CLOSURES_LITERAL_TRANSCRIPTION`), yarım gün, hafta sonu ya da "listede yok, dolayısıyla açık".
- Bu aralıkta beş hafta içi günde XU100 kapanışı yoktur: 2023-02-09, 10, 13, 14 (Şubat 2023 depremi) ve 2023-04-24. Takvim B bunları seans sayar; ama H99 pencerelerine dokunmazlar (H99'un en erken S20 tarihi 2023-08-23).

**Uzatma** (2026-08-20…2026-12-31) Faz 2A'da BIST'in 2026 tatil tablosundan aynı şemayla eklendi. İçinde: tam kapanış 2026-08-30 (Pazar) ve 2026-10-29; yarım gün 2026-10-28. Bir çapraz denetim yapıldı: 2026-08-20…2026-09-21 aralığında takvimin seans günleri kümesi XU100 kayıt günleri kümesine eşittir (23 = 23). Bu aralıktaki 33 satırın `verification_status`'ü `FAZ2A_TRANSCRIBED_SESSION_SET_EQUALS_XU100_DATES_THROUGH_20260921`'dir; sonraki 101 satır henüz XU100'e karşı denetlenmemiştir (`…NOT_YET_CROSS_CHECKED_AGAINST_XU100`).

`load_calendar_b_extended` uzatmanın Takvim B'nin son gününün ertesi başladığını denetler ve birleşik takvimin sha'sını `<B sha>+<uzatma sha>` biçiminde taşır. 2027 için yeni bir tatil tablosu eklenmezse 2027 tarihli bir f6 isteği `CALENDAR_NOT_COVERING` ile reddedilir; sessizce bayat bir değer dönmez.

Kaynak dosyalar: `data/raw/v2_market20_official_pay_calendar_evidence_r4.csv`, `data/raw/pay_calendar_b_extension_20260820_20261231.csv`, `docs/PROVENANCE.md` §7, `docs/specs/SPEC_MARKET20_V0.md` §1, §4.

### 3.4.4 Takvim C ve bülten kanıtı

Takvim C eski kohort (2020-01-01…2023-09-21) içindir. Dosya elle yazılmaz: `market20.calendar_c_rows()` dört yılın tatil tablolarından alınmış sabitlerden (`HOLIDAY_TABLES_2020_2023`) her günü üretir; test dosyanın bu fonksiyonun çıktısıyla bayt bayt aynı olduğunu sınar. sha256'sı `6dfd6134…`'tür.

Takvim C'de beş hafta içi gün ne tatil tablosunda ne de XU100 serisinde vardır: 2023-02-09, 2023-02-10, 2023-02-13, 2023-02-14 ve 2023-04-24 (`XU100_GAP_CLOSURES`). Bunlar kapanış sayılır ve `source_locator`'ları `NOT_LISTED_IN_HOLIDAY_TABLE_NO_XU100_CLOSE_UNANNOUNCED_CLOSURE`'dır.

Bu kararın doğru olup olmadığı sonradan **bülten kanıtıyla** sınandı: `data/raw/pay_calendar_c_bulletin_evidence_20200101_20230921.csv` Takvim C'nin 42 hafta içi kapanışının her biri için THB'nin yayımlanıp yayımlanmadığını ve yayımlandıysa kaç pay satırında işlem olduğunu (yalnız toplam sayılar) tutar. Karar kuralı (`evidence_decision`): HEAD isteği 404 → `NOT_PUBLISHED`; 200 ve işlem gören pay satırı 0 → `PUBLISHED_NO_TRADING`; 200 ve ≥ 50 → `TRADING_SESSION`; 1–49 arası → dur ve elle incele.

Sonuç: 37 tatil günü `NOT_PUBLISHED`; dört deprem günü `PUBLISHED_NO_TRADING` (bülten yayımlanmış ama işlem yok); 2023-04-24 ise `TRADING_SESSION` (o gün işlem olmuş, yalnız XU100 serisinde kayıt yok). Bu yüzden iki farklı takvim vardır:

- **f6 takvimi** Takvim C'nin kendisidir ve değişmez.
- **Eski kohort sonuç takvimi** (`outcomes_oot.load_calendar_oot`) = Takvim C seansları ∪ kanıtta `TRADING_SESSION` olan günler (yani 2023-04-24) ∪ Takvim A ∪ B uzatması, eksi ilan dışı kapanışlar.

Kaynak dosyalar: `data/raw/pay_calendar_c_20200101_20230921.csv`, `data/raw/pay_calendar_c_bulletin_evidence_20200101_20230921.csv`, `borsai/market20.py` (`calendar_c_rows`), `borsai/outcomes_oot.py` (satır 116–216).

### 3.4.5 Sonuçlar için kullanılan takvim

Canlı arzların sonuç hesabı (`outcomes.load_calendar`) Takvim A ile B uzatmasının birleşimini kullanır (2023-09-22…2026-12-31). İki dosyanın sha256'sı `market20.py`'deki pinlerle denetlenir (`CALENDAR_A_SHA256 = 15d4d975…`, `CALENDAR_B_EXT_SHA256 = 273ca0e7…`). Ardından `data/raw/bist/UNANNOUNCED_CLOSURES.csv` dosyasındaki günler takvimden çıkarılır.

**İlan dışı kapanış nasıl yakalanır?** `download_range` bir seansın THB'sini indirirken 404 alırsa sonraki resmî seansların THB'sine bakar. Sonraki bir seansın bülteni yayımlanmışsa 404 alınan gün ilan dışı kapanıştır: `UNANNOUNCED_CLOSURES.csv`'ye `date, kind, url, http_status, later_session_published, detected_at` satırı yazılır ve gün takvimden düşer. Sonraki hiçbir seans yayımlanmamışsa bülten "henüz yayımlanmadı" demektir ve indirme durur. Ölçüm: şu ana kadar böyle bir gün olmadı; dosya hiç oluşmadı (2026-08-18…2026-09-21 arasındaki 25 resmî seansın hepsinin THB ve THM'si yayımlanmış).

Kaynak dosyalar: `borsai/outcomes.py` (`load_calendar`, `download_range`, `_record_closure`), `docs/PROVENANCE.md` §10.

### 3.4.6 D_h tanımı: hangi gün kaçıncı seans?

Tanım `docs/specs/SPEC_SCORING.md` §2 ve §9'dadır; kodu `outcomes.resolve_sessions`'tır.

```
traded(a, s) = THB'de "<a>.E" satırı var
               VE TOPLAM SOZLESME SAYISI > 0
               VE KAPANIS FIYATI > 0
ilk görünüş  = "<a>.E" kodunun THB'de ilk göründüğü resmî seans
D_1(a)       = ilk görünüşten başlayarak traded olan ilk resmî seans
D_h(a)       = D_1'den başlayarak traded olan h'inci resmî seans
```

`.E` eki BIST'te payın normal işlem kodunu gösterir (ör. `NETGL.E`). Kurallar:

- **Yarım gün** bir seans sayılır. H99'da 6 yarım gün seansı var: EKDMR D3, MCARD D7, LXGYO D8, GENKM D10, SVGYO D10, ENTRA D4. Bunlar takvimde yalnız üç güne düşer (2024-04-09, 2026-03-19, 2026-05-26). Sonuç satırında `half_day = 1` yazılır.
- **Tam gün durdurma.** Pay o gün işlem görmediyse (`traded` yanlış) gün sayılmaz; D_h bir sonraki seansa kayar. Satıra `shifted_by_suspension = k` yazılır: D_1'den o ufka kadar atlanan seans sayısı. Durdurma nedeniyle sayılmayan gün tavan serisini **bozmaz**.
- **Gün içi geçici durdurma.** `GECICI DURDURMA = 1` ama sözleşme > 0 ise gün sayılır ve `halt_flag = 1` yazılır.
- **Bilinmeyen kod.** `GECICI DURDURMA` 0 ya da 1 dışında bir değerse komut `UnknownOfficialCode` ile durur; satır elle incelenmeden skorlanmaz.
- **15 seans sınırı.** İlk görünüşten itibaren 15 resmî seans içinde D_10 oluşmazsa oluşmayan ufuklar `TARGET_UNAVAILABLE` olur (`MAX_SEEN = 15`).
- **Bekleyen seans.** Bülteni henüz yerelde olmayan bir seansa gelinirse satır `PENDING` kalır.
- **Kayıttaki T ile gerçekleşen D_1 farklıysa** skorlamada gerçekleşen D_1 kullanılır ve fark raporlanır.

H99 ile uyum: 990 seansın hepsi `ACTIVE_NOT_SUSPENDED` olduğu için bu "işlem gördü" tanımı H99'da takvime dayalı tanımla aynı D_h'leri verir. `tests/test_outcomes.py::test_1_h99_reproduction_is_exact` bunu 990 seans tarihi, 396 hedef, 990 tavan etiketi ve 99 seri uzunluğu için sınar.

Kaynak dosyalar: `borsai/outcomes.py` (satır 489–572), `docs/specs/SPEC_SCORING.md` §2, §9, §10, `tests/test_outcomes.py`.

## 3.5 Etiketler: tavan, seri uzunluğu, getiri

Etiket (hedef), modelin tahmin etmeye çalıştığı gerçekleşen değerdir. Projede dört aile etiket vardır: her seans için "tavan kapattı mı", seri uzunluğu L, getiri R_h ve "arz fiyatının üstünde mi" Y_h. Hepsi yalnız resmî THB/THM'den gelir.

### 3.5.1 Tavan etiketi

Tanım (`SPEC_SCORING` §3, `outcomes.ceiling_label`):

```
ceiling_close_k = 1  eğer  Decimal(KAPANIS FIYATI, D_k) == Decimal(UST LIMIT FIYATI, D_k)
                = 0  değilse
                = NA eğer o seansın THM satırı yok, üst limit boş ya da ≤ 0
k = 1..10
```

Ayrıntılar:

- Karşılaştırma iki ham metnin `Decimal`'e çevrilmiş hâli arasındadır. `"10.12"` ile `"10.120"` eşittir (Decimal sayısal değere bakar); `"10.11"` ile `"10.12"` eşit değildir. Bu, kabul testindeki örnektir.
- Üst limit **o seansın kendi THM satırından** okunur. "Getiri %10'a ulaştı mı" diye bakılmaz; kodda hiçbir yerde 1,10 sabiti kullanılmaz.
- NA bir etiket tahmin edilmez; satır `NA_LIMIT` durumunu alır ve ilgili tavan metrikleri o arzda hesaplanmaz.

**Neden "%10" değil?** Üst limit, referans fiyatın %10 üstünün **fiyat adımına** yuvarlanmış hâlidir. Fiyat adımı, fiyat düzeyine göre değişen en küçük fiyat aralığıdır (ör. 2019 THM'sinde 0–19,999 TL için 0,01; 20–49,999 TL için 0,02; 50–99,999 TL için 0,05). Bu yüzden:

- H99'un 990 seansında üst limit / referans oranı 1,09604…1,1 aralığındadır (ölçtüm).
- Dört arzda D1 referans fiyatı arz fiyatından bir adım farklıdır: LILAK (arz 37,39 / referans 37,40), ARTMS (25,35 / 25,36), AVPGY (55,08 / 55,10), BORLS (25,29 / 25,30).
- D1'de tavan kapatan 81 arzın yalnız 50'sinde `R_D1` tam olarak 0,1'dir. Diğerlerinde 0,1'in biraz altındadır (en küçüğü 0,0989…) ya da üstündedir (LILAK 0,10029…, BORLS 0,10004…).
- Canlı örnek: NETGL'in D1 referansı 25,52'dir; 25,52 × 1,1 = 28,072 eder ama THM'deki üst limit 28,06'dır. Kapanış 28,06 olduğu için etiket 1'dir; getiri ise 0,0995…'tir.

Kaynak dosyalar: `borsai/outcomes.py` (`ceiling_label`), `data/build_training_table.py` (satır 157–168), `docs/DATA.md` "Tavan", `docs/specs/SPEC_SCORING.md` §3.

### 3.5.2 Seri uzunluğu L

```
L = D_1'den başlayan kesintisiz ceiling_close = 1 sayısı   (0…10)
    ilk 0'da durur; sonraki tavanlar sayılmaz
    önce bir NA gelirse L bilinmez (None)
```

Kod `outcomes.streak`'tir. Eğitim tablosunda sütun adı `ceiling_streak_L`'dir. Birkaç canlı örnek bu kuralı iyi gösterir:

- CITAS D1–D5 tavan, D6–D7 değil, D8–D9 yine tavan: L = 5. D8–D9'daki tavanlar L'ye girmez.
- TKNKA D1–D7 tavan, D8 değil, D9–D10 tavan: L = 7.
- VEYAS D1 tavan değil, D3 tavan: L = 0.

Tavan serisi modelleri (ayrık zamanlı "hazard" modelleri) bu L'yi tahmin eder: S_k = P(L ≥ k).

Kaynak dosyalar: `borsai/outcomes.py` (`streak`), `data/outcomes/*.csv`, `docs/specs/SPEC_CEILING_V0.md` §2.

### 3.5.3 Getiri R_h ve yön Y_h

```
R_h = close(D_h) / ipo_price − 1          h ∈ {1, 3, 5, 10}
Y_h = 1[ close(D_h) > ipo_price ]         (eşitse 0)
```

- `close(D_h)` D_h seansının resmî THB kapanışıdır. `ipo_price` resmî kesin halka arz fiyatıdır (H99'da MASTER'dan, canlıda `registry/inputs/<T>.json`'dan).
- Hesap kesin kesirle yapılır (`outcomes.exact_return`, eski koddan aynen): kapanış ve fiyat `Fraction`'a çevrilir, bölünür, sonra 50 anlamlı haneli Decimal metnine yazılır ve sondaki sıfırlar atılır. Sonuç 0'sa metin `"0"`'dır.
- H99'un TARGETS dosyası bu kesrin payını ve paydasını ayrıca taşır; üretici ikisinin tutarlılığını sınar.
- Y kesin büyüktür ile tanımlıdır. Örnek: QUICK'in D5 kapanışı 76,60, arz fiyatı 76,60; `R_D5 = 0`, `Y_D5 = 0`. VEYAS'ın D10'u da aynı durumdadır (136 = 136).

**Fiziksel sınır.** Günlük fiyat marjı ±%10 olduğu için tahmin çıktısı `[0,9^h − 1, 1,1^h − 1]` aralığına kırpılır (`horizons.physical_return_bounds`): D1 [−0,1; 0,1], D3 [−0,271; 0,331], D5 [−0,40951; 0,61051], D10 [−0,6513…; 1,5937…]. Bu sınır yalnız tahmin içindir. Gerçekleşen değer fiyat adımı yüzünden sınırı çok az aşabilir (LILAK, BORLS); skorlama ham gerçekleşen değeri kullanır.

Kaynak dosyalar: `borsai/outcomes.py` (`exact_return`), `borsai/horizons.py`, `data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_d1_d3_d5_d10_targets.csv`.

### 3.5.4 H99'daki etiket dağılımları

Hepsi `data/training_table.csv`'den ölçüldü.

Y = 1 sayıları (99 arz üzerinden):

| Ufuk | D1 | D3 | D5 | D10 |
|---|---|---|---|---|
| Y = 1 | 89 | 80 | 77 | 70 |
| Y = 0 | 10 | 19 | 22 | 29 |

Her seansta tavan kapatan arz sayısı:

| Seans | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Tavan | 81 | 70 | 67 | 54 | 48 | 46 | 39 | 30 | 26 | 25 |

Seri uzunluğu L'nin dağılımı:

| L | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Arz | 18 | 11 | 4 | 13 | 12 | 8 | 6 | 6 | 4 | 3 | 14 |

L ≥ 1 / 3 / 5 / 10 olan arz sayısı: 81 / 66 / 41 / 14.

Kaynak dosyalar: `data/training_table.csv`, `tests/test_training_table.py`.

### 3.5.5 Örnek hesap: NETGL

NETGL'in arz fiyatı 25,52 TL'dir (`registry/inputs/NETGL.json`). İlk işlem günü 2026-09-17'dir. `data/outcomes/NETGL.csv`'den on seans:

| h | Seans | Kapanış | Üst limit | Tavan | R_h | Y_h |
|---|---|---|---|---|---|---|
| 1 | 2026-09-17 | 28,06 | 28,06 | 1 | 0,0995297805… | 1 |
| 2 | 2026-09-18 | 30,86 | 30,86 | 1 | — | — |
| 3 | 2026-09-21 | 33,94 | 33,94 | 1 | 0,3299373040… | 1 |
| 4 | 2026-09-22 | 30,56 | 37,32 | 0 | — | — |
| 5 | 2026-09-23 | 27,52 | 33,60 | 0 | 0,0783699059… | 1 |
| 6 | 2026-09-24 | 24,78 | 30,26 | 0 | — | — |
| 7 | 2026-09-25 | 22,32 | 27,24 | 0 | — | — |
| 8 | 2026-09-28 | 20,10 | 24,54 | 0 | — | — |
| 9 | 2026-09-29 | 18,09 | 22,10 | 0 | — | — |
| 10 | 2026-09-30 | 16,29 | 19,89 | 0 | −0,3616771159… | 0 |

Adım adım:

1. **Seanslar.** 2026-09-19/20 ve 2026-09-26/27 hafta sonudur; sayılmaz. Bu aralıkta tatil yoktur. Bütün satırlarda `halt_flag = 0`, `half_day = 0`, `shifted_by_suspension = 0`.
2. **Tavan.** D1, D2, D3'te kapanış = üst limit (Decimal eşit). D4'te 30,56 ≠ 37,32. Seri D4'te kırılır: **L = 3**.
3. **D10 getirisi.** R_D10 = 16,29 / 25,52 − 1. Kesin kesir: 1629/2552 − 1 = −923/2552. 50 anlamlı haneli metin: `-0.3616771159874608150470219435736677115987460815047`. Kapanış arz fiyatının altında olduğu için **Y_D10 = 0**.
4. **D1 getirisi.** 28,06 / 25,52 − 1 = 127/1276 = 0,0995297805…; tavan olmasına rağmen tam 0,1 değildir (§3.5.1).

Kaynak dosyalar: `data/outcomes/NETGL.csv`, `registry/inputs/NETGL.json`, `borsai/outcomes.py`.

## 3.6 Özellikler

Özellik (feature), modele giren sayısal girdidir. Projede üç aile vardır: talep toplama **sonrası** listeleme öncesi bilinen f1–f5 (ve f6, f1r), talep toplama **öncesi** planlanan yapıdan pb1–pb4 ve izlenebilirlik için tutulan rejim etiketi. Her özelliğin tanımı kodda tek bir yerde yazılıdır; eğitim ve tahmin aynı fonksiyonu çağırır.

### 3.6.1 f1–f5: V1.5 çekirdek özellikleri

Tanımlar `borsai/features.py`'dedir (`compute_features`). Eski repodaki canlı tahmin kodundan değiştirilmeden taşındı ve H99'un READY dosyasındaki değerlerle 99 arzın hepsinde Decimal olarak eşittir.

| Ad | Formül | Birim | H99'da (min / medyan / maks) |
|---|---|---|---|
| f1 | Kaynakta bildirilen `ipo_size_tl`; yoksa `ipo_price_tl × shares_offered` | TL | 290,87 milyon / 1,40 milyar / 6,825 milyar |
| f2 | `shares_offered / post_ipo_share_capital × 100` | % (halka açıklık) | 10,03 / 25 / 40,47 |
| f3 | `total_demand_multiple` (toplam talep katı) | kat | 1,0 / 3,24 / 14,6 (97 dolu) |
| f4 | `capital_increase_shares / shares_offered × 100` | % (sermaye artırımı payı) | 22,22 / 75 / 100 |
| f5 | 1 yalnız f3 eksikse, değilse 0 | 0/1 | 2 arzda 1 |

Hesap ayrıntıları:

- **Aritmetik bağlamı.** Eski kod bölme ve çarpmayı Python'un varsayılan Decimal bağlamında (28 anlamlı hane, `ROUND_HALF_EVEN`) yapıp sonucu 10 ondalığa `ROUND_HALF_UP` ile yuvarlıyordu. Yeni kod bu bağlamı açıkça kurar (`LEGACY_DECIMAL_CONTEXT`), ortam ayarına bağlı kalmaz. Sondaki sıfırlar atılır: f2 = `"28"`, f4 = `"71.4285714286"`.
- **f1'in kaynak değeri.** H99'da 95 arzda kaynak değer fiyat × paya eşittir. Dört arzda (OBAMS, AKFIS, DSTKF, KLYPV) kaynak değer tam TL'ye yuvarlanmıştır; fark en çok 0,46 TL'dir. Model bu kaynak değerlerle eğitildi; port bunu korur. Şartnamedeki "ln(fiyat × pay)" yazımı ile bu tek tanım arasındaki fark `docs/SPEC_DEVIATIONS.md` A1'de kayıtlıdır; ln farkı ~1e-9'dur.
- **f3 eksik olabilir; eksik ≠ 0.** Talep katı bilinmiyorsa değer boş kalır; asla sıfır yazılmaz.
- **f5** ham özelliklerde yoktur; ön işlemede türetilir (§3.7).

Girdi hataları etiketli bir istisna (`FeatureError`) verir; çıplak `ZeroDivisionError` dışarı sızmaz:

| Kod | Ne zaman |
|---|---|
| `INPUT_MISSING` | zorunlu alan boş, `None` ya da `DATA_NOT_FOUND` |
| `INPUT_NOT_NUMERIC` | sayıya çevrilemiyor ya da sonsuz |
| `INPUT_NOT_POSITIVE` | fiyat, pay, sermaye, f3 ya da büyüklük ≤ 0 |
| `INPUT_NEGATIVE` | `capital_increase_shares` < 0 |
| `DIVISION_BY_ZERO` | payda (pay ya da sermaye) sıfır |
| `INPUT_INCONSISTENT` | sermaye artırımı payı satılan paydan büyük ya da satılan pay arz sonrası sermayeden büyük |

Tahmin tarafı (`borsai/predict.py`) bunlara model düzeyinde ret ve uyarılar ekler: f3 boşsa `F3_MISSING` ile ret; f3'ün filtre durumu eğitim moduna açıkça zıtsa `F3_FILTER_STATUS_CONFLICT` ile ret; f4 = 0 ise `F4_ZERO_NO_TRAINING_EXAMPLE` uyarısı (H99'da en küçük f4 22,2'dir, yani eğitimde örneği yoktur); f1–f4 eğitim aralığı dışındaysa `OUT_OF_TRAINING_RANGE` uyarısı; f3 eğitim p05/p95 dışındaysa kırpma ve `F3_WINSORIZED` uyarısı.

Kaynak dosyalar: `borsai/features.py`, `borsai/predict.py` (satır 1–45), `docs/DATA_NOTES.md` §1, §4, §5, `docs/SPEC_DEVIATIONS.md` A1.

### 3.6.2 f6: market20 (XU100'ün 20 seanslık getirisi)

f6, arzın ilk işlem gününden hemen önceki piyasa havasını ölçer. Tanım (`borsai/market20.py`, `SPEC_MARKET20_V0` §2):

```
sessions = takvimde resmî seans sayılan günler (artan)
i   = bisect_left(sessions, ref_date) − 1      # ref_date'ten KESİN önceki son seans
S0  = sessions[i]
S20 = sessions[i − 20]                          # 21 kapanış, 20 aralık
f6  = XU100[S0] / XU100[S20] − 1                # Decimal, 60 hane, ROUND_HALF_EVEN
```

`bisect_left`, sıralı bir listede bir değerin girebileceği en soldaki konumu bulur; bir eksiği "ref_date'ten kesin önceki son seans"tır.

**ref_date nedir?**

- Eğitimde, backtest'te ve nihai fit'te ref_date = T (ilk işlem günü).
- Canlı kayıtta, kayıt T'den önce yapıldıysa ref_date = kayıt tarihi (İstanbul). Böylece S0, tahmin gününden önceki son seanstır; o günün kapanışı henüz yayımlanmamış olabileceği için gün içi bilgi kullanılmaz (`ref_date_rule = LIVE_PREDICTION_DATE`).
- Geç kayıtta (kayıt T'de ya da sonrasında) ref_date = T (`LATE_RECORD_T_SPEC_MARKET20_V0_4E`).
- Eski kohortta ref_date = T, Takvim C ile (`OOT_FIRST_TRADING_DATE_SPEC_MARKET20_V0_4E`).

**Hangi takvim, hangi XU100?**

| Kullanım | Takvim | XU100 dosyası | Fonksiyon |
|---|---|---|---|
| H99 eğitimi / backtest | B | `…pinned_through_20260819.json` | `h99_market20` |
| Canlı ve geç kayıt | B + uzatma | en yeni pinli (`xu100_graphic_20260922.json`) | `load_live_sources` |
| Eski kohort | C | en yeni pinli | `load_oot_sources` |

Canlı ve eski kohort kaynakları yüklenirken takvimin seans günleri kümesi ile XU100 kayıt günleri kümesi ilgili aralıkta karşılaştırılır; fark varsa durulur (`check_calendar_vs_xu100`). Bu, ilan dışı kapanışları ya da eksik kayıtları yakalar.

**Geçerlilik kuralları.** f6 asla doldurulmaz (impute edilmez). Kurallardan biri tutmazsa sonuç ret kodudur:

| # | Kural | Ret kodu |
|---|---|---|
| 1 | Takvim `ref_date − 1` gününü içeriyor | `CALENDAR_NOT_COVERING` |
| 2 | i ≥ 20 (yeterli geçmiş) | `INSUFFICIENT_HISTORY` |
| 3 | Penceredeki 21 seansın hepsinde XU100 kapanışı var | `XU100_CLOSE_MISSING` |
| 4 | `ref_date − S0 ≤ 12` takvim günü | `STALE_S0` |
| 5 | Canlıda `T − ref_date ≤ 12` takvim günü | `PREDICTION_TOO_EARLY` |
| 6 | Kayıtlar yalnız `XU100`; aynı tarihte çelişen iki değer yok; değer > 0 | `XU100_INTEGRITY` |
| 7 | `hisTs < ref_date` olmayan kayıt hiç okunmaz (as_of koruması) | (test) |

Kural 1 eski koddaki bir hatayı kapatır: eski kod takvim 2026-08-19'da bittiği hâlde 2026-09-30 için sessizce S0 = 2026-08-19 döndürüyordu.

**H99'da ölçülen.** Takvim B ile 99/99 arzda f6 hesaplanır. Değerler −0,1117 … +0,1548, medyan +0,0230. T − S0 her arzda 1–3 gündür. En erken S20 2023-08-23'tür. Aynı fonksiyon Takvim A ile çağrılsaydı 6 arz (HATSN, DMRGD, MEKAG, DOFER, MHRGY, BORLS) `INSUFFICIENT_HISTORY` ile reddedilirdi; Takvim B'nin seçilme nedeni budur.

**Kayıt biçimi.** Dondurma kaydı f6 bloğunu şu alanlarla saklar: `ref_date, f6, refusal, S0_date, S20_date, close_S0, close_S20, calendar_sha256, xu100_sha256` (+ `ref_date_rule`, `calendar`, `xu100_file`). Decimal'ler metin olarak yazılır.

**NETGL örneği** (`registry/records/NETGL/`): geç kayıt olduğu için ref_date = T = 2026-09-17. S0 = 2026-09-16 (kapanış 13.122,58), S20 = 2026-08-19 (kapanış 14.458,98). f6 = 13122,58 / 14458,98 − 1 = −0,0924269900… Takvim sha'sı `<B>+<uzatma>` biçimindedir.

Ön işlemede f6'ya log, kırpma, doldurma ya da eksiklik göstergesi uygulanmaz; yalnız sıfır varyans denetimi ve z-skor (§3.7).

Kaynak dosyalar: `borsai/market20.py`, `borsai/freeze.py` (`market20_for_record`), `docs/specs/SPEC_MARKET20_V0.md` §2–§4, §11, `registry/records/NETGL/*.json`.

### 3.6.3 f1r: reel arz büyüklüğü ve TÜFE'nin T − 2 ay kuralı

f1 nominal TL'dir. Enflasyon yüzünden 2021'deki 1 milyar TL'lik arz ile 2026'daki 1 milyar TL'lik arz aynı büyüklükte değildir; eski kohort eğitime katılınca bu fark belirginleşir. Faz 7'nin tavan modelleri (`ceiling_hazard_v1_real`, `_pooled`) ve düşen arz modelleri bu yüzden f1'i TÜFE ile 2025 fiyatlarına çevirir:

```
size_TL     = f1 (aynı tek tanım: kaynak ipo_size_tl ya da fiyat × pay)
m           = T'nin yılı-ayı
tufe_month  = m − 2 ay
f1r_ham     = size_TL / (TÜFE[tufe_month] / 100)       birim: 2025 TL
f1r         = ln(f1r_ham)   (ön işlemede, kırpmadan sonra)
```

Örnekler `borsai/tufe.py`'den: T = 2026-09-25 → 2026-07; T = 2026-10-01 → 2026-08; T = 2020-01-06 → 2019-11. Dosyanın 2019-11'den başlamasının nedeni budur: eski kohortun ilk T'si 2020 Ocak'tır.

**Neden iki ay geri?** Ay m'nin endeksi m + 1'in 3'ünde (hafta sonu ya da bayramsa sonraki iş günü) saat 10:00'da yayımlanır. Dolayısıyla m − 2'nin endeksi en geç m − 1'in ilk günlerinde yayımlanmıştır; T ise m ayının içindedir. Kural her T için yayımlanmış bir değer verir; T ayın 1'i olsa bile. Gecikme log ölçeğinde küçüktür.

**Bekçiler ve ret kodları** (`tufe.index_for`, `tufe.verify_pin`):

| Kod | Ne zaman |
|---|---|
| `TUFE_MISSING` | tufe_month dosyada yok |
| `TUFE_NOT_PIT` | o ayın `release_date`'i T'den önce değil (kural gereği olmamalı; yine de bekçi) |
| `TUFE_FILE_MISMATCH` | dosyanın pinli öneki değişmiş (eski bir satır, temel yıl ya da zincirleme değişmiş) |

Canlı kayıtta deflatörlü bir model varken ilgili ay dosyada yoksa kayıt **hiç yazılmaz** (`freeze.TufeMissing`); hata iletisi eksik ayı ve ekleme komutunu söyler.

**Ay ekleme veri sürümünü değiştirmez.** Yeni ay dosyanın sonuna bir satırdır; eski satırlar bayt bayt aynı kalır. Bunu güvenceye almak için pin, bütün dosyanın değil, başlık dahil `through_month` satırına kadarki baytların sha256'sıdır (`prefix_sha256`). Şu anki pin: `through_month = 2026-08`, `prefix_sha256 = 3d61cbcf…` (`borsai/specs.py: TUFE_PIN`). Ekleme `build_tufe_csv.py --append-month` komutuyla yapılır; komut yeni tablonun eski her ayı aynen verdiğini, [2025=100] temelinde olduğunu ve m'de bittiğini denetler; tam derleme yeni dosyayı bayt bayt üretmezse yazdığı her şeyi geri alır. Bu kopyada dosya 2026-08'de biter; `docs/PROVENANCE.md` §11a ilk gerçek eklemenin Eylül 2026 TÜFE'si olacağını yazar.

**NETGL örneği.** T = 2026-09-17 → tufe_month = 2026-07. Endeks 132,31 (bülten 58297, yayım 2026-08-03). f1 = 2.233.000.000 TL. f1r_ham = 2.233.000.000 / 1,3231 = 1.687.703.121,457… (2025 TL). Bölme `predict_hazard.real_size`'da 60 haneli Decimal ile tek yuvarlamayla yapılır.

Kaynak dosyalar: `borsai/tufe.py`, `borsai/specs.py` (`TUFE_PIN`, `DEFLATOR`), `borsai/freeze.py` (`TufeMissing`, `tufe_for_record`), `data/raw/tuik/build_tufe_csv.py`, `docs/specs_faz7/SPEC_HAZARD_V1.md` §3.2.

### 3.6.4 PB özellikleri: pb1–pb4

PB ("pre-bookbuilding", talep toplama öncesi) modelleri talep katı henüz yokken yalnız SPK onaylı **planlanan** yapıdan tahmin yapar. Girdiler sekiz alandır (`PB_REQUIRED_FIELDS`):

| Alan | Anlamı (SPK tablosu sütunu) |
|---|---|
| `ipo_price_try` | Satış fiyatı (tek değer olmalı) |
| `planned_pre_ipo_capital` | Mevcut Sermaye |
| `planned_post_ipo_capital` | Yeni Sermaye |
| `planned_capital_increase_shares` | Bedelli |
| `planned_existing_share_sale` | Mevcut Pay Satışı |
| `planned_base_offer_shares` | Bedelli + Mevcut Pay Satışı (taban arz) |
| `planned_additional_sale_ceiling` | Ek Pay Satışı tavanı |
| `planned_max_offer_shares` | taban + ek satış tavanı |

Formüller (eski `pb_core4.py`'den aynen; `features.compute_pb_features`):

```
pb1 = ln(ipo_price_try × planned_base_offer_shares)                    Decimal 60 hane → binary64
pb2 = planned_base_offer_shares / planned_post_ipo_capital × 100        kesin kesir → binary64
pb3 = planned_capital_increase_shares / planned_base_offer_shares × 100 kesin kesir → binary64
pb4 = planned_additional_sale_ceiling / planned_base_offer_shares × 100 (özellik değil; yalnız doğrulama ve uyarı)
```

Zorunlu özdeşlikler (Decimal, tam eşitlik):

- ID-A: `planned_post_ipo_capital = planned_pre_ipo_capital + planned_capital_increase_shares`
- ID-B: `planned_base_offer_shares = planned_capital_increase_shares + planned_existing_share_sale`
- ID-C: `planned_max_offer_shares = planned_base_offer_shares + planned_additional_sale_ceiling`
- ayrıca taban > 0, sermaye > 0, fiyat × taban > 0; pb2 ve pb3 (0, 100] içinde; pb4 ≥ 0.

Ret kodları: `PB_FIELD_MISSING` (alan boş ya da ayrıştırılamıyor), `PB_IDENTITY` (özdeşlik ya da aralık ihlali; alan adı `ID-A` vb.), `PB_PRICE_RANGE` (fiyat "10-12" gibi bir aralık). Doldurma yoktur.

**H99'da ölçülen** (`data/raw/PREBOOKBUILD_…_R2_99.csv`): 99/99 satırda üç özdeşlik tutar. pb1 19,49 / 21,13 / 22,64 (min / medyan / maks); pb2 10,01 / 25 / 40,47; pb3 22,2 / 75 / 100 (17 arzda tam 100); pb4 92 arzda 0, 5 arzda 20, birer arzda 18,4 ve 10. pb4'ün özellik olmamasının nedeni bilgi içeriğinin 7 satırdan ibaret olmasıdır.

Planlanan ≠ nihai: PB fiyatı 99 arzın hiçbirinde nihai fiyattan farklı değildir; planlanan taban pay adedi 10 arzda nihai `shares_offered`'dan farklıdır. Yani pb1–pb3 çoğu arzda f1, f2, f4'e eşittir; PB'nin asıl farkı f3/f5'in yokluğu ve bilgi kesimidir (§3.8.4).

PB dosyasının diğer önemli alanları: `first_bookbuilding_date` (ilk talep toplama günü B; PB modellerinin bilgi kesimi), `spk_publication_date`, `spk_bulletin`, `price_source_semantics` (99'unda `SPK_APPROVED_PLANNED_IPO_PRICE`), `additional_sale_semantics`, `pit_status` (99'unda `PASS`, kural `SPK_PUBLICATION_DATE < FIRST_BOOKBUILDING_DATE`). Yükleyici (`data.load_pb`) her satırda `spk_publication_date < first_bookbuilding_date < first_trading_date` sırasını denetler. Ölçülen aralıklar: SPK yayını → talep toplama 4 / 6 / 13 gün; talep toplama → ilk işlem 4 / 8 / 12 gün (min / medyan / maks). Bu dosya `data_version.json`'da yoktur; sha256'sı `borsai/data.py`'de `PB_SHA256 = 5e52d4d2…` olarak sabitlenir ve her okumada denetlenir.

Kaynak dosyalar: `borsai/features.py` (satır 170–293), `borsai/data.py` (`load_pb`), `data/raw/PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv`, `docs/specs/SPEC_PB_V0.md` §1, §2, §5.

### 3.6.5 Tahsis rejimi etiketi

Halka arzlarda pay dağıtım kuralları yıllar içinde değişti. Kod bunu bir tarih kuralıyla etiketler (`registry.ALLOC_REGIMES`):

| Talep toplama başlangıcı | Etiket |
|---|---|
| < 2021-11-11 | `PRE_20211111` |
| 2021-11-11 … 2023-03-29 | `THRESH100_20211111` |
| ≥ 2023-03-30 | `EQUAL_DIST_20230330` |

`data.alloc_regime(regime_date)` bu kuralın tek tanımıdır. `regime_date` talep toplamanın ilk günüdür (H99'da PB dosyasının `first_bookbuilding_date`'i, eski kohortta girdi belgesinin `bookbuilding_start`'ı). H99'un 99 arzının hepsi `EQUAL_DIST_20230330`'dır. Havuzlanmış tavan modelinde bundan cezasız bir ikili terim türetilir: `r = 1[alloc_regime ≠ EQUAL_DIST_20230330]`; canlıda ve H99'da r = 0'dır.

Kaynak dosyalar: `borsai/data.py` (`alloc_regime`), `borsai/registry.py` (satır 849–850), `borsai/specs.py` (`REGIME`), `docs/specs_faz7/SPEC_HAZARD_V1.md` §3.3.

## 3.7 Ön işleme: fold içi dönüşümler

Ham özellikler modele doğrudan girmez. `borsai/preprocess.py`, eski V1.3 "11 adımlı" ön işlemenin portudur ve **yalnız eğitim fold'undan öğrenir**: eşikler, medyanlar, ortalama ve standart sapma test arzını hiç görmeden hesaplanır, sonra test arzına aynen uygulanır. Bu, geleceğin sızmasını önler.

### 3.7.1 Adımlar (V1.5 tarifi)

1. **f3 karşılaştırılabilirlik filtresi.** Eğitimdeki f3'ü dolu satırların `total_demand_filter_status` modu (en sık değeri) bulunur. Durumu moda **açıkça zıt** olan (biri `FILTERED`, öteki `UNFILTERED`) satırın f3'ü boşaltılır. Eşitlikte mod deterministik seçilir: en yüksek sayı, eşitse alfabetik en küçük metin. Eski kodda bu seçim Python küme sırasına bağlıydı; tek davranış farkı budur. H99'da tam `FILTERED` metni hiç geçmediği için filtre hiçbir satırı boşaltmaz.
2. **Eksiklik sayımı.**
3. **%40 kuralı.** Bir özelliğin eğitimde eksik oranı %40'tan kesin büyükse o özellik o fold'dan düşer.
4. **f3 kırpma (winsor).** Eğitimdeki dolu f3 değerlerinin Type-7 p05 ve p95 kantilleri kesin kesirle (`Fraction`) hesaplanır; değerler bu aralığa kırpılır. Type-7, R'ın ve numpy'ın varsayılan doğrusal kantilidir: `h = (n − 1)p + 1` sıralı konumu iki komşu değer arasında doğrusal ara değerlenir.
5. **Medyanla doldurma.** Eksik f3, kırpılmış değerlerin medyanıyla doldurulur.
6. **f5.** f3 eksik olup doldurulan satıra 1, diğerlerine 0 (yalnız f3 düşmediyse).
7. **log.** f1'e doğal logaritma (Decimal, 60 hane). f1 ≤ 0 ise hata (`NonPositiveLogInputError`); kırpılmaz.
8. **Sıfır varyans.** Eğitimde tek değer alan sütun düşer. f3 düşerse f5 de düşer (`F3_COUPLED_DROP`).
9. **z-skor.** `z = (x − ortalama) / std`, std nüfus standart sapmasıdır (ddof = 0, n'e bölünür). f1 için ortalama ve std log uzayında 60 haneli Decimal'dedir; diğerleri için ortalama ve varyans kesin kesirdir. `binary64`'e (float) çevrim en sonda bir kez yapılır.

Ek bütünlük denetimleri: sonsuz değer (I1), pozitif std (I2) ve "kesin olarak farklı değer sayısı float'a çevrildikten sonra da korunmalı" (I3). İhlalde `NumericRepresentationIntegrityError`; tolerans ya da onarım yoktur.

Bilerek korunan iki eski ayrıntı: f1'in z payındaki çıkarma 28 haneli bağlamda yapılır (eski kod ortam bağlamını kullanıyordu); test satırının filtre kararı, filtre **sonrası** eğitim satırlarının moduna bakar.

H99'un 97 dolu f3'ü üzerinde (tek bir fold değil, bilgi için) p05 = 1,1487, p95 = 8,332'dir.

### 3.7.2 Tarifler

Aynı adımlar farklı modellerde farklı özellik kümeleriyle çalışır. `Recipe` nesnesi hangi özelliğin hangi adımdan geçtiğini söyler:

| Tarif | Sütunlar | Kırpma | log | Doldurma, f5, %40 | Kullanan |
|---|---|---|---|---|---|
| `V1_5` | f1, f2, f3, f4 (+f5) | f3 | f1 | var | `v1_5_h99`, `v1_6_h99` |
| `MARKET20` | f1–f5 + f6 | f3 | f1 | var (f6'da yok) | `v1_5_market20_v0` |
| `CEILING` | f1, f2, f3 | f3 | f1 | yok; eksik = hata | `ceiling_hazard_v0` |
| `PB` | pb1, pb2, pb3 | yok | yok | yok | `pb_v0` |
| `PB_CEILING` | pb1, pb2 | yok | yok | yok | `pb_ceiling_v0` |
| `CEILING_V1_CLIP` | f1, f2, f3 | üçü de | f1 | yok | `ceiling_hazard_v1_clip` |
| `CEILING_V1_REAL` | f1r, f2, f3 | üçü de | f1r | yok | `ceiling_hazard_v1_real`, `_pooled` |
| `FALL_V0` | f1r, f3, add_sale | f1r, f3 | f1r, f3 | yok | `fall_d10_v0_h99`, `fall_d10_v0_pooled` |
| `FALL_V0_ADDSALE` | add_sale | yok | yok | yok | `fall_d10_v0_addsale` |

PB tariflerinde pb1 özellik tanımında zaten logaritmalıdır; ön işleme yalnız z-skor uygular. `add_sale` ek satış bayrağıdır: `1[additional_sale_shares > 0]`. Kırpma Faz 7 tariflerinde ham değerde, log'dan önce yapılır.

Kaynak dosyalar: `borsai/preprocess.py`, `docs/specs/SPEC_CEILING_V0.md` §4, `docs/specs/SPEC_MARKET20_V0.md` §2, `docs/SPEC_DEVIATIONS.md` J8, K4.

## 3.8 Eğitim tabloları

### 3.8.1 v1: `data/training_table.csv`

Modellerin çoğu bu tablodan eğitilir. Her arz için bir satır vardır: **99 satır, 31 sütun.** Sıra önce `first_trading_date`, sonra `ticker` artan. Biçim UTF-8, BOM yok, LF satır sonu. Eksik değer boş hücredir (kaynaktaki `DATA_NOT_FOUND`).

| Grup | Sütunlar | Kaynak |
|---|---|---|
| Kimlik | `ticker`, `first_trading_date`, `point_in_time_status` | MASTER, PROV (READY ile eşitlik denetlenir) |
| Sayısal girdiler | `ipo_price_tl`, `shares_offered`, `post_ipo_share_capital`, `capital_increase_shares`, `existing_share_sale_shares`, `total_demand_multiple` | MASTER (`ipo_price` → `ipo_price_tl`, `existing_share_sale` → `existing_share_sale_shares`) |
| Etiket girdiler | `total_demand_multiple_origin`, `total_demand_filter_status` | MASTER |
| Ek satış | `additional_sale_shares` | MASTER |
| Getiri | `R_D1`, `R_D3`, `R_D5`, `R_D10` | TARGETS `target_return` |
| Yön | `Y_D1`, `Y_D3`, `Y_D5`, `Y_D10` | TARGETS `above_ipo_flag` |
| Tavan | `ceiling_close_D1` … `ceiling_close_D10` | SESSIONS `close` ve `upper_limit` |
| Seri | `ceiling_streak_L` | tavan sütunlarından |

Eksik hücreler yalnız iki sütundadır: `total_demand_multiple` (2: ALBTN, ENDAE) ve `additional_sale_shares` (4: KARCL, MASFN, ALBTN, METEN). `point_in_time_status` 20 satırda `PASS`, 79 satırda `UNKNOWN`'dır.

**Üretici** `data/build_training_table.py`'dir. Yalnız kopyalar ve denetler. Durduğu durumlar (`SourceInvariantError`):

- MASTER'da tekrarlı ticker; MASTER, READY ve PROV'da ticker kümeleri farklı.
- PROV ile READY'nin `point_in_time_status`'ü farklı ya da `PASS`/`UNKNOWN` dışında.
- READY ile MASTER'ın ilk işlem günü farklı.
- Sayısal alan `Decimal`'e çevrilemiyor.
- Bir arzın seansları 1…10 değil; 1. seans tarihi ilk işlem günü değil; seans ya da hedef `OFFICIAL_VERIFIED`/`NO_CONFLICT` değil.
- Hedefin seans tarihi ya da kapanışı SESSIONS'tan farklı; hedefteki arz fiyatı MASTER'dan farklı.
- `kapanış / arz fiyatı − 1` kesin kesri TARGETS'taki pay/payda kesrine eşit değil.
- `above_ipo_flag` kapanış > fiyat testiyle tutarsız.
- Bir seansta kapanış üst limitin üstünde.

Tavan sütunları üreticide SESSIONS'ın `close` ve `upper_limit` alanlarının Decimal eşitliğinden yeniden hesaplanır; L "ilk 0'da dur" kuralıyla sayılır.

**Sürüm dosyası** `data/data_version.json`'dur. İçeriği: tablonun sha256'sı (`b307cd0e…`), bayt sayısı (29.934), satır ve sütun sayısı, sütun listesi, sıra kuralı, kodlama, eksik değer kuralı, ilk işlem günü aralığı (2023-09-22…2026-08-06), `outcome_sessions_through` (2026-08-19), üreticinin sha256'sı (`0d0626db…`) ve beş kaynak dosyanın (MASTER, READY, PROV, TARGETS, SESSIONS) yol ve sha256'sı. Sürüm dosyasının kendi sha256'sı `a0c7d082…`'dir; bu değer `borsai/specs.py`'de `H99_DATA_VERSION_SHA256` olarak yazılıdır ve her model şartnamesinin `training.data_version_sha256` alanına girer. `fit`, veri sürümü şartnameyle tutmazsa durur.

`outcome_sessions_through = 2026-08-19` H99'daki en geç hedef seansıdır: QUICK'in D10'u.

Kaynak dosyalar: `data/training_table.csv`, `data/data_version.json`, `data/build_training_table.py`, `docs/DATA.md`, `tests/test_training_table.py`.

### 3.8.2 Yükleyici: `borsai.data.load_dataset`

Modeller tabloyu doğrudan okumaz; `load_dataset()` üzerinden alır. Yükleyici şunları yapar:

1. Tablonun ve beş kaynağın sha256'sını `data_version.json` ile karşılaştırır.
2. Satır sayısını, ticker tekilliğini ve sırayı denetler.
3. Her satır için MASTER ile arz fiyatı, pay adedi ve ilk işlem günü eşitliğini; TARGETS ile R, Y, arz fiyatı eşitliğini; D1 seans tarihi = ilk işlem günü kuralını denetler.
4. Tabloda olmayan üç bilgiyi kaynaklardan okur: her ufkun `target_session_date`'i (TARGETS), D1…D10 seans tarihleri (SESSIONS; fiyat sütunları okunmaz) ve `ipo_size_tl` (MASTER; f1 için).
5. `ceiling_streak_L`'nin baştaki tavan sayısına eşit olduğunu sınar.
6. En geç hedef seansının `outcome_sessions_through`'a eşit olduğunu sınar.

Sonuç değişmez (`frozen`) bir `Dataset` nesnesidir: `IPORow` satırları, veri sürümü sha'sı, tablo sha'sı ve kesim tarihi.

Kaynak dosyalar: `borsai/data.py` (satır 1–237).

### 3.8.3 v2: `data/training_table_v2.csv`

Faz 7'de eski kohortun (H99 öncesi, 2020–2023) açık kümesi eğitime eklendi. v2 tablosu **170 satır, 39 sütundur**: H99'un 99 satırı + eski kohortun açık kümesinden 71 arz. v1 tablosu, sürüm dosyası ve üreticisi değiştirilmedi.

- H99 satırlarında ilk 31 sütun `training_table.csv` ile hücre hücre aynıdır.
- Açık küme satırlarında girdiler `registry/oot/inputs/<T>.json`'dan (`registry.model_inputs`), sonuçlar `data/outcomes_oot/<T>.csv`'den SPEC_SCORING §3 tanımlarıyla gelir. Her açık üyenin on seansının hepsi `OK` olmalıdır (710/710).
- Kasa (SEALED) üyelerinin hiçbir dosyası okunmaz; tabloda kasa satırı yoktur (`sealed_rows: 0`).

Sekiz ek sütun:

| Sütun | H99'da | Açık kümede |
|---|---|---|
| `ipo_size_tl` | MASTER | girdi belgesi |
| `cohort` | `H99` | `OOT_OPEN` |
| `sale_method` | boş | `OFF_EXCHANGE_BOOKBUILD` 44, `ON_EXCHANGE` 27 |
| `market` | boş | `YILDIZ` 42, `ANA` 29 |
| `alloc_regime` | `EQUAL_DIST_20230330` (99) | `PRE_20211111` 25, `THRESH100_20211111` 31, `EQUAL_DIST_20230330` 15 |
| `alloc_regime_date` | PB `first_bookbuilding_date` | `bookbuilding_start` |
| `tufe_month` | T'nin ayı − 2 | aynı |
| `tufe_index` | o ayın endeks metni | aynı |

Ölçülen: açık kümenin ilk işlem günleri 2020-08-06…2023-09-21 (yıllara göre 2020: 4, 2021: 26, 2022: 20, 2023: 21). `point_in_time_status` açık kümede 71'in hepsinde `PASS`'tir: derleyici her girdi belgesinin her kaynağının ilk işlem gününden önce yayımlandığını ve belge sha'sının tuttuğunu denetler. Açık kümede f3 3 satırda boş, ek satış 1 satırda boştur; f3 kökeni `SOURCE_REPORTED` 50, `CALCULATED_FROM_SOURCE_TOTALS` 15, `SOURCE_REPORTED_APPROX` 3; filtre durumu `UNFILTERED` 35, `NOT_SPECIFIED` 30, `FILTERED` 3. (H99'da hiç olmayan tam `FILTERED` değeri burada 3 satırda vardır. Bu yüzden §3.7.1'deki f3 filtresi havuzlanmış eğitimde gerçekten bir satırı boşaltabilir; havuz modellerinin şartnamesi bunu `F3_FILTER_RULE` ile yazar. Kaç fold'da kaç satır düştüğünü bu bölümde ölçmedim.)

**Sürüm dosyası** `data/data_version_v2.json` kod adı (ticker) taşımaz. Pinleri:

- tablo sha256 `5adda8b2…`, 63.398 bayt; üretici `data/build_training_table_v2.py` sha256 `801626b4…`;
- kaynaklar: `training_table.csv`, `data_version.json`, MASTER ve PB dosyasının sha256'ları;
- kohort dosyası `registry/oot/cohort_pre_h99.csv` için **önek pini**: ilk 47.150 baytın sha256'sı (`7d05b334…`). Dosya yalnız sonuna ekleme alabilir; önceki baytlar değişirse yükleyici durur;
- açık üyelerin girdi dosyaları ve sonuç dosyaları için birer **birleşik sha256** (`85f8ef33…` ve `dae31319…`): her dosya için `ad<TAB>sha256` satırları sıralanıp birlikte hash'lenir;
- TÜFE önek pini (`through_month = 2026-08`).

Sürüm dosyasının kendi sha256'sı `2ee8d51b…`'dir ve `specs.py`'de `V2_DATA_VERSION_SHA256` olarak durur.

**Yükleyici** (`load_dataset_v2`) bütün pinleri denetler, sonra her satırı aynı fonksiyonlarla (`_h99_v2_cells`, `_oot_v2_cells`) kaynaklardan **yeniden üretir** ve diskteki satırla hücre hücre karşılaştırır. Üretici `--check` kipinde diske yazmadan aynı karşılaştırmayı yapar.

Kaynak dosyalar: `data/training_table_v2.csv`, `data/data_version_v2.json`, `data/build_training_table_v2.py`, `borsai/data.py` (satır 285–575), `docs/specs_faz7/SPEC_HAZARD_V1.md` §3.4, `docs/SPEC_DEVIATIONS.md` J19.

### 3.8.4 Eğitim kümeleri ve nokta-zamanında kuralları

Bir tablo birden çok eğitim kümesine bölünür. Kümeler `borsai/specs.py`'de adıyla tanımlıdır:

| Küme | Tablo | n | Tanım |
|---|---|---|---|
| `H99_ALL_ROWS` | v1 | 99 | bütün satırlar (V1.5, V1.6, market20, PB, PB tavan) |
| `H99_F3_PRESENT` | v1 | 97 | f3 dolu satırlar (tavan modelleri) |
| `H99_F3_PRESENT+OOT_OPEN_F3_PRESENT` | v2 | 165 | H99'un 97'si + açık kümenin f3'lü 68'i (havuzlanmış tavan) |
| düşen arz `h99` | v1 | 94 | f3 ve ek satış dolu |
| düşen arz `pooled` | v2 | 161 | 94 + açık kümenin 67'si |
| düşen arz `addsale` | v2 | 165 | ek satış dolu (H99 95 + açık 70) |

**Walk-forward kesimleri** nokta-zamanında kuralının çekirdeğidir (`borsai/backtest.py`):

- **V1.5 planı** (`H99_WALK_FORWARD_STRICT_PRIOR_DATE_MIN_TRAIN_10`): test arzı k ve ufuk h için eğitim kümesi, h ufkunun hedef seans tarihi k'nin ilk işlem gününden **kesin önce** olan arzlardır: `target_session_date(j, D_h) < T(k)`. Aynı gün ve sonrası dışlanır. Eğitim n'i 10'dan azsa fold skorlanmaz. H99'da 351 skorlanabilir fold vardır (D1/D3/D5/D10: 89/88/87/87).
- **PB planı:** kesim ilk talep toplama günü B(k)'dir: `target_session_date(j, D_h) < B(k)`. PB modelleri talep toplamadan önce çalıştığı için bilgileri daha eskidir.
- **Tavan planları:** her arz için D1…D10 kişi-dönem satırları üretilir; satır ancak seans tarihi kesimden (T ya da B) önceyse eğitime girer. Böylece serisi henüz bitmemiş arzlar sansürlü (yarım) olarak eğitime katılır.

**Kesim tarihleri ve sıra kuralı.** Dondurulmuş modellerin nihai fit'i H99'un tamamıyla yapılır ama hiçbir eğitim seansı 2026-08-19'dan sonra olamaz. Bu sabit `OUTCOME_CUTOFF = "2026-08-19"` adıyla `scoring.py`, `ceiling_path.py`, `post_d1.py` ve `post_break.py`'de ayrı ayrı denetlenir; `outcomes.py`'de `SEQUENCE_CUTOFF` adını taşır. `LISTING_CUTOFF = "2026-08-06"` ise H99'un son arzının ilk işlem günüdür; ondan sonra listelenen arzlar canlı sicile (§3.9) girer.

**H99'un PIT sınırı.** H99'un 79 arzında girdilerin arz anında yayımlandığı kanıtlı değildir (`UNKNOWN`). Bu, eğitimde bilinçli olarak kabul edilmiş bir zayıflıktır ve tabloda sütun olarak görünür. Canlı arzlarda ve eski kohortun açık kümesinde ise her girdi alanı yayın zamanıyla birlikte saklanır ve denetlenir (§3.9).

Kaynak dosyalar: `borsai/specs.py` (`H99_TRAINING`, `H99_F3_TRAINING`, `POOLED_TRAINING`, `FALL_*_TRAINING`), `borsai/data.py` (`FALL_SETS`), `borsai/backtest.py` (satır 1–35, `plan_folds`, `plan_folds_pb`), `borsai/scoring.py` (satır 504–560).

## 3.9 Canlı arzların girdileri ve paydası

### 3.9.1 Girdi belgesi: `registry/inputs/<T>.json`

2026-08-06'dan sonra listelenen her arz için listeleme öncesi resmî belgelerden bir girdi belgesi yazılır. Şema `borsai.inputs/1`'dir. Üst düzey anahtarlar:

| Anahtar | Anlamı |
|---|---|
| `schema_version` | `borsai.inputs/1` |
| `ticker`, `company` | işlem kodu ve unvan |
| `stage` | `POST_BOOKBUILD_PRE_LISTING` (talep toplama bitti, işlem başlamadı) |
| `collected_at`, `collected_at_basis` | toplama zamanı; `LOCAL_CLOCK_SELF_REPORTED` (kanıt değil) |
| `collection_rules` | toplama kuralları (metin) |
| `first_trading_date_source` | ilk işlem gününün kaynak belgesi |
| `fields` | 20 alan |
| `sources` | belge tablosu: kimlik → tür, yayın zamanı, sha256, yol |

Toplama kuralları belgenin içinde yazılıdır: yalnız resmî belgeler (KAP ve SPK), hepsi ilk işlem gününden önce yayımlanmış; değerler belgedeki yazımdan, binlik noktalar atılıp ondalık virgül noktaya çevrilerek; belgede olmayan alan boş bırakılır ve gerekçe yazılır; tahmin, türetme, ikincil kaynak yok; gerçekleşen sonuç okunmaz.

**20 alan** üç gruptadır (`registry.INPUT_FIELDS`):

- V1.5 alanları (9): `ipo_price_tl`, `shares_offered`, `post_ipo_share_capital`, `capital_increase_shares`, `existing_share_sale_shares`, `total_demand_multiple`, `total_demand_filter_status`, `additional_sale_shares`, `ipo_size_tl`.
- PB alanları (8): `ipo_price_try`, `planned_pre_ipo_capital`, `planned_post_ipo_capital`, `planned_capital_increase_shares`, `planned_existing_share_sale`, `planned_base_offer_shares`, `planned_additional_sale_ceiling`, `planned_max_offer_shares`.
- Tarih alanları (3): `first_trading_date`, `bookbuilding_start`, `bookbuilding_end`.

**Alan yapısı.** Dolu bir alan şu anahtarları taşır: `value` (metin), `source_id`, `source_document`, `source_published_at`, `source_sha256`, `source_path`; çoğunda `quote` (belgedeki birebir alıntı, PDF metin katmanında aranarak doğrulandı); bazılarında `cross_checks` (aynı değeri doğrulayan başka belgelerden alıntılar), `locator` (belgenin neresinden okunduğu), `origin` (f3 için kökeni) ve `pb_semantics`. Boş alan `value: null` ve zorunlu `missing_reason` taşır; ayrıca `checked_sources` ve `evidence` olabilir.

**Denetimler.**

- `validate_inputs`: 20 alanın hepsi var; dolu alanın beş kaynak anahtarı dolu ve `sources` tablosuyla tutarlı; yayın zamanı saat dilimli ISO biçiminde; tarih alanları ISO tarih; f3 kökeni izinli değerlerden (`SOURCE_REPORTED`, `SOURCE_REPORTED_APPROX`, `CALCULATED_FROM_SOURCE_TOTALS`, `CALCULATED_FROM_PRIMARY_TOTALS`); filtre durumu `NOT_SPECIFIED`, `UNFILTERED` ya da `FILTERED`.
- `inputs_pit_problems`: her dolu alanın kaynağı ilk işlem gününden (İstanbul tarihi) **kesin önce** yayımlanmış; belge dosyası diskte var ve sha256'sı tutuyor; istenirse kayıt zamanından sonra yayımlanmamış.
- Testte ayrıca: PB alanlarının hepsi SPK bülteninden gelir ve talep toplama başlamadan önce yayımlanmıştır; PB özdeşlikleri (ID-A/B/C) tutar.

`model_inputs(doc)` modellere giden düz sözlüğü üretir (V1.5 ve PB alanlarının metin değerleri).

**NETGL örneği** (`registry/inputs/NETGL.json`; dört kaynak belge):

| Alan | Değer | Kaynak | Alıntı ya da yer |
|---|---|---|---|
| `ipo_price_tl` | 25.52 | KAP 1662138 (sonuç bildirimi) | "HALKA ARZ FİYATI 25,52"; 3 çapraz denetim |
| `shares_offered` | 87500000 | KAP 1662138 | "SATIŞA SUNULAN PAY ADEDİ 87.500.000" |
| `ipo_size_tl` | 2233000000 | KAP 1662138 | "HALKA ARZ BÜYÜKLÜĞÜ (TL) 2.233.000.000" |
| `post_ipo_share_capital` | 312500000 | KAP 1663155 (işlem başlama) | "312.500.000 TL nominal değerli payları" |
| `capital_increase_shares` | 62500000 | SPK Bülteni 2026/56 | Bedelli sütunu; sonuç belgesi planlananın tamamının satıldığını yazar |
| `existing_share_sale_shares` | 25000000 | SPK Bülteni 2026/56 | Mevcut Pay Satışı sütunu |
| `additional_sale_shares` | 0 | SPK Bülteni 2026/56 | Ek Pay Satışı "-" |
| `total_demand_multiple` | 2.84 | KAP 1662138 ek 1 | "toplamda 2,84 katı kadar talep"; köken `SOURCE_REPORTED` |
| `total_demand_filter_status` | NOT_SPECIFIED | KAP 1662138 ek 1 | belgede "filtre" ifadesi yok |
| `first_trading_date` | 2026-09-17 | KAP 1663155 | "İşlem Görmeye Başlayacağı Tarih 17/09/2026" |
| `bookbuilding_start` / `_end` | 2026-09-09 / 2026-09-11 | KAP 1663155 | "Halka Arz Tarihi 09-11/09/2026" |
| `ipo_price_try` | 25.52 | SPK Bülteni 2026/56 | "25,52 TL sabit fiyat" |
| `planned_pre_ipo_capital` | 250000000 | SPK Bülteni 2026/56 | A.1 tablosu, Mevcut Sermaye |
| `planned_post_ipo_capital` | 312500000 | SPK Bülteni 2026/56 | Yeni Sermaye |
| `planned_capital_increase_shares` | 62500000 | SPK Bülteni 2026/56 | Bedelli |
| `planned_existing_share_sale` | 25000000 | SPK Bülteni 2026/56 | Mevcut Pay Satışı |
| `planned_additional_sale_ceiling` | 0 | SPK Bülteni 2026/56 | Ek Pay Satışı "-" |
| `planned_base_offer_shares` | 87500000 | SPK Bülteni 2026/56 | Bedelli + Mevcut Pay Satışı; ek 1'deki "Toplam 87.500.000" ile denetlendi |
| `planned_max_offer_shares` | 87500000 | SPK Bülteni 2026/56 | taban + ek satış |

Belgelerin yayın zamanları: SPK Bülteni 2026/56 2026-09-03 20:18:20; KAP 1662138 ve eki 2026-09-13 17:30:28; KAP 1663155 2026-09-15 18:10:17 (hepsi +03:00). Hepsi 2026-09-17'den öncedir.

Özdeşlikler NETGL'de tutar:

```
shares_offered        87.500.000 = 62.500.000 (sermaye artırımı) + 25.000.000 (ortak satışı) + 0 (ek satış)
ID-A  312.500.000 = 250.000.000 + 62.500.000
ID-B   87.500.000 = 62.500.000 + 25.000.000
ID-C   87.500.000 = 87.500.000 + 0
f1 = 2.233.000.000 = 25,52 × 87.500.000      (kaynak değer, fiyat × payla aynı)
f2 = 87.500.000 / 312.500.000 × 100 = 28
f3 = 2,84    f4 = 62.500.000 / 87.500.000 × 100 = 71,4285714286    f5 = 0
pb1 = ln(2.233.000.000) = 21,5266…   pb2 = 28,0   pb3 = 71,428…   pb4 = 0
```

**Boş alan örneği: VEYAS.** `total_demand_multiple` boştur. `missing_reason`: sonuç belgesi toplam talep katını yayımlamıyor; tablodaki talep sütunu dağıtım sütununa eşit (toplam 44.375.000; planlanan 65.000.000); kat 0,68 ya da 1,00 olarak **türetilmez**. Filtre durumu da boştur ("f3 yok; filtre durumu uygulanamaz"). Bu yüzden f3 isteyen dört model VEYAS için ret verdi (`registry/ipos.csv` notu: `F3_MISSING`).

Ölçülen: yedi canlı belgenin hepsi 20 alan taşır; VEYAS dışında hiçbirinde boş alan yoktur.

Kaynak dosyalar: `registry/inputs/*.json`, `borsai/registry.py` (satır 134–241), `tests/test_registry_inputs.py`.

### 3.9.2 Kaynak belge klasörleri: `registry/source_docs/`

Her canlı arz için bir klasör vardır; içinde PDF'ler ve bir `MANIFEST.json` (şema `borsai.source_docs/1`). Manifest belge kimliği başına şu alanları tutar: `document_id`, `kind` (`KAP_NOTIFICATION_PDF`, `KAP_ATTACHMENT_PDF`, `SPK_BULLETIN`), `url`, `download_url`, `downloaded_at`, `published_at` ve onun dayanağı `published_at_basis`, `kap_api_publish_date`, `issuer`, `title`, `summary`, `related_stocks`, `path`, `sha256`, `size_bytes`; ek PDF'lerde ayrıca `parent`, `attachment_object_id`, `download_sha256`, `download_transform`; SPK bülteninde `printed_date` ve `http_last_modified`. Yedi klasörde toplam 31 belge vardır: 16 KAP bildirimi, 8 KAP eki, 7 SPK bülteni.

Test (`test_source_manifest_matches_files`) klasördeki dosya kümesinin manifestle aynı olduğunu, her sha256'nın tuttuğunu, URL'lerin yalnız `kap.org.tr` ya da `spk.gov.tr` olduğunu ve KAP eklerinin `%PDF-` ile başlayıp sarmallı indirmeden farklı sha taşıdığını sınar. Bu salt okunur kopyada PDF'ler yoktur; manifestler vardır.

`_ENUMERATION/ENUMERATION.json` paydanın eksiksiz olduğunun kanıtıdır. İçinde: KAP sorguları ve ham yanıt dosyasının sha256'sı; Borsa İstanbul'un 2026-08-01…2026-09-22 arasındaki bildirimlerinin konu sayıları (ör. "Payların İşlem Görmeye Başlaması" 8, "Varantların veya Sertifikaların İşlem Görmeye Başlaması" 10); listeleme benzeri her bildirim ve verilen karar; SPK 2026/44–61 bültenlerinin "İlk Halka Arzlar" onayları; sonuç ("başka arz yok"); ertelenen arz (Bewen Enerji, KAP 1641554).

Kaynak dosyalar: `registry/source_docs/*/MANIFEST.json`, `registry/source_docs/_ENUMERATION/*`, `docs/PROVENANCE.md` §8.

### 3.9.3 Payda: `registry/ipos.csv`

"Payda", canlı doğruluğun hangi arzlar üzerinden hesaplandığıdır. Kural (CLAUDE.md kural 2): 2026-08-07'den (`SCOPE_START`) sonra işlem görmeye başlayan her arz sicile girer; dondurulmadıysa nedeniyle "atlandı" satırı olur. Sessiz dışlama yoktur.

Sütunlar: `ticker, company, first_trading_date, listing_source_id, status, skip_reason, note, added_at`. Dosya yalnız ekleme alır (`append_ipos`). Kurallar (`validate_ipos`):

- `status` ∈ {`FROZEN`, `SKIPPED`, `OUT_OF_SCOPE`}.
- `FROZEN` satırda `skip_reason` boştur; diğerlerinde doludur.
- `skip_reason` ∈ {`NO_RECORD_BEFORE_LISTING`, `PUSH_PROOF_MISSING`, `INPUTS_NOT_AVAILABLE`} ya da `OTHER:<metin>`; `OUT_OF_SCOPE` her zaman `OTHER:` ile başlar.
- `listing_source_id` `KAP_<sayı>` biçimindedir; `added_at` saat dilimli zaman damgasıdır.
- Halka arz satırlarında (`FROZEN`/`SKIPPED`) ticker ve unvan doludur, aynı arz iki kez geçmez, ilk işlem günü ≥ 2026-08-07'dir.

Ölçülen: 26 satır. 7 `FROZEN` (CITAS, TKNKA, VEYAS, KPEKS, INTET, BKRGY, NETGL); 19 `OUT_OF_SCOPE`: 10 varant/sertifika, 3 borsa yatırım fonu, 3 bedelli sermaye artırımı kalan payı, 1 kod değişikliği, 1 pazar değişikliği, 1 ertelenen ve işlem görmeyen halka arz (Bewen Enerji). `SKIPPED` satır yoktur.

Kaynak dosyalar: `registry/ipos.csv`, `borsai/registry.py` (satır 41–131), `docs/specs/SPEC_SCORING.md` §4.

## 3.10 Canlı sonuç dosyaları: `data/outcomes/<T>.csv`

### 3.10.1 Biçim

Her canlı arzın sonucu tek bir dosyadadır: 10 satır (h = 1…10), 16 sütun.

| Sütun | Anlamı |
|---|---|
| `h` | seans sırası (1–10) |
| `session_date` | D_h tarihi |
| `close_raw` | THB `KAPANIS FIYATI` ham metni |
| `upper_limit_raw`, `reference_raw` | THM üst limit ve referans ham metni |
| `trade_count_raw` | THB `TOPLAM SOZLESME SAYISI` |
| `halt_flag` | gün içi geçici durdurma (0/1) |
| `half_day` | yarım gün seansı (0/1) |
| `shifted_by_suspension` | D_1'den bu ufka kadar atlanan seans sayısı |
| `ceiling_close` | 0, 1 ya da `NA` |
| `R_h`, `Y_h` | yalnız h ∈ {1, 3, 5, 10} satırlarında dolu |
| `ipo_price` | girdi belgesindeki arz fiyatı |
| `thb_sha256`, `thm_sha256` | o seansın bülten zip'lerinin sha256'sı |
| `status` | `OK`, `NA_LIMIT`, `PENDING` ya da `TARGET_UNAVAILABLE` |

Yedi canlı arzın ölçülen özeti (hepsinde 10 satırın hepsi `OK`; durdurma, yarım gün ve kayma yok):

| Arz | Arz fiyatı | D1 | D10 | L | D10 kapanış | R_D10 | Y_D10 |
|---|---|---|---|---|---|---|---|
| CITAS | 73,7 | 2026-08-18 | 2026-08-31 | 5 | 128 | +0,7368 | 1 |
| TKNKA | 85,4 | 2026-08-20 | 2026-09-02 | 7 | 190 | +1,2248 | 1 |
| VEYAS | 136 | 2026-08-20 | 2026-09-02 | 0 | 136 | 0 | 0 |
| KPEKS | 94 | 2026-08-21 | 2026-09-03 | 5 | 95,2 | +0,0128 | 1 |
| INTET | 53,6 | 2026-09-01 | 2026-09-14 | 4 | 61,15 | +0,1409 | 1 |
| BKRGY | 12,93 | 2026-09-02 | 2026-09-15 | 0 | 7,77 | −0,3991 | 0 |
| NETGL | 25,52 | 2026-09-17 | 2026-09-30 | 3 | 16,29 | −0,3617 | 0 |

Kaynak dosyalar: `data/outcomes/*.csv`, `borsai/outcomes.py` (`OUTCOME_COLUMNS`, `outcome_rows`).

### 3.10.2 Nasıl güncellenir

Üç komut vardır (`python -m borsai.outcomes …`):

- **`fetch YYYY-MM-DD`**: tek bir seansın THB ve THM'sini indirir; yerelde varsa yalnız manifest sha'sıyla denetler. Kaynak sınaması için kullanılır (Faz 2B'nin ilk commit'inde 2026-08-17 bültenleri böyle alındı; o gün işlem gören yeni arz yoktu).
- **`update [--through YYYY-MM-DD]`**: (1) takvimi yükler; (2) kapsamdaki ilk arzın ilk işlem gününden önceki seanstan başlayarak bugüne (ya da `--through`'a) kadar eksik bültenleri indirir (`download_range`); 404'te ilan dışı kapanış kuralını uygular; (3) takvimi yeniden yükler; (4) kapsamdaki her arz için sonuç satırlarını yalnız yerel bültenlerden üretir ve yazar (`build_outcomes`). Arz fiyatı `registry/inputs/<T>.json`'dan gelir; girdi belgesi olmayan arz `NO_IPO_PRICE` olarak raporlanır.
- **`completeness [--start] [--through]`**: tamlık denetimi (§3.10.3). Başlangıç varsayılanı 2026-08-07'dir; bitiş varsayılanı yerelde kesintisiz bülteni olan son seanstır. Açıklanamayan bir kod varsa çıkış kodu 3'tür.

**Yazma kuralı** (`write_outcome`): yeni dosya `CREATED` olur. Var olan dosyada yalnız `PENDING` satırlar değişebilir; dolu bir satır yeniden hesapta farklı çıkarsa `OutcomeConflict` ile durulur ("resmî veri değişmiş olabilir"). Dosya aynıysa `UNCHANGED`. Ağsız yeniden üretim testi, yerel bültenlerden üretilen dosyaların repodakilerle bayt bayt aynı olduğunu sınar.

**Sıra bekçisi** (`sequence_guard`): 2026-08-19'dan sonraki bir bülten, yerelde yoksa ancak şu koşulla indirilir: `models/INDEX.json` (ve varsa `models/INDEX_POST_D1.json`) ile listeledikleri bütün model JSON'ları git'te commit edilmiş olmalı; `registry/records/` ve `registry/post_d1/` altındaki her kayıt commit edilmiş olmalı; bu klasörlerde commit edilmemiş değişiklik olmamalı. Değilse `SequenceRuleError`. Ayrıca `scoring.sequence_violations` bir testte, 2026-08-19 sonrası ya da yeni bir arzın işlem gününü kapsayan her bülten zip'i ve her `data/outcomes/<T>.csv` için, onu ekleyen commit'in atalarında bütün Faz 1 model dosyalarının ve ilgili arzın ilk tahmin kaydının bulunduğunu doğrular.

Tarihçe (git günlüğünden): sonuç tanımları `e469a93`'te (2026-09-22 17:52) veri olmadan kodlandı; ilk canlı sonuçlar `f1f9d44`'te (18:20) girdi; NETGL'in D4–D10'u `c1eb7ae`'de (2026-09-30 23:09) eklendi.

Kaynak dosyalar: `borsai/outcomes.py` (satır 409–475, 680–817, 940–977), `borsai/scoring.py` (`sequence_violations`), `GITLOG.txt`, `docs/PROVENANCE.md` §10.

### 3.10.3 Tamlık denetimi: `data/outcomes/COMPLETENESS.csv`

Amaç, sicile girmemiş bir halka arz kalmadığını resmî veriden göstermektir. Yöntem: pencere içindeki her seansta THB'de **ilk kez görünen** her işlem kodu listelenir (taban, pencere başından önceki son seansın THB'sidir) ve sırayla şu kurallarla sınıflanır:

0. Temerrüt (buy-in) pazarı satırı (`PAZAR` ya da `YAPISAL BAZDA PIYASA ALT BOLUMU` = `BUYIN`, ya da `ENSTRUMAN TIPI` `BUYIN` ile başlıyor) → `TEMERRUT_PAZARI` (var olan payın temerrüt kodu).
1. `ENSTRUMAN GRUBU` ≠ `EQT` (pay değil: varant, sertifika, fon …) → `PAY_DISI_ARAC`.
2. Pay ve ticker `ipos.csv`'de → `IPOS_CSV:<durum>`.
3. Pay; aynı gün kaybolan bir pay koduyla aynı bülten adı → `KOD_DEGISIKLIGI`.
4. Aksi hâlde → `ACIKLANAMAYAN_YENI_PAY`: olası yeni halka arz; komut durur.

Ayrıca `ipos.csv`'deki her halka arz pencerede yeni pay olarak görünmelidir (`listed_not_seen` boş olmalı).

Sütunlar: `first_seen, code, ticker, name, instrument_group, market, traded_first_seen, classification, reason, ipos_status, ipos_first_trading_date`.

Ölçülen (pencere 2026-08-07…2026-09-30): 6.413 satır. `PAY_DISI_ARAC` 6.367 (alım varantı `ECW` 3.574, satım varantı `EPW` 2.784, borsa yatırım fonu `ETF` 5, `NSE` grubu 3, fon `GSF` 1), `TEMERRUT_PAZARI` 34, `IPOS_CSV` 11 (yedi arzın `.E` kodu, INTET'in birincil piyasa kodu `INTET.HE` ve üç bedelli kalan pay kodu), `KOD_DEGISIKLIGI` 1 (`MARKA.E` → `USHOL.E`), `ACIKLANAMAYAN_YENI_PAY` 0. İlk koşu 2026-09-21'e kadar 5.579 satırdı; NETGL D4–D10 güncellemesi 834 satır ekledi. Temerrüt pazarı kuralı (0) ilk koşuda açıklanamayan bir kod çıkınca sonradan eklendi (`docs/SPEC_DEVIATIONS.md` E20).

Kaynak dosyalar: `data/outcomes/COMPLETENESS.csv`, `borsai/outcomes.py` (satır 819–937), `docs/PROVENANCE.md` §10, `docs/SPEC_DEVIATIONS.md` M23.

## 3.11 Eski kohort sonuçları: `data/outcomes_oot/` (yapı)

Eski kohort, H99'dan önceki 2020-01-01…2023-09-21 arzlarıdır. Üyelik `registry/oot/cohort_pre_h99.csv`'dedir: 136 satır, 135 `MEMBER` ve 1 `OUT_OF_SCOPE`. Üyeler sonuç görülmeden, deterministik bir çekilişle ikiye ayrıldı (`registry.draw_vault`): önce sonucu bir biçimde görülmüş olabilecek 5 üye çıkarılıp açık kümeye kondu (`EXPOSED_ARCHIVE` 4, `EXPOSED_CODEX` 1); kalanlar ilk işlem yılına göre tabakalara ayrıldı ve her tabakanın yarısı (tek sayıda aşağı yuvarlanarak) sabit tohumlu (`VAULT_SEED = 20260924`) bir rastgele sayı üreteciyle kasaya (`SEALED`) çekildi. Sonuç: açık küme 71 (`OPEN` 66 + 5), kasa 64. Kasa üyelerinin sonuçları, doğrulanacak özellikler önceden kaydedilip push edilmeden okunamazdı; kasa daha sonra bir kez açıldı (`registry/oot/VAULT_OPEN.json`). Bu bölümde eski kohort üyelerinin kodları bilerek yazılmıyor.

Klasörün yapısı:

- `data/outcomes_oot/<T>.csv`: 135 dosya. Sütunlar canlı sonuç dosyasının 16 sütunu + `outcome_basis`. `outcome_basis` her satırda `MACHINE_EXTRACTED`'dır: değerleri makine ayıkladı, insan görmedi. Anlamlar canlıdakiyle aynıdır (§3.4.6, §3.5). Ölçülen: 1.350 satırın hepsi `OK`.
- `data/outcomes_oot/raw/<T>.json`: 135 dosya, şema `borsai.oot_raw_rows/1`. Her seans için yalnız o payın `.E` satırının ham THB alanları (açılış, en yüksek, en düşük, kapanış, A.O.F, hacim, sözleşme, grup, pazar, ad, durdurma) ve THM alanları (referans, üst, alt), bülten sha256'larıyla.
- `data/raw/bist/MANIFEST_OOT.csv`: ayıklamada okunan her zip'in tarihi, türü, URL'si, sha256'sı, baytı, `Last-Modified`'ı, indirme zamanı ve iç dosya adı (1.168 satır).

Ayıklama kuralları (`borsai/outcomes_oot.py`): zip'ler repo dışındaki karantinaya indirilir; repo içinde bir karantina yolu reddedilir. Ayıklayıcı yalnız hedef kodun satırını tutar; başka satır hiçbir dosyaya, günlüğe ya da ekrana yazılmaz. D_10'dan sonraki hiçbir seansın bülteni okunmamış olmalıdır (`assert_window_bound`). İndirme, o kohortun bütün listeleme öncesi tahmin kayıtları commit edilip push kanıtı alınmadan açılmaz (`download_gate`). Sonuç takvimi §3.4.4'teki birleşik takvimdir. Eski bültenlerde tarih alanının `GG.AA.YYYY` biçiminde gelebildiği de ayrıca ele alınır (`DOTTED_DAY`).

v2 eğitim tablosu bu klasörün yalnız açık kümeye ait 71 dosyasını okur (§3.8.3).

Kaynak dosyalar: `borsai/outcomes_oot.py` (satır 1–140), `registry/oot/cohort_pre_h99.csv`, `registry/oot/VAULT_OPEN.json`, `data/raw/bist/MANIFEST_OOT.csv`.

## 3.12 Pinler ve sabitler: tek tabloda

Veriyle ilgili bütün kilitler aşağıdadır. sha256'ların ilk 8 hanesi yazıldı.

| Ad | Değer | Nerede |
|---|---|---|
| `H99_DATA_VERSION_SHA256` | `a0c7d082` (`data/data_version.json`) | `borsai/specs.py` |
| `V2_DATA_VERSION_SHA256` | `2ee8d51b` (`data/data_version_v2.json`) | `borsai/specs.py` |
| eğitim tablosu v1 | `b307cd0e` | `data/data_version.json` |
| eğitim tablosu v2 | `5adda8b2` | `data/data_version_v2.json` |
| `PB_SHA256` | `5e52d4d2` | `borsai/data.py`, `specs.PB_SOURCE` |
| `SESSIONS_SHA256` | `eca620d3` | `borsai/outcomes.py` |
| `CALENDAR_A_SHA256` | `15d4d975` | `borsai/market20.py` |
| `CALENDAR_B_SHA256` | `49b58029` | `borsai/market20.py` |
| `CALENDAR_B_EXT_SHA256` | `273ca0e7` | `borsai/market20.py` |
| `CALENDAR_C_SHA256` | `6dfd6134` | `borsai/market20.py` |
| `XU100_SHA256` (≤ 2026-08-19) | `34859d7e` | `borsai/market20.py` |
| XU100 (≤ 2026-09-21) | `04637c91` | `borsai/market20.py` (`XU100_PINNED`) |
| `TUFE_PIN` | önek `3d61cbcf`, `through_month` 2026-08 | `borsai/specs.py` |
| TÜFE kaynak tablosu | `6f7ee8e4` | `data/raw/tuik/…58290.source.json` |
| `OUTCOME_CUTOFF` / `SEQUENCE_CUTOFF` | 2026-08-19 | `scoring.py`, `ceiling_path.py`, `post_d1.py`, `post_break.py` / `outcomes.py` |
| `LISTING_CUTOFF` | 2026-08-06 | `borsai/scoring.py` |
| `SCOPE_START` | 2026-08-07 | `borsai/registry.py` |
| `MAX_SEEN` | 15 seans | `borsai/outcomes.py` |
| `WINDOW_SESSIONS`, `MAX_STALE_DAYS`, `MAX_LEAD_DAYS` | 20, 12, 12 | `borsai/market20.py` |
| `LAG_MONTHS` | 2 | `borsai/tufe.py` |
| `MISSINGNESS_FOLD_DROP_THRESHOLD` | 40/100 (kesin büyüktür) | `borsai/preprocess.py` |
| `WINSOR_P05`, `WINSOR_P95` | 1/20, 19/20 | `borsai/preprocess.py` |
| `MODEL_NUMERIC_PRECISION` | 60 hane | `borsai/preprocess.py` |
| `EXACT_DIGITS` | 50 hane | `borsai/outcomes.py` |
| `RUNTIME_PINS` | Python 3.12, scikit-learn 1.9.0, numpy 2.5.2, scipy 1.18.0, joblib 1.5.3, threadpoolctl 3.6.0 | `borsai/specs.py` |

Ortamla ilgili tek veri notu (`docs/ENV.md`): eski V1.5 karşılaştırma ölçütü Windows'ta üretilmişti; macOS'ta yeniden koşunca Ridge tahminleri en çok 2,7e-15, Logit olasılıkları en çok 3,1e-9 farklı çıktı. Bu yüzden eski kodla parite testleri "birebir" değil toleranslıdır. Veri değerlerinin kendisi metin ve Decimal olarak taşındığı için bu fark veride değil, sayısal kütüphanelerdedir.

Kaynak dosyalar: `borsai/specs.py`, `borsai/market20.py`, `borsai/outcomes.py`, `borsai/tufe.py`, `borsai/preprocess.py`, `borsai/data.py`, `docs/ENV.md`.

## 3.13 Belirsiz ya da açık kalan noktalar

- **H99'un 100. üyesi** bilinmiyor (`DEFERRED_RECONCILIATION`). 99'luk kohort bu hâliyle donmuştur.
- **79 H99 arzında PIT kanıtı yok** (`UNKNOWN`). Girdilerin arz anında yayımlandığı bu satırlar için kanıtlanmadı.
- **f3'ün tanımı arzdan arza değişiyor** (kaynak bildirimi / hesaplanmış, filtreli / filtresiz, ek satışlı / ek satışsız payda). Yeni arz girişinde "hangi talep katı" sorusunun tek tanımı DATA_NOTES'ta açık iş olarak yazılı.
- **Ek satışın `shares_offered` içinde olup olmadığı** hiçbir sözleşmede yazılı değil; H99'da 6 arzda içinde.
- **Takvim B uzatmasının 2026-09-21 sonrası 101 satırı** henüz XU100'e karşı çapraz denetlenmedi. 2027 için takvim yok; o tarihlerde f6 `CALENDAR_NOT_COVERING` verir.
- **TÜFE dosyası 2026-08'de bitiyor.** T'si Kasım 2026 olan bir arz 2026-09 endeksini ister; o ay eklenmeden deflatörlü modellerin kaydı yazılmaz.
- **Takvim B'nin 2023-09-22 öncesi kısmı** (264 gün) yalnız yeniden kurma kuralıyla doğrulandı. H99'un ilk arzlarının f6 penceresi bu kısma uzanır (en erken S20 2023-08-23); XU100 kapanışı olmayan beş gün ise H99 pencerelerine değmez ve 99/99 arzda 21 kapanışın hepsi vardır.
- **2023-04-24** Takvim C'de kapanış, bülten kanıtına göre ise işlem günüdür. f6 takvimi ile eski kohort sonuç takvimi bu gün için bilerek farklıdır.
- **BIST verisinin lisansı.** Uygulama başkalarına dağıtılacaksa önce bu soru cevaplanmalı (`docs/ENV.md`). `docs/app/SPEC_APP.md` uygulamanın THB/THM'nin kendisini değil, ondan türetilmiş parametreleri ve skorları gömdüğünü, bu türev verinin dağıtımının Borsa İstanbul lisansı açısından henüz sorulmadığını yazar.

Kaynak dosyalar: `data/raw/HISTORICAL99_FROZEN_COHORT_V1_canonical_membership.csv`, `docs/DATA_NOTES.md`, `data/raw/pay_calendar_b_extension_20260820_20261231.csv`, `data/raw/tuik/tufe_genel_2025_100.csv`, `data/raw/pay_calendar_c_bulletin_evidence_20200101_20230921.csv`, `docs/ENV.md`, `docs/app/SPEC_APP.md` (satır 601).

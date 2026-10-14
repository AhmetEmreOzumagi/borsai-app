KITAP_AUDIT_1: [P] 0 kritik, 1 orta, 1 düşük; [K] 3; [B] 5

# AUDIT_1_VERI — Veri katmanının bağımsız denetimi

Görev `BORSAI_FAZ9_KITAP_AUDIT_1_20261008` (`docs/prompts/FAZ9_KITAP_AUDIT_1_VERI.md`). Denetlenen: HEAD `ee3796d`, kılavuz `docs/fable_kitap_audit/kitap/03_veri.md` (tamamı), `01_genel_bakis.md` §1.5–§1.6, `10_dosya_dizini.md` `data/` ve `registry/` satırları. Ağ yok. Ölçüm betikleri ve ham çıktıları `ekler/1/` altındadır (`audit1_*.py` + `.out.txt`). İşaretler: **[ÖLÇTÜM]** kendi hesabım, **[ÇIKARIM]** yorum.

## Özet

1. **Veri katmanında sonucu değiştiren hata bulunmadı.** 99 arzın 990 tavan etiketi, 99 seri uzunluğu, 396 getiri ve yön etiketi ham bülten metninden (`thb_raw_*`, `thm_raw_*`) `borsai` kullanmadan yeniden üretildi; `training_table.csv` ile metin düzeyinde birebir aynı. Yedi canlı arzın sonuç dosyası 73 zip'ten bağımsız ayrıştırıcıyla bayt bayt yeniden üretildi.
2. f1–f5 (99/99 READY ile Decimal-eşit), f6 (99/99 model JSON'uyla Decimal-eşit; 7 canlı kayıtla eşit), pb1–pb4 (üç özdeşlik 99/99), TÜFE ayı ve tahsis rejimi (170/170 v2 satırı) sıfırdan doğrulandı.
3. Nokta-zamanı: TÜFE T−2 ayının yayımı 177 arzın hepsinde T'den en az 25 gün önce; f6'da S0 < T 99 + 7 arzda; 7 canlı girdinin 20 alanının her kaynağı T'den önce yayımlanmış ve belge sha'ları tutuyor. 79 `UNKNOWN` satırı DATA.md'de dürüstçe yazılı.
4. Kodda ve belgelerde pinli 23 sha256'nın hepsi dosyayla eşleşiyor; 73 bülten zip'i manifestle eşit; H99'da pinli 13 bültenle çakışan sha'lar aynı.
5. Payda: 40 THB'nin bağımsız taramasında yeni pay kodu olarak yalnız 7 arz, 3 bedelli kalan pay, INTET'in birincil piyasa kodu ve 1 kod değişikliği göründü; `ipos.csv` dışında kalan halka arz yok.
6. Sıra kuralı git DAG ile tutuyor: 16 Faz 1 modelinin hepsi `f1f9d44` (ilk sonuç) ve `c1eb7ae`'nin atası, push kanıtları sonuç commit'inden önce. Eski kohort: açık kümenin sonuçları (`77b54f7`) ilk kayıtların push kanıtından sonra; kasa sonuçları (`71b9071`) hem ikinci kayıtların push kanıtından hem `VAULT_OPEN.json` commit'inden sonra.
7. Tek [P] ORTA: tamlık denetimi, aynı THB'de iki kez geçen (çelişkili) bir pay kodunu "pay dışı araç (grup yok)" diye sınıflıyor; durmuyor. Bugün böyle bir kod yok (0 satır), ama "sessiz dışlama yok" ilkesinin gizli bir deliği.
8. Tek [P] DÜŞÜK: SPEC_SCORING §2 metni 15 seans sınırını "D_1'den itibaren" sayıyor; §9 sözde kodu, kod ve kılavuz "ilk görünüşten itibaren" sayıyor. Etkilenen arz yok.
9. Kılavuz hataları küçük: "her dosya sha256 ile kilitli" aşırı genelleme (7 dosya pinsiz), görev dosyası sayısı (79 yerine 77), "100 bayttan kısa" (kod ≤ 100).
10. Ölçülemeyenler: "son 100" seçim kuralı (evren listesi repoda yok), türetilmiş XU100 dosyasının özgünü, 2019 THB biçimi, KAP Java sarmalı.

## Bulgular tablosu

| no | tür | önem | kılavuzdaki yer | kısa tanım | kanıt | öneri |
|---|---|---|---|---|---|---|
| 1 | [P] | ORTA | §3.10.3 kural 4 ("aksi hâlde ACIKLANAMAYAN_YENI_PAY; komut durur"); SPEC_SCORING §4 "sessiz dışlama yok" | `outcomes.completeness` çelişkili kodu (aynı THB'de iki satır; `Bulletin.rows`'tan düşer, `conflicts`'e girer) `b.rows.get(code)` ile `None` alır, grup `""` olur ve kod `PAY_DISI_ARAC` / "pay dışı araç (grup yok)" olarak sınıflanır; `ACIKLANAMAYAN_YENI_PAY` üretmez, komut durmaz | `borsai/outcomes.py:878-892` (`row = b.rows.get(code)`; `group = row.group if row else ""`; `elif group != EQUITY_GROUP`). [ÖLÇTÜM] `COMPLETENESS.csv`'de "grup yok" satırı 0; bağımsız taramada çelişkili kod 0 (`audit1_live.out.txt`). Beklenen: çelişkili kod → DUR; gerçek: pay dışı sayılır | Kodda: `code in b.conflicts` ise `ACIKLANAMAYAN_YENI_PAY` (ya da ayrı `SOURCE_CONFLICT` sınıfı, `ok = False`). Model yok, yeni model_id gerekmez; tamlık dosyası değişmez (0 satır) |
| 2 | [P] | DÜŞÜK | §3.4.6 "15 seans sınırı. İlk görünüşten itibaren" | Şartname metni ile sözde kod/kod çelişiyor: `SPEC_SCORING.md:37` "D_10, D_1'den itibaren 15 resmi seans içinde"; `SPEC_SCORING.md:148-152` ve `outcomes.resolve_sessions` (`seen` sayacı `first` = ilk görünüşten başlar, `outcomes.py:554-558`) ilk görünüşten sayar. Kılavuz koda uyuyor | [ÖLÇTÜM] 7 canlı arzda ilk görünüş = D_1 (`audit1_live.out.txt`); H99'da 990 seans `ACTIVE_NOT_SUSPENDED`. Etkilenen satır 0 | Belgede: §2 cümlesini §9 ile hizala ("ilk görünüşten itibaren 15"). Kod ve sonuçlar değişmez; model_id gerekmez |
| 3 | [K] | ORTA | §3.1 ilke 3 "Her dosya sha256 ile kilitlidir … Okuyucu her seferinde parmak izini yeniden hesaplar" | Aşırı genelleme: `membership.csv`, `field_provenance.csv`, `bist/MANIFEST.csv`, `MANIFEST_OOT.csv`, `tuik/tufe_bultenleri.csv`, `tuik/*.source.json`, `pay_calendar_c_bulletin_evidence_*.csv` için kodda ya da sürüm dosyasında pin yok (ilk ikisinin sha'sı yalnız `docs/PROVENANCE.md`'de yazılı). Hiçbiri modele girmiyor; DATA.md beş pinli kaynağı doğru sayıyor | [ÖLÇTÜM] `audit1_pins.out.txt` "pin?" satırları: 23 dosyadan 16'sı pinli, 7'si pinsiz | Kılavuz düzeltmesi (bu görevin işi değil); isteğe bağlı proje kararı: ikisini `data_version.json`'a eklemek |
| 4 | [K] | DÜŞÜK | §1.6 "Görev dosyası 79" | `ee3796d`'de `docs/prompts/` 77 izlenen dosya (diskte 84; 7'si bu denetimlerin izlenmeyen dosyaları) | [ÖLÇTÜM] `git ls-tree -r ee3796d docs/prompts` → 77 | Kılavuz |
| 5 | [K] | DÜŞÜK | §3.2.1 "100 bayttan kısa yanıt hata sayılır" | Kod `len(data) <= 100` → 100 bayt da hata | `borsai/outcomes.py:395` | Kılavuz |
| 6 | [B] | — | §3.3.1 "son 100 halka arz" seçim kuralı | Kural ham veriden yeniden uygulanamıyor: 100'lük evren listesi repoda yok. Doğrulanan sonuçları: 99 üye, ilk işlem günleri 2023-09-22…2026-08-06, 79 dış kanıt üyesinin hiçbiri QUICK'ten sonra değil, kanonik 20 sıra no 1–20, 1 boşluk `DEFERRED_RECONCILIATION` | `audit1_cohort_calendar.out.txt` | — |
| 7 | [B] | — | §3.2.5 türetilmiş XU100 dosyası (9.684 → 9.682 kayıt) | Özgün dosya eski repoda; repodaki kanıt yalnız PROVENANCE §1 ve §7 metni. Ölçülebilen: 9.682 kaydın hepsi 2026-09-22 dosyasında Decimal-eşit, 23 ek kayıt, çelişkili tarih yok. T'den önceki bir revizyon sorusu bu veriyle ölçülemez; XU100 kapanışının geriye dönük revize edilmediği iki dosyanın örtüşmesiyle yalnız 2026-08-19…2026-09-22 penceresi için gösterilebiliyor | `audit1_cohort_calendar.out.txt` | — |
| 8 | [B] | — | §3.2.1 "THB 2019 sonunda 56 sütun" | Repoda 2019 bülteni yok; 2026'nın 40 THB'si 57, 33 THM'si 19 sütun ve THM'de `FIYAT ADIMI` var (ölçüldü) | `audit1_live.out.txt` | — |
| 9 | [B] | — | §3.2.2 KAP ekinin 27 baytlık Java sarmalı | Sarmallı ham yanıt saklanmıyor; ölçülebilen: 8 ekin hepsi `%PDF-` ile başlıyor ve `download_sha256 ≠ sha256` | `audit1_live.out.txt` | — |
| 10 | [B] | — | §3.10.2 sıra bekçisi; CLAUDE.md kural 1 POST_BREAK | `sequence_guard` yalnız `models/INDEX.json`, `INDEX_POST_D1.json`, `registry/records`, `registry/post_d1`'i denetler; `INDEX_POST_BREAK.json` ve `registry/post_break` kapsam dışı. CLAUDE.md POST_BREAK sınıfını DAG'dan hesaplatır, indirme kapısı istemez; kılavuz kodu doğru anlatıyor. Yorum gerektirdiği için [B] | `borsai/outcomes.py:413-438` | Proje sahibine soru 3 |

## Bölüm bölüm kontrol listesi

| § | kontrol edilen iddia | tutan | tutmayan / ölçülemeyen |
|---|---|---|---|
| 3.1 | 6 ilke + kesim sabitleri (`OUTCOME_CUTOFF`, `LISTING_CUTOFF`, `SEQUENCE_CUTOFF` 5 dosyada) | 5 | 1 (ilke 3, bulgu 3) |
| 3.2.1 | URL kalıbı, iç dosya adı, cp1254/`;`/iki başlık, TARIH denetimi, SOURCE_CONFLICT, sütun sayıları, Last-Modified saatleri (40 THB akşam ≥12 GMT, 33 THM sabah <09 GMT, hepsi aynı gün), manifest 73/40/33/15.414.084 bayt/59+14 indirme günü, `xb` yazma, SourceChanged bekçisi, MANIFEST_OOT 1.168 (584+584, 2020-02-06…2023-10-04, zip repoda 0) | 15 | 2 (2019 sütun sayısı [B]; "100 bayttan kısa" [K]) |
| 3.2.2 | 3 belge türü, bildirim/ek URL'leri, yayın zamanı dayanağı, `kap_api_publish_date`, tarama 8 kayıt | 5 | 1 (Java sarmalı [B]) |
| 3.2.3 | SPK URL kalıbı, nesne kimliği zamanı = `published_at` (7/7 bülten, 3 farklı bülten), Last-Modified ve basılı tarihle tutarlı | 3 | 0 |
| 3.2.4 | 2025 ortalaması 100,000000; xls sha/bayt/yayım; `tufe_bultenleri` 82 satır ve `tufe_genel` ile ay/kimlik/tarih eşit; 82 ay 2019-11…2026-08; `--check` bayt-eşit (klonda); 78 + 4 geç ay (listesi aynı); `source.json` alanları | 8 | 0 |
| 3.2.5 | uç nokta, JSON alanları, 9.682/9.705 kayıt ve aralıklar, yalnız XU100, revizyon 0, 23 ek, 579.614 bayt | 7 | 1 (türetme [B]) |
| 3.2.6 | 4 yılın pdf sha'ları takvim C satırlarında ve `market20.py`'de aynı; PDF repoda yok | 2 | 0 |
| 3.3.1 | 6 sütun değeri, 20/79 kaynak, kanonik 20 listesi ve tarih aralığı, SOHOE, 96 farklı gün, 3 çift gün, yıl dağılımı 19/33/18/29, HATSN | 9 | 1 ([B] seçim kuralı) |
| 3.3.2 | 9 dosyanın satır×sütun sayıları (membership 99×15, MASTER 99×38, PROV 99×22, READY 99×23, SESSIONS 990×40, TARGETS 396×18, field_prov 11.880×15, Takvim A 1.063×11, PB 99×32), BOM/`utf-8-sig`, ham = normalleştirilmiş 990/990 (11 alan), `ACTIVE_NOT_SUSPENDED` 990, 984/6, PIT 20/79, NO_CONFLICT 99, SUPERSEDED 1, PARTIAL 99, DATA_NOT_FOUND 79×3, TARGETS kesin kesir 396/396 | 14 | 0 (CRLF→LF dönüşümü eski repoya bakmadan ölçülemez, PROVENANCE'a dayanır) |
| 3.3.3 | f2 formülü (READY 99/99), ek satış 93 + 6 (liste aynı), `additional_sale` 95/89/6/4 (listeler aynı), f3 köken ve filtre sayıları, 31 tanım metni, ALBTN/ENDAE, GOLDA 9,2 / 10,12 / 1 | 7 | 0 (NETGL taşıma kuralı ve p = 0,30 eski repo kayıtları; bakılmadı) |
| 3.4.1–3.4.5 | 4 takvimin gün/seans/yarım gün sayıları (1.063/728/6; 1.327/910/8; 134/95/1; 1.360/930/9), ardışıklık, A dağılımı 722/6/31/304, A yarım günleri, `used_by_historical99` 433 = SESSIONS tarihleri, A ∩ B 1.063 günde bayrak farkı 0, B 264/1.063 doğrulama durumu, B'de 5 XU100 boşluğu, uzatma kapanışları ve yarım günü, 33/101 durum, 23 = 23 çapraz denetim, C yerleştiricileri 52/9/921/373/5, C bülten kanıtı 42 = 37/4/1 ve günleri, C ↔ A ardışık, `UNANNOUNCED_CLOSURES.csv` yok, 25 seans | 22 | 0 |
| 3.4.6 | `traded` tanımı, D_h = Takvim A'dan n'inci seans (99/99 arz, 990 tarih), 6 yarım gün seansı ve 3 takvim günü, halt/shift/15/PENDING kuralları kodla aynı | 6 | 1 (bulgu 2, şartname metni) |
| 3.5.1 | Decimal eşitlik, THM'den okuma, 1,10 sabiti yok, oran 1,096045…1,1, 4 arzın D1 referansı, 81 D1 tavan / 50 tam 0,1 / min 0,0989 / LILAK ve BORLS, NETGL 28,06 vs 28,072; ek: üst limit = ⌊ref×1,1⌋ ve alt limit = ⌈ref×0,9⌉ adım tablosuna göre 990/990 | 8 | 0 |
| 3.5.2–3.5.3 | L kuralı (CITAS 5, TKNKA 7, VEYAS 0), `exact_return` 50 hane, Y kesin büyüktür (QUICK D5 = 0, VEYAS D10 = 0), fiziksel sınır | 5 | 0 |
| 3.5.4 | Y = 1 89/80/77/70; tavan 81/70/67/54/48/46/39/30/26/25; L dağılımı 18/11/4/13/12/8/6/6/4/3/14; 81/66/41/14 | 4 | 0 |
| 3.5.5 | NETGL on seans, L = 3, −923/2552, 50 haneli metin, Y_D10 = 0, 127/1276 | 5 | 0 |
| 3.6.1 | f1–f5 READY 99/99, 4 yuvarlanmış kaynak değer (fark ≤ 0,46), min/medyan/maks (f1 290,87 M / 1,40 Mr / 6,825 Mr; f2 10,03/25/40,47; f3 1/3,24/14,6; f4 22,22/75/100), f5 = 1 iki arz, hata kodları | 6 | 0 |
| 3.6.2 | f6 formülü, 99/99 JSON eşit, −0,1117/0,0230/0,1548, T−S0 1–3 gün, en erken S20 2023-08-23, Takvim A ile 6 ret (liste aynı), 7 canlı kayıt (ref_date = T, S0, S20, f6, sha'lar), NETGL f6 −0,0924269900 | 9 | 0 |
| 3.6.3 | T−2 kuralı (3 örnek), ret kodları, pin öneği = tam dosya, NETGL 132,31 / 2026-08-03 / 1.687.703.121,457… | 5 | 0 |
| 3.6.4 | 8 alan, özdeşlikler 99/99, pb1/2/3 aralıkları, pb3 = 100 (17), pb4 92/5/1/1, fiyat farkı 0, taban farkı 10, PIT PASS 99, SPK<B<T 99, aralıklar 4/6/13 ve 4/8/12 | 10 | 0 |
| 3.6.5 | rejim tarih kuralı 170/170, H99 99 EQUAL_DIST, OOT 25/31/15, `alloc_regime_date` = PB tarihi 99/99 | 4 | 0 |
| 3.7 | Type-7 p05/p95 (97 f3: 1,1487 / 8,332), ddof = 0, yalnız eğitimden öğrenme: 3 fold × 2 tarifte test değeri değiştirilince parametreler ve z bit-eşit; tarif tablosu `RECIPES` ile aynı | 4 | 0 |
| 3.8.1–3.8.2 | 99×31, sıra, BOM yok, 2 + 4 eksik hücre, üretici klonda bayt-eşit, durma koşulları kodla aynı, sürüm dosyası alanları ve sha'ları, `load_dataset` denetimleri (çalıştı) | 8 | 0 |
| 3.8.3 | 170×39, H99 satırları 31 sütunda hücre hücre aynı (99/99), açık küme 71 (yıl 4/26/20/21), PASS 71, f3 boş 3, ek satış boş 1, köken 50/15/3, filtre 35/30/3, sale_method 44/27, market 42/29, `--check` ve `load_dataset_v2` çalıştı, kohort önek pini, birleşik sha'lar | 12 | 0 |
| 3.8.4 | küme n'leri 99/97/165/94/161/165; kesim sabitleri | 2 | 0 (walk-forward Denetim 3) |
| 3.9.1 | 7 belgede 20 alan, VEYAS'ta 2 boş + gerekçe, kaynak anahtarları ve tablo tutarlılığı, yayım < T, belge sha'ları, PB alanları SPK'dan ve talep toplamadan önce, NETGL 20 değer ve 4 belge zamanı, özdeşlikler, f1 = fiyat × pay | 9 | 0 |
| 3.9.2 | 31 belge = 16/8/7, klasör = manifest 7/7, sha 31/31, URL yalnız kap/spk, tarama 8 kayıt + BEWEN | 5 | 0 |
| 3.9.3 | 26 satır 7/19 ve 10/3/3/1/1/1, kurallar kodla aynı, `SCOPE_START` | 3 | 0 |
| 3.10 | 16 sütun, 7 dosya bayt-eşit yeniden üretim, özet tablosu (L, D10 kapanış, R, Y), üç komut, yazma kuralı, sıra bekçisi, `e469a93`/`f1f9d44`/`c1eb7ae` zamanları, tamlık 6.413 = 6.367 (3.574/2.784/5/3/1) + 34 + 11 + 1 + 0, ilk koşu 5.579, MARKA→USHOL | 10 | 0 |
| 3.11 | 136/135/1, 64/66/5 (4 + 1), yıl tabakaları ⌊n/2⌋ kuralıyla aynı, 135 + 135 dosya, 1.350 OK (üretici denetimi; ayrıca `load_dataset_v2` 710/710), MANIFEST_OOT, kasa sonuçları yalnız `71b9071`'de ve VAULT_OPEN'ın torunu | 7 | 0 |
| 3.12 | 24 pin/sabit satırı: 23 sha ve sabit kodla aynı; `RUNTIME_PINS` kurulu sürümlerle aynı | 24 | 0 |
| 3.13 | 9 açık nokta: hepsi hâlâ açık (101 satır, TÜFE 2026-08, 2027 takvimi yok, ENV.md/SPEC_APP lisans notu) | 9 | 0 |
| 1.5 | zaman çizelgesi 12 satır (commit zamanları, push kanıtları 11:32:27Z ve 14:06:05Z), 20 alan değeri, f1–f6 ve f1r, gerçekleşen 10 kapanış ve yüzdeler, D4–D10 taban (alt limite eşit 7/7), D10 = en düşük mümkün yol | 20 | 0 (§1.5.3–§1.5.8 sınıf ve skor hükümleri Denetim 3) |
| 1.6 | 30 model (27 + 1 + 2), 99×31, 170×39, 135 = 71 + 64, 26 satır, 7 + 7 + 0 kayıt, 2.146 satır (72/19/1/2.054), 175 commit, 31 kanıt (18 commit), 56 test dosyası, `borsai/` 25.956 satır (39 dosya), manifestler 73 / 1.168 | 13 | 1 (79 → 77) |
| 10 | 58 `data/` ve `registry/` yolu | 57 | 0 (`registry/post_d1/` yok; kılavuz zaten "bu kopyada yok" diyor) |

## Bağımsız yeniden hesaplananlar

| Ne | Betik | Kendi sonucum | Repodaki değer |
|---|---|---|---|
| 990 tavan etiketi, 99 L, 396 R/Y (ham metinden) | `ekler/1/audit1_labels.py` | tabloyla 0 uyuşmazlık; 81/70/67/54/48/46/39/30/26/25; L 18/11/4/13/12/8/6/6/4/3/14 | `training_table.csv`, DATA.md |
| üst/alt limit = fiyat adımı yuvarlaması | aynı | ⌊ref×1,1⌋ 990/990, ⌈ref×0,9⌉ 990/990 (adım: <20 0,01; <50 0,02; <100 0,05; <250 0,10; <500 0,25; <1000 0,50) | kılavuz §3.5.1 (yön belirtmiyor) |
| D_h = Takvim A'dan n'inci seans | `audit1_cohort_calendar.py` | 99/99 arz, SESSIONS ile aynı | SESSIONS, TARGETS |
| f1–f5 (MASTER'dan, 28 hane + 10 ondalık HALF_UP) | `audit1_features.py` | READY ile 99/99 eşit | READY, `features.py` |
| pb1–pb4, özdeşlikler | aynı | 99/99; pb4 92/5/1/1 | PB dosyası, kılavuz §3.6.4 |
| f6 (Takvim B + eski XU100) | `audit1_f6_tufe_pit.py` | 99/99 Decimal-eşit; Takvim A ile 6 ret | `models/v1_5_market20_v0.json` `market20_training` |
| canlı f6 (B + uzatma, yeni XU100) | aynı | 7/7 eşit | `registry/records/*/*.json` |
| TÜFE T−2 PIT | aynı | 177/177 yayım < T; marj 25–58 gün; T−1 kullanılsaydı 16 ihlal | `tufe_genel_2025_100.csv` |
| 23 sha256 pini, 73 zip, birleşik OOT sha'ları, kohort öneği, TÜFE öneği | `audit1_pins.py` | hepsi eşit | `specs.py`, `market20.py`, `outcomes.py`, `data.py`, `data_version*.json` |
| 7 canlı sonuç dosyası (zip'lerden, bağımsız ayrıştırıcı) | `audit1_live.py` | 7/7 bayt-eşit | `data/outcomes/*.csv` |
| tamlık (40 THB, bağımsız) | aynı | yeni EQT kodu 12 (7 arz + 3 BE + INTET.HE + USHOL.E), pay dışı 6.367, buyin 34 | `COMPLETENESS.csv` 6.413 satır |
| SPK nesne kimliği zamanı | aynı | 7/7 `published_at` ile saniyesine eşit | manifestler |
| sıra kuralı (DAG) | kabuk/`audit1_oot_sequence.py` | Faz 1 16 modelin ekleme commit'leri (`5fa849d`, `b09cab5`) `e469a93`, `f1f9d44`, `c1eb7ae`'nin atası; 11 sonraki model değil (beklenen); OOT: 71 açık `77b54f7` (kayıt kanıtı 2026-09-24T22:39Z < commit 2026-09-25T13:32Z), 64 kasa `71b9071` (kanıt 06:40Z ve VAULT_OPEN `2f914dd`'den sonra) | push_proofs, git |
| üretici yeniden üretimi (klon) | `/tmp/…/clone_experiments.py` (çıktısı `ekler/1/clone_experiments.out.txt`) | `build_training_table.py` ve `data_version.json` bayt-eşit; v2 `--check` ve TÜFE `--check` eşit; Takvim C `calendar_c_bytes()` sha eşit | — |
| ön işleme sızıntısı (klon) | aynı | 3 fold × (V1_5, CEILING_V1_CLIP): test satırının f1/f3'ü değiştirilince winsor, medyan, μ, σ, sütunlar ve z bit-eşit; test arzı eğitimde değil | — |
| Type-7 p05/p95 (97 f3) | kabuk | 1,14871 / 8,332 | kılavuz §3.7.1 |

Not (klon deneyi): fold'ları V1.5 kesimiyle (D5 hedef tarihi < T) kurdum; `CEILING_V1_CLIP` için eğitim satırlarının D10 seansının T'yi aşabilmesi benim kurgumun sonucudur, tavan planının kişi-dönem kesimi (seans tarihi < T) Denetim 3'ün konusudur ve burada ölçülmedi.

## Bakılmayanlar

- Walk-forward kesimleri, bootstrap, sınıflama (LIVE/LATE/RETRO) ve skorlar: Denetim 3.
- Eski repodan kopya dosyaların CRLF→LF dönüşümü, türetilmiş XU100'ün özgünü, NETGL "planlanan ayrım" kuralı ve p = 0,30 ölçümü: kanıt eski repoda, ORTAK kurala göre bakılmadı.
- 2019 bülten biçimi; KAP ham (sarmallı) yanıtları; tatil tablosu PDF'leri; TÜİK xls'in 2005 başlangıcı (yalnız `--check` koşuldu).
- `registry/oot/candidate_features*`, `source_docs_faz7` içerikleri (yalnız dosya sayıları: 135/136, 1.284 belge).
- `draw_vault` çekilişinin tohumla yeniden koşulması (yalnız tabaka sayıları ⌊n/2⌋ kuralıyla doğrulandı).
- Tam test koşusu yapılmadı; yedi veri katmanı test dosyası tek koşuda çalıştırıldı (sonuç `ekler/1/pytest_single_files.txt`).

## Proje sahibine açık sorular

1. Tamlık denetimi, bir THB'de iki kez geçen pay kodunu "DUR" mu saymalı (bulgu 1)? Bugün vaka yok; kural değişikliği yalnız koddur.
2. `membership.csv` ve `field_provenance.csv` `data_version.json`'a pin olarak eklensin mi, yoksa belgelerde "modele girmeyen, pinsiz" diye mi anılsın (bulgu 3)?
3. `sequence_guard` POST_BREAK dizinini ve `registry/post_break`'i de kapsasın mı (bulgu 10)? CLAUDE.md bunu istemiyor; soru tutarlılık içindir.

## Koruma ve hijyen sayımları

- Koruma: `ekler/1/koruma_once.txt` ve `koruma_sonra.txt`; dokuz sha ve boş durum çıktısı iki ölçümde aynı (aşağıdaki hijyen betiği karşılaştırır).
- Hijyen: rapor ve `ekler/1/` altında `th[bm]` + 8 haneli tarih kalıbı: 0; kasa (SEALED) kodu geçişi: 0 (`ekler/1/hijyen.txt`).

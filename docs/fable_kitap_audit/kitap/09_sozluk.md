# 9. Sözlük

Bu sözlük, 1–8. bölümlerde geçen teknik terimleri, kısaltmaları, kod adlarını ve proje jargonunu tek yerde toplar. Her maddenin sonundaki *Bkz.* bağlantısı, terimin en ayrıntılı anlatıldığı bölümü gösterir. Bölüm 1'deki kısa başlangıç sözlüğü (§1.1.1) ile Bölüm 2'nin başındaki terim tablosu (§2.0) burada genişletilmiştir.

Okuma notları:

- **Sıralama.** Maddeler Türk alfabesine göre dizilidir (A B C Ç D E F G Ğ H I İ J K L M N O Ö P R S Ş T U Ü V Y Z). Türkçede olmayan Q, W ve X harfleri sırasıyla P'den, V'den sonra gelir. Ğ ile başlayan madde yoktur. Sembolle, sayıyla ya da Yunan harfiyle başlayan terimler en baştaki "Semboller ve sayılar" grubundadır.
- **I ve İ.** Büyük I ile yazılan kısaltmalar (IPC, INDEX, IBM Plex) I altında; Türkçe İ ile başlayan sözcükler ve küçük i ile başlayan kod adları (`invoke`, `include_str!`) İ altındadır.
- **Kod adları.** Dosya, fonksiyon, alan ve model adları kod yazısıyla verilir ve repodaki yazımlarıyla aranabilir. Sıralamada ters tırnak, tırnak ve alt çizgi yok sayılır.
- **Sayılar.** Düz metinde ondalık virgül (0,305), repodan aktarılan skor ve parametrelerde ondalık nokta (−0.0569) kullanılır; ikisi aynı yazım farkıdır (§1.7.3).
- **Atıflar.** "bkz. **X**" aynı sözlükteki başka bir maddeyi, "*Bkz. §x.y*" kitabın bölümünü gösterir. Bir madde içinde "SPEC_SCORING §10" ya da "AUDIT §1.2" gibi bir belge adıyla geçen § işareti o belgenin kendi bölümüdür, bu kitabın değil.
- **Yazılmayanlar.** Eski kohort kasasındaki arzların kodları ve resmî bülten dosyalarının tek tek adları burada da yazılmaz (§6.12.3).

## Semboller ve sayılar

**`?` işleci** (Rust): Bir `Result` hata ya da `Option` boş taşıyorsa fonksiyondan hemen geri döner; Rust'ta istisna yerine bu kullanılır. *Bkz. §7.1*

**`#[ignore]`** (Rust test işareti): Testi yalın `cargo test` koşusunun dışında bırakır. Asıl repoyu (`BORSAI_REPO`) ya da geçici bir klonu isteyen testler böyle işaretlidir; `app/scripts/test.sh` onları `--include-ignored` ile koşar. *Bkz. §7.11, §7.12*

**`#[tauri::command]`**: Bir Rust fonksiyonunu ön uçtan adıyla çağrılabilen Tauri komutuna çeviren işaret; fonksiyon ayrıca `generate_handler!` listesine eklenir. *Bkz. §7.1, §7.7*

**`.E` eki**: Borsa İstanbul'da payın normal işlem kodunun soneki (ör. `NETGL.E`). "İşlem gördü" tanımı ve sonuç ayıklama bültendeki bu satıra bakar. *Bkz. §3.4.6*

**`.gitattributes`**: Repo kökündeki git ayarı; `* text=auto eol=lf` ile bütün metin dosyalarını LF satır sonuyla tutar ve ikili dosya türlerini işaretler. CRLF'ye dönen bir model JSON'u sha256'sını bozardı. *Bkz. §7.5*

**`.venv/`**: Repo içindeki Python sanal ortamı (CPython 3.12.14); git'e girmez. Testler `.venv/bin/pytest -q` ile koşar. *Bkz. §2.8*

**@fontsource**: Yazı tiplerini npm paketi olarak getiren kaynak; IBM Plex yazı tipleri buradan alınıp derlemeye gömülür, çalışma anında ağdan inmez. *Bkz. §8.23*

**@INF** (uç nokta): L2 cezalı bir tavan modelinin λ = ∞ ucu. Özellik katsayıları 0'dır, yalnız gün grubu sabitleri kalır ve her arza aynı eğri verilir. Kural gibi raporlanır; "özellikler bir şey katıyor mu?" sorusunun ölçüsüdür (ör. `ceiling_hazard_v0@INF`, `ceiling_path_v0@INF`). *Bkz. §4.1.4, §4.4.9*

**@ZERO** (uç nokta): Lojistik C ızgarasının "C = ZERO" ucu: olasılık eğitimdeki oran (n₁/n) olur, girdi okunmaz. `fall_d10_v0_pooled@ZERO` ve `break_floor_v0@ZERO` (F1 = 25/82 ≈ 0,305; F2 = 11/78 ≈ 0,141) bu türdendir. *Bkz. §4.8.3, §5.3.6*

**%95 aralık** (güven aralığı): Eşleşik farkın blok bootstrap ile bulunan belirsizlik bandı. Backtest'te sıralanmış 4000 değerin 100. ve 3899. elemanı (0'dan sayılarak), canlı ve zaman-dışı terazide 2,5 ve 97,5 yüzdelikleridir. *Bkz. §6.7*

**|Δ| ≤ 1e-9** (parite toleransı): İki gerçekleme (Python–Rust ya da ilk uygulama–bağımsız yeniden üretim) arasında kabul edilen en büyük mutlak fark. Koşullu değerlerde eşik 1e-12'dir; bit eşitliği ayrıca sayılır. *Bkz. §2.4.6, §7.11*

**10–15 olay/parametre kuralı**: Lojistik ya da tehlike modelinde her katsayı için kabaca 10–15 azınlık olayı gerektiğini söyleyen bütçe kuralı; altında kestirimler kararsızlaşır. `ceiling_hazard_v0`'da ≈ 14, `post_d1_hazard_v0`'da 33,5; `fall_d10_v0_h99`'un 6,5'i bilerek kabul edildi. *Bkz. §4.4.5, §4.8.3*

**2025=100**: TÜFE serisinin temel yılı; 2025'in 12 aylık ortalaması 100'dür. 2025 öncesi aylar TÜİK'in bu temele zincirlediği değerlerdir. *Bkz. §3.2.4*

**27 + 1 + 2**: Bugün donmuş 30 modelin üç dizine dağılımı: listeleme öncesi 27 (`INDEX.json`), D1 sonrası 1, kırılma akşamı 2. *Bkz. §2.7.2*

**α (alfa)**: Ridge regresyonunun ceza katsayısı; büyük α daha güçlü büzme demektir. V1.5 ızgarası {0,1; 1; 10; 100}, V1.6'nınki 0,001…10 000 ve INF. Kırılma modelinde α_h başlığın sabit terimini gösterir. *Bkz. §4.2.2, §4.3.4, §5.3.5*

**β (beta)**: Doğrusal öngörücüdeki özellik katsayıları (z ölçeğinde). L2 cezası yalnız β'ya uygulanır; sabitler cezasızdır. *Bkz. §4.2.1, §4.4.5*

**γ (gama)**: Tavan modelinde üç gün grubunun cezasız sabitleri (g1, g2, g3). `ceiling_hazard_v0`'da γ = (−1,8095; −2,1470; −1,0071). *Bkz. §4.4.5, §4.4.7*

**δ (delta)**: Üç anlamda geçer: (a) havuz modelinde rejim teriminin cezasız katsayısı; (b) D1 sonrası modelde ofsete eklenen D1 katsayıları (δ_lock ≈ −0,328, δ_turn ≈ +0,251); (c) yakın dönem etiketinin tolerans eşiği (RPS'te 0,010, düşüş modelinde Brier'de 0,008). *Bkz. §4.7.2, §5.2.4, §6.8*

**η (eta)**: Doğrusal öngörücü: sabit + Σ katsayı × özellik. Lojistik modelde olasılık p = σ(η)'dır. *Bkz. §4.2.1, §5.1.3*

**λ (lambda)**: L2 ceza gücü; büyüdükçe katsayılar 0'a büzülür, λ = ∞'da yalnız sabitler kalır. Tavan ızgarası {0,1; 1; 3; 10; 30; 100; 300; 1000; INF}; eşitlikte büyük λ seçilir. `ceiling_hazard_v0` için 10, `post_d1_hazard_v0` için 30 seçildi. *Bkz. §4.2.2, §4.4.6, §5.2.4*

**ρ_h (ro)**: Limit yolu getirisi, ρ_h = C_h / P − 1: seri h gün sürerse D_h'deki getiri. *Bkz. §4.6.2*

**σ (sigma)**: (a) Sigmoid fonksiyonu σ(η) = 1/(1 + e^(−η)); (b) z-skorundaki standart sapma (popülasyon, ddof = 0). *Bkz. §4.2.1, §4.2.3*

## A

**A/B/R commit kalıbı**: Her yeni işte önce **A** (kod, tanımlar ve beklenti kuralları; gerçek sonuç yok), sonra **B** (resmi backtest ya da sonuç verisi), sonra **R** (rapor) commit'lenir; dondurma ayrı oturumda K, F1, F2 commit'leriyle yapılır. A'nın B'nin atası olması, kuralların sonuçtan önce yazıldığının git'teki kanıtıdır. *Bkz. §2.3.4, §2.4.3*

**Açık küme** (OPEN): Eski kohortun kasaya çekilmeyen 71 üyesi: 66 `OPEN` + 4 `EXPOSED_ARCHIVE` + 1 `EXPOSED_CODEX`. Sonuçları ilk açılan ve `training_table_v2.csv`'ye eklenen kısımdır. *Bkz. §3.11, §6.12.2*

**Açılış bütünlük denetimi** (`verify_embedded`): Uygulama açılırken gömülü INDEX'in ve her model dosyasının sha256'sını, sırasını ve parametrelerini denetler. Tek uyuşmazlıkta bütün tahmin komutları `INTEGRITY_FAILED` döner; kısmi çalışma yoktur. *Bkz. §7.4*

**Açılış emir toplama**: Borsa İstanbul'da seans açılmadan emirlerin toplandığı aşama; 09:40'ta başlar ve o andan itibaren günün teorik açılış fiyatı görünür. POST_D1 kaydının zaman sınırı buna dayanır. *Bkz. §5.2.7*

**Ad-hoc imza**: macOS paketinin kişisel kullanım için `signingIdentity "-"` ile imzalanması. Başkalarına dağıtım için Apple imzası ve notarization gerekir. *Bkz. §7.5, §2.8*

**`add_sale`** (ek satış bayrağı): 1[additional_sale_shares > 0], yani ek satışın kullanılıp kullanılmadığı. Düşen arz modellerinin özelliğidir; alan boşsa model 0 varsaymaz, reddeder (`ADDITIONAL_SALE_MISSING`). *Bkz. §3.7.2, §4.8.3*

**Alt limit** (taban fiyatı): THM'deki `ALT LIMIT FIYATI`; referans fiyatın %10 altının fiyat adımına yukarı yuvarlanmış hâli: Lo(x) = ⌈x·0,9 / adım⌉ · adım. Ertesi günün alt limiti Lo(bugünkü kapanış)'tır. *Bkz. §5.1.2*

**Altın ledger** (golden ledger): Resmi backtest koşusunun pinlenmiş fold ledger'ı (`tests/reference/macos_golden*/`, `docs/faz8/backtest/`). Testler backtest'i yeniden koşup bayt bayt karşılaştırır; MODELS.md ve skor dosyalarının backtest blokları bunlardan üretilir. *Bkz. §6.5.5*

**Altın renk**: Sade görünümde yalnız ana ekran kapısından geçen model çıktısının rengi (#FFB648). Basit kural ve gerçekleşen değer asla altın olmaz. *Bkz. §8.11, §8.23*

**Altın vektör** (golden vector): Python'un ürettiği ve dosyaya dondurduğu girdi–beklenen çıktı satırları; Rust testi her satırı yeniden hesaplar. Bugün `app/parity/golden/` altında 13 102 satırdır. *Bkz. §7.1, §7.11*

**amend** (git): Son commit'i yeniden yazma komutu. Ata ilişkilerini değiştirebileceği için yalnız proje sahibi yapabilir; kurallar onu fiilen yasaklar. *Bkz. §6.2*

**Ana ekran kapısı** (`headline_gate`): Sade görünümde bir çıktının altın renkle öne çıkıp çıkmayacağına Rust'ın karar verdiği kural: çıktının önceden ilan edilmiş birincil hücresi (birden çoksa hepsi) skor dosyasında "geçiyor" olmalıdır. Ön uçta elle liste yoktur. *Bkz. §8.11*

**Analiz** (ekran): Sade görünümde bir arzın resmi sayfası: dondurulmuş kayıt, bültenden gelen kapanışlar, fiyat koridoru, kırılma kartı, seri hesaplayıcı ve getiriler; tavan sayıları yalnız kayıttan okunur, model yeniden çalıştırılmaz. *Bkz. §8.15*

**AOF** (ağırlıklı ortalama fiyat): THB'deki `A.O.F` alanı; günün işlemlerinin miktarla ağırlıklı ortalama fiyatı. Modellerde özellik olarak kullanılmaz. *Bkz. §5.1.2, §5.2.2*

**AppError**: Uygulama komutlarının ortak hata yapısı: `code` (makine okunur sabit), `message` (geliştirici metni), `detail` (ham çıktı, ör. Python'un stderr'i). Ön uç kodu `tr.ts`'teki Türkçe metne çevirir. *Bkz. §7.2*

**APPPIN** (commit türü): Model dizini büyüdükçe (19 → 23 → 27) uygulamanın altın MANIFEST'ini ve sha pinlerini yeniden bağlayan commit'ler; yeni modeller bir sonraki port görevine kadar uygulamada "tanınmayan" sayılır. *Bkz. §2.6.7, §6.15.4*

**AppState**: Tauri'de bütün komutların paylaştığı durum: açılışta doğrulanmış gömülü model kümesi ve değişebilen ayar/repo bilgisi. *Bkz. §7.2*

**Aracı kurum**: Halka arzı yürüten ve sonuç bildirimini (dağıtım tablosu, talep katı) KAP'ta yayımlayan yatırım kuruluşu. *Bkz. §3.2.2*

**Araştırma arşivi**: Birincil hücresini geçemeyen modellerin indiği yer; model silinmez, donmuş olarak listede kalır ama ana ekranda öne çıkmaz. *Bkz. §2.1, §2.7.3*

**Arc / Mutex** (Rust): `Arc` bir değeri kopyalamadan iş parçacıkları arasında paylaştıran atomik referans sayacı; `Mutex` aynı anda yalnız bir erişime izin veren kilit. *Bkz. §7.2*

**Arz** (halka arz, IPO): Bir şirketin paylarını ilk kez borsada satışa sunması; kitapta çoğunlukla Borsa İstanbul'da ilk kez işlem görmeye başlayan pay için kullanılır. *Bkz. §2.0, §3.1*

**Arz-bırak çapraz doğrulama** (iç arz-bırak CV): Tavan ve kırılma modellerinde ceza seçimi için her eğitim arzının bütün satırlarının birlikte dışarıda bırakıldığı çapraz doğrulama. Aynı arzın kişi-dönem satırları bağımsız olmadığı için satır satır değil arz arz bırakılır. *Bkz. §4.2.4, §4.4.6*

**Arz fiyatı** (P, `ipo_price`): Kesin halka arz fiyatı; getiri ve limit yolu bu fiyata göre hesaplanır. Canlıda girdi belgesinden, H99'da MASTER dosyasından gelir. *Bkz. §3.5.3, §4.1.1*

**Arz sonrası sermaye** (`post_ipo_share_capital`): Arzdan sonraki toplam pay adedi; f2'nin paydasıdır. *Bkz. §3.3.2, §3.6.1*

**async komut**: Tauri'de pencereyi dondurmasın diye eşzamansız yazılan komut; Python çağıranlar (`freeze_record`, `set_config`, `market20_via_python` …) böyledir. *Bkz. §7.2*

**Aşama** (`stage`): (a) Girdi aşaması: `PRE_BOOKBUILD` (talep toplama öncesi) ya da `POST_BOOKBUILD_PRE_LISTING` (talep toplandı, işlem başlamadı); (b) kayıt aşaması: listeleme öncesi, `POST_D1`, `POST_BREAK`. *Bkz. §3.9.1, §7.9.1, §6.11.5*

**Aşırı uyum** (overfitting): Az veriyle çok katsayı kestirilince modelin eğitim verisinin gürültüsünü öğrenmesi; L2 cezası buna karşı kullanılır. *Bkz. §4.2.2*

**Ata / torun** (git): A commit'inden B'ye geçmiş zinciri izlenerek ulaşılabiliyorsa A, B'nin atası, B de A'nın torunudur; `git merge-base --is-ancestor A B` ile sınanır. "Model sonuçtan önce var mıydı?" sorusu saatle değil bu ilişkiyle cevaplanır. *Bkz. §6.3.3*

**Atlandı**: bkz. **SKIPPED**. *Bkz. §3.9.3*

**Atom** (karışım atomu): Tavan yolu modelinin getiri dağılımını oluşturan (değer, ağırlık) çiftleri: bir limit yolu atomu ve kırılma sonrası hücrelerden gelen atomlar. Medyan, kuantiller ve p_up bunlardan okunur. *Bkz. §4.6.4*

**AUC**: Bir olasılık modelinin olayı olaysızdan ayırma gücünün ölçüsü (0,5 rastgele, 1 mükemmel). `ceiling_hazard_v0`'ın 1 − S_1 değeri "D1'de tavan yok" olayını iki dönemde 0,81 / 0,80 ile ayırır. *Bkz. §4.8.1*

**AUDIT** (ilk denetim): Fable'ın 21 Eylül 2026 tarihli ilk denetimi (`docs/fable_audit_20260921/AUDIT.md`); koddaki "AUDIT §1.2-c" gibi atıfların kaynağı. Bu kopyada yoktur, içeriği yalnız atıflardan bilinir. *Bkz. §2.2.3, §6.16*

**Ayarlar ve Hakkında** (ekran): Repo klasörü, Python yolu, skor kaynağı ve görünüm seçiminin yapıldığı, gömülü model bütünlüğünün ve sha'ların gösterildiği ekran. *Bkz. §8.20*

**Ayırt edilemiyor**: Hüküm sözcüklerinden biri: n ≥ 30 iken farkın %95 aralığı 0'ı içeriyorsa kullanılır; model ile kural arasında güvenilir fark yoktur. Sade görünümde "≈ fark net değil". *Bkz. §6.8, §8.11*

**Ayrık zamanlı tehlike modeli** (discrete-time hazard): Seri uzunluğunu gün gün "bozulma olasılığı" h_d ile modelleyen yapı; S_k = Π(1 − h_d) çarpımı eğrinin azalmasını kendiliğinden sağlar. Kişi-dönem verisi üzerinde lojistik regresyonla fit edilir. *Bkz. §4.4.1, §4.4.2*

**Ayrıntılı görünüm** (`AYRINTILI`): Uygulamanın ilk arayüzü; gömülü 27 modeli, kuralları, uyarıları ve skor hücrelerini yan yana gösterir. Sade görünüm gelince kodu ve testleriyle aynen bırakıldı; seçim Ayarlar'dadır. *Bkz. §8.2, §8.22*

**Azami arz** (`planned_max_offer_shares`): Planlanan en büyük arz: taban arz + ek satış tavanı (özdeşlik ID-C). *Bkz. §3.6.4*

## B

**b** (kırılma günü): Serinin bozulduğu seans numarası, b = L + 1; tavan olmayan ilk işlem görmüş kapanışın günüdür. NETGL'de L = 3, b = 4. *Bkz. §5.1.1*

**b_floor**: Kırılma günü kapanışının alt limite tam eşit olup olmadığı: 1[KAPANIS_b == ALT LIMIT_b]. `break_floor_v0`'ın asıl bilgi taşıyan özelliğidir (ertesi gün taban odds'unu ≈ 7,4 kat artırır). *Bkz. §5.3.4, §5.3.5*

**B(k)**: k arzının ilk talep toplama günü (`first_bookbuilding_date`); PB modellerinin bilgi kesimi. *Bkz. §4.1.1, §4.5.1*

**b_turnover**: Kırılma günü el değiştirmesi: ln(TOPLAM ISLEM ADEDI_b / shares_offered); eğitimin p05/p95'ine kırpılıp z-skorlanır. F1'deki işareti beklentinin tersidir. *Bkz. §5.3.4*

**BacktestStop**: Walk-forward planında kendi kendini eğitme, aynı gün sızıntısı ya da gelecek sızıntısı bulununca kodu durduran hata. *Bkz. §6.5.2*

**Bağımsız mod**: Uygulamanın repo bağlanmadan çalıştığı mod: derlemeye gömülü 27 model, TÜFE tablosu ve skor kopyalarıyla tahmin, senaryo ve doğruluk paneli çalışır; sicil, dondurma, Monitör ve Analiz çalışmaz. *Bkz. §7.1, §8.5*

**Bağımsız yeniden üretim**: Yeni bir modelin backtest sonucunun, ilk uygulamayı görmemiş ayrı bir oturum (Fable) tarafından yalnız şartnameden ve `borsai` import edilmeden sıfırdan hesaplanması; eşik |Δ| ≤ 1e-9. Faz 7'den beri her yeni model için zorunludur. *Bkz. §2.4.6, §6.16*

**BAND_RULE_MISMATCH** (bant koruması): Kırılma akşamında THM'den ölçülen alt limit / referans oranı [0,9; 0,9020] dışındaysa verilen uyarı; yastık rozeti gizlenir, satır `BAND_CHANGED` etiketi alır, tahmin yine üretilir. *Bkz. §5.3.11*

**base_always_ceiling** ("her zaman tavan"): Her seansın tavan kapandığını varsayan basit kural: R_h = 1,1^h − 1, p_up = 1, S_k = 1. *Bkz. §4.1.5*

**base_floor_by_type**: Kırılma modeli için iki hücreli karşılaştırıcı: eğitimde test arzıyla aynı `b_floor` sınıfındaki ertesi gün taban oranı (taban üstünde 6/47 ≈ 0,128; tabanda 19/35 ≈ 0,543). *Bkz. §5.3.6*

**base_km_expanding** (genişleyen KM): Eğitimdeki bütün arzların kişi-dönem satırlarından kurulan Kaplan–Meier eğrisi; tavan modellerinin birincil karşılaştırıcısı. Sade görünümde "bütün geçmişin tablosu". *Bkz. §4.1.5, §8.11*

**base_km_last10** (son-10 KM): Aynı Kaplan–Meier eğrisi, ama her gün için yalnız o günün satırı eğitimde bulunan son 10 arzla; sade görünümde "son 10 arzın tablosu". *Bkz. §4.1.5*

**base_last10_rate** (son-10 taban oranı): (ilk işlem günü, kod) sırasındaki son 10 eğitim arzının Y_h ortalaması; hızlı tepki veren ama gürültülü olasılık kuralı. *Bkz. §4.1.5*

**base_rate** (taban oranı): Eğitimdeki Y_h ortalaması, yani arz fiyatının üstünde kapananların oranı; p_up kafalarının karşılaştırıcısı. Sade görünümde "taban oranı". *Bkz. §4.1.5*

**base_record**: POST_D1 kaydının içinde arzın listeleme öncesi birincil kaydını ve sha'sını taşıyan blok; ofset bu kaydın girdilerinden hesaplanır. *Bkz. §5.2.7*

**base_train_mean** (eğitim ortalaması): Eğitimdeki R_h'lerin aritmetik ortalamasını tahmin eden getiri kuralı. *Bkz. §4.1.5*

**base_train_median** (eğitim medyanı): Eğitimdeki R_h'lerin medyanını tahmin eden kural. MAE'yi en küçükleyen sabit medyan olduğu için getiri modellerinin asıl çıtasıdır. *Bkz. §4.1.5, §6.6.1*

**base_zero**: Getiriyi her ufukta 0 tahmin eden kural. *Bkz. §4.1.5*

**Basit kural** (baseline): Hiçbir arz özelliğine bakmadan eğitim hedeflerinden (ya da hiçbir şeyden) sabit tahmin üreten, model gibi dondurulan karşılaştırıcı; modelin yenmesi gereken çıtadır. *Bkz. §2.0, §4.1.5*

**Baz fiyat** (D1 baz fiyatı): İlk işlem gününün limitlerinin hesaplandığı başlangıç fiyatı. H99'da 95/99 arzda arz fiyatının kendisi, 4 arzda fiyat adımına yuvarlanmış hâlidir (`snap`, HALF_UP). *Bkz. §4.6.2, §3.5.1*

**Bedelli**: SPK tablosunda sermaye artırımıyla (yeni pay çıkarılarak) satılacak pay; girdide `capital_increase_shares` ve `planned_capital_increase_shares`. *Bkz. §3.2.3, §3.6.4*

**Bedelsiz**: SPK A.1 tablosunun bir sütunu (karşılığı ödenmeyen sermaye artırımı payı); modellerde kullanılmaz. *Bkz. §3.2.3*

**Bekçi testi** (guard): Kodun doğruluğunu değil, deponun kurala uyup uymadığını sınayan test: sıra, kasa hijyeni, sonuç alanı yasağı, pin değişmezliği. Çoğu geçici git depolarında bozuk senaryolar kurarak kendini de sınar. *Bkz. §2.4.7, §6.15.2*

**Beklenen seri** (E[L]): Seri uzunluğunun beklenen değeri, E[L] = Σ_{k=1..10} S_k. NETGL için `ceiling_hazard_v0` 3,28 gün verir. *Bkz. §4.4.1, §4.4.8*

**"Beklentiden çok iyi" freni**: Şartnamede önceden yazılmış eşik; aşılırsa sonuç sızıntı şüphesiyle ele alınır ve model bağımsız yeniden üretimden geçmeden dondurulmaz. Faz 4, 5 ve 8'de tetiklendi. *Bkz. §2.6.1, §6.9.4*

**Belirsiz**: (a) Yakın dönem hücresinde aralık ne "bozuyor" ne "tolerans içinde" tanımına uyuyorsa verilen etiket; (b) bu kitapta repo dosyalarından doğrulanamayan bilgi için kullanılan işaret. *Bkz. §4.7.4, §6.8*

**BIST** (Borsa İstanbul): Türkiye'nin pay borsası; sonuç verisinin (THB/THM), seans takviminin ve fiyat kurallarının tek resmi kaynağı. *Bkz. §3.1, §3.2.1*

**BIST100**: bkz. **XU100**. *Bkz. §3.2.5*

**BigUint** (`num-bigint`): Rust'ta sınırsız büyüklükte doğal sayı türü; Rust portundaki `Dec` türünün katsayısını tutar. *Bkz. §7.8.1*

**Birincil hücre**: Bir model için sonuçlar görülmeden ilan edilen tek karşılaştırma (metrik + ufuk + karşılaştırıcı + fold kümesi); hüküm yalnız ona göre verilir, öteki hücreler "keşif"tir. Çoklu karşılaştırmaya karşı savunmadır. *Bkz. §2.0, §6.9.2*

**Birincil kayıt**: Bir (model, arz) için birden çok kayıt varsa skorlanacak olanı seçen, önceden yazılı kural: f3 isteyen modellerde D_1'den önce push kanıtlı en son kayıt, PB modellerinde ve kurallarda en erken kayıt. *Bkz. §6.11.3*

**Bit eşitliği**: İki f64 sayının 64 bitinin tamamen aynı olması (`x.to_bits() == y.to_bits()`); 1e-9 toleransından sıkıdır. *Bkz. §7.1*

**Bit-eşitlik tabanı** (`bit_equal_floor.json`): Model başına bit-eşit altın satır sayısının alt sınırı; toleransın altında kalan "sessiz sürüklenmeyi" yakalar. 28 model için toplam 12 879 satırdır. *Bkz. §7.11*

**Blok bootstrap**: Bootstrap'ta gözlemleri tek tek değil bloklar hâlinde (burada ilk işlem ayı) çekmek; aynı ay listelenen arzlar birbirine bağlı olduğu için aralığı dürüstçe genişletir. *Bkz. §4.2.6, §6.7.3*

**Bootstrap**: Eldeki örnekten iadeli yeniden örnekler çekip istatistiği her birinde hesaplayarak belirsizliği ölçme yöntemi; BorsAi'de 4000 tekrar. *Bkz. §6.7.2*

**borsai** (Python paketi): Projenin çekirdeği: özellikler, ön işleme, fit, tahmin, backtest, dondurma, sicil, sonuç ve skorlama modülleri. Tahmin modülleri yalnız standart kütüphane kullanır. *Bkz. §2.3.3, §2.8*

**borsai_dirty**: Kayıt, model JSON'u ya da günlük satırında, yazım anında `borsai/` altında commit'lenmemiş değişiklik olup olmadığını gösteren bayrak. Model dondurma temiz ağaçta (`false`) yapılır. *Bkz. §2.4.3, §6.11.2*

**borsai_predict** (crate): Modellerin Rust'a taşınmış saf portu; dosya sistemine ve ağa bağımlı değildir, Python'un sayı türlerini ve yuvarlama sırasını birebir taklit eder. *Bkz. §7.8*

**borsai_source_sha256**: `borsai/*.py` dosyalarının birleşik içerik hash'i. Model JSON'u kendi commit hash'ini taşıyamadığı için kod sürümünü bu alan bağlar. *Bkz. §6.11.1*

**"bozuyor"** (yakın dönem etiketi): Yeni aday − eski model farkının %95 aralığının alt ucu 0'ın üstündeyse verilen etiket; yeni model bugünkü dönemde kötüleşme getiriyor demektir (ör. `v1_real`, `v1_pooled`). *Bkz. §4.7.4, §6.8*

**break_floor_v0**: Kırılma akşamı modeli: kırılma gününün bülteninden (`b_floor`, `b_turnover`) ertesi seansın (F1) ve sonraki iki seansın (F2) taban kapanma olasılığını veren iki başlıklı L2-lojistik. `models/INDEX_POST_BREAK.json`'dadır; uygulamaya henüz gömülü değildir. *Bkz. §5.3, §2.7.5*

**Brier skoru**: Olasılık tahmininin karesel hatası, (1/n) Σ (p − y)²; 0 mükemmel, 0,25 "hep %50" düzeyi. Backtest p_up tablolarında olasılık [0,01; 0,99]'a kırpılır, canlıda ve sonraki fazların hücrelerinde kırpılmaz. *Bkz. §6.6.2*

**build.rs**: Cargo'nun asıl derlemeden önce koşturduğu Rust programı. BorsAi'de INDEX'i denetler, model ve skor dosyalarını gömülecek `embedded.rs`'e yazar ve kurala uymayan durumda derlemeyi kırar. *Bkz. §7.1, §7.3*

**Bülten** (günlük bülten): Borsa İstanbul'un her seans için yayımladığı THB ve THM zip dosyaları. O gün işlem gören bütün payları taşıdığı için bir bültenin repoya girmesi o günkü bütün sonuçların girmesi sayılır. *Bkz. §3.2.1, §6.10.2*

**Büzme** (shrinkage): Ceza terimi yüzünden katsayıların 0'a doğru çekilmesi; λ ve α büyüdükçe, C küçüldükçe artar. *Bkz. §4.2.2*

## C

**C** (lojistik ceza parametresi): scikit-learn lojistik regresyonunda ceza gücünün tersi (C ≈ 1/λ); küçük C güçlü büzme demektir. V1.5 ızgarası {0,01; 0,1; 1; 10}, V1.6 ızgarası ZERO, 0,0001…100; eşitlikte küçük C seçilir. *Bkz. §4.2.2, §4.3.4, §4.3.7*

**C_h** (limit yolu fiyatı): Seri h gün sürerse D_h kapanışı: C_1 = U(snap(P)), C_k = U(C_{k−1}); her adımda %10 yukarı, sonra fiyat adımına aşağı yuvarlama. NETGL'de 28,06; 30,86; 33,94; … *Bkz. §4.6.2*

**Canlı arzlar** (yedi arz): Kapsam başlangıcından (2026-08-07) bu yana işlem görmeye başlayıp sicile `FROZEN` giren yedi arz: CITAS, TKNKA, VEYAS, KPEKS, INTET, BKRGY, NETGL. Faz 1 modelleri için satırları LATE_RECORD'dur; tek istisna eski depodaki kayıt sayesinde LIVE olan NETGL × `v1_5_h99` hücresidir. Sonradan donan modeller için hepsi RETRO'dur. *Bkz. §2.7.4, §3.9.3*

**Canlı sicil** (canlı terazi): Model dondurulduktan sonra listelenen arzlarda, tahminin sonuçtan önce push edildiği ölçümler; en dürüst kanıttır ama yavaş büyür. Bugün asıl modellerde LIVE sayısı 0'dır. *Bkz. §2.7.4, §6.10.1*

**capabilities** (Tauri yetenekleri): Pencerenin hangi Tauri çekirdek ve eklenti izinlerini kullanabileceğini listeleyen dosya; BorsAi'de yalnız `core:default` ve `dialog:default`. *Bkz. §7.1, §7.5*

**Cargo** (`Cargo.toml`, `Cargo.lock`): Rust'ın paket yöneticisi ve derleme aracı; `Cargo.toml` crate bildirimi, `Cargo.lock` çözülmüş tam sürümler ve sağlama toplamlarıdır. *Bkz. §7.1, §7.3*

**cargo 164**: `app/scripts/test.sh`'ın koştuğu Rust test sayısı: 169 `#[test]` fonksiyonundan geçici klon isteyen 5'i çıkınca 164 kalır. *Bkz. §7.12*

**ceiling_close** (tavan etiketi): D_k kapanışının o seansın THM üst limitine Decimal olarak eşit olup olmadığı: 1, 0 ya da NA. "%10'a ulaştı mı" diye bakılmaz; kodda 1,10 sabiti yoktur. *Bkz. §3.5.1*

**ceiling_hazard_v0**: Listeleme öncesi tavan serisi modeli: f1, f2, f3 ve üç gün grubu sabitiyle ayrık zamanlı L2-lojistik tehlike modeli; çıktısı S_1..S_10. Backtest'te iki KM kuralını geçer, eski kohortta geçemez; ana ekranda öne çıkan tavan modelidir. *Bkz. §4.4, §2.7.3*

**ceiling_hazard_v1_*** (v1 ailesi): v0'ın eski dönem zaafına üç düzeltme adayı ve bir kural satırı: `_clip` (üç özelliği kırpar), `_real` (arz büyüklüğünü TÜFE ile reelleştirir), `_pooled` (açık kümeyi eğitime katıp rejim terimi ekler), `_pooled@INF`. Hiçbiri öne çıkma kuralını geçmedi. *Bkz. §4.7*

**ceiling_path_v0**: bkz. **Tavan yolu modeli**. *Bkz. §4.6*

**ceiling_streak_L**: Eğitim tablosunda seri uzunluğu L'nin sütun adı. *Bkz. §3.5.2, §3.8.1*

**check_form**: Girdi formundaki her değişiklikte çağrılan Rust komutu; biçim, tutarlılık, PB özdeşlikleri ve aşamaya göre zorunluluk notlarını verir, model çalıştırmaz. *Bkz. §7.9.1, §8.13*

**class_evidence**: Skor satırında sınıfın hangi commit'lerden ve kanıtlardan hesaplandığını yazan alan (ör. `MODEL_FROZEN_AFTER_BREAK_OUTCOME`). *Bkz. §5.5.6, §6.10.2*

**Claude Code**: Kod, veri ve denetim işlerini yürüten oturumlar; kullanıcı görev dosyasını gösterir, oturum uygular. Opus, Sonnet ve Fable modelleriyle çalışır. *Bkz. §2.4.1*

**Claude Design**: Sade görünüm tasarımının (12 pano) üretildiği kanvas; repodaki kopyası `docs/design/ui_v2/`. *Bkz. §2.3.14, §8.24*

**CLAUDE.md**: Repo kökündeki kurallar dosyası: altı kural (dondurma, payda, üç terazi, deney günlüğü, değişiklik = yeni model_id, skorlama), sıra kuralı ve genel ilkeler; "dürüst doğruluk için en az set; kodla zorlanır". *Bkz. §6.2, §2.4.8*

**Codex + GPT-6 Astra**: Repo dışında, web erişimiyle çalışan veri toplama aracı; eski kohortun girdilerini ve izahname alanlarını çıkardı. Repoya yazmaz; her değeri Claude Code resmi belgede yeniden doğrular. *Bkz. §2.4.1, §2.3.8*

**commit**: Git'te bir değişiklik kümesinin kaydı; her commit ebeveynine bağlanır ve sha ile anılır. *Bkz. §6.3.3*

**config.json**: Uygulama ayar dosyası (`borsai.app_config/1`): repo kökü, Python yolu, skor kaynağı (`REPO` / `EMBEDDED`) ve görünüm (`ui_view`). Uygulama verisi dizinindedir, repo dışındadır. *Bkz. §7.6*

**cp1254**: Bülten CSV'lerinin karakter kodlaması (Türkçe Windows kod sayfası); UTF-8 olarak okunamaz. *Bkz. §3.2.1*

**crate**: Rust'ın derleme birimi (kütüphane ya da program). BorsAi workspace'i iki crate'ten oluşur: `borsai-app` ve `borsai_predict`. *Bkz. §7.1*

**CRLF / LF**: Satır sonu biçimleri (Windows / Unix). Repo `.gitattributes` ile LF'ye zorlar; eski repodan gelen 9 dosya CRLF'den LF'ye çevrildi. *Bkz. §2.2.1, §7.5*

**CSP** (Content Security Policy): Webview'e hangi kaynaktan betik, stil ve resim yüklenebileceğini, nereye bağlanılabileceğini söyleyen güvenlik politikası. BorsAi'de dış bağlantı yasaktır (`connect-src 'self' ipc: http://ipc.localhost`). *Bkz. §7.1, §7.5*

## Ç

**Çapraz doğrulama** (cross-validation): Eğitim kümesini parçalara bölüp her parçayı sırayla dışarıda tutarak görülmemiş veri performansını taklit etme; ceza parametresi böyle seçilir. *Bkz. §4.2.4*

**Çerçeve** (framework): React, Svelte gibi arayüz kütüphaneleri. BorsAi ön ucu bilerek çerçevesizdir: saf render fonksiyonları ve ekran bağlayıcıları. *Bkz. §8.1*

**Çift yuvarlama**: Bir değerin önce bir hassasiyete (ör. 60 haneli Decimal), sonra f64'e yuvarlanması. Python böyle yaptığı için Rust portu da aynısını taklit eder. *Bkz. §7.8.1*

**Çoklu karşılaştırma**: Aynı veride çok hücreye bakılınca bazılarının şans eseri "geçiyor" çıkması sorunu; çözümü önceden ilan edilmiş birincil hücre ve görünür varyant sayacıdır. *Bkz. §6.9.1*

## D

**D1, D_h**: Arzın ilk işlem günü (D1) ve oradan itibaren işlem gördüğü h'inci resmi seans (D_h). Yarım gün sayılır, tam gün durdurma sayılmaz; "işlem gördü" = THB'de `.E` satırı var, sözleşme > 0 ve kapanış > 0. *Bkz. §3.4.6*

**d1_lock** (D1 kilidi): D1'in gün içi en düşük fiyatının üst limite eşit olması, yani fiyatın gün boyu tavanda kilitli kalması; karşılanmamış talebin bültenden okunan ölçüsü. *Bkz. §5.2.2*

**D1 sonrası model**: bkz. **post_d1_hazard_v0**. *Bkz. §5.2*

**d1_turnover** (D1 el değiştirmesi): ln(TOPLAM ISLEM ADEDI / shares_offered); arz edilen payların ilk gün ne kadarının el değiştirdiği. *Bkz. §5.2.2*

**DAG** (yönlü çevrimsiz çizge): Commit'lerin ebeveyn oklarıyla oluşturduğu döngüsüz çizge. Sınıf hesabı saatlere değil, bu çizgedeki ata ilişkisine bakar. *Bkz. §6.3.3*

**DATA_NOT_FOUND**: Kaynak dosyalarda eksik değeri gösteren metin; eğitim tablosunda boş hücreye çevrilir, asla 0 yazılmaz. *Bkz. §3.3.2, §3.8.1*

**Debounce**: Art arda gelen tuş vuruşlarında yalnız sonuncusundan belli süre (Yeni arz girişinde 180 ms) sonra çalışma; `check_form` çağrısı böyle seyreltilir. *Bkz. §8.13*

**Dec** (Rust Decimal türü): Rust portunun Python Decimal'ini taklit eden türü: (−1)^neg × katsayı × 10^üs. Ayrıştırma, bağlamlar ve `str()` metni birebir taklit edilir. *Bkz. §7.8.1*

**Decimal**: Python'un taban 10'da kesin ondalık türü; "10.12" metni tam 10,12 kalır. BorsAi'de bütün kaynak değerler ham metinden `Decimal` ile okunur, float'a çevrilip geri yazılmaz. *Bkz. §3.1, §7.1*

**Decimal bağlamı** (context): Decimal işlemlerinin hassasiyeti ve yuvarlama kuralı. Projede 28 hane (eski kodun varsayılanı), 60 hane (model hesapları) ve 200 hane (kesin özdeşlikler) bağlamları vardır. *Bkz. §3.6.1, §7.8.1*

**Deflatör**: Nominal büyüklüğü reel hâle çeviren endeks; BorsAi'de TÜİK TÜFE (2025=100). Deflatörlü modeller (`ceiling_hazard_v1_real`, `_pooled`, `fall_d10_v0_h99`, `_pooled`) TÜFE ayı yoksa kayıt yazdırmaz. *Bkz. §3.6.3, §4.7.2*

**"Değer mi" analizi**: Fable'ın şartnamenin başında (şartnamenin kendi §0'ında) yeni bir modelin ölçülebilir kazanç sağlayıp sağlamayacağını önceden hesaplaması; cevap "dur" ise model yazılmaz (ör. kırılma akşamında D10 hedefi). *Bkz. §2.4.3, §5.3.1*

**Değişiklik = yeni model_id** (kural 5): Özellik, ön işleme, ızgara, eğitim kesimi ya da veri sürümü değişirse yeni kimlik verilir; eskisi ve skorları listede kalır. Kodu şartnameye uydurmak aynı kimliktir, şartnameyi değiştirmek yeni kimlik. *Bkz. §6.2, §2.1*

**Denetim hükümleri**: Fable denetimlerinin kısa sonuç etiketleri: `PUSH_OK` (push edilebilir), `FREEZE_OK` (dondurulabilir), `REPRO_OK` (bit-eşit yeniden üretildi), `S2_OK`, `S6_OK`, `VAULT_SCORE_OK`, `UYGUN` ve `DÜZELTMEYLE UYGUN`. *Bkz. §2.4.6, §6.16*

**Deney günlüğü** (`experiments/log.jsonl`): Her backtest koşusunun kendiliğinden bir satır eklediği append-only JSON Lines günlüğü (kural 4); bugün 2 146 satır, bunların 2 054'ü Faz 7C keşif varyantıdır. *Bkz. §6.13*

**DISCLAIMER**: Her ekranın altındaki sabit uyarı: "Bu uygulama yatırım tavsiyesi değildir; çıktılar istatistiksel tahmin ve olasılıklardır." Hukuki metin değildir. *Bkz. §8.9*

**DOMAIN_ERROR**: Rust portunda Python'un etiketsiz istisnasının (ör. `math.log(0.0)`, `decimal.Overflow`, `Inexact`) karşılığı olan hata kodu. *Bkz. §7.8.10*

**Dondur sihirbazı**: Uygulamada resmi kaydın altı adımlı akışı (ön koşullar, kaynak belgeler, girdi belgesi, Python denetimi, ilk işlem günü uyarısı, dondur). Kaydı Python yazar; uygulama parite karşılaştırması yapar ve git komutlarını yalnız metin olarak gösterir. *Bkz. §7.9.4, §8.22*

**Dondurma**: (a) Bir modelin parametrelerinin JSON'a yazılıp commit ve push edilmesi; donmuş model bir daha değişmez. (b) Tahmin kaydının ilk işlem gününden önce yazılıp push edilmesi (kural 1). *Bkz. §2.0, §6.2, §6.11*

**DUPLICATE_RECORD** (mükerrer kayıt): Etkin bir kayıtla aynı girdi sha'sını ve aynı INDEX sha'sını taşıyan ikinci kaydı reddeden kural. *Bkz. §6.11.2*

**"DUR" kuralı**: Görev dosyalarındaki "beklenmeyen bir şey olursa dur" maddesi; oturum durur, karar proje sahibi ve orkestratörle verilip ek görev dosyasına ya da SPEC_DEVIATIONS'a yazılır. *Bkz. §2.6.6*

**Durdurma** (işlem durdurma): Tam gün durdurulan seans D_h sayımına girmez, ufuk kayar (`shifted_by_suspension`) ve tavan serisini bozmaz. Gün içi geçici durdurma (`GECICI DURDURMA`, `halt_flag`) günü yine saydırır. *Bkz. §3.4.6*

**Duyarlılık koşusu** (sensitivity): Bir modelin varyantıyla yapılan, kayıt amaçlı koşu (ör. "yalnız `b_floor`"); günlüğe `kind: sensitivity` diye yazılır, hiçbir tabloya ve hükme girmez. *Bkz. §6.13.2, §5.3.9*

**Düşen arz modeli** (`fall_d10_v0_*`): "Arz D10'da arz fiyatının altına iner mi?" sorusu için L2-lojistik aday ailesi (`_h99`, `_pooled`, `_addsale`, `_pooled@ZERO`); özellikler reel büyüklük, ln f3 ve ek satış bayrağı. Hiçbiri öne çıkmadı. *Bkz. §4.8*

**Düşme olasılığı**: P(D_h kapanışı ≤ arz fiyatı) = 1 − p_up; Rust'ta hesaplanır, ön uç çıkarma yapmaz. *Bkz. §4.8.1, §8.6*

## E

**Eğitim kümesi**: Bir modelin fit edildiği arz kümesi; `specs.py`'de adıyla tanımlıdır: `H99_ALL_ROWS` (99), `H99_F3_PRESENT` (97), havuz kümesi (165), düşüş kümeleri (94, 161, 165). *Bkz. §3.8.4*

**Eğitim tablosu** (`training_table.csv`, `training_table_v2.csv`): Arz başına bir satırlık eğitim verisi. v1: H99'un 99 satırı × 31 sütun; v2: 99 + açık kümenin 71 satırı × 39 sütun. Sürüm dosyalarıyla pinlidir. *Bkz. §3.8.1, §3.8.3*

**EK 2, EK 3, EK 5** (uygulama şartname ekleri): EK 2 tavan yolu modellerinin uygulamaya eklenmesi, EK 3 v1 / D1 sonrası / düşüş portları ve panelleri; EK 5 (kırılma kartının Rust portu) henüz yazılmadı. *Bkz. §2.3.5, §2.3.10, §2.7.5*

**Ek görev dosyası** (`…_EK1.md`): Ana görev sürerken çıkan bir durağın kararını taşıyan görev dosyası (ör. temerrüt pazarı kuralı, takvim C bülten kanıtı). *Bkz. §2.4.2*

**Ek satış** (ek pay satışı): Talep yeterliyse taban arzın üstüne satılabilen ek pay. Tavanı SPK tablosunda (`planned_additional_sale_ceiling`), kullanılan miktar sonuç bildiriminde (`additional_sale_shares`) yazılır. *Bkz. §3.2.3, §3.3.3*

**Ekran görüntüsü koşusu**: Uygulamanın `--features snapshot` ve demo bayraklarıyla açılıp gerçek düğmelere tıklayarak kendi ekran görüntülerini aldığı geliştirme betikleri (`screens_v2.sh` …); asıl repoya yazmadığını sha listeleriyle denetler. *Bkz. §8.25*

**Ekstrapolasyon** (dışdeğerleme): Modelin eğitim aralığı dışındaki girdiyle tahmin yapması. Eski kohortun nominal olarak küçük arzlarında `ceiling_hazard_v0`'ın zaafının yaklaşık yarısı buydu. *Bkz. §4.7.1*

**El değiştirme** (turnover): Günün işlem gören pay adedinin arz edilen paya oranı; logaritmasıyla `d1_turnover` ve `b_turnover` özelliklerini verir. *Bkz. §5.2.2, §5.3.4*

**Eski kohort**: H99'dan önce, 2020-01-01…2023-09-21 arasında listelenen 135 arz; açık küme (71) ve kasa (64) diye ayrılır ve zaman-dışı terazinin malzemesidir. *Bkz. §2.0, §6.12.2*

**Eşitlik kuralı** (tie-break): İç çapraz doğrulamada iki aday bit düzeyinde eşit skor alırsa "daha çok büzen" adayın seçilmesi: Ridge'te büyük α, lojistikte küçük C, tehlike modelinde büyük λ. *Bkz. §4.2.4*

**Eşleşik fark** (paired difference): Aynı arzlarda "model kaybı − kural kaybı" farklarının ortalaması; negatif fark modelin lehinedir. Yalnız ikisinin de skorlandığı arzlar sayılır. *Bkz. §4.2.6, §6.6.6*

**EXPOSED_ARCHIVE / EXPOSED_CODEX**: Eski kohortta sonucu bir biçimde görülmüş olabilecek 5 üyenin etiketi (bülteni arşivde bulunan 4, toplama aracının listeleme sonrası başlık gördüğü 1); kasa çekilişinden önce açık kümeye alındılar. *Bkz. §6.12.2*

**exposure_class**: Makine kaydındaki tür alanı (`MACHINE_SEQUENCED`); kaydın nasıl üretildiğini söyler. Satırın sınıfı ise skorlamada ayrıca hesaplanır. *Bkz. §5.5.2*

## F

**f1** (arz büyüklüğü): Kaynakta bildirilen `ipo_size_tl`, yoksa fiyat × satılan pay (TL); ön işlemede doğal logaritması alınır. *Bkz. §3.6.1*

**F1 / F2** (kırılma hedefleri): F1 = kırılmadan sonraki seans (D_{b+1}) taban kapanır mı; F2 = sonraki iki seans (D_{b+1}, D_{b+2}) taban mı. `break_floor_v0`'ın iki başlığıdır. Aynı adlar dondurma commit'lerinde (F1, F2) ve tasarım farklarında (F1–F27) başka anlamda da geçer. *Bkz. §5.3.3, §2.4.3, §8.24*

**F1–F27** (tasarım farkları): Onaylı tasarımdaki öğelerden uygulamada çizilmeyen ya da değiştirilen 27 tanesinin numaralı listesi; nedenleri çoğunlukla "ön uç hesap yapmaz" ya da "bu bilgi hiçbir dosyada yok"tur. *Bkz. §8.24*

**f1r** (reel arz büyüklüğü): f1 / (TÜFE[T'nin ayı − 2] / 100), yani 2025 fiyatlarıyla TL; ön işlemede kırpılıp ln alınır. *Bkz. §3.6.3*

**f2** (halka açıklık oranı): shares_offered / post_ipo_share_capital × 100. *Bkz. §3.6.1*

**f3** (toplam talep katı): `total_demand_multiple`; toplam talebin taban arza oranı (ek satış hariç). Eksik olabilir ve eksik ≠ 0; f3 isteyen modeller boşsa `F3_MISSING` ile reddeder. *Bkz. §3.6.1, §8.13*

**F3_MISSING**: Talep katı boşken f3 isteyen modellerin ret kodu; VEYAS'ta dört model bu kodla reddetti. *Bkz. §4.3.5, §6.10.3*

**f4** (sermaye artırımı payı): capital_increase_shares / shares_offered × 100. *Bkz. §3.6.1*

**f5** ("f3 eksik" bayrağı): f3 yoksa 1, varsa 0; ham özellik değildir, ön işlemede türetilir. Katsayısı yalnız iki arzdan öğrenildiği için V1.5 f3'süz çağrıyı reddeder. *Bkz. §3.6.1, §4.3.5*

**f6** (market20): XU100'ün arzdan önceki 20 seanslık getirisi, XU100[S0] / XU100[S20] − 1; S0, ref_date'ten kesin önceki son seanstır. Asla doldurulmaz; kurallardan biri tutmazsa ret kodu döner (`STALE_S0`, `CALENDAR_NOT_COVERING` …). *Bkz. §3.6.2, §4.3.8*

**Fable**: Şartname ve karar listesi yazan, bağımsız yeniden üretim ve denetim yapan Claude Code modeli; yazdığı şartnamenin kodunu yazan el olmaz. *Bkz. §2.4.1, §6.16*

**fail-closed** (şüphede kapalı): Bütünlük denetiminden geçmeyen bir durumda kısmi gösterim yerine hiç gösterim yapmamak: sha uyuşmazlığında tahmin kapanır, kurala aykırı skor dosyasında panel kapanır, ortam isteyen test ortamsız kırmızı olur. *Bkz. §7.4, §8.10*

**Faz**: Projenin iş aşamaları (0–9; Faz 10 bekliyor). Her commit konusu `BORSAI_FAZ…` önekiyle fazı söyler. *Bkz. §2.3*

**FAZ10** (gün gün tavan modeli): Seri sürerken her akşam o günün bülteniyle "yarın da tavan mı" olasılığını yeniden hesaplayacak modelin bekleyen şartname görevi (`docs/prompts/FAZ10_FABLE_STREAK_SPEC.md`). *Bkz. §2.7.6, §2.6.11*

**Fisher bilgisi**: Bir katsayının veriden ne kadar bilgi aldığının ölçüsü (≈ Σ h(1 − h)); tavan modelinin λ ızgarasının ölçeği buna göre seçildi (≈ 70). *Bkz. §4.4.6*

**Fixture** (test fikstürü): Testlerin okuduğu hazır veri dosyası. `app/tests/fixtures/ui/` altındaki 97 dosya Rust komutlarının gerçek çıktısıdır; `fixtures/scores/` ve `fixtures/outcomes/` ise bilerek sentetiktir. *Bkz. §8.25, §7.12*

**Fiyat adımı** (tick): Fiyat düzeyine göre değişen en küçük fiyat aralığı: 20 TL altı 0,01; 20–50 0,02; 50–100 0,05; 100–250 0,10; 250–500 0,25; 500–1000 0,50; 1000–2500 1,00; üstü 2,50. Limitler bu adıma yuvarlandığı için üst limit / referans oranı tam 1,1 değildir. *Bkz. §3.5.1, §4.6.2*

**Fiyat istikrarı**: Halka arzdan sonra aracı kurumun fiyatı desteklemek için yapabildiği işlemler; SPK kuralına göre en çok 30 gün sürer. Eski kohort için izahname alanı olarak toplandı, modelde kullanılmaz. *Bkz. §2.3.9, §6.3.4*

**Fiyat marjı** (±%10 bant): Borsa İstanbul'da bir payın günlük fiyatının referans fiyattan en çok %10 yukarı ya da aşağı gidebilmesi; tavan ve taban buradan gelir. Eski dönemde bazı pazarlarda farklıydı. *Bkz. §4.1.1, §6.12.1*

**Fiziksel getiri sınırı**: ±%10 bant yüzünden D_h getirisinin [0,9^h − 1; 1,1^h − 1] aralığında kalması (D1 [−0,10; 0,10], D10 [−0,651; 1,594]). Tahminler bu aralığa kırpılır; gerçekleşen değer fiyat adımı yüzünden çok az aşabilir. *Bkz. §3.5.3, §7.8.1*

**Fold**: Walk-forward'daki tek "eğit, sonra bir arzı tahmin et" adımı; eğitim kümesi plan koşulunu sağlamazsa fold skorlanmaz. *Bkz. §3.1, §6.5.1*

**FON_KRIZI_2026**: Eylül 2026 fon krizi için rejim uyarı etiketi: D_1 ≥ 2026-09-16 olan arzlarda kartta "olağan dışı piyasa" uyarısı çıkar. Model girdisi değildir, n'den düşülmez, bitiş tarihi açıktır. *Bkz. §2.6.4, §5.3.11*

**Fraction** (kesin kesir): Python'un rasyonel sayı türü; getiriler, kantiller ve oranlar kesin kesirle hesaplanıp sonra metne ya da f64'e çevrilir. *Bkz. §3.5.3, §3.7.1*

**FREEZE_OK**: bkz. **Denetim hükümleri**. *Bkz. §2.4.6*

**frozen_at**: Model dizinindeki dondurma zamanı alanı; yerel saattir ve kanıt değildir (`frozen_at_basis` bunu açıkça yazar). *Bkz. §4.1.3, §6.11.1*

## G

**Gece botu**: Her akşam resmi kaynakları okuyup sonuçları ve makine kayıtlarını yazacak, yeni arzı fark edip ilk işlem gününden önce donduracak ve kendi commit'ini push edecek planlanan otomasyon; henüz kurulmadı. *Bkz. §2.7.7, §2.4.5*

**Geç kayıt**: bkz. **LATE_RECORD**. *Bkz. §6.10.2*

**"Geçiyor" / "geçemiyor"**: Hüküm sözcükleri: n ≥ 30 iken farkın %95 aralığının tamamı 0'ın altındaysa "geçiyor" (model daha iyi), tamamı üstündeyse "geçemiyor" (kural daha iyi). Uygulama bu sözcüğü kendisi üretmez, skor dosyasındaki `verdict`'i basar. *Bkz. §6.8, §8.9*

**gen_golden.py**: Altın vektörleri üreten Python betiği (tohum 20260922); `--check` dosyaları yeniden üretip diskteki baytlarla karşılaştırır. *Bkz. §7.11*

**GIT_OPTIONAL_LOCKS=0**: Okuma amaçlı git komutlarının `index.lock` bırakmasını önleyen ortam değişkeni; orkestratör ve uygulama git'i her zaman bununla çağırır. *Bkz. §2.4.5, §7.3*

**Girdi belgesi** (`registry/inputs/<T>.json`): Bir arzın listeleme öncesi resmi belgelerden toplanan 20 alanı (şema `borsai.inputs/1`). Her dolu alan değer, alıntı, kaynak belge kimliği, yayın zamanı ve belge sha256'sını; boş alan gerekçesini (`missing_reason`) taşır. *Bkz. §3.9.1*

**git**: Sürüm kontrol sistemi; BorsAi'de zaman ve sıra iddialarının dayanağıdır (commit DAG'ı + push kanıtı). *Bkz. §6.3.3*

**Git kilidi**: Bir Claude Code oturumu commit atarken başka kimsenin git komutu çalıştırmaması kuralı; `index.lock` hatasında beklenir, kilit silinmez. *Bkz. §2.4.5*

**GitHub commit status API**: Push kanıtının yöntemi: commit'e bir durum yazılır; GitHub commit'i tanımıyorsa 404 döner, başarılı yanıttaki `created_at` sunucu saatidir. Kimlik `gh` CLI ya da `GH_TOKEN` ile sağlanır. *Bkz. §6.3.4*

**golden_unchanged.sh**: Eski altın vektör dosyalarının, yeni model eklense de bayt bayt aynı kaldığını git'teki dört taban commit'e karşı denetleyen betik. *Bkz. §7.11*

**Gömme** (embed): Bir dosyanın içeriğini derleme anında programa sabit olarak koymak (`include_str!`); uygulama 27 + 1 modeli, model dizinlerini, TÜFE tablosunu ve skor kopyalarını böyle taşır. *Bkz. §7.1, §7.3*

**Görev dosyası** (`docs/prompts/<FAZ>_<AD>.md`): Bir Claude Code oturumunun sormadan çalışabileceği kadar eksiksiz iş tanımı: model ve ayar, rol, bağlam, kararlar, ÖNCE OKU, adımlar, kurallar, teslim, kabul kapısı. Bugün 79 dosya vardır. *Bkz. §2.4.2, §2.5*

**Grup A / B / C** (sonuç ekranı): Ayrıntılı sonuç ekranının bölümleri: A getiri ve olasılık, B tavan serisi, C tavan yolu getiri dağılımı. Kırılma sonrası hücre grupları Z ve B ile karıştırılmamalıdır. *Bkz. §8.22, §7.9.3*

**Grup Z / Grup B** (kırılma sonrası hücreler): Tavan yolu hücrelerinin iki grubu: Z, D1'de tavan kapanmayan arzlar (t = 0); B, serisi t ≥ 1 gün sürüp bozulan arzlar. *Bkz. §4.6.3*

**Gün grupları** (`day_groups`): Tavan modelinin günleri topladığı üç grup: g1 = {1}, g2 = {2, 3}, g3 = {4…10}. Aynı gruptaki günler aynı devam olasılığını paylaştığı için 3. günden sonra "yarın da tavan" değişmez. *Bkz. §4.4.3, §2.6.11*

## H

**H99** ("Historical 99"): Ana eğitim kohortu: ilk işlem günü 2023-09-22…2026-08-06 arasındaki 99 arz (hedef 100'dü, biri doğrulanamadı). Bütün modeller bu sonuçları görerek yazıldığı için H99 her model için RETRO'dur. *Bkz. §3.3, §2.3.2*

**H99 kanonik dosyaları**: Eski repodan kopyalanan dokuz H99 dosyası: üyelik, MASTER (işlem öncesi alanlar), PROV (kaynak kimlikleri), READY (f1–f5 ham değerleri), SESSIONS (D1–D10 bülten alanları), TARGETS (getiri hedefleri), alan kaynakları, Takvim A ve PB dosyası. *Bkz. §3.3.2*

**Hacim**: Bu kitapta çoğunlukla THB'deki `TOPLAM ISLEM ADEDI` (günün işlem gören pay adedi) için kullanılır; TL cinsinden `TOPLAM ISLEM HACMI` ayrı bir alandır. *Bkz. §5.1.2, §3.2.1*

**Halka arz sonuçları bildirimi**: Aracı kurumun KAP'ta yayımladığı, satılan pay adedini, talep katını ve dağıtım tablosunu içeren bildirim; asıl tablo çoğu zaman ek PDF'tedir. *Bkz. §3.2.2*

**Hareketi azalt** (`prefers-reduced-motion`): İşletim sistemindeki "hareketi azalt" ayarı açıksa sade görünümün bütün CSS açılış animasyonlarının kapanması. *Bkz. §8.23*

**Havuzlama merdiveni** (N_MIN = 10): Tavan yolunda 10'dan az gözlemli bir hücreyi deterministik sırayla komşu hücrelerle genişletme kuralı: önce kendi hücresi, sonra diğer grubun aynı m'si, sonra m ∓ 1, m ∓ 2 … Bugünkü dondurulmuş hücrelerde hiç tetiklenmez. *Bkz. §4.6.3, §7.8.6*

**Havuzlanmış model** (pooled): H99'a eski kohortun açık kümesi eklenerek eğitilen model (`ceiling_hazard_v1_pooled`, `fall_d10_v0_pooled`). *Bkz. §4.7.2, §4.8.3*

**Hazard** (tehlike, h_d): "Seri d − 1 gün sürdüyse d. gün bozulur mu?" olasılığı: h_d = P(L = d − 1 | L ≥ d − 1). *Bkz. §4.4.1, §5.1.1*

**HEAD**: Git'te o anki geçerli commit; bu kitabın anlattığı durumda `ee3796d`. *Bkz. §2.7.1*

**headline_gate**: bkz. **Ana ekran kapısı**. *Bkz. §8.11*

**Hesaplayıcı eki** (`attach_calc`): Seri hesaplayıcının "geçmiş arzlarda" satırı: `base_km_expanding`'in seçilen j'deki koşullu değeri ve "j gün tavan yapan n arzdan m tanesi" sayımı. *Bkz. §7.7, §8.16*

**Hijyen taraması**: Repoya giren her metnin 64 kasa koduna (büyük/küçük harf duyarlı) ve bülten dosya adı kalıbına karşı taranması; kodlar taranırken bile ekrana yazdırılmaz. *Bkz. §2.6.5, §8.25*

**Hücre** (skor hücresi): Bir karşılaştırmanın sonucu: model, karşılaştırıcı, ufuk, metrik, n, fark, %95 aralık, kazanç/kayıp/eşit ve hüküm; "birincil" ya da "keşif" etiketi taşır. *Bkz. §6.6.6, §6.9.2*

**Hüküm dili**: Sayıların nasıl söyleneceğini belirleyen kural (`scoring.verdict`): n < 10'da hüküm yok; 10 ≤ n < 30'da "yetersiz örnek"; n ≥ 30'da aralığa göre "geçiyor", "geçemiyor" ya da "ayırt edilemiyor"; aralık yoksa "aralık için yetersiz". *Bkz. §6.8*

**Hüküm hücresi** (`verdictCell`): Sade görünümde işaret (✓ / × / ≈) ve skor dosyasındaki `verdict` metni; renk yalnız "geçiyor" (yeşil) ve "geçemiyor" (kırmızı) için verilir. *Bkz. §8.11*

## I

**IBM Plex**: Sade görünümün yazı tipi ailesi (Sans, Sans Condensed, Mono); `@fontsource` paketlerinden derlemeye gömülür. *Bkz. §8.23*

**ID-A / ID-B / ID-C** (PB özdeşlikleri): Planlanan yapının Decimal tam eşitlikle sağlaması gereken üç özdeşlik: arz sonrası sermaye = arz öncesi sermaye + bedelli; taban arz = bedelli + ortak satışı; azami arz = taban arz + ek satış tavanı. Tutmazsa PB modelleri `PB_IDENTITY` ile reddeder. *Bkz. §3.6.4*

**INDEX.json, INDEX_POST_D1.json, INDEX_POST_BREAK.json** (model dizinleri): Her aşamanın donmuş modellerini listeleyen dizinler (27, 1 ve 2 model). Her girdi model dosyasının sha256'sını, şartname hash'ini ve eğitim bilgisini taşır; bir kayıt kendi aşamasının dizinindeki bütün modelleri içerir. *Bkz. §6.11.1, §2.7.2*

**INTEGRITY_FAILED**: Gömülü model kümesi açılış denetiminden geçmezse bütün tahmin komutlarının döndürdüğü hata kodu. *Bkz. §7.4*

**IPC** (süreçler arası iletişim): Tauri'de webview içindeki TypeScript ile Rust arka uç arasındaki mesajlaşma; ön uç `invoke` ile komut çağırır, argüman ve yanıt JSON'dur. *Bkz. §7.1*

## İ

**i18n/tr.ts**: Arayüzdeki bütün Türkçe metinlerin tek dosyası (≈ 2 100 satır); başka dosyada Türkçe karakterli metin sabiti bulunursa test kırmızı olur. "geçiyor" sözcüğü burada yalnız bir kez geçer. *Bkz. §8.9*

**İç LOOCV** (iç çapraz doğrulama): Walk-forward'ın her dış fold'unda, yalnız o fold'un eğitim kümesi içinde, ızgaradaki adayları birini dışarıda bırakarak skorlayıp en iyisini seçmek; ön işleme her iç bölmede yeniden kurulur. *Bkz. §4.2.4*

**İçerik adresli dosya adı**: Dosya adının içeriğin sha256'sının ilk 12 hanesini taşıması (ör. `…_65a39d7392dd.json`); dosyalar `xb` kipinde açıldığı için var olan dosya yeniden yazılamaz. *Bkz. §6.3.1, §6.11.2*

**İlan dışı kapanış**: Tatil tablosunda olmadığı hâlde THB'nin hiç yayımlanmadığı hafta içi gün (ör. deprem kapanışı); seans sayılmaz, kanıtıyla ayrı bir dosyaya yazılır. *Bkz. §3.4.1, §3.4.5*

**İlk işlem günü** (T): Payın Borsa İstanbul'da ilk kez işlem gördüğü gün (`first_trading_date`); listeleme öncesi kaydın zaman sınırı ve walk-forward kesimidir. *Bkz. §3.1, §4.1.1*

**İmzalı veri paketi**: Repo kopyası olmayan kullanıcılar için önerilen, botun her gece yayımlayacağı minisign (Ed25519) imzalı, artan sıra numaralı, dosya başına sha256'lı paket; henüz yok. *Bkz. §2.7.7*

**include_str!** (Rust makrosu): Bir dosyanın metnini derleme anında programın içine gömer; çalışma anında diskte o dosyanın bulunması gerekmez. *Bkz. §7.1, §7.3*

**index.lock**: Git'in yazma sırasında oluşturduğu kilit dosyası; oturumlar bu hatada bekleyip yeniden dener, kilidi silmez. *Bkz. §2.4.5, §7.3*

**inputs_pit_ok**: Bir kaydın girdilerinin nokta-zamanında olduğunu söyleyen koşul: her dolu alanın kaynağı D_1'den önce yayımlanmış ve belge sha256'sı tutuyor; f6 için S0 < ref_date ≤ D_1. LATE_RECORD sınıfı için zorunludur. *Bkz. §6.10.2, §3.9.1*

**invoke**: Tauri'nin ön uçtan Rust komutu çağıran fonksiyonu; Rust `Ok` dönerse Promise çözülür, `Err` dönerse reddedilir. Testlerde sahtesiyle değiştirilir. *Bkz. §7.1, §8.4*

**İptal kaydı** (`CANCELLATION`): Hatalı bir kaydı silmeden geçersizleştiren ayrı kayıt; neden zorunludur. İlk işlem gününden itibaren (POST_D1'de T_open'dan sonra) yapılamaz. *Bkz. §6.11.4*

**İşlem kodu** (ticker): Payın borsadaki kısa kodu (ör. NETGL); bültende `.E` ekiyle geçer. *Bkz. §3.2.1, §3.4.6*

**İşlem sayısı** (`TOPLAM SOZLESME SAYISI`, `trade_count_raw`): THB'deki günlük toplam sözleşme sayısı; "işlem gördü mü" testinde ve Analiz ekranının işlem sayısı çubuklarında kullanılır. *Bkz. §3.2.1, §8.15*

**İzahname**: Halka arzın SPK onaylı tanıtım belgesi. Eski kohort için yedi alan (dağıtım yöntemi, fiyat istikrarı, satmama süreleri, sektör …) çıkarıldı; bunlar model girdisi değildir. *Bkz. §2.3.9*

**İzinli izlenmeyen**: Görev sırasında çalışma ağacında bulunmasına izin verilen, commit'lenmemiş dosyalar (ör. bekleyen görev dosyaları). *Bkz. §2.4.2, §2.7.6*

## J

**j** (seri günü): "Seri j gün sürdü" koşulu; koşullu olasılıklar S_k / S_j ile hesaplanır. Resmi j yalnız sonuç dosyasından gelir; hesaplayıcıda farklı bir j "varsayımsal"dır. *Bkz. §4.4.1, §8.16*

**jsdom**: Node içinde çalışan sahte tarayıcı belgesi; DOM isteyen vitest dosyaları bununla koşar. *Bkz. §8.25*

**JSON / JSON Lines**: Metin tabanlı veri biçimi; JSON Lines her satırda bir JSON nesnesi tutar (deney günlüğü, altın vektörler). *Bkz. §6.13.1, §7.1*

## K

**K-PIN** (önceden onaylı pin kuralı): Görev dosyasının, görevin bilerek kıracağı testleri ve yerine gelecek genel ilişkiyi önceden yazması; kullanıcı tek satırla onaylar. Türleri K-PIN, K-PIN-L, K-PIN-UI, K-PIN-FIX. *Bkz. §2.4.7, §6.15.4*

**k_t / r_t** (yastık ölçüleri): k_t = ln(P_t / P) / ln(1/0,9), arz fiyatına "taban adımı" cinsinden uzaklık; r_t = 10 − t, D10'a kalan seans sayısı. k_t ≥ r_t ise D10'da arz altı yapısal olarak imkânsızdır. *Bkz. §5.4.2*

**K-UI, K-FIX, K-FRZ …** (görev kararları): Görev dosyalarındaki numaralı bağlayıcı kararlar (ör. K-UI-4 ana ekran kapısı, K-FIX-1 Analiz'den listeye dönüş). *Bkz. §2.4.2, §8.24*

**k1, k2, k3** (seçim koşulları): Öne çıkma kurallarının koşulları. Tavan v1 adayları için k1 = kasa birincil hücresi geçiyor, k2 = v0'a karşı aralığın üst ucu < 0, k3 = yakın dönem etiketi "bozuyor" değil; kırılma modelinde k1 backtest, k2 canlı aşamasının koşuludur. *Bkz. §4.7.5, §5.3.10*

**Kabul kapısı**: Görev dosyasının sonunda, işin tamam sayılması için denetlenebilir şartlar (K1…K5). *Bkz. §2.4.2*

**Kabul testi**: Şartnamenin numaralı kabul maddelerini sınayan test (ör. SPEC_SCORING §10, uygulamanın U1–U80'i). *Bkz. §6.15.3, §8.10*

**Kalibrasyon**: Verilen olasılıkların gerçekleşme oranıyla tutması. BorsAi'de hüküm değil, ortalama tahmin ile gözlenen oranın yan yana yazıldığı betimleyici satırdır. *Bkz. §6.6.5*

**Kanonik 20**: H99'un eski repodan alan alan kanıtlı alınan 20 üyesi; nokta-zamanında durumları `PASS`, diğer 79 üyeninki `UNKNOWN`'dır. *Bkz. §3.3.1, §3.3.2*

**Kanonik JSON**: Aynı içeriğin her makinede aynı baytları vermesi için anahtarları sıralı, boşluksuz JSON (`canonical_json`); hash girdisidir. Dosyaya yazım için `pretty_json_bytes` (2 boşluk girinti) kullanılır. *Bkz. §6.3.2*

**KAP** (Kamuyu Aydınlatma Platformu): Şirketlerin ve borsanın resmi duyuru platformu; halka arz sonuçları ve işlem başlama bildirimleri buradan alınır. *Bkz. §3.2.2*

**Kaplan–Meier** (KM): Tehlikeyi her gün için "o gün bozulan / o gün risk altında olan" oranıyla tahmin eden, özellik kullanmayan klasik sağkalım tahmincisi; S_k bu oranlardan kurulur. Projenin tavan kurallarının temelidir. *Bkz. §4.1.5, §4.4.2*

**Karantina**: Eski kohort bültenlerinin repoya girmeden indirildiği repo dışı klasör (`~/Desktop/BorsAi_quarantine`); repoya yalnız açık üyelerin ayıklanmış satırları ve zip pinleri girer. *Bkz. §6.12.4*

**KARARLAR.md**: Şartnameyle birlikte yazılan karar listeleri (Faz 6 D1–D8, Faz 7 K1–K5, Faz 7C C1–C5, Faz 8 A/B/C); proje sahibinin onayını taşır. *Bkz. §2.3.8, §2.3.9*

**Kart**: Uygulamada bir sorunun özet bölümü: "Tavan serisi — kaç gün tavan?", "Düşüş (D10)", "Kırılma akşamı: yarın da taban mı?" kartları ve model kartı. *Bkz. §8.15, §8.22*

**Kasa** (vault, SEALED): Eski kohortun, yıl içinde tabakalı ve sabit tohumla çekilip sonuçları hiç görülmeden kapalı tutulan 64 üyesi; doğrulanacak özellikler önceden push edildikten sonra 29 Eylül 2026'da bir kez açıldı. Üyelerinin kodları hiçbir dosyaya yazılmaz. *Bkz. §6.12.3, §6.12.6*

**Kasa çekilişi**: Kasa üyelerini seçen deterministik çekiliş: yıl içinde tabakalı %50, `numpy PCG64(20260924)`; maruz kalmış 5 üye önceden açık kümeye alındı. Bağımsız denetim 135/135 aynı sonucu üretti. *Bkz. §6.12.3*

**Kayan nokta** (f64, binary64): Bilgisayarın olağan ondalık sayısı; 53 bit anlamlı hane (≈ 15–17 ondalık) taşır ve her işlem yuvarlanır (0,1 + 0,2 ≠ 0,3). *Bkz. §7.1*

**Kayıt** (tahmin kaydı): Bir arz için o aşamanın dizinindeki bütün modellerin çıktılarını, girdileri ve parametre hash'lerini birlikte saklayan JSON (`registry/records/<T>/…`, şema `borsai.record/1`); sınıf kayda yazılmaz. *Bkz. §2.0, §6.11.2*

**Kazanç / kayıp / eşit sayımı**: Bir hücrede modelin kuraldan daha az, daha çok ve aynı yanıldığı arz sayıları; ortalamanın birkaç uç arzla sürüklenip sürüklenmediğini gösterir. *Bkz. §6.6.6*

**Kesim tarihleri** (`OUTCOME_CUTOFF`, `LISTING_CUTOFF`): Sıra kuralının sabitleri: 2026-08-19 (H99'un son sonuç seansı) ve 2026-08-06 (H99'un son ilk işlem günü). Kodda `SEQUENCE_CUTOFF` adıyla da geçer. *Bkz. §3.1, §3.8.4*

**Kesin önce kuralı**: Walk-forward'da eğitim satırının hedef seansının test arzının kesim gününden kesin önce (<) olması şartı; aynı gün dahil değildir. *Bkz. §6.5.2*

**Keşif** (exploration): (a) Birincil olmayan, hüküm vermeyen hücre etiketi; (b) sonuçlar görüldükten sonra yapılan özellik araması (Faz 7C'de 2 054 varyant, günlükte `kind: exploration`). *Bkz. §6.9.2, §4.8.2*

**Kırılma akşamı** (E_b): Serinin bozulduğu günün (D_b) THB'si yayımlandıktan sonraki akşam; `break_floor_v0` yalnız b ∈ 1..9 için çağrılır. *Bkz. §5.3.2*

**Kırılma günü**: bkz. **b**. *Bkz. §5.1.1*

**Kırılma sonrası hücre**: Tavan yolu modelinde, serisi t günde biten eğitim arzlarının son limit gününden m seans sonraki gerçekleşmiş getirilerinin toplandığı ampirik dağılım (g, m). *Bkz. §4.6.3*

**Kırpma** (winsor): Değerleri eğitimin p05 ve p95 kantillerine çekmek: x' = min(max(x, p05), p95); uç değerlerin modeli sürüklemesini önler. Kırpılan değer `clipped: true` ve uyarıyla işaretlenir. *Bkz. §4.2.3, §5.1.3*

**Kilit** (kilitlenme): Fiyatın gün boyu limitte kalması (tavanda en düşük = üst limit, tabanda en yüksek = alt limit); limite gün içinde dokunmaktan güçlü bir işarettir. *Bkz. §5.2.2, §5.3.4*

**Kişi-dönem verisi** (person-period): Her arzın risk altında olduğu her gün için bir satır ("o gün seri bozuldu mu?") kurularak tehlike modelinin sıradan lojistik regresyonla fit edilmesini sağlayan veri yapısı; sansürü doğal taşır. H99'da 508 satır ve 85 olay vardır. *Bkz. §4.4.2*

**Kişisel kayıt** (senaryo kaydı): Kullanıcının uygulama verisine sakladığı tahmin (`borsai.app_scenario/1`); `official: false` taşır, repoya yazılamaz, sicile ve skora asla girmez. *Bkz. §7.7, §8.19*

**Klonda prova** (adım 0b): Oturumun değişikliği önce `git clone --local` ile açılan geçici bir klonda deneyip kırılacak testlerin tam listesini çıkarması. *Bkz. §2.4.7*

**KM**: bkz. **Kaplan–Meier**. *Bkz. §4.1.5*

**Kod değişikliği** (`KOD_DEGISIKLIGI`): Tamlık denetiminde, aynı gün kaybolan bir pay koduyla aynı bülten adını taşıyan yeni kod; yeni arz sayılmaz. *Bkz. §3.10.3*

**Kohort**: Aynı kuralla seçilmiş arz grubu (H99, eski kohort). *Bkz. §3.1, §3.3.1*

**Komut** (Tauri komutu): Ön ucun adıyla çağırdığı Rust fonksiyonu; BorsAi'de 55 komut vardır, hepsi `Result<T, AppError>` döner. *Bkz. §7.1, §7.7*

**Koşullu güncelleme**: Modeli yeniden çalıştırmadan "seri j gün sürdü" bilgisiyle eğriyi yeniden ölçekleme: P(L ≥ k | L ≥ j) = S_k / S_j; "yarın da tavan" = S_{j+1} / S_j. *Bkz. §4.4.1, §8.16*

**Koşullu RPS** (RPS_1): D1 sonrası modelin birincil metriği: k = 2..10 için koşullu eğrinin RPS'i, (1/9) Σ (S_cond[k] − 1[L ≥ k])². *Bkz. §5.1.3, §5.2.6*

**Kotasyon** (halka arzsız): Payların halka arz yapılmadan borsada işlem görmeye başlaması; eski kohort evreninde bir satır bu yüzden `OUT_OF_SCOPE` oldu. *Bkz. §6.12.2*

**Kör hesap**: Fable'ın bağımsız skor hesabını, Opus'un skorlarını görmeden önce commit edip sonra iki sonucu karşılaştırması (Faz 6 açık küme ve kasa). *Bkz. §2.4.6, §6.16*

**Kuantil** (q10, q50, q90): Bir dağılımın belirli bir oranının altında kaldığı değer; tavan yolu modeli karışımın %10, %50 (medyan) ve %90 kuantillerini verir. *Bkz. §4.6.4*

**Kullanıcı beyanı** (U52): Ayrıntılı görünümde kullanıcının bir günü "seri sürüyor" diye işaretlemesi; proje sahibinin kararıyla yalnız etikettir, hiçbir olasılığa, sicile ya da skora girmez ve Rust komutlarına parametre olarak bile gitmez. *Bkz. §2.3.5, §8.10*

**Kural satırı**: Bir model ailesinin yanında dondurulan özelliksiz karşılaştırıcı (`@INF`, `@ZERO`). *Bkz. §4.7.2, §4.8.3*

**Kuyruk** (emir kuyruğu): Fiyat limitteyken biriken karşılanmamış alış (tavanda) ya da satış (tabanda) emirleri; kilit, kuyruğun gün sonunda tükenmediğini gösterir. *Bkz. §5.2.2, §5.3.4*

## L

**L** (seri uzunluğu): D1'den başlayan kesintisiz tavan kapanışı sayısı (0–10); ilk tavan olmayan günde durur, sonraki tavanlar sayılmaz. *Bkz. §3.5.2*

**L2 cezası** (Ridge cezası): Amaç fonksiyonuna (λ/2)·‖β‖² eklemek; katsayıları büzer, aşırı uyumu azaltır. Sabit terim cezasızdır. *Bkz. §4.2.2*

**LATE_RECORD** (geç kayıt): Model sonuçtan önce donmuş ve push kanıtlı, ama kayıt D_1'den sonra push edilmişse satırın sınıfı; girdiler nokta-zamanında olmalıdır. Canlı terazide `n_late` olarak ayrı görünür. *Bkz. §2.0, §6.10.2*

**Ledger** (fold ledger): Bir backtest koşusunda fold başına bir satır yazılan CSV: eğitim kümesi hash'leri, tahmin, gerçekleşen, seçilen hiperparametre ve iç skor tablosu. *Bkz. §6.5.5*

**legacy/**: Eski repodan birebir kopyalanan, değiştirilmeyen referans kod (V1.5 çekirdeği, eski toplayıcı, "true live" dondurma düzeni); port testleri ona karşı koşar. *Bkz. §2.2.1*

**LEGACY_SELF_REPORTED** (kendi beyanı): Eski repodan gelen, zamanı yalnız kendi beyanına dayanan kayıt; kanıtlı canlı metriğe girmez, ayrı alt satırda durur. *Bkz. §2.2.2, §6.10.3*

**LIVE** (canlı): Model sonuçtan önce donmuş ve push kanıtlı, kayıt da D_1'den önce push kanıtlı olan satırın sınıfı; tek gerçek prospektif kanıttır. Bugünkü tek LIVE satır NETGL'in eski repodan gelen V1.5 kaydıdır. *Bkz. §2.0, §6.10.2*

**libmpdec**: CPython'un Decimal türünü gerçekleyen C kütüphanesi; Rust portu onun üs kurallarını ve sınırlarını taklit eder. *Bkz. §7.8.1*

**Limit yolu**: Seri sürdükçe fiyatın art arda üst limitlerden geçtiği deterministik yol (C_h); H99'da 424/424 gerçek kapanışı Decimal eşitlikle üretir. *Bkz. §4.6.2*

**Listeleme öncesi**: Tahminin ilk işlem gününden önce dondurulmuş bir kayda yazıldığı aşama; modelleri `models/INDEX.json`'dadır. *Bkz. §4.1.3, §4.10*

**Log-kayıp** (log-loss): Gerçekleşen olaya verilen olasılığın negatif logaritmasının ortalaması; emin olup yanılmayı Brier'den sert cezalandırır. İkincil metriktir. *Bkz. §6.6.3, §4.2.1*

**Logit / log-odds**: logit(p) = ln(p / (1 − p)); olasılığı (−∞, +∞) aralığına açar. Bir katsayı, özellik bir birim artınca log-odds'un ne kadar arttığını söyler; odds e^β katına çıkar. *Bkz. §4.2.1*

**Lojistik regresyon**: Bir olayın olasılığını sigmoid(doğrusal öngörücü) ile modelleyen yöntem; katsayılar en çok olabilirlikle bulunur. *Bkz. §4.2.1*

**LOOCV** (leave-one-out): Her seferinde bir gözlemi dışarıda bırakan çapraz doğrulama. *Bkz. §4.2.4*

## M

**M24 kuralı** (sonuç ilerlemesi): Skor pinlerinde yalnız PENDING → dolu geçişine izin veren ilişki kuralı; dondurulmuş alanlar, dolu ufuklar ve yeni arzlar yine kırmızı verir. *Bkz. §2.4.7, §6.14.3*

**MACHINE_EXTRACTED**: Eski kohort sonuç satırlarının dayanağı (`outcome_basis`): değerleri makine ayıkladı, insan görmedi. *Bkz. §3.11, §6.12.4*

**MACHINE_SEQUENCED** (makine sıralı): Kırılma akşamı kayıtlarının türü ve prospektif satırların sınıfı. Tahmin skorlama anında yalnız pinli resmi dosyalardan deterministik üretilir, prospektiflik git DAG'ından okunur, push kanıtı gerekmez; ayrı ölçekte (`live_break`) sayılır. *Bkz. §5.5, §6.10.1*

**MAE** (ortalama mutlak hata): (1/n) Σ |R̂ − R|; getiri tahminlerinin birincil metriği, ekranda "puan" ile yazılır. *Bkz. §6.6.1*

**Makine kaydı**: Kırılma akşamı tahminini, ara değerleri, kod hash'lerini ve yapısal sıfır bloğunu taşıyan dosya (`registry/post_break/<T>/machine_<UTC>_<sha>.json`, şema `borsai.post_break_machine_record/1`). *Bkz. §5.5.4*

**MANIFEST.csv, MANIFEST_OOT.csv**: İndirilen her bülten zip'inin tarih, tür, URL, sha256, bayt ve yayın zamanını tutan pin dosyaları (canlı 73 satır, eski kohort 1 168 satır). *Bkz. §3.2.1, §3.11*

**Maruziyet beyanı**: Orkestratörün ya da bir oturumun sonuç verisine baktığında bunu görev dosyasına ya da kayda yazması; görülen değerler yazılmaz. *Bkz. §2.4.2, §2.6.5*

**MedAE** (medyan mutlak hata): Mutlak hataların medyanı; aykırı değerlere az duyarlı, ikincil metrik. *Bkz. §6.6.1*

**Medyan seri**: Birikimli P(L ≤ l)'nin ilk kez 0,5'i geçtiği l; NETGL için `ceiling_hazard_v0`'da 3 gündür. *Bkz. §4.4.8*

**"Mekanik olan öğrenilmez, kodlanır"**: Aritmetik olarak kesin olan bir sonucun (ör. yastık kuralı) modele öğretilmeyip kodla hesaplanması ilkesi. *Bkz. §2.1, §5.4.1*

**MIN_TRAIN_N = 10**: Bir fold'un skorlanabilmesi için gereken en küçük eğitim arzı sayısı; H99 backtest'lerindeki n = 87'nin nedeni budur. *Bkz. §6.5.3*

**min10**: 10. günün en düşük mümkün kapanışı: kırılma günü kapanışına alt limit işlevinin 10 − b kez uygulanması. min10 > P ise D10'da arz altı imkânsızdır. *Bkz. §5.4.3*

**Mod göstergesi / mod bandı**: Ekranın hangi kipte olduğunu gösteren etiket: SENARYO (sicile girmez), RESMİ KAYIT, DOĞRULUK. Sade görünümde küçük bir hap, ayrıntılı görünümde tam genişlikte banttır. *Bkz. §8.11, §8.22*

**model_id**: Bir modelin değişmez kimliği (ör. `ceiling_hazard_v0`); değişiklik yeni kimlik ister. *Bkz. §2.1, §6.2*

**Model performansı** (ekran): Sade görünümde her modelin kendi sorusunda basit kurala karşı sonuçlarını, üç sınavı ayrı ayrı ve canlı sicil ilerlemesini gösteren ekran; sayılar yalnız skor dosyalarından gelir. *Bkz. §8.17*

**MODELS.md**: `python -m borsai.report` ile altın ledger'lardan üretilen backtest sonuç belgesi; elle düzenlenmez. *Bkz. §6.5.5*

**Monitör**: Sade görünümün ana ekranı: takipteki arzların durumu, sayımlar, model tahminleri ve olay akışı; repo modu ister. *Bkz. §8.12*

**Murphy ayrıştırması**: Brier skorunu kalibrasyon ve çözünürlük (ayırt etme) paylarına bölen yöntem; D1 sonrası modelin kazancının ≈ %92'sinin ayırt etmeden geldiğini gösterdi. *Bkz. §5.6.1*

**Mutasyon testi**: Koda bilerek küçük bir hata sokup testlerin kırmızıya dönüp dönmediğine bakmak; kırmızı olmayan mutant bir test açığıdır, kodun davranışını değiştirmiyorsa "eşdeğer mutant"tır. *Bkz. §2.4.6, §6.15.5*

## N

**n kuralları** (küçük n): Canlıda n < 10 iken yalnız satır tablosu; 10 ≤ n < 30'da "yetersiz örnek"; hüküm yalnız n ≥ 30'da ve aralıkla verilir (`MIN_N_METRIC = 10`, `MIN_N_VERDICT = 30`). *Bkz. §6.8, §8.10*

**NA_LIMIT**: O seansın THM üst limiti yoksa tavan etiketinin NA olduğu satır durumu; ilgili tavan metrikleri o arzda hesaplanmaz. *Bkz. §3.5.1*

**NETGL vakası**: 17 Eylül 2026'da işlem görmeye başlayan arzın yolu: D1–D3 tavan, D4–D10 yedi taban, D10 getirisi −%36,17. Kırılma akşamı modelinin ve rejim sorusunun çıkış noktasıdır; kitabın örnek arzıdır. *Bkz. §2.6.3, §3.5.5*

**Neumaier toplaması**: Kayan noktada küçük terimlerin kaybolmasını telafi eden toplama yöntemi; CPython 3.12'nin `sum()`'ı bunu kullandığı için Rust portu da aynı algoritmayı yazar. *Bkz. §7.1, §7.8.1*

**Newton–Raphson**: Gradyan ve Hessian matrisiyle adım adım en küçük noktayı bulan çözücü; tavan ve D1 sonrası modellerde numpy ile yazılmıştır (durma: max|∇| ≤ 1e-10). *Bkz. §4.4.5, §5.2.4*

**NLL** (negatif log-olabilirlik): −Σ [y ln p + (1 − y) ln(1 − p)]; lojistik modelin en küçüklenen amaç fonksiyonu. *Bkz. §4.2.1*

**no_frontend_math.test.ts**: Ön uç kaynağını tarayıp hesap işlemlerini (çarpma ve bölme yalnız `format.ts` ile `svg.ts`'te serbest), yasak fonksiyonları ve `tr.ts` dışındaki Türkçe metni yakalayan statik test. *Bkz. §8.6*

**Nokta-zamanında** (point-in-time, PIT): Bir tahminde yalnız o anda gerçekten yayımlanmış bilgiyi kullanmak, geleceği sızdırmamak. *Bkz. §3.1, §3.8.4*

**NOT_APPLICABLE** (kapsam dışı): Modelin o arz için tanımlı olmadığı durum; ret değildir. D1 sonrası modelde `D1_NOT_CEILING`, kırılma modelinde `NOT_APPLICABLE_B10` ve `NOT_APPLICABLE_NO_BREAK`. *Bkz. §5.2.1, §5.3.2*

**Notarization**: Apple'ın dağıtılan macOS uygulamalarını onaylama süreci; uygulama başkalarına dağıtılacaksa gerekir. *Bkz. §2.8*

**npm**: Node'un paket yöneticisi; uygulamanın ön uç bağımlılıkları (`package.json`) ve `npm test` (tsc + vitest) bununla yönetilir. Çalışma zamanı bağımlılığı yalnız iki pakettir. *Bkz. §2.8, §8.25*

## O

**Ofset**: D1 sonrası modelde listeleme öncesi `ceiling_hazard_v0`'ın doğrusal öngörücüsünün hiç değiştirilmeden alınıp üstüne yalnız D1 düzeltmesinin eklenmesi; δ = 0'da model karşılaştırıcının kendisidir. *Bkz. §5.2.3*

**Olay delegasyonu**: Her düğmeye ayrı dinleyici bağlamak yerine ekranın kökündeki tek dinleyicinin `data-action` özniteliğinden hangi düğmeye basıldığını bulması. *Bkz. §8.1*

**OOT** (out-of-time): bkz. **Zaman-dışı test**. *Bkz. §6.12.1*

**OOT_BLIND / OOT_RETRO**: Zaman-dışı terazinin sınıfları: model ve kayıt sonuçtan önce, kohort düzeyi kapıya uygun biçimde push kanıtlıysa OOT_BLIND; değilse yalnız bilgi olan OOT_RETRO. *Bkz. §6.12.5*

**OPERATIONAL_RULES**: Şartname beklentilerindeki sözel ifadeleri ("≈ 0", "çoğu") sayıya çeviren, sonuç görülmeden yazılan etiket kuralları (Faz 1B ve Faz 4…8). *Bkz. §6.9.3, §2.4.3*

**Option / Result** (Rust türleri): `Option<T>` değer var/yok (`Some`/`None`), `Result<T, E>` başarı/hata (`Ok`/`Err`); Rust'ta istisna yoktur, hata dönüş değeriyle taşınır. *Bkz. §7.1*

**Opus**: Kod, modelleme, backtest, dondurma ve uygulama işlerini yapan Claude Code modeli (önce Opus 5, Faz 5'ten itibaren Opus 5.5). *Bkz. §2.4.1*

**Orantılı odds varsayımı**: Bir özelliğin her gün tehlikenin log-odds'unu aynı miktarda kaydırdığı varsayımı (β bütün günlerde ortak). *Bkz. §4.4.5*

**Orkestratör**: Planı yöneten, görev dosyalarını yazan, raporları diskten okuyup kilit sayıları yeniden hesaplayan claude.ai proje sohbeti; kod yazmaz, commit atmaz, git'i yalnız okur. *Bkz. §2.4.1*

**Ortak satışı** (mevcut pay satışı): Var olan ortakların sattığı pay; girdide `existing_share_sale_shares` ve `planned_existing_share_sale`. *Bkz. §3.2.3*

**OUT_DIR**: Cargo'nun `build.rs` çıktıları için verdiği geçici derleme dizini; `embedded.rs` ve süzülmüş skor kopyası buraya yazılır. *Bkz. §7.1, §7.3*

**OUT_OF_SCOPE** (kapsam dışı): Paydada halka arz olmayan bildirimlerin durumu (varant, sertifika, fon, bedelli kalan pay, kod ya da pazar değişikliği, ertelenen arz); nedeni `OTHER:` ile yazılır, hiçbir sayıma girmez. *Bkz. §3.9.3*

**outcome_ingest_commit**: Bir arzın sonucunu repoya ilk sokan commit: sonuç dosyasını ekleyen commit ile D_1…D_10 tarihli herhangi bir bülteni ekleyen ilk commit'in en erkeni. Sınıf formülü modelin bunun atası olup olmadığına bakar. *Bkz. §6.10.2*

**OutcomeConflict**: Var olan bir sonuç dosyasında dolu bir satır yeniden hesapta farklı çıkarsa verilen hata ("resmi veri değişmiş olabilir"); yalnız PENDING satırlar değişebilir. *Bkz. §3.10.2*

## Ö

**Ölçek** (scale): Skorların karışmaması için her gözlemin taşıdığı terazi etiketi: `backtest`, `backtest_near_era`, `live`, `live_conditional`, `live_post_d1`, `live_break`, `OOT_PRE_H99`, `OOT_PRE_H99_POST_D1_MACHINE_SEQUENCED`. Farklı ölçekler birleştirilmeye çalışılırsa `ScaleMixError`. *Bkz. §5.1.4, §6.10.1*

**"Ölçmeden aktarma yok"**: Handoff'tan, eski rapordan ya da hafızadan gelen hiçbir öncülün yeniden ölçülmeden kullanılmaması ilkesi; orkestratörün kendi sayıları için de geçerlidir. *Bkz. §2.4.4*

**Ön eleme**: Tasarıma maruz backtest sonucunun anlamı: kanıt değil, canlı sınavdan önceki eleme. Kırılma kartı "ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = k" etiketiyle gösterilir. *Bkz. §5.3.10, §2.6.1*

**Ön işleme**: Ham özelliklerin modele girmeden geçtiği fold içi dönüşümler (f3 filtresi, %40 kuralı, kırpma, medyanla doldurma, f5, log, sıfır varyans, z-skor); parametreler yalnız eğitim fold'undan öğrenilir. *Bkz. §3.7, §4.2.3*

**Ön kayıt** (pre-registration): Modelin bütün kurallarının hiçbir fit yapılmadan önce yazılıp mühürlenmesi. BorsAi'de şartname commit'i uygulama commit'inin atası ve push kanıtlıdır. *Bkz. §4.3.1, §6.9.3*

**Ön uç** (frontend): Pencerede görünen TypeScript arayüz; Rust komutlarını çağırır, sayıları biçimlendirir ve SVG çizer. Kendisi hesap yapmaz, dosyaya ve git'e yazmaz. *Bkz. §8.1*

**"Ön uç hesap yapmaz"**: Ekrandaki her sayının bir Rust komutundan ya da dosyadan olduğu gibi gelmesi kuralı; yalnız biçimlendirme, piksel koordinatı, karşılaştırma ve metin işlemine izin verilir. *Bkz. §8.6, §7.2*

**ÖNCE OKU**: Görev dosyasında oturumun işe başlamadan okuyacağı dosyaların bölüm numaralarıyla listesi. *Bkz. §2.4.2*

**Önceden yazılmış beklenti**: Şartnamenin her hücre için sonuç görülmeden yazdığı beklenen fark aralığı; gerçekleşenle satır satır karşılaştırılır ("tuttu", "tutmadı", "daha iyi"). *Bkz. §2.4.3, §6.9.3*

**Öne çıkma** (öne çıkan model): Uygulamada bir modelin önceden yazılmış seçim kuralıyla kartın ilk satırına ve renkli işarete konması; model kayıttan ya da listeden çıkmaz ("terfi yok"). *Bkz. §4.10, §5.3.10*

**Önek pini** (`prefix_sha256`): Dosyanın tamamının değil, başlık dahil belirli bir satıra kadarki baytlarının sha256'sı. Sona ekleme pini bozmaz, eski bir satır değişirse bozar (TÜFE tablosu, kohort dosyası). *Bkz. §3.6.3, §3.8.3*

## P

**P_close_ceiling** (P(Dk'de tavan kapanışı)): Serinin bozulduktan sonra yeniden tavana dönebileceğini de sayan ikincil çıktı: S_k + (1 − S_k)·r. *Bkz. §4.4.7*

**p_floor_F1 / p_floor_F2**: Kırılma modelinin çıktıları: ertesi seansın ve sonraki iki seansın taban olasılıkları. *Bkz. §5.3.3*

**P_L** (P(L = l)): Seri uzunluğunun olasılık dağılımı: P(L = 0) = 1 − S_1, P(L = l) = S_l − S_{l+1}, P(L = 10) = S_10. *Bkz. §4.4.1*

**p_up**: Modelin "D_h kapanışı arz fiyatının üstünde" (Y_h = 1) olayı için verdiği olasılık. *Bkz. §4.1.1*

**Parite**: İki ayrı gerçeklemenin (Python ve Rust) aynı girdide aynı çıktıyı vermesi; Python'un ürettiği altın vektörlerle, |Δ| ≤ 1e-9 toleransla ve bit-eşitlik tabanıyla sınanır. *Bkz. §7.1, §7.11*

**Parite olayı** (incident): Dondurma sonrasında Rust tahmini ile Python kaydı uyuşmazsa `app/parity/incidents/<UTC>.json` dosyasına yazılan kayıt; kaydın kendisi yine geçerlidir. *Bkz. §7.9.4*

**Pay dışı araç** (`PAY_DISI_ARAC`): Tamlık denetiminde `ENSTRUMAN GRUBU` ≠ `EQT` olan yeni kodlar (varant, sertifika, borsa yatırım fonu …); halka arz sayılmaz. *Bkz. §3.10.3*

**Pay Piyasası**: Borsa İstanbul'un payların işlem gördüğü piyasası; seans takvimi, fiyat adımı ve marj kuralları bu piyasanın prosedüründen gelir (21.09.2026 tarihli rev. 54 bant kuralını değiştirmedi). *Bkz. §2.6.9, §4.6.2*

**Payda** (`registry/ipos.csv`): Kapsam başlangıcından (2026-08-07) sonra işlem görmeye başlayan her arzın satırı (`FROZEN`, `SKIPPED`, `OUT_OF_SCOPE`); sessiz dışlamayı önler (kural 2). Bugün 26 satırdır. *Bkz. §3.9.3, §6.2*

**Payların İşlem Görmeye Başlaması**: Borsa İstanbul'un ilk işlem gününü, baz fiyatı ve işlem görecek pay tutarını duyurduğu KAP bildirimi; payda ve eski kohort evreni bu bildirimlerden çıkarıldı. *Bkz. §3.2.2, §6.12.2*

**Pazar** (YILDIZ / ANA): Payın işlem gördüğü pazar bölümü; v2 tablosunda eski kohort için `market` sütunu. *Bkz. §3.8.3*

**PB** (pre-bookbuilding, talep toplama öncesi): Talep katı henüz yokken yalnız SPK onaylı planlanan yapıdan tahmin yapan model ailesi (`pb_v0`, `pb_ceiling_v0`, `pb_ceiling_path_v0`); bilgi kesimi B(k)'dir. Ret kodları `PB_FIELD_MISSING`, `PB_IDENTITY`, `PB_PRICE_RANGE`. *Bkz. §3.6.4, §4.5*

**pb_v0 / pb_ceiling_v0**: PB ailesinin getiri/p_up modeli (V1.5 sınıfı, pb1–pb3) ve tavan serisi modeli (pb1, pb2). Talep katının değeri bu modellerle f3'lü kardeşlerin farkından ölçülür. *Bkz. §4.5.3, §4.5.4*

**pb1–pb4**: PB özellikleri: pb1 = ln(fiyat × taban arz), pb2 = taban arz / arz sonrası sermaye × 100, pb3 = bedelli / taban arz × 100, pb4 = ek satış tavanı / taban arz × 100 (yalnız uyarı, özellik değil). *Bkz. §3.6.4*

**PCG64**: numpy'ın rastgele sayı üreteci; kasa çekilişi `PCG64(20260924)`, canlı ve zaman-dışı bootstrap `PCG64(20260921)` tohumuyla çalışır. *Bkz. §6.7.5, §6.12.3*

**PENDING**: Bülteni henüz yerelde olmayan seans satırının durumu; yalnız PENDING satırlar sonradan doldurulabilir. *Bkz. §3.4.6, §3.10.2*

**Pin** (pinlemek): Bir dosyanın beklenen sha256'sını kodda, manifestte ya da testte sabitleyip her okumada yeniden denetlemek; dosya değişirse kod durur ya da test kırmızı olur. *Bkz. §3.1, §6.3.1*

**Plan** (backtest planı): Bir modelin walk-forward kesim gününü ve skorlanabilirlik koşulunu tanımlayan kimlik (`PLAN_V15`, `PLAN_PB`, `PLAN_CEILING`, `PLAN_BREAK_H99` …). *Bkz. §6.5.4*

**Popülasyon standart sapması** (ddof = 0): n'e bölünerek hesaplanan standart sapma; z-skorunda kullanılır. *Bkz. §3.7.1, §4.2.3*

**POST_BREAK**: Kırılma akşamı aşaması; kayıtlar makine sıralıdır ve `registry/post_break/` altına yalnız eklenerek yazılır. *Bkz. §5.5, §6.11.5*

**POST_D1**: D1 akşamı aşaması; kaydın zaman sınırı D1'i izleyen ilk seans günü 09:40'tır (T_open), zaman kanıtı push'tur. Bugün `registry/post_d1/` hiç oluşmadı. *Bkz. §5.2.7, §6.11.5*

**post_d1_hazard_v0** (D1 sonrası model): D1 tavan kapandıysa, D1 bülteninden iki özellikle (`d1_lock`, `d1_turnover`) "seri yarın ve sonra nasıl sürer" eğrisini güncelleyen ofset tehlike modeli; `models/INDEX_POST_D1.json`'dadır. *Bkz. §5.2*

**predict_all**: Ön ucun "Tahmin et"te çağırdığı Rust komutu; gömülü 27 modeli aynı girdiyle INDEX sırasıyla koşar. *Bkz. §7.9.2*

**PRODUCT_BREAK_FLOOR** (ürün karşılaştırıcısı): Kırılma modelinin birincil karşılaştırıcısı: ürünün o akşam zaten verebildiği, tavan yolu hücrelerinden türetilen "yarın taban" olasılığı. Taban üstü kırılmalara yüksek olasılık verdiği için zayıftır; sade görünümde "ürünün eski cevabı". *Bkz. §5.3.7*

**Proje bilgi alanı**: Repo dışında, claude.ai projesinde duran belgeler (HANDOFF, STRATEJI, Ekim yol haritası, proje talimatı). *Bkz. §2.1, §2.4.1*

**Proje sahibi**: Oturumları başlatan, push eden, onay veren ve yeni arzları haber veren kişi; push, tag ve amend yalnız onun işidir. *Bkz. §2.4.1*

**Prospektif / retrospektif**: Prospektif, model arzın sonucundan önce dondurulup push edilmiş demektir; retrospektif, geçmiş veride geriye dönük test. *Bkz. §5.1.4, §6.10.1*

**Pseudo-satır**: Tavan modelinde her gün grubuna z = 0'da, ağırlığı 0,5 olan bir olaylı ve bir olaysız eklenen yapay satır; az olaylı erken fold'larda sabitin sonsuza kaçmasını önler. *Bkz. §4.4.5*

**Puan** (yüzde puanı): Getiri hatası (MAE) için ekranda kullanılan birim: 0,030 hata = 3,0 puan; "%3" göreli yüzde diye yanlış okunmasın diye. *Bkz. §8.7*

**Push**: Yerel commit'lerin uzak depoya (GitHub) gönderilmesi; yalnız proje sahibi yapar (gece botunun veri commit'leri için gevşetme kararı verildi). *Bkz. §2.4.5*

**Push kanıtı** (`registry/push_proofs/<sha>.json`): Bir commit'in o anda uzak depoda bulunduğunu GitHub sunucu saatiyle (`created_at`) gösteren dosya; commit'i ve bütün atalarını kapsar, bir kez yazılır. Bugün 31 dosya vardır. *Bkz. §2.0, §6.3.4*

**PUSH_OK**: bkz. **Denetim hükümleri**. *Bkz. §2.4.6*

**pytest / pytest-xdist**: Python test çatısı ve paralel koşu eklentisi; ara koşular `-n 6 --dist loadgroup` ile paralel, son kabul koşusu sıralı `pytest -q` (952 test). *Bkz. §2.8, §6.15.1*

## Q

**QUICK** (H99 çapası): H99'un "son 100 arz" sayımının başladığı arz (ilk işlem 2026-08-06); üyelik dosyasında `historical_anchor`. *Bkz. §3.3.1*

## R

**r** (rejim terimi): Havuz modelinde r = 1[tahsis rejimi ≠ EQUAL_DIST_20230330]; cezasız katsayısı δ'dır, canlıda ve H99'da 0'dır. *Bkz. §4.7.2*

**R_h** (getiri): R_h = kapanış(D_h) / arz fiyatı − 1, h ∈ {1, 3, 5, 10}; kesin kesirle hesaplanıp 50 anlamlı haneli metin olarak yazılır. *Bkz. §3.5.3*

**ref_date**: f6'nın hesaplandığı referans tarih: eğitimde ve backtest'te T, canlı kayıtta kayıt tarihi (T'den önceyse), geç kayıtta T. *Bkz. §3.6.2*

**Referans fiyat**: Günün üst ve alt limitlerinin hesaplandığı baz fiyat (THM `REFERANS FIYATI`); ertesi günün referansı bugünün kapanışıdır. *Bkz. §3.2.1, §5.1.2*

**REFUSED / RET**: Modelin girdiyle tahmin vermeyip etiketli ret kodu döndürmesi; kayıtta hücre "ret + neden" olur, `n_refused` olarak sayılır, atlama değildir. *Bkz. §6.10.3, §3.6.1*

**Rejim etiketleri** (`regime_tags`): Arzın dönem kurallarını (borsada satış, fiyat adımı dönemi, marj kuralı, tahsis rejimi, pazar …) ya da özel durumları (`FON_KRIZI_2026`) gösteren etiketler; model girdisi değildir. *Bkz. §6.12.5, §5.3.11*

**Rejim şeridi**: Sade görünümde `FON_KRIZI_2026` etiketli arz varsa Monitör'de ve o arzın Analiz sayfasında çizilen uyarı şeridi. *Bkz. §8.11*

**Repo modu**: Ayarlardaki repo kökü doğrulandığında açılan mod: sicil, sonuç ve skor dosyaları repodan okunur, resmi kayıt için Python çağrılabilir. Repo isteyen komutlar aksi hâlde `REPO_MODE_REQUIRED` döner. *Bkz. §7.1, §7.6, §8.5*

**REPRO_OK**: bkz. **Denetim hükümleri**. *Bkz. §2.4.6*

**Ret kodu**: Modelin ya da özellik hesabının neden tahmin vermediğini söyleyen etiket (ör. `INPUT_MISSING`, `F3_MISSING`, `PB_IDENTITY`, `TUFE_MISSING`, `D1_LIMIT_NA`); çıplak istisna dışarı sızmaz. *Bkz. §3.6.1, §7.8.10*

**RETRO** (geçmişe dönük): Model, arzın sonucu repoya girdikten sonra dondurulduysa satırın sınıfı; yalnız bilgi listesinde (`retro_info`) görünür, hiçbir n'e girmez. *Bkz. §2.0, §6.10.2*

**Ridge regresyon**: Sürekli hedefe L2 cezalı doğrusal regresyon (‖y − Xβ‖² + α‖β‖²); V1.5'in getiri kafası. *Bkz. §4.2.2, §4.3.4*

**ROUND_HALF_EVEN / ROUND_HALF_UP**: Decimal yuvarlama kuralları: tam yarıda çift olana (bankacı yuvarlaması) ya da sıfırdan uzağa. f1 çarpımı HALF_EVEN, oranların 10 ondalığa indirilmesi HALF_UP ile yapılır. *Bkz. §7.1, §3.6.1*

**RPS** (Ranked Probability Score): Sıralı bir sonucun bütün dağılımını tek sayıyla ölçen skor: (1/10) Σ_k (S_k − 1[L ≥ k])²; tavan modellerinin birincil metriği, küçük olan iyidir. *Bkz. §6.6.4, §4.2.5*

**Rust**: Bellek güvenliğini çöp toplayıcı olmadan sağlayan derlenen dil; uygulamanın arka ucu ve modellerin uygulamadaki tek tahmin gerçeklemesi Rust'tadır. *Bkz. §7.1*

## S

**S_cond** (koşullu eğri): D1 tavan kapandıktan sonraki eğri: S_cond[k] = S_k / S_1; `p_break_next` = 1 − S_cond[2] "yarın bozulur mu" olasılığıdır. *Bkz. §5.2.5*

**S_k** (sağkalım eğrisi): P(L ≥ k), serinin en az k gün sürme olasılığı; tavan modellerinin birincil çıktısı: S_k = Π_{d≤k} (1 − h_d). *Bkz. §4.4.1*

**S0 / S20**: f6 penceresinin uçları: S0, ref_date'ten kesin önceki son seans; S20, ondan 20 seans önceki seans (21 kapanış, 20 aralık). *Bkz. §3.6.2*

**Sade görünüm** (`SADE`): 3 Ekim 2026'da onaylanan yeni arayüz: koyu Safir paleti, Monitör, Analiz ve seri hesaplayıcı; yalnız kapıdan geçen sayıları öne çıkarır. Varsayılan görünümdür. *Bkz. §8.2, §8.11*

**Saf render fonksiyonu**: Bir görünüm modeli alıp HTML metni döndüren, yan etkisiz fonksiyon (ör. `renderMonitor(vm)`); aynı girdi her zaman aynı HTML'i verdiği için kolay test edilir. *Bkz. §8.1*

**Safir**: Sade görünümün onaylı renk paleti (koyu lacivert zemin; altın yalnız model çıktısı). *Bkz. §8.23*

**Sağdan sansür**: Bir gözlemin sonu görülmediği için yalnız "en az şu kadar" bilinmesi (ör. 10 gün tavan yapan arz ya da walk-forward kesiminde serisi henüz bitmemiş arz). Kişi-dönem yapısı sansürü doğal taşır. *Bkz. §4.4.2, §4.4.11*

**Sağkalım analizi** (survival analysis): "Bir olay ne zaman olur?" sorusunu inceleyen istatistik dalı; tavan serisi modeli onun ayrık zamanlı hâlidir, "hayatta kalan" hâlâ seride olan arzdır. *Bkz. §4.4.1*

**Sahte invoke** (`vi.mock`): vitest'te Tauri'nin `invoke` fonksiyonunu kayıt tutan sahtesiyle değiştirme; ekranın hangi komutu hangi argümanla çağırdığı böyle sınanır (ör. Analiz'de `predict_all`'ın hiç çağrılmaması). *Bkz. §8.25*

**Satış yöntemi** (`sale_method`): Arzın satış yöntemi: borsa dışında talep toplama (`OFF_EXCHANGE_BOOKBUILD`) ya da borsada satış (`ON_EXCHANGE`); v2 tablosunda eski kohort için doludur. *Bkz. §3.8.3*

**Satmama süresi** (lock-up): İhraççının ya da ortakların arzdan sonra belirli bir süre pay satmama taahhüdü; eski kohort için izahname alanı olarak toplandı. *Bkz. §2.3.9*

**SCOPE_START**: Paydanın başlangıç tarihi, 2026-08-07; bundan sonra işlem görmeye başlayan her arz sicile girer. *Bkz. §3.9.3*

**Seans**: Borsanın açık olduğu bir işlem günü; hafta sonu ve tam kapanışlar sayılmaz, yarım gün bir seans sayılır. *Bkz. §3.1, §3.4.1*

**Seans takvimi** (Takvim A, B, B uzatması, C): Her takvim gününü sınıflandıran dosyalar: A H99 sonuçları için (2023-09-22…2026-08-19), B f6 için (2023-01-01'den), B uzatması 2026 sonuna kadar, C eski kohort için (2020–2023). *Bkz. §3.4*

**Senaryo**: Formdaki değerlerle yapılan, sicile ve doğruluk hesabına girmeyen tahmin; kişisel kayıt olarak saklanabilir. *Bkz. §8.14, §8.19*

**serde / serde_json**: Rust'ta veri yapılarını JSON'a çevirip geri okuyan kütüphane; BorsAi `preserve_order` ve `float_roundtrip` özelliklerini açar. *Bkz. §7.1*

**Seri hesaplayıcı**: "Seri j gün sürdüyse yarın ne olur?" sorusunu S_{j+1} / S_j ile cevaplayan bileşen; model yeniden çalıştırılmaz, yanına basit kuralın "geçmiş arzlarda" oranı ve gün grubu notu konur. *Bkz. §8.16, §2.6.11*

**sha256**: Herhangi bir bayt dizisinden 64 onaltılık haneli parmak izi üreten özet fonksiyonu; tek bayt değişse sonuç tamamen değişir. Dosyaları mühürlemek (pinlemek) için kullanılır. *Bkz. §6.3.1, §7.1*

**SHA256SUMS**: Bir klasördeki dosyaların sha256 listesini `sha256sum` biçiminde tutan pin dosyası (altın ledger, denetim ve izahname klasörlerinde). *Bkz. §6.5.5*

**shares_offered** (satışa sunulan pay): Arzda satılan toplam pay adedi; çoğu arzda bedelli + ortak satışıdır, 6 H99 arzında kullanılan ek satışı da içerir. *Bkz. §3.3.2, §3.3.3*

**shifted_by_suspension**: D_1'den o ufka kadar tam gün durdurma yüzünden atlanan seans sayısı. *Bkz. §3.4.6*

**Sıfır modeli**: Özellik kullanmayan uç (`@INF`, `@ZERO`); "katkı yalnız mekanik mi, özellikler bir şey katıyor mu?" sorusunun ölçüsü. *Bkz. §4.6.1, §5.3.6*

**Sınıf** (canlı sınıf): Bir (model, arz) satırının kanıt türü: LIVE, LATE_RECORD, RETRO, MACHINE_SEQUENCED; zaman-dışında OOT_BLIND ve OOT_RETRO. Elle yazılmaz; her skorlamada git DAG'ı, push kanıtları ve tarihlerden hesaplanır. *Bkz. §6.10.2*

**Sıra bekçisi** (`sequence_guard`, `sequence_violations`): Sıra kuralını iki yerde zorlayan kod: indirme kapısı commit'lenmemiş kayıt varken bülten indirmez (`SequenceRuleError`); geçmiş denetimi her test koşusunda bülten ve sonuç commit'lerinin model ve kayıt commit'lerinin torunu olduğunu sınar. *Bkz. §6.11.6, §3.10.2*

**Sıra kuralı**: "Önce tahmin, sonra sonuç" ilkesinin depo düzeyi: 2026-08-19 sonrası bültenler ve 2026-08-06 sonrası arzların sonuçları Faz 1 modelleri dondurulmadan; eski kohort sonuçları bütün kayıtlar push edilmeden; kasa sonuçları doğrulanacak özellik push edilmeden repoya girmez. *Bkz. §6.2*

**Sicil**: Resmi kayıtların, paydanın ve push kanıtlarının bütünü; uygulamada aynı adlı ekran kayıtları ve künyelerini gösterir, sicile yazmaz. *Bkz. §2.7.4, §8.18*

**Sigmoid**: σ(η) = 1/(1 + e^(−η)); her gerçek sayıyı 0–1 arasına taşır. Rust portu taşmasız biçimini kullanır. *Bkz. §4.2.1, §7.8.4*

**SKIPPED** (atlandı): Paydada dondurulmamış arzın durumu; nedeni zorunludur (`NO_RECORD_BEFORE_LISTING`, `PUSH_PROOF_MISSING`, `INPUTS_NOT_AVAILABLE`). Bugün böyle satır yoktur. *Bkz. §3.9.3, §6.10.3*

**Skor dosyaları**: `scores/scores.json` (backtest + canlı), `scores_post_d1.json`, `scores_break.json`, `scores_oot.json`; her terazi ve ölçek ayrı dosyadadır, uygulama yalnız okur. *Bkz. §6.10.1, §2.4.8*

**Skorlanabilir fold**: Eğitim kümesi plan koşulunu sağlayan fold; H99'da V1.5 için 351 (89/88/87/87), tavan planında 87. *Bkz. §6.5.3*

**Snapshot** (`--features snapshot`): Yalnız geliştirmede etkinleşen ekran görüntüsü özelliği; üretim derlemesinde `dev_*` komutları `SNAPSHOT_UNAVAILABLE` döner. *Bkz. §7.3, §7.7, §8.25*

**Sonnet**: Mekanik işleri (sonuç güncellemesi, test altyapısı, pin onarımı, veri alma) yapan Claude Code modeli (Sonnet 5). *Bkz. §2.4.1*

**Sonuç dosyası** (`data/outcomes/<T>.csv`): Canlı arzın D1–D10 seansları için ham kapanış, limitler, sözleşme sayısı, tavan etiketi, getiri ve bülten sha'larını tutan 10 satırlık dosya. *Bkz. §3.10.1*

**Sonuç körlüğü**: Eski kohort girdileri toplanırken listeleme sonrası bilgiye bakılmaması; toplama görevleri haber sitelerini ve "kaç tavan yaptı" sayfalarını yasaklar, istemeden görüleni `exposure_log`'a yazdırır. *Bkz. §2.6.5*

**SourceChanged**: Sha256'sı zaten kayıtlı bir bülten başka baytlarla gelirse indiricinin durduğu hata; "BIST eski dosyayı sessizce değiştirdi mi" sorusunun bekçisidir. *Bkz. §3.2.1, §6.12.6*

**Sözleşme sayısı**: bkz. **İşlem sayısı**. *Bkz. §3.2.1*

**Spearman korelasyonu**: Sıralamalar arasındaki ilişkinin ölçüsü; f3 ile seri uzunluğu arasında 0,55 bulundu. *Bkz. §2.3.3*

**SPEC_APP**: Masaüstü uygulamasının Fable şartnamesi (`docs/app/SPEC_APP.md`, EK 1 dahil; EK 2 ve EK 3 ayrı dosyalarda). *Bkz. §2.3.5*

**SPEC_DEVIATIONS.md** (sapmalar defteri): Şartnamenin belirsiz kaldığı her yerde seçilen yorumun gerekçesiyle yazıldığı defter; A–O bölümlerinde 312 numaralı madde (ör. C7, M24, N20). Davranışı değiştiren bir madde yeni model_id ister. *Bkz. §6.14, §2.4.8*

**SPEC_SCORING**: Sonuç, sınıf, birincil kayıt, metrik ve hüküm dilini tanımlayan skorlama şartnamesi (`docs/specs/SPEC_SCORING.md`). *Bkz. §2.3.3, §6.4*

**SPK** (Sermaye Piyasası Kurulu): Halka arzları onaylayan düzenleyici; haftalık bülteninin "A.1 İlk Halka Arzlar" tablosu planlanan arz yapısının (PB girdileri) resmi kaynağıdır. *Bkz. §3.2.3*

**State** (Tauri durumu): Komutların ortak durumu; `Builder::manage` ile uygulamaya bağlanır, komut `tauri::State` parametresiyle alır. *Bkz. §7.1*

**stdlib** (Python standart kütüphanesi): Python'la gelen modüller; tahmin kodu yalnız bunları kullanır (`__future__`, `math`, `typing`, `decimal`, `dataclasses`) ki Rust'a birebir taşınabilsin. *Bkz. §2.8*

**Süzülmüş skor kopyası**: `scores_oot.json`'un satırları (dolayısıyla arz kodları) atılarak uygulamaya gömülen ≈ 744 KB'lık kopyası; süzgeç hesap yapmaz. *Bkz. §7.3*

**SVG** (Scalable Vector Graphics): Tarayıcının çizdiği, metin olarak yazılan vektör grafik biçimi; uygulamanın bütün grafikleri `svg.ts`'te elle üretilir. *Bkz. §8.8*

## Ş

**Şartname** (spec): Bir modeli kodlanmadan önce bütünüyle tanımlayan Fable belgesi: özellikler, model sınıfı, fold planı, karşılaştırıcılar, birincil hücre ve önceden yazılmış beklenti; commit edildikten sonra değiştirilmez. *Bkz. §2.0, §6.9.3*

**Şema sürümü** (`schema_version`): Dosya biçimini adlandıran alan (ör. `borsai.record/1`, `borsai.inputs/1`, `borsai.scores/1`); okuyucu tanımadığı sürümde durur. *Bkz. §6.11.2, §7.4*

**"Şimdi yapılacaklar"**: Dondurma sonrasında uygulamanın gösterdiği, kullanıcının kendi terminalinde çalıştıracağı git add, commit, push ve push kanıtı komut bloğu; uygulama bunları çalıştırmaz. *Bkz. §7.9.4*

## T

**T**: bkz. **İlk işlem günü**. *Bkz. §4.1.1*

**T − 2 ay kuralı**: Reel büyüklükte TÜFE ayı olarak ilk işlem ayının iki ay öncesinin kullanılması; bir ayın endeksi izleyen ayın 3'ü civarında yayımlandığı için T'de her zaman bilinir. *Bkz. §3.6.3*

**T_open**: POST_D1 kaydının sınırı: D1'i izleyen ilk resmi seans günü saat 09:40:00 (İstanbul); push kanıtı bundan kesin önceyse kayıt LIVE adayıdır. *Bkz. §5.2.7, §6.11.5*

**Taban**: (a) Günün alt limit fiyatı; (b) kapanışın bu fiyata tam eşit olması ("taban kapattı"). *Bkz. §2.0, §5.1.1*

**Taban arz** (`planned_base_offer_shares`): Ek satış hariç planlanan arz: bedelli + ortak satışı (özdeşlik ID-B). *Bkz. §3.6.4*

**Taban oranı**: bkz. **base_rate**. *Bkz. §4.1.5*

**Tabanda kırılma**: Serinin, kırılma günü kapanışın alt limitte olmasıyla bozulması (`b_floor = 1`); ertesi gün taban olasılığı belirgin yüksektir (H99'da 19/35). *Bkz. §5.3.4, §5.3.6*

**Tahmin sonucu** (ekran): "Tahmin et"ten sonra açılan senaryo ekranı: "Kaç gün tavan?" paneli, seri hesaplayıcı, getiri tahmini ve dayanaklar; sicile ve doğruluk hesabına girmez. *Bkz. §8.14*

**Tahsis rejimi** (`alloc_regime`): Talep toplama başlangıcına göre pay dağıtım kuralı dönemi: `PRE_20211111`, `THRESH100_20211111`, `EQUAL_DIST_20230330` (30.03.2023'ten beri bireysel yatırımcıya eşit dağıtım). H99'un 99 arzının hepsi son rejimdedir. *Bkz. §3.6.5*

**Talep katı**: bkz. **f3**. *Bkz. §3.6.1*

**Talep toplama** (bookbuilding): Yatırımcı taleplerinin toplandığı arz dönemi (`bookbuilding_start` / `bookbuilding_end`); talep katı bu dönem bitince sonuç bildirimiyle açıklanır. *Bkz. §3.6.4, §4.5.1*

**Tamlık denetimi** (`COMPLETENESS.csv`): Pencere içinde THB'de ilk kez görünen her işlem kodunu sınıflayarak sicile girmemiş halka arz kalmadığını gösteren denetim; açıklanamayan yeni pay varsa komut durur. *Bkz. §3.10.3*

**TARGET_UNAVAILABLE**: İlk görünüşten itibaren 15 seans içinde D_10 oluşmazsa oluşmayan ufukların durumu; bütün modellerden aynı anda düşer. *Bkz. §3.4.6*

**Tasarıma maruz**: Modelin özellik, grup ya da eşiklerinin aynı veri (H99) görülerek seçilmiş olması; o verideki backtest kanıt değil ön elemedir. *Bkz. §4.1.4, §5.1.4*

**TASK_ID**: Görev dosyasının başındaki kimlik (ör. `BORSAI_FAZ8_FREEZE_20261002`); model ve ayar satırıyla birlikte en başta yazılır. *Bkz. §2.4.2*

**Tatil tablosu**: Borsa İstanbul'un her yıl yayımladığı Pay Piyasası tatil PDF'i; takvimler bundan kurulur, URL ve sha256'ları takvim satırlarında yazılıdır. *Bkz. §3.2.6, §3.4.1*

**Tauri**: Arayüzü işletim sisteminin webview'inde çizip Rust arka uca bağlayan masaüstü uygulama çatısı; BorsAi Tauri 2 kullanır. *Bkz. §7.1, §8.1*

**tauri.conf.json**: Uygulama kimliği (`tr.borsai.app`), pencere boyutu (1440 × 900, en küçük 1024 × 680), CSP ve paketleme hedeflerini tutan Tauri ayar dosyası. *Bkz. §7.5*

**Tavan**: (a) Günün üst limit fiyatı; (b) kapanışın bu fiyata Decimal olarak tam eşit olması ("tavan kapattı"). *Bkz. §2.0, §3.5.1*

**Tavan serisi**: D1'den başlayan kesintisiz tavan kapanışları; uzunluğu L'dir. *Bkz. §3.5.2, §4.4*

**Tavan yolu modeli** (`ceiling_path_v0`, `ceiling_path_v0@INF`, `pb_ceiling_path_v0`): Donmuş bir tavan modelinin S_k'sını deterministik limit yoluyla ve kırılma sonrası ampirik hücrelerle birleştirip D_h getirisinin bütün dağılımını veren model; yeni serbest parametresi yoktur. *Bkz. §4.6*

**Temerrüt pazarı** (buy-in, `TEMERRUT_PAZARI`): Var olan bir payın teslim edilemeyen işlemleri için açılan pazar kodu; tamlık denetiminde yeni arz sayılmaz. *Bkz. §3.10.3, §2.3.4*

**Teorik açılış fiyatı**: Açılış emir toplama sırasında oluşan, seansın açılacağı fiyatın göstergesi; 09:40'tan itibaren görünür. *Bkz. §5.2.7*

**Terazi**: Doğruluğun ölçüldüğü ayrı kanıt ortamı: backtest (retrospektif), canlı (prospektif) ve zaman-dışı eski kohort; "üç terazi, asla toplanmaz" (kural 3). *Bkz. §6.10.1, §2.0*

**Terfi yok**: Bir modelin başka birinin yerine geçmemesi; modeller yan yana durur, yalnız önceden yazılmış kuralla "öne çıkarılır". *Bkz. §2.1, §5.3.10*

**Teslim raporu**: Görevin sonunda oturumun yazdığı rapor (commit hash'leri, sayılar, sapmalar); orkestratör kilit sayıları diskten yeniden hesaplar. *Bkz. §2.4.2, §2.4.4*

**THB** (fiyat bülteni): Borsa İstanbul'un seans sonunda yayımladığı günlük bülten: açılış, en yüksek, en düşük, kapanış, işlem adedi, hacim, sözleşme sayısı ve durdurma alanları; akşam ~18:30'da yayımlanır. *Bkz. §3.2.1*

**THM** (limit bülteni): Borsa İstanbul'un seans öncesi yayımladığı günlük bülten: referans fiyat, üst ve alt limit, fiyat adımı; sabah ~08:00'de yayımlanır. *Bkz. §3.2.1, §5.1.2*

**Tohum** (seed): Rastgele sayı üretecinin başlangıç değeri; aynı tohum aynı sonucu verir (bootstrap 20260921, kasa çekilişi 20260924, altın vektörler 20260922). *Bkz. §6.7.4*

**TOPLAM ISLEM ADEDI**: THB'de günün işlem gören pay adedi; bu kitapta "hacim" diye anılır, `d1_turnover` ve `b_turnover`'ın payıdır. *Bkz. §5.1.2*

**TÜFE**: TÜİK'in Tüketici Fiyat Endeksi genel endeksi (2025=100); reel büyüklüğün deflatörü. Dosya bugün 2026-08'de biter; eksik ay `TUFE_MISSING`, yayımlanmamış ay `TUFE_NOT_PIT`, değişmiş dosya `TUFE_FILE_MISMATCH` verir. *Bkz. §3.2.4, §3.6.3*

**TÜİK** (Türkiye İstatistik Kurumu): TÜFE'nin resmi kaynağı; sunucusu komut satırı istemcilerine 403 döndürdüğü için tablolar tarayıcıyla indirilir. *Bkz. §3.2.4*

**Type-7 kantil**: R'ın ve numpy'ın varsayılan doğrusal kantil tanımı: h = (n − 1)p + 1 konumunda iki komşu değer arasında doğrusal ara değerleme; projede kesin kesirle hesaplanır. *Bkz. §4.2.3, §3.7.1*

**TypeScript**: JavaScript'e tür denetimi ekleyen dil; ön uç bununla yazılır, derleyici (`tsc`) tür hatalarını yakalar. *Bkz. §8.1*

## U

**U-kuralları** (U1–U80): Uygulama şartnamesinin ve eklerinin numaralı kabul testleri (ör. U19 "geçiyor" sözcüğü, U24 fail-closed, U25 hesap yok, U34 ağ yok, U52 beyandan sayı yok); kod yazılmadan önce şartnameye yazılır. *Bkz. §8.10*

**Uçtan uca test** (e2e): Akışın tamamını (dondurma, D1 sonrası kayıt, kişisel kayıt izolasyonu) `git clone --local` ile açılan geçici bir klonda koşturan bash betikleri; asıl repoya hiçbir şey yazılmaz. *Bkz. §7.12, §8.25*

**Ufuk** (horizon): Getirinin ölçüldüğü seans: D1, D3, D5, D10; ufuklar ve çıktılar asla birleştirilmez. *Bkz. §4.1.2, §6.6*

**ULID**: 48 bit milisaniye ve 80 bit rastgele değerden oluşan, zamana göre sıralanabilen 26 karakterlik kimlik; kişisel kayıt dosya adlarında kullanılır. *Bkz. §7.7*

**uv**: Python sürümlerini ve ortamları yöneten araç; projenin yorumlayıcısı (CPython 3.12.14) uv'nin kurduğu sürümdür, sanal ortam ise stdlib `venv` ile kuruldu. *Bkz. §2.8*

**UYGUN / DÜZELTMEYLE UYGUN**: bkz. **Denetim hükümleri**. *Bkz. §2.3.5*

## Ü

**Üç terazi** (kural 3): Backtest, canlı ve zaman-dışı ölçümlerin ayrı tutulup asla toplanmaması kuralı; bkz. **Terazi**. *Bkz. §6.2, §6.10.1*

**Üretimdeki model**: Sade görünümde kendi sorusu için gösterilen dört model: `ceiling_hazard_v0`, `v1_5_h99`, `post_d1_hazard_v0`, `break_floor_v0`. *Bkz. §8.11, §8.12*

**Üst limit** (tavan fiyatı): THM `UST LIMIT FIYATI`; referans fiyatın %10 üstünün fiyat adımına aşağı yuvarlanmış hâli. *Bkz. §3.5.1, §4.6.2*

## V

**V1.5** (`v1_5_h99`): Eski repoda ön kayıtla dondurulan ana model: her ufuk için Ridge (getiri) ve L2-lojistik (p_up) iki kafa, özellikler f1–f5, eğitim H99. Birincil hücresi (D5 MAE) backtest'te geçer. *Bkz. §4.3*

**v1_5_full20**: Eski repoda 20 arzla eğitilmiş ayrı model; TKNKA'nın eski kaydında kullanıldı, `v1_5_h99` sütununa yazılmaz. *Bkz. §2.2.2, §6.10.3*

**v1_5_market20_v0** (market20 modeli): V1.5'e f6 piyasa özelliğini ekleyen model; V1.5'ten ayırt edilemiyor. *Bkz. §4.3.8*

**V1.6** (`v1_6_h99`): V1.5'in yalnız ızgarası genişletilmiş tek değişkenli değişikliği; V1.5'ten ayırt edilemiyor. *Bkz. §4.3.7*

**Varyant sayacı** (`n_variants_same_data`): Model kartında, aynı veri sürümüyle denenmiş farklı (model_id, şartname) çiftlerinin ve keşif satırlarının sayısı; çoklu karşılaştırmayı görünür kılar (`v1_5_h99` kartında 23). *Bkz. §6.9.5*

**VAULT_OPEN.json**: Kasanın açıldığını gösteren işaret dosyası; kasa kodu içermez ve kasa bekçilerinin kipini belirler. *Bkz. §6.12.6*

**VBTS** (Volatilite Bazlı Tedbir Sistemi): Borsa İstanbul'un aşırı oynaklıkta bir paya kademeli tedbir (ör. kredili işlem yasağı) uygulaması; tavan serisindeki arzlara ≈ 6.–9. seansta geldiği gözlendi (üç vaka). Model girdisi değildir. *Bkz. §2.6.9, §5.3.4*

**verdict**: Skor dosyasındaki hüküm alanı; uygulama ekranda bunu aynen basar. *Bkz. §8.9, §8.11*

**Veri sürümü** (`data_version.json`): Eğitim tablosunun ve kaynak dosyaların sha256'larını tutan sürüm dosyası; kendi hash'i şartnameye girer, değişirse yeni model_id gerekir. *Bkz. §3.8.1, §3.1*

**Vite**: Ön uç kaynaklarını tek pakete toplayan ve geliştirmede sayfayı canlı yenileyen araç. *Bkz. §8.1*

**vitest**: Vite ile çalışan JavaScript test çatısı; ön uç testleri 24 dosyada 376 testtir. *Bkz. §8.25*

## W

**Walk-forward backtest** (ileri yürüyen geriye dönük test): Her arzı yalnız o arzın kesim gününden önce sonucu kesinleşmiş arzlarla sıfırdan eğitilen modelle tahmin etmek; "o gün elimizde ne vardıysa onunla tahmin etseydik" sorusunun taklidi. *Bkz. §6.5, §4.2.4*

**Webview**: Uygulamaya gömülebilen tarayıcı motoru (macOS'ta WKWebView, Windows'ta WebView2); Tauri arayüzü bununla çizer, Chromium paketlemez. *Bkz. §7.1*

**Windows uyumu**: Uygulamanın bugünkü hedefi yalnız macOS arm64'tür; Windows için varsayılan Python yolu gibi Mac'e özel noktalar düzeltilmelidir. *Bkz. §7.5, §2.7.7*

**Workspace** (Cargo): Birden çok crate'i tek `Cargo.lock` altında toplayan yapı. *Bkz. §7.1*

## X

**xb kipi**: Python'da dosyayı "yalnız yoksa oluştur" kipinde açmak; var olan bülten, kayıt ya da kanıt dosyası yeniden yazılamaz. *Bkz. §3.2.1, §6.3.4*

**XHARZ**: Borsa İstanbul'un halka arz endeksi; sonucun doğrudan türevi olduğu için kullanılmaz. *Bkz. §3.2.5*

**XU100** (BIST 100 endeksi): Borsa İstanbul'un 100 paylık ana endeksi; f6'nın kaynağı. Pinli iki dosya vardır (2026-08-19'a ve 2026-09-21'e kadar); yeni dosya yalnız ekleme yapabilir (`check_revision`). *Bkz. §3.2.5*

## Y

**Y_h** (yön): Y_h = 1[kapanış(D_h) > arz fiyatı]; eşitlik 0 sayılır. *Bkz. §3.5.3*

**Yakın dönem hücresi / etiketi**: İlk işlemi 2024-01-01 ve sonrası olan H99 fold'larında yeni aday − eski model farkı; etiketleri "bozuyor", "tolerans içinde", "belirsiz". Eski veriyi eğitime katmanın bugünü bozup bozmadığını ölçer. *Bkz. §4.7.4, §6.8*

**Yakınsamama**: Çözücünün en küçük noktaya ulaşamaması. V1.6 ve sonrasında yalnız o aday ızgaradan çıkar (`CANDIDATE_NOT_CONVERGED`); tavan modelinde 100 yinelemede durmazsa `MODEL_NOT_FIT_DID_NOT_CONVERGE`. *Bkz. §4.3.7, §4.4.5*

**Yapısal sıfır** (`D10_STRUCTURAL_ZERO`): Kesin alt limit zinciriyle min10 > P ise "D10 kapanışı ≤ arz" olasılığının 0 olması; model değil koddur, skorlanmaz, yalnız rozet olarak gösterilir. *Bkz. §5.4.3*

**Yarım gün**: Tatil tablosunda "yarım gün seans" yazan gün (genelde bayram arifesi); bir seans sayılır, sonuç satırında `half_day = 1`. *Bkz. §3.4.1, §3.4.6*

**Yasak sözcükler**: Arayüzde kullanılmayan ifadeler: "kesin", "garanti", "kazandırır", "al/sat", "hedef fiyat", "sinyal" ve tek başına "doğruluk %<sayı>"; test `tr.ts`'i tarar. *Bkz. §8.9*

**Yastık aritmetiği**: Tavan serisinin fiyatı arz fiyatının üstüne taşıdığı payın (yastık) kaç tabanla silinebileceği hesabı; kalan gün yetmiyorsa D10'da arz altı mekanik olarak imkânsızdır. *Bkz. §5.4, §2.6.9*

**Yazan el ≠ denetleyen el**: Şartnameyi Fable'ın yazması, kodu Opus'un yazması ve sonucu yine Fable'ın sıfırdan yeniden üretmesi ilkesi. *Bkz. §2.1, §2.4.1*

**Yeni arz girişi** (ekran): Yeni bir halka arzın belgelerden okunan değerlerinin girildiği form; alanlar SPK, KAP ve BIST belgelerine göre üç gruptadır, `check_form` her değişiklikte denetler. *Bkz. §8.13*

**Yeniden tavan oranı** (r_a, r_b): Seri bozulduktan sonra bir günün yeniden tavan kapanma oranı (k = 2..4 için r_a, k = 5..10 için r_b); P_close_ceiling'de kullanılır. *Bkz. §4.4.7*

**Yetersiz örnek**: Canlıda 10 ≤ n < 30 iken her hücreye konan etiket; kazanan vurgusu yoktur. *Bkz. §6.8*

**Yol bekçileri**: Dışarıdan gelen yolları ve kodları denetleyen Rust fonksiyonları (`valid_ticker`, `safe_rel`, `resolve_path`, `write_export`); kişisel kaydın repo altına yazılmasını sembolik bağlar dahil engeller. *Bkz. §7.5*

**Yön isabeti**: Tahminin işaretinin Y_h ile tutup tutmadığı; tek başına gösterilmez, çünkü arzların çoğu yukarı gittiği için "hep yukarı" demek bile yüksek isabet verir. *Bkz. §6.6.1*

## Z

**z-skor**: z = (x − μ) / σ; μ ve σ yalnız eğitim kümesinden (σ popülasyon standart sapması). Özellikleri karşılaştırılabilir ölçeğe getirir ve L2 cezasının hepsine eşit davranmasını sağlar. *Bkz. §4.2.3, §3.7.1*

**Zaman-dışı test** (OOT, eski kohort terazisi): Donmuş modellerin H99'dan önceki 2020–2023 arzlarında, tahminler sonuç repoya girmeden push edilerek sınanması; üçüncü terazidir ve hükmü "(zaman-dışı terazide)" ekiyle yazılır. *Bkz. §6.12*

**Zaman kanıtı**: Bir şeyin belli bir anda var olduğunun kanıtı; BorsAi'de yalnız push kanıtıdır (GitHub sunucu saati), yerel saat ve dosyanın içindeki tarih kanıt sayılmaz. *Bkz. §2.4.5, §6.3.4*

**ZERO** (C = ZERO): Lojistik ızgarada "yalnız sabit terim" adayı; olasılık eğitim oranıdır, sklearn'e sıfır sütunlu matris verilmez. *Bkz. §4.3.7*

**Zip** (bülten arşivi): THB/THM'nin indirildiği sıkıştırılmış dosya; içinde tek CSV vardır, baytlar değiştirilmeden saklanıp sha256 ile pinlenir. *Bkz. §3.2.1*

# Ekran görüntüleri (SPEC_APP aşama 2, 3, P ve 4)

`bash app/scripts/screens.sh` ile üretildi: `npm run tauri dev -- --features snapshot` ve
`VITE_BORSAI_DEMO=1`; `src/dev/demo.ts` gerçek düğmelere tıklar, WKWebView görüntüsü alınır
(1200 × 800 pencere). Uygulama verisi geçici dizindedir; repo'nun `data/`, `registry/`, `scores/`
dizinlerine yazılmaz. Repo modu açık; f6 repo modunda Python `borsai.market20` ile,
ref_date = çekim günü.

**Mod bandı ekran başına değişir** (SPEC_APP §3, aşama 5): Girdi / Sonuç / Kişisel kayıtlar turuncu
`SENARYO · Bu tahmin sicile girmez`; Sicil ekranının dört hâli mavi `RESMİ KAYIT` (liste, arz
sayfası — kayıt dosya adı + zaman kanıtı göstergesi —, kayıt yok, dondur sihirbazı); Doğruluk,
Ayarlar ve Hakkında gri nötr bant (Ayarlar ve Hakkında'da mod sözcüğü yoktur). Yani `02`–`12`
turuncu, `14`–`24` mavi, `01`, `13` ve `25`–`30` gri bantlıdır.

**25–25c** asıl repo'nun `scores/scores.json`'unu okur; **26–30** ekran görüntüsü koşusuna özgü
sentetik skor dosyalarıdır (`app/tests/fixtures/scores/`, hepsi `synthetic: true`; panel başlığında
kaynak `FIXTURE` ve kurgusal uyarısı görünür). Geçiş yalnız `--features snapshot` ile derlenen
`dev_scores_fixture` komutuyla olur; üretim derlemesinde bu yol yoktur.

**14–16b** asıl repo'ya karşı salt okumadır (sicil ekranı, NETGL arz sayfası). **17–24 (dondur
sihirbazı ve klondaki yeni kayıt) YALNIZ GEÇİCİ BİR KLONDA** koşar: betik `git clone --local` ile bir klon açar, kurgusal
`SNTC3` kaynak belgelerini oraya kopyalar ve demo repo kökünü o klona çevirir (Python yolu asıl
repo'nun `.venv`'i, cwd klon). Asıl repoda sihirbaz çalıştırılmaz; betik sonunda asıl repo
`registry/` sha listesini karşılaştırır. Kayıttaki `SNTC3` değerleri NETGL'in girdileriyle
doldurulmuş kurgusal bir arzdır; T geçmişte olduğu için adım 5 kırmızı uyarı verir.

| Dosya | Ne gösterir |
|---|---|
| `01_ayarlar_repo_modu.png` | Ayarlar: repo kökü doğrulaması (INDEX sha, git HEAD, `import borsai`, uygulama verisi repo dışında); **nötr bant** (mod sözcüğü yok) |
| `02_girdi_veyas.png` | Girdi formu: VEYAS sicil girdi belgesinden salt okuma kopyası, aşama, alan tablosu |
| `03_girdi_veyas_f3_f6.png` | f3 tanımı (§3a.1) ve f6 repo modu sonucu (S0/S20, XU100 sha) |
| `04_sonuc_veyas_grup_a.png` | **U7**: VEYAS (f3 boş) → 5 RET bloğu: dört model `F3_MISSING` (v1_5_h99, v1_6_h99, ceiling_hazard_v0, ceiling_path_v0), `v1_5_market20_v0` `MARKET20_XU100_CLOSE_MISSING` (repo modu f6: çekim günü penceresinde XU100 kapanışı eksik; market20 sarmalayıcısı f3'ten önce reddeder, Python'la aynı; kayıttaki f6 ile beşinin de `F3_MISSING` olduğu `stage2.rs::u7_veyas_four_refusals`'ta sınanır) ve 14 dolu sütun; Grup A'da tavan yolu sütunları (medyan + rozet, %10–%90, p_up, S_h, fiyat) |
| `04b_sonuc_veyas_grup_c.png` | **U48**: Grup C "tavan yolu: getiri dağılımı (h = 1..10)"; fiyat kuralı (medyan limit atomuysa `C_h` + "limit yolu", değilse "≈"), yelpaze grafiği (q10–q90 bandı, q50, kesikli rho_h), limit yolu satırı |
| `05_sonuc_veyas_grup_b.png` | Grup B: S_k tablosu, beklenen/medyan L, "her zaman tavan" sabit sütunu, ceiling_hazard_v0 RET |
| `06_sonuc_veyas_tavan_grafikleri.png` | S_k eğrisi, P(L = k) çubukları, P(Dk'de tavan kapanışı) |
| `07_sonuc_veyas_kosullu.png` | §3g şerit (data/outcomes/VEYAS.csv): "seri D1'de bozuldu; gerçekleşen L = 0", koşullu eğri yok |
| `08_senaryo_netgl_sonuc.png` | NETGL senaryosu, kişisel kayıt olarak saklandı |
| `08b_senaryo_netgl_grup_c.png` | NETGL Grup C: üç tavan yolu modeli, `C_1..C_10` metinleri ve h = 4'ten itibaren medyanın limit atomundan ayrılması |
| `09_senaryo_netgl_kosullu_j3.png` | NETGL şeridi (3 tavan + bekliyor) → gözlenen j = 3, P(L ≥ k \| L ≥ 3) eğrisi ve tablosu |
| `09b_senaryo_netgl_getiri_kosullu_j3.png` | **U49**: "Getiri (koşullu)" sekmesi, durum 1 (j = 3); D1–D3 "gerçekleşti" (kapanışlar `data/outcomes/NETGL.csv`), D4–D10 koşullu medyan/[q10, q90]/p_up/S_h/atom, `P(L = t \| L ≥ 3)` çubukları |
| `10_senaryo_netgl_varsayimsal_j5.png` | j = 5 seçildi → "varsayımsal j" etiketi |
| `11_kisisel_kayitlar.png` | Kişisel kayıtlar listesi (sicile ve doğruluk hesabına girmez) |
| `11b_kisisel_kayitlar_tumunu_disa_aktar.png` | **§3f**: "Tümünü dışa aktar" sonucu (tek JSON dizisi, kayıt sayısı); hedef geçici uygulama verisindedir, repo altına aktarma Rust'ta reddedilir (U27) |
| `12_senaryo_yuklendi.png` | Kaydedilen senaryo sonuç ekranına geri yüklendi (çıktı dosyadaki gibi) |
| `13_hakkinda.png` | Hakkında: derleme HEAD, gömülü INDEX sha, 19 model, bütünlük |
| `14_sicil_listesi.png` | **Sicil ekranı**: arzlar, kayıt/etkin sayısı, `git status -- registry`, push kanıtı dosya sayısı, payda satırı |
| `15_arz_sayfasi_netgl.png` | NETGL arz sayfası: kayıt sekmesi, kayıt künyesi, git izleme + **push kanıtı göstergesi** (sınıf hesaplanmaz), "kaynak: kayıt …, params sha …" |
| `16_arz_sayfasi_netgl_kosullu.png` | **U38**: koşullu görünüm yalnız dondurulmuş kayıttaki `models[].output.S`'ten; gözlenen j = 3 (`data/outcomes/NETGL.csv`) |
| `16b_arz_sayfasi_netgl_getiri_kosullu.png` | Resmi kayıt 16 modelli (Faz 4 öncesi): hem kayıt bloğunda hem "Getiri (koşullu)" sekmesinde "bu kayıt Faz 4 modellerini içermiyor (kayıt INDEX'ten eski)" |
| `25_dogruluk_gercek_dosya.png` | **Doğruluk paneli** (§3d), gerçek `scores/scores.json`: kaynak/üretim/as-of/sha başlığı, rejim uyarısı, `v1_5_h99` model kartı ve backtest hücre tablosu (birincil hücre kalın çerçeve + "birincil (önceden ilan)", ötekiler "keşif"; hüküm metinleri `verdict` alanından) |
| `25b_dogruluk_gercek_tavan_yolu.png` | **U51**: `ceiling_path_v0` (kind = ceiling_path) bloğu getiri/p_up modeli gibi okunuyor; birincil hücre D5 MAE vs `base_train_median`, −11.6 puan [−16.1, −7.4], n = 85 |
| `25c_dogruluk_retro_atlanan.png` | RETRO (model başına gruplu, hiçbir teraziye girmez), **FROZEN olmayan payda satırları** (SKIPPED ve OUT_OF_SCOPE ayrı alt tablolarda, altında "atlanan yalnız SKIPPED sayar" notu) ve ayrı modeller (INDEX dışı, metrik yok) |
| `26_dogruluk_n7_satir_tablosu.png` | **U16**: n = 7 → yalnız satır tablosu (arz, D1, sınıf, kayıt, zaman kanıtı, tahmin, gerçekleşen, kuralların tahmini, durum); metrik, hüküm ve renk yok. Altında geçersiz kullanım ve iptal edilen kayıt bölümleri |
| `27_dogruluk_n12_yetersiz_ornek.png` | **U17**: 10 ≤ n < 30 → hücreler var, her satırda "yetersiz örnek", `ci95` null satırında "aralık için yetersiz", kazanan rengi yok; altta legacy self-reported bölümü (kendi n'i) |
| `28_dogruluk_n35_hukum.png` | **U18**: n ≥ 30 → "geçiyor" / "geçemiyor" / "ayırt edilemiyor" doğru renkte (metinler `verdict` alanından); altında betimleyici (aralıksız, hükümsüz) alt tablosu |
| `29_dogruluk_kosullu_sentetik.png` | **U51**: sentetik `models[].conditional` (EK 2 §5): j = 1 (n = 4) satır tablosu, j = 3 (n = 12) "yetersiz örnek"; j'ler ve koşulsuz tablo toplanmaz |
| `30_dogruluk_butunluk_hatasi.png` | **U24**: §2.3 fail-closed — `n_scored = 7` iken canlı hücre üretilmiş kopyada panel yerine kural ihlali ve ham ayrıntı |
| `17_dondur_adim1_on_kosullar.png` | Sihirbaz adım 1: repo modu, git HEAD, INDEX sha eşitliği, `borsai.__file__`, `git status -- registry` (geçici klon) |
| `18_dondur_adim2_kaynak_belgeler.png` | Adım 2: kaynak belgeler ve MANIFEST (kurgusal SNTC3 belgeleri) |
| `19_dondur_adim3_alanlar.png` | Adım 3: 20 alan, dolu alanlarda kaynak + alıntı, boş alanlarda `missing_reason` |
| `20_dondur_adim3_belge_yazildi.png` | Adım 3: `registry/inputs/SNTC3.json` yazıldı (pretty_json_bytes biçimi, sha) |
| `21_dondur_adim4_5_denetim_ve_uyari.png` | Adım 4 yetkili denetim (Python `inputs_pit_problems` boş) ve adım 5 **kırmızı** T uyarısı |
| `22_dondur_adim6_kayit_ve_parite.png` | **U30/U32/U50**: kayıt 19 model içerir; `parite: 19/19 desteklenen model, \|Δ\|max = 0`; altında "Şimdi yapılacaklar" bloğu (`git add`/`commit -- <aynı yollar>`/`push`, `borsai.push_proof $(git rev-parse HEAD)`) — uygulama bunları çalıştırmaz |
| `23_arz_sayfasi_klon_19_model.png` | **U50**: geçici klonda dondurulan YENİ kayıt (19 model) arz sayfasında; kayıttaki tavan yolu çıktıları Grup A/C ile aynı render (U38: değerler yalnız kayıttan) |
| `24_arz_sayfasi_klon_getiri_kosullu.png` | Aynı kayıtta "Getiri (koşullu)": SNTC3 için gözlenen seri dosyası yok → j = 0 (koşulsuz), kaynak satırı "kaynak: kayıt …, params sha …" |

**Metni sonradan değişen ekranlar (görüntüler yeniden üretilmedi; FAZ3_APP_AUDIT_FIX):** `23` ve `24`'ün
bandında (arz sayfasındaki push kanıtı göstergesiyle aynı dize) "push kanıtı bulunamadı" yazıyor; bugünkü metin
"bu kaydı ekleyen commit için kanıt dosyası yok; torun commit kanıtı skorlamada değerlendirilir" (B12;
bant ve sayfa aynı dizeyi taşır, A5-3). `22`'deki "Dondur" düğmesi artık adım 1'in ön koşulları da
geçmeden açılmaz (B3); görüntüde ön koşullar geçmiş olduğundan görünüm aynıdır.

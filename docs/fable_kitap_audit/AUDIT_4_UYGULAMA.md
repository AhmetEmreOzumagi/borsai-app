KITAP_AUDIT_4: [P] 1 kritik, 10 orta, 15 düşük; [K] 8; [B] 6

## Özet (proje sahibi için)

1. **Sayılar doğru, bazı etiketler yanlış.** Üreticiden bağımsız 372 yeni girdi × 27 model + 148 D1 sonrası vaka = 10 192 satırda Python ile Rust arasında 0 uyuşmazlık, 10 166 satır bit-eşit (en büyük fark 8.9e-15, yalnız bilinen ln yolunda). Uygulamanın gösterdiği sayı Python'un yazdığı sayıdır.
2. **Sunum öncesi düzeltilmesi gereken ilk şey:** Tahmin sonucu ve Analiz'deki getiri tablosunda öne çıkmayan her ufuk "≈ fark net değil" yazıyor; skor dosyası D1 getirisi için **"geçemiyor"** diyor (model basit kuraldan kötü, aralık sıfırı dışlıyor). Ekran, dosyanın tersini ima ediyor.
3. **Monitör veri şeridi "Üretimdeki model 4 — kendi sorusunda öne çıkan"**: 4 sabit liste uzunluğu; kapıdan geçen üretim modeli 3 (`post_d1_hazard_v0` geçmiyor, canlı n = 0).
4. **D1 sonrası modelin "Geçmiş test" sütunu canlı bloktan besleniyor** (dosyada geçmiş test bloğu yok). Bugün "—" görünüyor; canlı hücreler oluşunca canlı hüküm "Geçmiş test" sütununa ve kapı kararına girer. Üç terazi kuralının gizli ihlali.
5. Ayrıntılı sonuç ekranında aynı p_up değeri iki farklı yuvarlamayla (`pct0` ve Rust `pct_up`) yarım değerlerde farklı yüzde verebiliyor (0.075 → %8 ve %7).
6. Giriş ekranındaki "Özdeşlikler" notu SUM satırı için yanlış: SUM tutmazsa hiçbir model durmaz (uyarı), ama satır kırmızı "× tutmuyor" ve not "modelleri durdurur" diyor.
7. Açılış bütünlüğü, gömme zinciri, dondurma akışı ve girdi belgesi bayt-eşitliği kanıtlandı (klonda bir bayt mutasyonu → `INTEGRITY_FAILED`; e2e dondurma yeşil, parite 27/27 |Δ| = 0).
8. Ön uç gerçekten hesap yapmıyor: `*`, `/`, `%` yalnız `format.ts` ve `svg.ts`'te; sade kodda hiç yok; grafik piksel eşlemesi elle yeniden çizildi (≤ 0.05 px fark).
9. Seri hesaplayıcı anlatımı doğru: "yarın da tavan" = S_{j+1}/S_j = 1 − h_{j+1} (5 650 hücrede en büyük fark 1.1e-16); j ≥ 3 sabitliği g3'ten; gün grubu notu dosyadan.
10. 80 U-kuralının hepsi için bir test var; 55 komut kaydı ve 169/164/376 test sayıları kılavuzdaki gibi.

## Bulgular

Önce ekranda yanıltıcı olanlar. Kanıt: dosya:satır; ajan raporları `ekler/4/ajan_*.md` (A: ön uç aritmetiği/grafik/yuvarlama, B: U-kuralları/şartname, D: altı sade ekranın zinciri).

| no | tür | önem | kılavuzdaki yer | kısa tanım | kanıt | öneri |
|---|---|---|---|---|---|---|
| 1 | [P] | KRİTİK | §8.14 getiri paneli; §8.15 getiri tablosu | Öne çıkmayan ufuklarda "Geçmiş test" sütunu sabit "≈ fark net değil". `scores/scores.json` v1_5_h99 return D1 × base_train_median: verdict "geçemiyor", diff +0.0046, ci95 [+0.0015, +0.0079], n = 89 (base_always_ceiling'e karşı da "geçemiyor"). Ekran dosyadaki hükmün tersini ima eder. | `app/src/sade/render/sonuc.ts:120`, `analiz.ts:214` (`approxLabel()`), `app/src/i18n/tr.ts:1470` [ÖLÇTÜM] | Kodda/metinde: öne çıkmayan satırda "birincil değil" yazılsın ya da dosyadaki keşif hükmü "keşif:" etiketiyle aynen gösterilsin. Model değişmez. |
| 2 | [P] | ORTA | §8.12 veri şeridi | "Üretimdeki model: 4 — kendi sorusunda öne çıkan": 4 = `PRODUCTION_MODELS.len()` sabiti; kapı fikstüründe `post_d1_hazard_v0` featured = false (3 öne çıkan). Model performansı ekranında aynı sayının alt etiketi "kendi sorusunda ölçülen" (doğru). | `commands/sade.rs:1413`, `sade/render/monitor.ts:42`, `tr.ts:1535-1536`, `app/tests/fixtures/ui/sade_gate.json` [ÖLÇTÜM] | Alt etiket "kendi sorusunda ölçülen" ya da sayı `scales.filter(featured)`. |
| 3 | [P] | ORTA | §8.17 "Üç ayrı sınav", §8.12 "Üretimdeki modeller", §8.11 kapı | `post_d1_hazard_v0` için kapı ve "Geçmiş test" sütunu `scores_post_d1.json /conditional_j1/cells` okur; bu blok `scale = live_post_d1` (n_scored 0, n_retro 7, cells []), dosyada `backtest` bloğu yok. Bugün "—"; canlı hücreler oluşunca canlı hüküm "Geçmiş test" sütununa ve `featured` kararına gider (kural 3). | `commands/sade.rs:1054-1056, 1385-1386`; `scores/scores_post_d1.json` yapısı [ÖLÇTÜM] | Backtest kaynağı yoksa `NO_TEST` + "test dosyada yok"; canlı hücreler yalnız canlı sütuna. Yeni model_id gerekmez. |
| 4 | [P] | ORTA | §8.14, §8.22 Grup A ve Düşüş kartı | Aynı ayrıntılı sonuç ekranında p_up iki yuvarlamayla gösterilir: `pct0` (JS `toFixed`, ×100 çarpımının ikili değerine göre) ve Rust `pct_up = 100 − round(100·(1 − p_up))`. 1e-5 ızgarada 78 yarım-değer uyuşmazlığı: p_up 0.005 → %1 / %0; 0.075 → %8 / %7; 0.665 → %67 / %66. Sade görünüm etkilenmez. | `render/format.ts` pct0; `commands/fall.rs:41-43`; `render/summary.ts:278-279`; ajan A F1 [ÖLÇTÜM, node ile tekrar doğrulandı] | Tek yuvarlama kaynağı (Rust tamsayı yüzde) ya da şartname §4'e yuvarlama kuralı; SPEC_APP §4'te kural yok (bulgu 24). |
| 5 | [P] | ORTA | §8.17 tablo "Hüküm" | Kırılma satırlarında hüküm alanı yokken `promotionCell` yeşil "✓" basar ("geçiyor" işaretiyle aynı); `scale = backtest_break` (n = 69, yakın dönem) ve `file_label` sade görünümde yazılmaz; n = 87 kohortuyla aynı tabloda. | `sade/render/perf.ts:57-59`, `common.ts:109-113`; ajan D F2 [ÖLÇTÜM] | Nötr işaret + "yakın dönem kohortu n = 69" + `file_label`. |
| 6 | [P] | ORTA | §8.17 "0 = fark yok" sütunu | RPS, MAE (puan) ve Brier farkları tek yatay eksende; kırılma −0.19 en uzun görünür, karşılaştırılamaz birimler. | `sade/render/perf.ts:21-36, 65`; ajan D F3 [ÖLÇTÜM] | Metrik başına eksen ya da çubuksuz sayı+aralık. |
| 7 | [P] | ORTA | §8.13 "Denetim paneli" | `identityNote` "tutmayan özdeşlik modelleri durdurur; satır kırmızı" ve SUM satırı "× tutmuyor" kırmızı; `SHARES_SUM_MISMATCH` form.rs'de `warn`, hiçbir model durmaz. | `tr.ts:1639`, `sade/render/giris.ts:140-141`, `commands/form.rs:225` [ÖLÇTÜM] | Not "ID-A/B/C PB modellerini durdurur; SUM uyarıdır"; SUM sarı. |
| 8 | [P] | ORTA | §8.17 canlı sicil satırları / ilerleme | `rowsNote` sabit cümle "D1 sonrası ve kırılma akşamı modelleri bu arzlardan sonra donduruldu; onlarda sayılan arz yok" (yeni arzda yanlışlanır); "Her aşama 30 sayılan arzda" + "1 / 30": 30 = backtest `MIN_N_VERDICT` sabiti, canlı blokta eşik alanı yok. | `tr.ts:1963`, `perf.ts:107-116`; ajan D F5 [ÖLÇTÜM] | Cümle dosyadaki sayıdan kurulsun; eşik kaynağı belirtilsin. |
| 9 | [P] | ORTA | §7.13 son satır | `test.sh --include-ignored` ve atlama listesini koruyan statik test yok (app altında yalnız betik ve iki test yorumu). Kılavuz "belirsiz" der; cevap "yok". Kapanış denetimi C2 önerisi uygulanmamış. | `grep -rl include-ignored app` → test.sh, stage2/stage3/records_parity yorumları; ajan B B6 [ÖLÇTÜM] | Atlama listesini sınayan küçük bir test. |
| 10 | [P] | ORTA | §7.11 | `app/parity/README.md` "23 model", "eski 19 altın"; `golden/README.md` "(19)", "8 Python dosyası": MANIFEST 27 model, 11 kaynak. Belgeler iki aşama geride. | `app/parity/README.md:11,27`, `golden/README.md:14,17` [ÖLÇTÜM] | Belge düzeltmesi. |
| 11 | [P] | DÜŞÜK | §7.3 | `BUILD_INFO.git_status_models_scores` derleme anını dondurur; klonda mutasyon geri alındıktan sonra ` M models/ceiling_hazard_v0.json` kaldı (sonraki cargo koşusu düzeltti). | üretilmiş `embedded.rs` BUILD_INFO satırı [ÖLÇTÜM] | "Hakkında"da "derleme anı" vurgusu. |
| 12 | [P] | DÜŞÜK | §8.8 | Eksen etiketleri yuvarlanır, çizgiler yuvarlanmaz (`toFixed(0)`): koridor fikstüründe çizgiler 14.6/20.7/26.8/32.9/39.0, etiket 15/21/27/33/39; dar aralıkta "10, 11, 11, 12, 13". | `render/svg.ts:106, 287, 368`; ajan A F3 [ÖLÇTÜM] | Çizgileri yuvarlanmış değerlere oturtmak. |
| 13 | [P] | DÜŞÜK | §8.6 tarama sınırları | `no_frontend_math` op regex'i `x *= 100` gibi bileşik atamaları ve tasarım gereği `+`/`-`, `Math.*`, `Number()`, `toFixed`, `.length` sayımlarını yakalamaz. | `app/tests/no_frontend_math.test.ts`; ajan A F9 [ÖLÇTÜM] | Regex'e `[*/%]=` eklemek. |
| 14 | [P] | DÜŞÜK | §8.7 | `readableCount(999999.9996)` = "1000 bin". | `render/format.ts:149-158`; ajan A F10 [ÖLÇTÜM] | Eşik yuvarlamadan sonra seçilsin. |
| 15 | [P] | DÜŞÜK | §8.8 | `intervalBar` aralık uçlarını sessizce kırpar (bugün etkisiz: `scaleRange` bütün değerleri kapsar). | `render/svg.ts:335`; ajan A F11 | Kırpma işareti. |
| 16 | [P] | DÜŞÜK | §8.10 U16 | "n < 10 yalnız satır" anlatımı: dosyada n < 10 hücre zaten yok; 10–30 bandı ekranda anlatılmıyor. | ajan D F6 | Metin. |
| 17 | [P] | DÜŞÜK | §8.18 künye | Geç kayıtta da yeşil "✓ push kanıtı var" (kanıt var ama T'den sonra). | ajan D F7 | Renk sınıfa bağlansın. |
| 18 | [P] | DÜŞÜK | §8.12 olay akışı | Gruplu RECORD olayının sınıfı yalnız tavan modelinden ("geç kayıt" derken getiri modeli canlı olabilir). | ajan D F8 | Model başına sınıf. |
| 19 | [P] | DÜŞÜK | §8.18 "Payda" | Alt metin `n_skipped`'ı atlıyor; `n_late` null → "0 geç kayıt". | ajan D F9, F10 | Metin. |
| 20 | [P] | DÜŞÜK | §8.12 "Tabanda kırılma" | "seri taban kapanışıyla bozuldu" sayımı L = 0 (seri hiç başlamamış) arzları da sayıyor. | `commands/sade.rs:862-863`; ajan D F11 [ÖLÇTÜM] | Alt metin "ilk tavan olmayan gün tabanda" ya da L ≥ 1 süzgeci. |
| 21 | [P] | DÜŞÜK | §8.19 | "güncel kümeyle aynı" = gömülü INDEX sha'sı, repo INDEX'i değil. | ajan D F12 | Metin "uygulamadaki kümeyle". |
| 22 | [P] | DÜŞÜK | §7.13 | `--cancel-post-d1` bir sapma değildir: EK 3 "Python'da doğrulanır" der, Python tek `--cancel` bayrağı taşır; tablo satırı kapanmalı. | `borsai/freeze.py:1588`; ajan B B9 | Belge. |
| 23 | [P] | DÜŞÜK | §8.10 U79 | U79 özeti şartname metnini tekrar eder; uygulanan metin "öne çıkan yok — kasa sonrası kural (§5.5): uygun aday yok" (p34 K-P4-1 kayıtlı). | ajan B B10 | Belge. |
| 24 | [P] | DÜŞÜK | §7.12 | 5 e2e testinin ikisi (prepare_screens*) ayrıca `BORSAI_E2E_SCREENS=1` ister. | ajan B B4 | Belge. |
| 25 | [P] | DÜŞÜK | §8.7 | SPEC_APP §4 ondalık sayısını verir ama yuvarlama kuralı (yarıda ne olur) yazmaz; fiilî kural JS `toFixed` (ikili değere göre): pct0(0.145) = %14, tl2(27.485) = 27.48 TL. Bulgu 4'ün kökü. | ajan A F2 [ÖLÇTÜM] | Şartnameye kural eklenmesi (yeni model_id gerekmez; gösterim). |
| 26 | [K] | ORTA | §8.12 "Veri" (proje sahibinin sorusu) | Kılavuz yalnız "`registry/ipos.csv` dondurulmuş satırlar" der. Gerçek: Monitör = ipos.csv'de FROZEN satırlar ∪ `registry/records/<T>/` altında etkin tahmin kaydı olan arzlar (`monitor_tickers`); yeni arz dondurulunca ipos satırı olmadan da görünür (şirket adı ve payda durumu boş). ipos.csv satırını ekleyen üretim komutu yok (`append_ipos` yalnız testlerde çağrılır; satır elle/Python ile append-only). Kapanışlar `data/outcomes/<T>.csv`'den (`borsai.outcomes update`). | `commands/sade.rs:722-740, 677-709`, `registry.rs:254-345`, `grep append_ipos` [ÖLÇTÜM] | — |
| 27 | [K] | DÜŞÜK | §8.12 veri şeridi | "kendi sorusunda öne çıkan" etiketi doğru diye aktarılmış (bulgu 2). | — | — |
| 28 | [K] | DÜŞÜK | §7.9.2 | Boş/bozuk T'de Rust `T_UNKNOWN`, Python `tufe_for_record` `ValueError` (kayıt yolunda ulaşılmaz). | `harness/tufe_expect.jsonl` py_exc [ÖLÇTÜM] | — |
| 29 | [K] | DÜŞÜK | §8.25 | "`app/docs/screens/` altında yalnız README.md var": asıl repoda 26 görüntü var (`v2/`). | `ls app/docs/screens/v2` [ÖLÇTÜM] | — |
| 30 | [K] | DÜŞÜK | §8.8 | "hepsinde y ∈ [0,1] aynı dönüşüm": yalnız lineChart/survivalCurve/calcCurve/barChart; fanChart, sparkline, corridorChart, returnDots, intervalBar veri güdümlü. | ajan A F7 | — |
| 31 | [K] | DÜŞÜK | §8.6 | "bütün sayımlar Rust'tan": bazı ekran sayımları TS `.length` (registry.ts:71,207; sicil.ts:28,32; about.ts:33; ayarlar.ts:35-36; accuracy.ts:373,399-402). | ajan A F8 | — |
| 32 | [K] | DÜŞÜK | §7.7 | `freeze_todo` komutu kayıtlı ama hiçbir TS dosyası ve test çağırmıyor (ölü IPC yüzeyi). | `grep freeze_todo app/src app/tests` → 0 [ÖLÇTÜM] | — |
| 33 | [K] | DÜŞÜK | §7.13 | `app/README.md` "Bilinen sapmalar" stderr sınıflaması, bağ aşırı reddi, fall portu, U79 metni, K-P4 kararlarını içermiyor; SPEC_DEVIATIONS yalnız Python tarafı. | ajan B B13 | — |
| 34 | [B] | — | §8.8 | `distBars` yükseklikleri en yüksek çubuğa göreli, eksen yok, değer yalnız ipucunda; ekran metni bunu söylemiyor (işlem sayısı çubuğu söylüyor). | ajan A F4 | metin |
| 35 | [B] | — | §8.14 | Getiri çubukları \|getiri\|/max, işaret düşer, not yok. | `sonuc.ts:104,112`; ajan A F5 | metin |
| 36 | [B] | — | §8.17 | Hata puanı çubukları max(model, kural)'a göreli; uzun = kötü, açıklama yok. | `perf.ts:43-51`; ajan A F6 | metin |
| 37 | [B] | — | §8.8 | Sparkline alan dolgusu min/max tabanına kapanır. | `svg.ts:192`; ajan A F12 | — |
| 38 | [B] | — | §8.10 U62 | U62 Rust'ta sayaçla değil 0.5^k çakışmasıyla, vitest'te sayaçla sınanır (zayıf ama kapsar). | ajan B B14 | — |
| 39 | [B] | — | §8.23 renk | Altın yalnız model çıktısı kuralının dışı: canlı ilerleme çubuğu dolgusu (`perf.ts:113`), "Üretimde" sayısı (`perf.ts:153`, `monitor.ts:42`) altın; `sonuc.ts:91` model satırı kapıdan bağımsız `gold` sınıfı (bugün öne çıkan v0 olduğu için görünmez). | [ÖLÇTÜM] | sınıf seçimi kapıya bağlansın |

## Bölüm bölüm kontrol listesi

| § | kontrol edilen iddia | tutan | tutmayan | not |
|---|---|---|---|---|
| 7.2 mimari, ön uç hesap yapmaz | 4 | 4 | 0 | ajan A taraması |
| 7.3 build.rs / gömme / süzgeç / kırma koşulları | 9 | 9 | 0 | bulgu 11 not |
| 7.4 sha zinciri | 5 | 5 | 0 | INDEX 7e636e8b…, POST_D1 94ac36fa…, ebeveyn caa4dc86…, 27 dosya |
| 7.5 CSP, capabilities, süreç çağrıları, git beyaz listesi, yazma yolları | 7 | 7 | 0 | |
| 7.7 55 komut, api.ts eşleşmesi | 3 | 2 | 1 | bulgu 32 |
| 7.8 port semantiği (bağımsız girdiler) | 28 model | 28 | 0 | |
| 7.9 TÜFE hazırlığı, dondur akışı, Python'a düşülen yerler | 12 | 12 | 0 | bulgu 28 bilgi |
| 7.10 D1 sonrası sihirbaz | kaynak okundu | — | — | koşturulmadı |
| 7.11 parite düzeneği | 7 | 6 | 1 | bulgu 10 |
| 7.12 test sayıları (169/13/164; dağılım 16 satır) | 19 | 19 | 0 | bulgu 24 ayrıntı |
| 7.13 sapma tablosu | 8 | 6 | 2 | bulgu 9, 22 |
| 8.5 iki mod | 3 | 3 | 0 | ajan D |
| 8.6 "ön uç hesap yapmaz" | 5 | 4 | 1 | bulgu 13, 31 |
| 8.7 biçimler | 14 | 13 | 1 | bulgu 14, 25 |
| 8.8 grafikler | 12 | 11 | 1 | bulgu 12, 30 |
| 8.9 metin kuralları (geçiyor tek kaynak, yasak sözcük) | 4 | 4 | 0 | ajan D hüküm tutarlılığı: 300 hücrede 0 ihlal |
| 8.10 U1–U80 haritası | 80 | 79 | 1 (zayıf) | bulgu 38 |
| 8.11 kabuk, kapı, ipuçları | 6 | 4 | 2 | bulgu 1 kökü, 3 |
| 8.12 Monitör zinciri | 18 | 14 | 4 | bulgu 2, 18, 20, 26 |
| 8.13 Giriş zinciri | 8 | 7 | 1 | bulgu 7 |
| 8.14 Tahmin sonucu zinciri | 12 | 11 | 1 | bulgu 1 |
| 8.15 Analiz zinciri | 10 | 9 | 1 | bulgu 1 |
| 8.16 seri hesaplayıcı (formül, g3, not, kalan gün, S_cond indisi, sayımlar, örnek tablo j = 0/3/6) | 9 | 9 | 0 | fikstür: j=3 %67/%45/%6, 66/53; j=6 %67, 33/27 |
| 8.17 Model performansı zinciri | 14 | 9 | 5 | bulgu 3, 5, 6, 8, 16 |
| 8.18 Sicil | 7 | 5 | 2 | bulgu 17, 19 |
| 8.19 Kayıtlarım | 3 | 2 | 1 | bulgu 21 |
| 8.20 Ayarlar/Hakkında | 6 | 6 | 0 | |
| 8.23 renk kuralı | 2 | 1 | 1 | bulgu 39 |
| 8.25 test/fikstür/görüntü sayıları | 5 | 4 | 1 | bulgu 29 |

## Bağımsız yeniden hesaplananlar

| ölçüm | betik (ekler/4/harness) | kendi sonucum | repodaki değer |
|---|---|---|---|
| 372 girdi × 27 model + 148 D1 sonrası paritesi (üreticiden bağımsız; H99 aralıkları, f3 eksik, f6 retleri, sınır değerleri, TÜFE ayı yok, yarım gün, D1 uçları) | `gen_cases.py`, `audit4_harness.rs`, `compare.py`; çıktı `summary.md`, `max_abs.json`, `status_counts.json` | 10 192 satır, 0 uyuşmazlık, 10 166 bit-eşit; maks \|Δ\| 8.882e-15 (pb_v0 D10), pb_ceiling* 3.6e-15, post_d1 1.8e-15; ret yolları: 30 kod | §7.11: 1.14e-13 / 1.78e-15 |
| Uygulama TÜFE hazırlığı vs Python `tufe_for_record` | `audit4_tufe.rs`, `tufe_expect.jsonl`, `rust_tufe_out.jsonl` | 125 T, 0 fark; gömülü = repo tablosu | §7.9.2 |
| S_{j+1}/S_j − (1 − h_{j+1}) | `rust_cond_check.jsonl` (klonda) | 5 650 hücre, maks 1.11e-16 | §8.16 |
| Bir bayt mutasyonu | klon, `cargo test --test integrity` | 5 test kırmızı: `INTEGRITY_FAILED (MODEL_SHA_MISMATCH)`; `integrity_fail_closed` yeşil | §7.4 |
| e2e dondurma (geçici klon) | `e2e_freeze_ozet.txt` | YEŞİL; parite 27/27 \|Δ\|max 0; DUPLICATE_RECORD; 7 eski kayıt 16/16 | §7.9.4 |
| Girdi belgesi baytları | klon, `cargo test --test stage3 bytes pretty` | 2/2 yeşil (Python `pretty_json_bytes`) | §7.8.1(e) |
| Gömülü sha'lar | Python | INDEX ve 27 dosya, POST_D1, MANIFEST hepsi eşleşiyor | §7.4 |
| Grafik yeniden çizimi (distBars 300×120 ve 560×150; corridorChart 760×300, gerçek fikstürler) | ajan A `measure.mjs` | maks 0.050 px fark, monoton | §8.8 |
| Yuvarlama | ajan A `measure.mjs` | pct0: 0.665→%67, 0.675→%68, 0.125→%13, 0.145→%14; pctSigned1(−0.00005)→%0.0; 78/100 001 p_up noktasında pct0 ≠ pct_up | §8.7 |
| Hüküm tutarlılığı (perf_view hücre seçimi yeniden üretildi) | `verdict_check.py` | 6 satır (3 geçiyor / 1 ayırt edilemiyor / 2 hükümsüz) fikstürle aynı; 300 hücre + OOT birincil: "geçiyor" iken CI 0'ı içeren ya da n < 30 olan 0 | §8.17 |
| Test sayıları (listeleme) | ajan B | 169 `#[test]`, 13 ignore (8 + 5), 164; vitest 355 + 21 döngü = 376; 55 komut; 50 invoke adı | §7.12, §8.25 |

Uygulama hangi modelleri hesaplıyor: 27 gömülü model ve `post_d1_hazard_v0` Rust'ta hesaplanır; `break_floor_v0` gömülü değildir, `break_view` olasılıkları `registry/post_break/<T>/machine_*.json`'dan okur, katsayıları `models/break_floor_v0.json` sha'sı makine kaydındaki `params_sha256`'ya eşitse döner (§7.7 doğru).

## Bakılmayanlar

- Uygulama pencere açılarak çalıştırılmadı; ekran görüntüsü alınmadı (fikstür + kod + klon testleri).
- D1 sonrası sihirbazı (`post_d1_flow`) ve `e2e_personal_isolation.sh` koşturulmadı; eski ayrıntılı görünümün ekranları (§8.22) zincir olarak çıkarılmadı (yalnız bulgu 4'ün yeri).
- Zaman-dışı panelin kasa alt bölümleri; `scores_oot.json` süzgecinin bayt boyutu.
- Windows notları (§7.5) ölçülmedi.
- Tam test takımı koşulmadı (kural gereği).

## Proje sahibine açık sorular

1. Öne çıkmayan ufuklarda dosyadaki keşif hükmü ("geçemiyor" dahil) ekranda gösterilsin mi, yoksa yalnız "birincil değil" mi yazılsın?
2. `post_d1_hazard_v0` için "Geçmiş test" sütunu ne göstermeli: "test dosyada yok" mu, yoksa canlı blok bilinçli olarak kapı girdisi mi (öyleyse sütun adı değişmeli)?
3. p_up yüzdesi için tek yuvarlama kaynağı Rust mı olsun (şartname §4'e kural)?

## Koruma ve hijyen sayımları

- Koruma: `ekler/4/koruma_once.txt` ve `koruma_sonra.txt`: dokuz sha iki ölçümde aynı, korunan yollarda status boş. Klonda `git status --porcelain -- app` yalnız iki harness test dosyasını (izlenmeyen) gösterir; asıl repoda boş.
- Hijyen: rapor ve `ekler/4/` altında kasa kodu 0, `thb/thm` + 8 hane kalıbı 0 (sayım `koruma_sonra.txt`'de).

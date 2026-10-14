# Kitap denetimi 4 — Ajan A: ön uç aritmetiği, yuvarlama, SVG grafikler

Repo: /Users/ahmet/Desktop/BorsAi @ ee3796d (salt okuma). Rehber: docs/fable_kitap_audit/kitap/08_uygulama_arayuz.md §8.6–§8.8.
Ölçüm ortamı: /tmp/borsai_kitap_audit_4/clone/app (vitest 5.0.1, node 22.23.2). Betikler ve ham çıktılar bu dizinde:
`scan.mjs` (+ `scan_out.tsv`), `measure.mjs` (+ `measure_out.txt`), `measure2.mjs` (+ `measure2_out.txt`), `regex_gap.txt`, `mod/` (format.ts/svg.ts kopyası; dom.ts yalnız `esc` taslağı).
Etiketler: [ÖLÇTÜM] ölçüldü / [ÇIKARIM] koddan çıkarım. Sınıf: [P] proje hatası, [K] rehber hatası, [B] belirsiz.

## 0. Rehber iddialarının özeti

| İddia | Sonuç |
|---|---|
| (a) `*`,`/`,`%` yalnız render/format.ts ve render/svg.ts'te; sade/** altında hiç yok | [ÖLÇTÜM] DOĞRU. `split()` portu + projenin op regex'i ile bağımsız tarama: iki dosya dışında 0 satır (scan_out.tsv'de `mulDivMod` satırı yok). `no_frontend_math.test.ts` + `sade_static.test.ts` klonda yeşil (2 dosya, 16 test). |
| (a') "ön uç anlamlı sayı üretmez" | [ÖLÇTÜM] BÜYÜK ÖLÇÜDE DOĞRU; istisnalar: `.length` sayımları, `j + 1`, `i + 1`, `Math.max` ölçek seçimi, `Number()` (bkz. §2). Regex'in kör noktaları §1-F9. |
| (b) svg.ts yanıltıcı ölçek kullanmaz | [ÖLÇTÜM] Piksel eşlemesi doğru ve monoton (distBars ve corridorChart yeniden çizildi, |Δ| ≤ 0.05 px). Yanıltıcı değil ama: y ekseni etiketi/ızgara çizgisi uyumsuzluğu (F3), eksensiz göreli çubuklar (F4, F5, F6). |
| (c) format.ts SPEC_APP §4'ü izler | [ÖLÇTÜM] Ondalık sayıları §4 ile uyumlu. §4'te YUVARLAMA KURALI YOK (F2). Yuvarlama fiilen "ikili değer üzerinde yarıda sıfırdan uzağa" (JS toFixed). Rust fall.rs ile tek tutarsızlık yarı-bağlarda (F1). |

## 1. Bulgular

### F1 [P] ORTA — Aynı olasılık iki yerde farklı yuvarlanabiliyor: `pct0(p_up)` ile `pctInt(pct_up)`
- Yerler: `app/src/render/results.ts:145,210,352`, `app/src/sade/render/sonuc.ts:114`, `app/src/sade/render/analiz.ts:248` → `pct0(p_up)` = toFixed(0)(100·p_up). `app/src/render/summary.ts:278-279` → `pctInt(f.d10.pct_up)`; Rust `app/src-tauri/src/commands/fall.rs:41-43`: `p_fall = 1 − p_up; k = round(100·p_fall); pct_up = 100 − k`.
- Her iki yol da "P(kapanış > arz)" olarak ekrana çıkar (tr.ts:922 `pUpLine`); ayrıntılı sonuç ekranında `renderFallSummary` (summary.ts:196) ile sonuç tablosu aynı ekrandadır.
- [ÖLÇTÜM] 0..1 aralığında 1e-5 adımla 100001 noktada 78 uyuşmazlık; hepsi .xx5 yarı-bağlarında (iki taraf da kendi çarpımını yukarı yuvarlar, toplam 101 olur). Somut: p_up = 0.005 → `pct0` "%1", düşüş kartı "P(kapanış > arz) = %0"; p_up = 0.075 → "%8" vs "%7"; p_up = 0.065 → "%7" vs "%6".
- Beklenen: tek yuvarlama kaynağı (ör. Rust `pct_up` değeri her yerde, ya da `pct_up := round(100·p_up)` ve `pct_fall := 100 − pct_up`). Gerçek: iki ayrı yuvarlama.
- Not: fall.rs içindeki çiftin kendisi tutarlı (`pct_fall + pct_up = 100`, fall.rs:196 testi). Sade görünümde `pct_up/pct_fall` kullanılmıyor (grep) → yalnız ayrıntılı görünüm.

### F2 [B] DÜŞÜK — SPEC_APP §4'te yuvarlama kuralı yok; rehber "kurallar §4'ten gelir" der
- `docs/app/SPEC_APP.md` §4 (tam alıntı, sayı biçimi maddesi): "Sayı biçimi: getiri 1 ondalık yüzde, fiyat 2 ondalık TL, olasılık 0 ondalık yüzde, metrik 4 ondalık, hata "puan"; tooltip'te ham binary64 (Python repr ile aynı, `format!("{:?}")`)." — yarı-yukarı / bankacı / ikili seçimi yazılı değil.
- Fiilî davranış [ÖLÇTÜM]: JS `toFixed`, ×100 çarpımından SONRA ikili değerin tam ondalık açılımı üzerinde yarıda sıfırdan uzağa yuvarlar (= Rust `f64::round` aynı çarpım üzerinde). Ondalık yarı-yukarı bekleyen okur için sürprizler: `pct0(0.145)` = "%14" (14.4999…), `points1(0.00045)` = "0.0 puan" (0.0449…), `tl2(1.005)` = "1.00 TL", `tl2(27.485)` = "27.48 TL".
- Rehber §8.7 bu kuralı yazmıyor; §4'e atıf yeterli değil ([K] payı).

### F3 [P] DÜŞÜK — Y ekseni etiketleri yuvarlanıyor, ızgara çizgileri yuvarlanmıyor; düşük fiyatlı arzda mükerrer etiket
- `app/src/render/svg.ts:285-287` (corridorChart): çizgi `sy(v)` tam değerde, etiket `v.toFixed(0)`; sapma ±0.5 TL. [ÖLÇTÜM] fixture `sade_arz_netgl.json` (760×300): ızgara 14.608/20.706/26.805/32.904/39.002 TL, etiketler "15, 21, 27, 33, 39". Sentetik 10–12.65 TL arz: etiketler "10, 11, 11, 12, 13" (ızgara 9.79/10.56/11.33/12.09/12.86) → iki "11".
- Aynı kalıp `svg.ts:368` (returnDots: küçük aralıkta "-%0, +%0, +%1, +%1, +%2") ve `svg.ts:106` (fanChart: "%0, %0, %1, %1, %1").
- Beklenen: etiket değerine "güzel" adım seçimi ya da etiketin çizgiyle aynı değeri taşıması (ör. 1 ondalık).

### F4 [B] DÜŞÜK — distBars: yükseklik en büyük çubuğa göre, y ekseni yok, ekran metni bunu söylemiyor
- `svg.ts:201,209`: `max = max(P_L)`, `bh = (v/max)·(ih−4)`. [ÖLÇTÜM] en yüksek çubuk daima ih−4 px (fixture'da l=3, P=0.2022 → 98 px / 128 px). SVG'de hiçbir `%` metni yok; P değerleri yalnız `<title>` tooltip'inde (11 adet).
- Ekran metinleri: `tr.ts:1705` kacSub "Seri uzunluğunun dağılımı, listeleme öncesi", `tr.ts:1842` "Kayıttaki dağılım (listeleme öncesi)" — göreli ölçek yazmıyor. Karşılaştırma: işlem çubuğu için `tr.ts:1800` tradeSub açıkça "çubuk arzın on günündeki en büyük güne göre" der. Tutarsız açıklama düzeyi.
- Tek grafik içinde ölçek paylaşıldığı için yanıltıcı değil; ancak Tahmin sonucu (560×150) ile Analiz (300×120) ve farklı modellerin çubukları yükseklikle karşılaştırılamaz. Rehber §8.8 "yükseklik en büyük çubuğa göre" demesi doğru.

### F5 [B] DÜŞÜK — Getiri çubukları |getiri| / max|getiri|, işaret kayboluyor
- `app/src/sade/render/sonuc.ts:104,112`: `max = Math.max(...|ret|)`, `fillPct(|ret|, max)`. −%5 ile +%5 aynı uzunlukta; işaret yalnız yandaki `pctSigned1` metninde. `tr.ts:1718` returnSub "Arz fiyatına göre; fiyat modelin çıktısıdır" — ölçek açıklaması yok. Rehber §8.6 bu `Math.max`'ı "Sınırlar" altında dürüstçe anıyor.

### F6 [B] DÜŞÜK — Performans skor çubuklarında uzun çubuk = daha kötü
- `app/src/sade/render/perf.ts:43-51`: `fillPct(m, max(m,k))`, `fillPct(k, max(m,k))`. Brier/MAE/RPS'te küçük iyi olduğundan uzun çubuk kötü modeldir; satırda "kısa = iyi" diyen metin yok (guide metinleri yalnız aralık çubuğu içindir, tr.ts:1907-1912).

### F7 [K] DÜŞÜK — Rehber §8.8 "hepsinde aynı iki dönüşüm, y ∈ [0,1]" der; çoğu grafik veri-güdümlü eksen kullanır
- Sabit 0..1 y ekseni yalnız `lineChart` (svg.ts:23), `survivalCurve` (227), `calcCurve` (408), `barChart` (63, kırpılmış). Veri-güdümlü: `fanChart` [min(0,veri), max(0,veri)] (96-98), `sparkline` [min, max] ∪ ref (182-184), `corridorChart` ±%8 (276-280), `returnDots` 0 dâhil ±%10 (355-361), `intervalBar` çağıranın [min,max]'ı (335). Rehber yalnız koridorun %8 payını anıyor.

### F8 [K] DÜŞÜK — Rehber §8.6 "sayımlar … hepsi Rust'ta üretilir" der; bazı ekran sayımları TS `.length`
- `app/src/render/registry.ts:71,207` (`t.records.length` → tablo hücresi), `app/src/sade/render/sicil.ts:28,32` (`c?.n_payda ?? vm.registry.ipos.length`, `… ?? vm.registry.proofs.length` yedekleri), `app/src/screens/about.ts:33`, `app/src/sade/render/ayarlar.ts:35-36` (`embedded_models.length`), `app/src/render/accuracy.ts:373,399-402` (payda tablosu başlık sayıları `rows.length`), `accuracy.ts:115` (`cells.length − shown.length`, yalnız >0 testi). Bunlar liste kardinalitesidir, model çıktısı aritmetiği değildir; ama rehberin genellemesi fazla geniş.

### F9 [P] DÜŞÜK — Tarama regex'inin kör noktaları (test "ruhu" korumuyor)
- `no_frontend_math.test.ts:46` / `sade_static.test.ts:27` `op = /[^/*]\s*[*/%]\s*[^/*=]/`. [ÖLÇTÜM] (regex_gap.txt): `x *= 100`, `s /= 2`, `k %= 3` KAÇAR (işleçten sonra `=` dışlandığı için); `j + 1`, `1 - p`, `Math.max(a,b)` KAÇAR (tasarım gereği); `const r = /ab/.test(s)` YAKALANIR (regex sabiti yanlış alarm — şu an kodda yok, format.ts hariç). Yani bileşik atama ile çarpma/bölme yapılırsa test yeşil kalır.
- Ayrıca taranmayan: `Math.abs/round/max/min`, `toFixed`, `Number()`, `.sort((a,b)=>a-b)`, `.length`, tekli `-`. Rehber §8.6 "Sınırlar" `Math.max/min`'i anıyor; bileşik atamayı anmıyor.

### F10 [P] DÜŞÜK — `readableCount` eşik/yuvarlama sırası
- `app/src/render/format.ts:149-158`: eşik ham değere, yuvarlama sonra. [ÖLÇTÜM] `readableCount(999999.9996)` = "1000 bin" (beklenen "1 milyon"); `readableCount(10000)` = "10 bin", `9999.5` → "9999.5" (eşik 1e4, 1e3 değil — tasarım kararı olabilir, rehber "bin" birimini açıklamıyor).

### F11 [P] DÜŞÜK (gizil) — `intervalBar` uçları sessizce kırpar
- `svg.ts:335`: `clamp(v, min, max)`; aralık ekseni dışına taşan CI ucu kenarda biter, işaret yok. [ÖLÇTÜM] ci=[−0.01, 0.2], max=0.1 → x2=220.0. Fiilen zararsız: `perf.ts:21-36 scaleRange` bütün diff ve CI uçlarını kapsar (min ≤ 0, max ≥ 0.02).

### F12 [B] DÜŞÜK — `sparkline` alan dolgusu taban çizgisine değil SVG altına kapanır
- `svg.ts:192`: alan `L…,h L…,h Z` ile o.h'ye kapanır; y alanı [min(veri, ref), max]. Dolgu "sıfırdan yükseklik" izlenimi verebilir. Standart sparkline davranışı; Monitör satırında (monitor.ts:89,134) eksen yok.

### F13 [K] DÜŞÜK — Rehber §8.7 örnekleri doğru [ÖLÇTÜM]: `pctSigned1(-0.00005)`="%0.0", `points1` 0.0046→"0.5 puan" (0.46→0.5), `fixed1(3.2811)`→"3.3". Tek eksik: yuvarlama kuralı (F2).

## 2. Aritmetik yeri tablosu (format.ts/svg.ts dışı; [ÖLÇTÜM] scan.mjs + grep; satırlar grep'e göre)

| Dosya:satır | İfade | Sınıf |
|---|---|---|
| sade/render/sonuc.ts:104 | `Math.max(...rets.map(abs))` | ölçek seçimi (CSS genişlik) — F5 |
| sade/render/sonuc.ts:112 | `fillPct(Math.abs(ret), max)` | CSS genişlik (göreli) — F5 |
| sade/render/perf.ts:35 | `Math.min(...lo)`, `Math.max(...hi, 0.02)` | ölçek seçimi (intervalBar aralığı) |
| sade/render/perf.ts:46-50 | `Math.max(m,k)`, `fillPct(m,max)` | CSS genişlik (göreli) — F6 |
| sade/render/perf.ts:113 | `progressPct(n, of)`; metin `${n} / ${of}` | CSS genişlik; sayılar Rust'tan |
| sade/render/analiz.ts:183 | `fillPct(value)` (max=1) | CSS genişlik, mutlak 0..1 |
| sade/render/calc.ts:53,64 | `d === j + 1`, `historyCount(…, vm.j + 1)` | **ekrana giden türetilmiş tamsayı** ("d. gün" = j+1); önemsiz ama regex görmez |
| sade/render/calc.ts:90-93 | `d[d.length-1]`, `groups.length-2` | indeks / metin |
| sade/screens/sihirbaz.ts:15 | `${i + 1}` | adım numarası (ekran) |
| sade/render/sicil.ts:28,32 | `?? vm.registry.ipos.length`, `?? proofs.length` | **ekrana giden sayım (yedek)** — F8 |
| sade/render/ayarlar.ts:35-36; screens/about.ts:33 | `embedded_models.length` | ekrana giden sayım — F8 |
| render/registry.ts:71,207 | `t.records.length` | ekrana giden sayım — F8 |
| render/accuracy.ts:115 | `cells.length − shown.length` | karşılaştırma (>0) |
| render/accuracy.ts:373,399-402; accuracy_oot.ts:140,182,208 | `rows.length` başlık sayıları | ekrana giden sayım — F8 |
| render/ceiling.ts:176 | `.sort((a,b)=>Number(a)−Number(b))` | seçme/sıralama (P_L_cond anahtarları) |
| render/ceiling.ts:123,220; results.ts:151,238,245 | `S_cond[k−1]`, `closes[h−1]`, `S[k−1]` | indeks |
| render/results.ts:201 | `Number(h.slice(1))` | ufuk ayrıştırma |
| screens/results.ts:172,220-221; screens/registry.ts:274-534; sade/screens/*:78,104 | `Number(dataset.*)`, `declared[h−1]` | olay/durum, ekrana sayı gitmez |
| sade/render/analiz.ts:38; sicil.ts:38; screens/sicil.ts:59 | `.sort(localeCompare)` | metin sıralama |

Sonuç: model çıktısı üzerinde **gerçek** (yeni bilgi üreten) aritmetik yok. `*`/`/`/`%` iki dosyada; `Math.exp/log/pow/sqrt`, `**`, `.reduce(` hiçbir yerde. Ekrana giden TS-türetimli sayılar yalnız liste sayımları ve `j+1`/`i+1`.

## 3. Yuvarlama tablosu ([ÖLÇTÜM], measure_out.txt)

| Çağrı | Çıktı | ×100 / değer (ikili tam açılım) | Rust `round` aynı çarpımda | Ondalık yarı-yukarı olsaydı |
|---|---|---|---|---|
| pct0(0.665) | %67 | 66.5000… (tam) | 67 | 67 |
| pct0(0.675) | %68 | 67.5000… (tam) | 68 | 68 |
| pct0(0.125) | %13 | 12.5 (tam) | 13 | 13 |
| pct0(0.145) | **%14** | 14.49999999999999822 | 14 | 15 |
| pct0(0.5) | %50 | 50 | 50 | 50 |
| pct0(0.505) | %51 | 50.5 (tam) | 51 | 51 |
| pctSigned1(0.00665) | +%0.7 | 0.66499999999999992 | — | 0.7 |
| pctSigned1(-0.00005) | %0.0 | 0.0050000000000000001 | — | 0.0 (işaretsiz) |
| pctSigned1(0.0005) | +%0.1 | 0.05000000000000000278 | — | 0.1 |
| fixed1(3.25) | 3.3 | 3.25 (tam, bağ → yukarı) | — | 3.3 |
| fixed1(3.35) | 3.4 | 3.35000000000000008882 | — | 3.4 |
| points1(0.00045) | **0.0 puan** | 0.04499999999999999833 | — | 0.1 puan |
| metric4(0.12345) | 0.1235 | 0.12345000000000000417 | — | 0.1235 |
| tl2(1.005) / (2.675) / (27.485) | 1.00 / 2.67 / 27.48 TL | hepsi ikilide bağın altında | — | 1.01 / 2.68 / 27.49 |

Kural [ÇIKARIM, spesifikasyonla doğrulanmış]: `toFixed(f)` ikili değerin tam ondalık açılımında yarıda büyük n'yi seçer; negatifler işaret ayrılarak işlenir → "ikili değerde yarıda sıfırdan uzağa". Rust `f64::round` aynı tanımdır; `pct0(p)` ≡ `round(100·p)` (aynı f64 çarpımı). Tek tutarsızlık F1 (farklı argümandan yuvarlama). `Math.round` (svg.ts:27,232,413) negatif bağda farklı (−0.5→−0) ama yalnız 0/25/50/75/100 sabitlerinde kullanılıyor → etkisiz. `ceiling.rs:127-130 integer_count` yalnız tamsayılık testi (tolerans), gösterim yuvarlaması değil.

## 4. Grafik tablosu + yeniden çizim

| Fonksiyon (svg.ts) | Y alanı | Sıfır tabanı | Çubuk 0'dan mı | X aralığı | Göreli/mutlak | Paylaşılan ölçek | Yanıltma riski |
|---|---|---|---|---|---|---|---|
| lineChart :18 | sabit [0,1] | evet | — | eşit (xMin..xMax, adım 1) | mutlak | seriler arası evet | yok |
| barChart :54 | sabit [0,1] (kırpma) | evet | evet | eşit (bw+gap) | mutlak | — | yok; y etiketi yok |
| fanChart :87 | [min(0,v), max(0,v)] | evet (0 dâhil) | — | eşit | veri-güdümlü | seriler arası evet | etiket yuvarlama (F3) |
| fillPct/progressPct :166 | [0,max] | evet | evet | — | göreli (max) | — | F5/F6 bağlama bağlı |
| sparkline :177 | [min, max] ∪ ref | hayır | — | eşit (i/n) | veri-güdümlü | satırlar arası HAYIR | alan dolgusu (F12) |
| distBars :200 | [0, max P_L] | evet | evet | eşit | göreli (en yüksek çubuk) | grafikler arası HAYIR | eksen yok, metin yok (F4) |
| survivalCurve :222 / calcCurve :397 | sabit [0,1], x 0..10 | evet | — | eşit (k/10) | mutlak | evet | yok |
| corridorChart :269 | [min−%8, max+%8] fiyat | hayır (fiyat) | — | eşit (h/10, 0=arz) | veri-güdümlü | kapanış/üst limit/model aynı | etiket yuvarlama, mükerrer etiket (F3) |
| intervalBar :334 | çağıranın [min,max], kırpma | sıfır çizgisi çizilir | — | — | mutlak (perf.scaleRange) | satırlar arası EVET | kırpma gizil (F11) |
| intervalTicks :346 | aynı | — | — | — | — | — | kırpma yok |
| returnDots :351 | [min(0,v)−%10, max(0,v)+%10] | evet (0 dâhil, çizgi) | — | eşit ((i+0.5)/n) | veri-güdümlü | tahmin/gerçek aynı | etiket yuvarlama ("-%0") (F3) |
| tradeBar :386 | [0,1] (Rust oranı), min 1 px | evet | evet | — | göreli (Rust max gün) | satır içinde evet | tradeSub açıklıyor |

Yeniden çizim [ÖLÇTÜM] (measure2.mjs → measure2_out.txt):
- **distBars**, fixture `app/tests/fixtures/ui/sade_record_ceiling_netgl_j3.json` `display.rows[0]` (ceiling_hazard_v0) P_L (11 değer, Σ = 1.0, max P_L[3] = 0.202206, mode_l = 3), Analiz çağrısı 300×120: formül `bw = (300 − 4·12)/11 = 22.909`, `ih = 102`, `bh = P/max·98`, `x = 4 + i·26.909`. Beklenen vs üretilen yükseklik (px): l0 88.42/88.4, l1 54.42/54.4, l2 46.95/46.9, l3 98.00/98, l4 65.43/65.4, l5 43.68/43.7, l6 29.17/29.2, l7 19.47/19.5, l8 13.00/13, l9 8.68/8.7, l10 17.44/17.4. Maks sapma 0.048 px (yalnız `toFixed(1)`); monoton (P sırası = yükseklik sırası) EVET; her çubuk y+h = 102 tabanında; x adımı 26.9 eşit; vurgulu çentik 3; y ekseni/`%` metni YOK; 11 tooltip. Tahmin sonucu çağrısı 560×150 (bw 46.545, ih 132): maks sapma 0.045 px, en yüksek 128 px. **Yükseklikler en yüksek çubuğa göredir; ekran metni bunu söylemez (tooltip hariç).**
- **corridorChart**, `sade_arz_netgl.json` (10 kapanış, ipo 25.52, 4 model noktası, kırılma b=4), 760×300: alan 14.608..39.002 (veri 16.29..37.32, pay 1.682); 10 kapanış karesi için beklenen/üretilen (x,y) birebir, maks sapma 0.050 px; tavan günleri `pt-up` D1–D3, sonrası `pt-down` fixture ile uyumlu.

## 5. Birim/etiket uyuşmazlıkları (görev 4)
- `svg.ts:287` koridor y etiketleri birimsiz tam sayı TL (çizgi tam değerde) — F3.
- `svg.ts:368` returnDots: "-%0" etiketi mümkün — F3.
- `sade/render/calc.ts:64` `historyCount(j, …, j+1)`: "d. gün" sayısı TS'de türetilir (tr.ts:1773-1774); anlamca doğru.
- Başka birim uyuşmazlığı görülmedi: `points1Bare` aralık uçları "puan" ile; `pct0(p_up)` olasılık; `price2` tablo başlığında birim; `countTr` işlem sayısı tr-TR binlik ayırıcı (rehber §8.7 "25.52 vs 17.885" karışma uyarısı yerinde); `returnDots` oran (0.25=%25) ile `pctSigned1(x.realized)` tutarlı.

## 6. Kontrol edilmeyenler
- Tam test paketi çalıştırılmadı (yalnız 2 tarama dosyası). `sade_svg_format.test.ts`, `format.test.ts` çalıştırılmadı (yalnız okundu; distBars testi göreli yüksekliği sınamıyor: yalnız 11 çubuk/vurgu/halka sayar).
- Rust tarafı yalnız fall.rs:36-44 ve ceiling.rs:127-130 okundu; `cargo test` yok; Rust `{:?}` ile `pyRepr` eşdeğerliği ölçülmedi.
- `app/src/dev/**` taramadan çıkarıldı (testler dâhil eder; yeşil).
- Çalışan uygulamada görsel doğrulama yapılmadı; CSS (`sade.css`) çubuk stilleri okunmadı.
- `screens/**` (eski ekranlar) `+/-` taraması yalnız scan.mjs düzeyinde; satır satır okunmadı.
- `registry/oot/` ve bülten dosyalarına dokunulmadı; fixture'lar yalnız `app/tests/fixtures/ui/` (sentetik UI fixture'ları).

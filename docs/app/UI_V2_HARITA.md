# UI v2 (sade görünüm) — tasarım ↔ veri haritası

Görev: `docs/prompts/FAZ9_APP_UI.md` (BORSAI_FAZ9_APP_UI_20261003). Tasarım: `docs/design/ui_v2/` (README, `png/`, `boards/`).
Bu belge kod yazılmadan önce yazıldı (adım 1). Her pano için öğe, veri kaynağı (Rust komutu ve dosya alanı), şartname kuralı
ve durum. "Çizilmez" satırları raporun "tasarım ↔ uygulama farkları" tablosuna aynen taşınır (K-UI-7).

Genel kurallar (her pano):

- **Sayılar.** Her sayı bir Rust komutundan gelir; TS yalnız biçimlendirir (`render/format.ts`) ve piksel koordinatı hesaplar
  (`render/svg.ts`). Yeni komutlar skor ya da metrik hesaplamaz (U25): okur, eşler, sayar, sıralar.
- **Biçim (K-UI-6, SPEC_APP §4).** Getiri 1 ondalık yüzde (`pctSigned1`: `+%25.5`), fiyat 2 ondalık TL (`tl2`), olasılık
  0 ondalık yüzde (`pct0`: `%50`), metrik 4 ondalık (`metric4`), gün 1 ondalık (`fixed1`). Tasarımdaki `0,499`, `3,28`,
  `+%25,52` yazımları örnek değildir.
- **Hüküm (K-UI-5, U19).** Hüküm hücresi dosyadaki `verdict` alanıdır. Sade açıklama `tr.ts`'te verdict'e bağlı ayrı bir
  dizedir; tasarımdaki "Model daha iyi / Fark net değil" etiketleri bu açıklama satırına döner. "geçiyor" dizesi `tr.ts`'te
  yalnız `VERDICT` eşlemesinde kalır; Rust'ta yalnız `scores.rs: VERDICT_PASS` sabiti kullanılır.
- **Ana ekran kapısı (K-UI-4).** Bir çıktı "öne çıkan" olarak yalnız `headline_gate` öyle diyorsa görünür; ön uçta elle liste yok.
- **Altın renk** yalnız modelimizin çıktısı (Safir paleti `#FFB648`); kural ve gerçekleşen asla altın değil. Renk tek başına
  bilgi taşımaz: her renkli değerin yanında sözcük ya da işaret (✓ ≈ × ◐) var.
- **Her ekranın altında** `DISCLAIMER` (tr.ts, değişmez) ve sürüm. Mod göstergesi üst barda (K-UI-12).
- **Bağımsız mod (K-UI-13).** Yeni arz girişi, Tahmin sonucu, Kayıtlarım, Ayarlar çalışır; Monitör, Analiz, Sicil
  "repo modu gerekli" boş durumu + Ayarlar bağlantısı; Model performansı gömülü `scores.json` ile geçmiş test satırlarını
  gösterir, D1 sonrası / kırılma / canlı bölümleri "repo modu gerekli" der.

## Yeni Rust komutları (salt okuma; `app/src-tauri/src/commands/sade.rs`, `sade_break.rs`)

| Komut | İmza | Okuduğu | Döndürdüğü (özet) |
|---|---|---|---|
| `monitor_view` | `() -> MonitorView` (repo modu; yoksa `REPO_MODE_REQUIRED`) | `registry/ipos.csv`, `registry/inputs/<T>.json` (yalnız `ipo_price_tl`, `shares_offered`), `registry/records/<T>/*` (etkin PREDICTION kaydı: `ceiling_hazard_v0.output.S`, `v1_5_h99.output.D5`), `registry/post_d1/<T>/*` (sayı), `registry/post_break/<T>/machine_*.json` (`streak.b`, `streak.L`, `streak.break_date`, `break_day.b_floor`, `models[break_floor_v0].output.F1/F2.p_floor`, `structural_zero_D10.impossible`, uyarı kodları), `data/outcomes/<T>.csv` (`h`, `session_date`, `close_raw`, `upper_limit_raw`, `ceiling_close`, `R_h`, `status`), `scores/scores.json` (`models[].live.rows[].class/status`), `scores/scores_break.json` (`live_break.denominator[].class`, `card.regime_warning`), `registry/push_proofs/` (sayı) | Arz satırları (D1 azalan), kapanış dizisi, D10 kapanışı ve `R_10` metni, gözlenen seri (`streak_view_in` ile aynı kural), kırılma günü ve türü, kayıttan beklenen ve medyan seri ile P(≥ 5) (`ceiling::row`, ceiling_display'in aynı yolu), ertesi gün taban (F1 p_floor), model başına sınıf, rejim etiketi; **sayımlar** (arz, seride, D10'da arz altında, tabanda kırılma, payda satırları, kayıt dosyaları, makine kayıtları, kanıt dosyaları, repo durumu); olay akışı (tarih, tür, arz, parametreler; yalnız dosyalardan) |
| `arz_view` | `(ticker: String) -> ArzView` (repo) | aynı dosyalar, tek arz | Başlık (arz fiyatı, D10, `R_10`, ilk işlem, seri L, arz adedi), zaman çizelgesi (listeleme öncesi kayıt + sınıflar; D1 sonrası kayıt sayısı; kırılma akşamı makine kaydı; D10), koridor (h = 1..10: kapanış, üst limit, referans, tavan bayrağı; kayıttaki `P_close_ceiling[h]`; kayıttaki V1.5 `price` D1/D3/D5/D10), getiri satırları (kayıttaki `return`, `p_up`, `price` + `R_h` metni), kayıt ve kanıt günlüğü |
| `break_view` | `(ticker: String) -> BreakView` (repo) | `registry/post_break/<T>/machine_*.json` (en erken = birincil), `scores/scores_break.json` (`models[0].card`, `live_break.denominator`, `retro_info[T]`), `models/break_floor_v0.json` (yalnız `horizons.F1/F2.p_floor.{C, coef, columns, intercept}`, `training.{n_F1, events_F1}`) | Makine kaydı alanları (b, D_b, L, b_floor, kapanış ve alt limit metni, `b_turnover_ratio`, `b_turnover_ln`, kırpılmış değer, z, p F1/F2, `@ZERO` p, yapısal sıfır `P`, `min10`, `impossible`, uyarı kodları, `exposure_class`), kart (`backtest_info`, `comparators_frozen`, `promotion`, `regime_warning`, eğitim n, varyant sayısı, model commit'i, push kanıtı zamanı), sınıf, karşılaştırıcılar (`retro_info[T].comparators`); katsayılar yalnız `sha256(models/break_floor_v0.json) == kayıttaki params_sha256` iken, değilse `status = "SHA_MISMATCH"` ve kart kapanır. Bülten dosya adları ve eğitim arz listeleri DÖNMEZ (hijyen) |
| `perf_view` | `() -> PerfView` (scores.json repo ya da gömülü; öbür dosyalar repo) | `scores/scores.json` (`models[].primary_cell`, `backtest.cells[]`, `live`), `scores/scores_post_d1.json` (`primary_cell`, `conditional_j1`), `scores/scores_break.json` (`card.backtest_info`, `promotion`, `live_break`), `scores/scores_oot.json` (`oot_pre_h99_all`, `post_d1_all` birincil hücreleri) | Fark satırları (alanlar dosyadaki gibi: `metric`, `rule_id`, `model_value`, `rule_value`, `diff`, `ci95`, `n`, `wins`, `losses`, `ties`, `label`, `verdict`; kırılma satırları `backtest_info`'dan, hükümsüz + `label`), üç terazi özeti (model başına geçmiş test hükmü, zaman-dışı hükmü ve n, canlı `n_live`/`n_late`/`n_scored`/`n_refused`), canlı satırlar (arz, D1, sınıf, durum; tavan: kayıt S'inden beklenen L (`ceiling::row`) ve gerçekleşen L; getiri: tahmin `prediction.D5.return`, gerçekleşen `realized.R.D5`; kırılma sınıfı), eşikler (`MIN_N_METRIC` 10, `MIN_N_VERDICT` 30) |
| `headline_gate` | `() -> HeadlineGate` | perf_view ile aynı dosyalar | Çıktı başına (model, çıktı, ufuk/k): dosya, `is_primary`, `featured`, birincil hücrelerin `verdict`'leri, `label` (kırılma), canlı n. Kural: `featured` ⇔ çıktı modelin önceden ilan edilmiş `primary_cell`'idir **ve** o hücrenin (`rule_ids`'teki her kural için) `label = "birincil"` satırlarının hepsi dosyada `verdict == VERDICT_PASS`; `break_floor_v0` için `featured` ⇔ `card.promotion.promoted` (etiket `promotion.label`). Dosya yoksa `featured = false`, `status = "NO_FILE"`. |
| `set_ui_view` | `(view: "SADE" \| "AYRINTILI") -> ConfigView` | `<app_data_dir>/config.json` | Ayarı yazar (başka alan değişmez) |
| `AppConfig.ui_view` | `#[serde(default)]` → yoksa `"SADE"` | — | Eski config dosyaları (alan yok) aynen okunur; geçersiz değer `"SADE"` sayılır; `set_config` geçersiz değeri `INVALID_ARGUMENT` ile reddeder |

Var olan komutlar aynen kullanılır: `predict_all`, `check_form`, `list_input_documents`, `read_input_document`,
`market20_via_python`, `ceiling_display`, `ceiling_summary`, `record_summary`, `record_ceiling`, `streak_view`,
`post_d1_view`, `post_d1_records`, `registry_view`, `read_record_json`, `scores_view`, `score_hints`, `app_info`,
`get_config`, `set_config`, `validate_repo`, kişisel kayıt komutları, sihirbaz komutları.

### Monitör ve perf_view'daki sabit liste (Rust, gösterim tanımı)

Ana ekranların gösterdiği çıktılar `sade.rs: HEADLINE_OUTPUTS` sabitindedir (hangi çıktının nerede durduğu; hükmü dosya verir):
`ceiling_hazard_v0` S (RPS); `v1_5_h99` return D1/D3/D5/D10 ve p_up D1/D3/D5/D10; `post_d1_hazard_v0` S_cond (RPS);
`break_floor_v0` p_floor F1/F2. Model performansının fark satırları = bu çıktıların birincil hücreleri + birincil olmayan
`v1_5_h99` p_up D10 için taban oran karşılaştırması (`rule_id = base_rate`, dosyada `label = keşif`) + kırılma
`backtest_info` iki satırı. Liste Rust'tadır; ön uçta model ya da hüküm listesi yok.

### `headline_gate`'in bugünkü dosyalarla beklenen çıktısı (orkestratörün K-UI-4 beklentisiyle)

Dosyalardan okundu (Python, salt okuma), kod yazılmadan:

| Model / çıktı | Birincil hücre (dosya) | Dosyadaki verdict | featured | K-UI-4 beklentisi |
|---|---|---|---|---|
| `ceiling_hazard_v0` S | RPS; `base_km_last10`, `base_km_expanding` (`label = birincil` iki satır) | geçiyor, geçiyor | **evet** | öne çıkar ✓ |
| `v1_5_h99` return D5 | MAE; `base_train_median` | geçiyor | **evet** | D5 getirisi öne çıkar ✓ |
| `v1_5_h99` p_up D10 | birincil değil (Brier `base_rate` hücresi `keşif`, ayırt edilemiyor) | — | hayır (≈) | D10 arz üstü olasılığı ≈ ✓ |
| `v1_5_h99` return D1/D3/D10, p_up D1/D3/D5 | birincil değil | — | hayır (≈) | (beklentide yok; aynı kural) |
| `post_d1_hazard_v0` S_cond | RPS; `ceiling_hazard_v0` (`scores_post_d1.json`; `conditional_j1.cells` boş, n_scored 0) | — | hayır (≈) | ≈ işaretli ✓ |
| `break_floor_v0` p_floor F1 | Brier; `PRODUCT_BREAK_FLOOR` (`scores_break.json`); `promotion.promoted = true`, aşama 1 | (hüküm alanı yok; `backtest_info.k1 = true`) | **evet**, etiket "ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = 0" | promotion ne diyorsa ✓ |
| `break_floor_v0` p_floor F2 | birincil değil | — | hayır (≈) | — |

## Panolar

### 1. Monitör (`Main`)

| Öğe | Veri kaynağı | SPEC kuralı | Durum |
|---|---|---|---|
| Üst bar: marka, sekmeler (Monitör, Analiz, Model performansı, Sicil, Kayıtlarım), kod arama, mod göstergesi, veri tarihi, yerel saat, "Yeni arz gir", Ayarlar | kabuk; veri tarihi `monitor_view.data_date` (outcomes'taki en geç `session_date`); saat yerel (gösterim) | §3 genel çerçeve, K-UI-12 | çizilir; kod arama arz koduna göre Analiz'i açar (yalnız `monitor_view` satırlarındaki kodlar) |
| Rejim şeridi "Fon krizi rejimi" | `scores_break.json` `card.regime_warning` (`tag`, `start_d1`) + satırların `regime_tags`; metin `tr.ts` | K-UI-12 (C4; D_1 ≥ 2026-09-16) | çizilir; tasarımdaki "130 fonu tasfiye, BIST100 −%16,65" sayıları dosyada yok → metinden çıkarıldı |
| Özet cümlesi "7 arz takipte; seride olan yok; NETGL ve BKRGY D10'da arz altında" | `monitor_view.counts` + satırlar | U25 | çizilir; "en güçlü seyir TKNKA +%122,48" → **çizilmez** (en büyük getiri seçimi; README §3) |
| Veri şeridi: Takipteki arz 7 (D1 aralığı) | `counts.n_ipos`, ilk/son D1 | — | çizilir |
| "Ortalama seri 3,43 / modelin ortalaması 3,67" | ortalama (U25) | U25 | **çizilmez** → "Seride: 0" sayımı |
| "D10'da arz altında 2/7" | `counts.n_d10_below` (`R_10` < 0, Rust karşılaştırması), `n_d10_known` | — | çizilir |
| "Tabanda kırılma 3/7; üçünde ertesi gün de taban" | `counts.n_break_floor` (`b_floor = 1`) / `n_break_known` | — | ilk kısım çizilir; "ertesi gün de taban" → **çizilmez** (sonuç dosyasında alt limit yok; etiket yalnız skor satırında, RETRO'da yok) |
| "Canlı sicil 0/30 sayılan arz yok" | — | kural 3 | **sayım biçimi değişti**: model başına canlı n "Üretimdeki modeller" panelinde (v1_5_h99'da 1); tek toplam sayı terazileri karıştırır |
| "Üretimdeki model 4/30; 26'sı ölçüt ve arşiv" | `headline_gate` çıktılarının model sayısı; toplam model sayısı `app_info` | — | "4" çizilir; "/30" → gömülü + iki dizin toplamı ön uçta toplama ister → **çizilmez** |
| Arz takip tablosu: Arz, şirket, ilk işlem, arz fiyatı, D10, arza göre | `monitor_view.rows[]` (`ipo_price` metin, `d10_close` metin, `r10` metin) | §4 biçim | çizilir |
| 10 seans kıvılcım çizgisi | `rows[].days[].close_raw` | SVG `render/svg.ts` | çizilir (yeni `sparkPath` koordinat fonksiyonu) |
| Seri | `rows[].streak` (`j_observed`, `broken`) | §3g | çizilir |
| "Listeleme öncesi tahmin: Beklenen / medyan, 5+ gün" | `rows[].ceiling` (`expected_l`, `median_l`, `p_ge5`; kayıttaki S'ten `ceiling::row`) | K-UI-4 (featured ise altın, değilse ≈) | çizilir |
| "Kırılma: k. gün taban / taban üstü" | `rows[].break_info` (`b`, `b_floor`) | — | çizilir |
| "Kırılma akşamı: ertesi gün taban" | `rows[].break_info.p_floor_f1` | K-UI-4 (break promotion) | çizilir; `structural_zero_D10.impossible` → "D10'da arz altına inemez" rozeti (TKNKA) |
| "Kayıt" sütunu (geç kayıt; getiri canlı) | `rows[].classes[]` (scores.json canlı satırları, model başına) + `break_class` | kural 3 | çizilir, model başına |
| Filtre "Tümü 7 / Seride 0 / Kırılma akşamı 0" | sayımlar | — | "Tümü" ve "Seride" çizilir; "Kırılma akşamı" = bugün kırılma akşamında olan arz (seri dün bozulmuş, ertesi seans yok) → dosyalardan "bugün" belirlenemez → **çizilmez** |
| Seçili arz paneli: son kapanış, arza göre, kıvılcım, seri (model medyanı / gerçek L), kırılma akşamı ertesi gün taban, D5 getiri (tahmin / gerçek), "Analizi aç" | `rows[]` (`ceiling.median_l`, `streak`, `break_info`, `d5.predicted`, `d5.realized`) | K-UI-4 | çizilir |
| "Gerçekleşen, kırılmadan sonra 7 seans taban" | alt limit gerekir | — | **çizilmez** (outcomes'ta alt limit yok) |
| Üretimdeki modeller: geçmiş test, eski dönem, canlı | `perf_view.scales[]` (+ `headline_gate`) | kural 3 (asla toplanmaz) | çizilir |
| Olay akışı | `monitor_view.events[]` (kırılma günleri: makine kaydı; D10 kapanışları: outcomes; model dondurma: `scores_break.json` `card.frozen_at` + push kanıtı; rejim başlangıcı: `regime_warning.start_d1`) | — | çizilir; "Sistem: kırılma akşamı canlı skorlaması açıldı" (commit zamanı) → **çizilmez** (git log gerekir) |
| Sayı sayma animasyonu | — | U25 | **çizilmez** |

### 2. Yeni arz girişi (`Giris`, `Giris_pre`)

| Öğe | Veri kaynağı | SPEC kuralı | Durum |
|---|---|---|---|
| Aşama (talep toplama öncesi / sonrası) | `STAGES` (tr.ts), `check_form(stage, fields)` | §3a | çizilir |
| Arz kodu | form durumu (`tickerLabel`) | §3a | çizilir |
| Sicildeki girdi belgesinden doldur (seçim + Doldur) | `list_input_documents`, `read_input_document` | §3a (salt okuma kopya) | çizilir |
| Gruplar: SPK bülteni (8), KAP sonuçları (8), BIST duyuruları (4), Piyasa | `FIELDS` (tr.ts) grup eşlemesi (yeni dışa aktarım), alan değerleri form durumunda | §3a | çizilir; grup başına "dolu / toplam" → sayım ön uçta (form durumu, model sayısı değil) → yalnız eksik zorunlu alanlar listelenir |
| Alan: etiket, sağa hizalı değer, birim eki, okunur tekrar ("312,5 milyon pay", "17 Eylül 2026, Perşembe"), geçerlilik işareti | `check_form.notes/requirements/suggestions`; okunur tekrar `format.ts` yeni biçimleyici (`readableCount`: bölme biçimlendirmedir; `readableDate`: ay adı `tr.ts`) | §3a, §4 | çizilir; haftanın günü → tarih hesabı → **çizilmez** |
| Denetim paneli: zorunlu / isteğe bağlı alanlar, ilerleme çubuğu | `check_form.requirements` + form durumu | §3a | eksik zorunlu alan listesi çizilir; oran çubuğu → **çizilmez** |
| "Taban arzın bileşimi bedelli %71,4 / ortak %28,6" | oran (bölme) | U25 | **çizilmez** |
| Planlanan yapı ve gerçekleşen dağıtım özdeşlikleri (ID-A/B/C, 2 = 4 + 5 + 6) | `check_form.notes` (`PB_IDENTITY`, `SHARES_SUM_MISMATCH`) | §3a | çizilir: özdeşlik başına "tutuyor / tutmuyor" (Rust notundan) ve iki taraf alan değerleriyle; toplama ön uçta yapılmaz |
| "Modellerin göreceği değerler" (f1..f6, pb1..pb4) | özellikler `predict_all`'dan önce Rust komutuyla gelmiyor (`pb_v0.output.features` yalnız tahminden sonra) | U25 | **çizilmez** (öneri: ayrı Rust komutu) |
| Piyasa: Hesapla / Elle gir / Boş bırak; 20 seans getirisi, S0/S20 tarih ve kapanışları | `market20_via_python` (`record.f6`, `S0_date`, `S20_date`, `close_S0`, `close_S20`) | §3a.2 | çizilir |
| "Toplam talep katı nasıl yazılır?" | `F3_DEFINITION` (tr.ts) | §3a.1 | çizilir (açılır) |
| Tahmin et / Resmi kayıt için hazırla | `predict_all`; sihirbaz (eski ekran, sade kabukta) | §3a, §3e | çizilir |
| "Ayrıntılı görünüme geç" | kabuk | K-UI-1 | çizilir (eski Girdi ekranı) |

### 3. Tahmin sonucu (`Sonuc`)

| Öğe | Veri kaynağı | SPEC kuralı | Durum |
|---|---|---|---|
| Başlık "<T> için tahmin", aşama ve kaynak cümlesi, Girdileri düzenle, Resmi kayıt için hazırla | `store.results` (`tickerLabel`, `stage`, `source`) | §3b, §3c | çizilir |
| Manşet cümlesi (beklenen seri, en olası yol, D5 getirisi) | `ceiling_summary(runs, j, null, t)` öne çıkan satır (`expected_l`, `mode_l`, `mode_break_day`) + `v1_5_h99` D5 `return` (predict_all); yalnız `headline_gate.featured` çıktılar | K-UI-4 | çizilir |
| Kaç gün tavan: büyük sayı, medyan, P(L = l) çubukları (l = 0..10, en olası vurgulu) | `ceiling_display(S, 0, ipo)` öne çıkan satır `P_L`, `expected_l`, `median_l`, `mode_l` | §3b grup B | çizilir |
| Model / basit kural tablosu (beklenen, medyan, 3+, 5+, 10) | `ceiling_summary` satırları (`FEATURED`, `RULE` `base_km_last10`) | §3b | çizilir |
| "Geçmiş testte model bu kurala göre hatasını yaklaşık %25 azalttı" | oran | U25 | **çizilmez** → iki değer yan yana (`model_value`, `rule_value`) + dosyadaki verdict |
| Seri hesaplayıcı: 0–9 düğmeleri | form durumu (j) | K-UI-8 | çizilir |
| D1–D10 şeridi (geçmiş günler, yarın) | j (seçim); senaryoda bülten yok | K-UI-8 | çizilir (beyan şeridi yok, U52 ayrıntılıda) |
| Yarın da tavan, bozulma, beklenen kalan gün, koşullu medyan, en az 5 gün, 10 gün | `ceiling_display(S, j)` öne çıkan satır `cond.s_cond[j]` (yarın da tavan = P(L ≥ j+1 \| L ≥ j)), `cond.p_break_next`, `cond.expected_remaining`, `cond.median_l`, `cond.s_cond[4]`, `cond.s_cond[9]`; aynı değerler `ceiling_summary.rows[FEATURED].cond` | K-UI-8, EK 1 | çizilir; tanımsızsa "—" |
| Koşullu ve koşulsuz eğri | `cond.s_cond` ve `S` (ceiling_display) | K-UI-8; koordinat `svg.ts` | çizilir |
| D1 sonrası satırı | senaryoda yok → tasarımdaki not (`COND.postD1Scenario`) | K-UI-8 | çizilir (not) |
| Getiri tahmini: D1/D3/D5/D10 getiri, fiyat, arz üstü olasılığı, geçmiş test işareti | `predict_all` `v1_5_h99.output.Dh.{return, price, p_up}`; işaret `headline_gate` (D5 birincil ✓, öbürleri ≈) | §3b, K-UI-4 | çizilir; çubuk genişliği `svg.ts` |
| "Geçmiş testte 5. gün tahmininin tipik hatası 0,22 (87 arz)" | `score_hints` `model_value` (MAE) ve n | §3b | çizilir (dosyadaki değer) |
| Rejim uyarısı paneli | `RESULTS.regime` (tr.ts, var) | U23 | çizilir |
| Bu tahminin dayanakları: uyarı, TÜFE, XU100, girdi kaynağı | `ceiling_summary.tufe`, `store.results.f6`, model uyarıları | §3b | çizilir |
| "Ayrıntılı görünüm: bütün modeller ve basit kurallar" | kabuk | K-UI-1 | çizilir |
| Kişisel kayıt olarak sakla | `save_scenario` | §3f | çizilir |

### 4. Analiz (`Arz`)

| Öğe | Veri kaynağı | SPEC kuralı | Durum |
|---|---|---|---|
| Başlık: kod, şirket, arz fiyatı, D10 kapanış, arza göre, ilk işlem, tavan serisi, arz adedi | `arz_view` | §4 | çizilir |
| Rozetler: rejim, kayıt sınıfı (model başına) | `arz_view.classes`, `regime_tags` | K-UI-12 | çizilir |
| Zaman çizelgesi (listeleme öncesi, ilk gün akşamı, kırılma akşamı, D10) | `arz_view.timeline` | — | çizilir |
| Fiyat koridoru: kapanış çizgisi, tavan/taban kapanış işaretleri, arz fiyatı çizgisi, kırılma günü işareti | `arz_view.corridor` (`close_raw`, `ceiling_close`), `ipo_price` | — | çizilir; günlük ±%10 bant mumları → alt limit outcomes'ta yok → **yalnız üst limit işareti** çizilir |
| Getiri modelinin beklentisi (kesikli) | kayıttaki `v1_5_h99.output.Dh.price` | — | çizilir (D1, D3, D5, D10) |
| "Model: o gün tavan kapanış olasılığı" satırı | kayıttaki `ceiling_hazard_v0.output.P_close_ceiling` | §3b (ikincil) | çizilir |
| Gerçekleşen kapanış satırı (tavan / tavan değil) | `ceiling_close` | — | çizilir; "taban" yazımı → alt limit yok → "tavan değil" yazılır |
| İşlem adedi çubukları | sonuç dosyasında hacim yok | — | **çizilmez** (README §3) |
| Kaç gün tavan? (kayıttan) | `record_summary` + `record_ceiling.display` | U38 | çizilir; "yeşil halka gerçekleşen seri" → `streak_view.j_observed` |
| Seri hesaplayıcı (resmi görünüm) | `record_summary(T, file, j, jObserved)`, `record_ceiling(T, file, j)` (`display.rows[].cond`), `streak_view(T)` (`j_observed`, `broken`, günler) | K-UI-8, U38 | çizilir; "Gözlenene dön" var; beyan yok |
| Bültende gözlenen seri şeridi | `streak_view.days[].file` | §3g | çizilir |
| D1 sonrası satırı | `post_d1_view(T, j, null)` (kayıt varsa), yoksa tasarımdaki not | K-UI-8 | çizilir |
| Kırılma akşamı kartı | `break_view` | EK 5 içeriği (makine kaydından), K-UI-4 | çizilir; katsayılar sha denetimli |
| Kırılma kartı "Gerçekleşen: taban, taban" | etiket yalnız skor satırında; RETRO'da yok | kural 6 | **çizilmez** |
| Kırılma kartında olasılık çubukları (model, tabanda kırılanların oranı, bütün kırılmalar, ürün) | `break_view` (`p_floor`, `comparators.base_floor_by_type.F1`, `@ZERO.F1`, `PRODUCT_BREAK_FLOOR.status`) | — | çizilir |
| Özellik tablosu (ham değer, girdi, katsayı) | `break_view.features`, `coef` | — | çizilir (katkı = katsayı × z hesaplanmaz; yalnız katsayı) |
| Getiri: tahmin ve gerçekleşen (nokta grafiği + tablo) | `arz_view.returns` (kayıt `return`, `p_up`; `R_h` metni), sınıf | §3b, kural 3 | çizilir |
| Kayıt ve kanıt günlüğü | `arz_view.log` | — | çizilir; "KAP arz adedi kaynak belge sabitlendi" (MANIFEST zamanı) → `read_source_manifest` gerekir → **çizilmez**; işlem adedi (lot) → **çizilmez** |

### 5. Model performansı (`Dogruluk`)

| Öğe | Veri kaynağı | SPEC kuralı | Durum |
|---|---|---|---|
| Veri şeridi: donmuş model ve kural 30 | `app_info` (gömülü + iki dizin) toplamı | U25 | **çizilmez** (toplama) → "Üretimde 4" ve aralık tanımı kalır |
| Keşif varyantı 2.054 | `experiments/log.jsonl` sayımı (uygulama okumuyor) | — | **çizilmez** |
| Aralık yöntemi "Blok …, ilk işlem ayı blokları, 4.000 tekrar" | `scores.json` hücre alanı (adı Rust/TS taramasında yasaklı sözcük) | U25 taraması | **çizilmez** (`ACCURACY` panelinde ayrıntılı görünümde var) |
| Canlı sicil 0/30 | `perf_view.scales[].live` | kural 3 | model başına çizilir |
| "Model, basit kuraldan daha iyi mi?" fark satırları: soru, model id, ölçü, kural, model ve kural değeri, fark, %95 aralık, kazanç/kayıp/eşit, hüküm | `perf_view.rows[]` | §8, U13–U22 | çizilir; hüküm hücresi dosyadaki `verdict`, sade açıklama ayrı satır |
| Okuma rehberi (nokta, çizgi, sıfır) | `tr.ts` | K-UI-5 | aynen çizilir |
| Aralık grafiği (nokta + çizgi + sıfır çizgisi) | `diff`, `ci95` | `svg.ts` koordinat | çizilir |
| "model hatası %25 daha düşük" | oran | U25 | **çizilmez** → iki değer yan yana |
| "6 soruda model daha iyi, 2 soruda fark net değil" | sayım (verdict'e göre) | — | çizilir: `perf_view.counts` (Rust sayar) |
| D1 sonrası geçmiş test satırları (−0,0512, −0,0105) | hiçbir skor dosyasında yok | kural 6 | **çizilmez** |
| Kalibrasyon grafiği (kırılma) | skor dosyalarında yok | — | **çizilmez** |
| Üç ayrı sınav: geçmiş test, eski dönem, canlı sicil | `perf_view.scales[]` | kural 3 | çizilir; asla toplanmaz |
| Canlı sicil satırları (arz, ilk işlem, kaç gün tavan sınıfı/beklenen/gerçek, D5 sınıfı/tahmin/gerçek, kırılma sınıfı) | `perf_view.live_rows[]` | kural 3, §8 (n < 10 yalnız satır tablosu) | çizilir |
| Araştırma arşivi | `scores.json` dışı modeller; metinler | — | **çizilmez** (ayrıntılı görünümün Doğruluk paneli her modeli listeler; bağlantı verilir) |

### 6. Sicil (`Sicil`)

| Öğe | Veri kaynağı | SPEC kuralı | Durum |
|---|---|---|---|
| Veri şeridi: payda (kayıtlı / kapsam dışı), listeleme öncesi kayıt, D1 sonrası kayıt, kırılma akşamı kaydı, zaman kanıtı dosyası, repo durumu | `monitor_view.counts` (`n_payda`, `n_frozen`, `n_out_of_scope`, `n_pre_listing_records`, `n_post_d1_records`, `n_machine_records`, `n_push_proofs`, `registry_status`) | kural 2 | çizilir |
| Kayıtlı arzlar tablosu (arz, şirket, ilk işlem, listeleme öncesi kayıt sayısı, D1 sonrası, kırılma akşamı, Aç) | `registry_view.tickers[]` + `monitor_view.rows[].break_info` | §3e | çizilir |
| Kapsam dışı satırlar | `monitor_view.counts.n_out_of_scope` | kural 2 | sayı çizilir |
| Kayıt künyesi (sekmeler: listeleme öncesi, kırılma akşamı, D1 sonrası) | `registry_view.tickers[].records[]` (dosya, kayıt zamanı, push kanıtı, ekleyen commit, girdi belgesi sha, INDEX sha, git HEAD), `break_view` (makine kaydı), `post_d1_records` | §3e, §3g | çizilir |
| Sınıf satırı ("Kaç gün tavan: geç kayıt") | `monitor_view.rows[].classes` | kural 3 | çizilir |
| D1 sonrası kayıt sihirbazı, Ham kayıt (JSON), İptal kaydı düş | eski ekran (sihirbaz, iptal) ve `read_record_json` | K-UI-11 | sihirbaz ve iptal eski ekrana bağlanır (sade kabuk içinde) |
| Yeni resmi kayıt | eski dondur sihirbazı | K-UI-11 | çizilir (sade kabukta) |

### 7. Resmi kayıt sihirbazı (`Dondur`) ve 8. D1 sonrası kayıt (`D1Sonrasi`)

| Öğe | Veri kaynağı | SPEC kuralı | Durum |
|---|---|---|---|
| Adım içerikleri, komutlar, metinler | eski `screens/registry.ts` (`openWizard`, `mode = "wizard"` / `"post_d1"`) aynen | K-UI-11 | eski ekran sade kabuğun içinde, `.sade` kökü altında var olan sınıflar yeni CSS'le |
| Adım göstergesi (✓, etkin, bekleyen) | kabukta; etkin adım eski ekranın DOM'undan okunamıyor (render dosyaları değişmez) | K-UI-11 | adım listesi çizilir (`FREEZE.steps`, `POST_D1.steps`); etkin adım işareti **çizilmez** |
| "Akılda tut" paneli | `tr.ts` metni | — | çizilir |

### 9. Kayıtlarım (`Kayitlarim`)

| Öğe | Veri kaynağı | SPEC kuralı | Durum |
|---|---|---|---|
| Liste (başlık, oluşturma, aşama, model kümesi, Aç, Dışa aktar, Sil) | `list_scenarios`, `load_scenario`, `export_scenario`, `delete_scenario`, `export_all_scenarios` | §3f | çizilir |
| Boş durum ve "Yeni arz gir" | — | §3 | çizilir |
| "Bir senaryo saklandığında liste böyle görünür" örnek satırı | örnek | README §5 | **çizilmez** (uygulama gerçek kayıtları listeler) |

### 10. Ayarlar ve Hakkında (`Ayarlar`)

| Öğe | Veri kaynağı | SPEC kuralı | Durum |
|---|---|---|---|
| Repo klasörü, Klasör seç, Python yolu, skor kaynağı, Kaydet, Doğrula, Repoyu kaldır | `get_config`, `set_config`, `validate_repo` | §6 | çizilir |
| **Görünüm: Sade / Ayrıntılı** | `set_ui_view` | K-UI-1 | çizilir (tasarımda yok; görev gereği) |
| Doğrulama listesi | `RepoCheck.checks` | §6 | çizilir |
| Hakkında: sürüm, bütünlük, listeleme öncesi / D1 sonrası modeller ve sha, gömülü skor kopyası, gömülü TÜFE | `app_info` | §1.4 | çizilir; "Kırılma akşamı modelleri 2" → gömülü değil (EK 5 portu ayrı görev) → **repo dizini olarak çizilmez**; "Gömülü modellerin tam listesi" → ayrıntılı görünümdeki Hakkında |

### 11. Stil rehberi (`Stil`) ve 12. Palet seçenekleri (`Palet`)

| Öğe | Veri kaynağı | Durum |
|---|---|---|
| Safir belirteçleri (zemin, pano, metin, model altını, yukarı/aşağı, eylem, kural grisi, rejim) | README tablosu | `app/src/sade/sade.css` `:root` değişkenleri olarak |
| Yazı tipleri (IBM Plex Sans / Condensed / Mono) | `@fontsource/*` (devDependencies, K-UI-9) | Vite paketler; ağ yok |
| Hareket (çizgi çizilmesi, çubuk büyümesi, belirme; `prefers-reduced-motion`) | CSS | K-UI-10; sayı sayma yok |
| Öbür paletler | — | çizilmez (uygulanan: Safir) |

## Tasarım ↔ uygulama farkları — ilk liste

| # | Öğe | Neden | Ne yapıldı |
|---|---|---|---|
| F1 | "Ortalama seri 3,43 / modelin ortalaması 3,67" | ortalama (U25) | "Seride" sayımı |
| F2 | "model hatası %25 daha düşük" (Sonuç, Model performansı) | oran (U25) | model ve kural değeri yan yana + dosyadaki verdict |
| F3 | Monitör özet cümlesinde "en güçlü seyir" | seçim/sıralama ölçütü tasarıma ait | yok |
| F4 | "BIST kapalı" göstergesi | takvim durumu dosyadan değil | yok; veri tarihi kalır |
| F5 | Analiz işlem adedi çubukları | sonuç dosyasında hacim yok | yok |
| F6 | Kalibrasyon grafiği ve D1 sonrası geçmiş test satırları | skor dosyalarında yok | yok |
| F7 | Sayı sayma animasyonu | ön uç aritmetiği (U25) | yok |
| F8 | Rejim şeridindeki piyasa sayıları (fon sayısı, BIST100 Eylül getirisi) | dosyada yok | rejim metni `tr.ts` + `start_d1` |
| F9 | "Tabanda kırılma: üçünde ertesi gün de taban", "kırılmadan sonra 7 seans taban", kırılma kartı "Gerçekleşen: taban, taban" | outcomes'ta alt limit yok; etiket yalnız skor satırında | yok |
| F10 | Monitör "Canlı sicil 0/30" tek sayı | modeller arası toplam terazileri karıştırır (v1_5_h99 canlı n = 1) | model başına canlı n |
| F11 | "Üretimdeki model 4/30", "Donmuş model ve kural 30", "Keşif varyantı 2.054" | toplam ve günlük sayımı uygulamada yok | "4" kalır, ötekiler yok |
| F12 | Filtre "Kırılma akşamı 0" | "bugün kırılma akşamı" dosyalardan belirlenemez | yok |
| F13 | Giriş: "Taban arzın bileşimi" yüzdeleri, ilerleme çubuğu, grup "8/8" sayaçları | oran ve sayaç (ön uç) | eksik zorunlu alan listesi |
| F14 | Giriş: "Modellerin göreceği değerler" (f1..f6, pb1..pb4) | tahminden önce özellikleri veren Rust komutu yok | yok (öneri: ayrı Rust komutu) |
| F15 | Giriş: tarihin haftanın günü | tarih hesabı | gün-ay-yıl okunur tekrar |
| F16 | Analiz koridorunda ±%10 bant mumları | alt limit yok | kapanış çizgisi + üst limit işareti |
| F17 | Kayıt günlüğünde KAP belge sabitleme ve işlem adedi satırları | MANIFEST/hacim okunmuyor | yok |
| F18 | Aralık yöntemi kutusu ("Blok …") | alan adı U25 taramasında yasaklı sözcük | yok (ayrıntılı görünümde) |
| F19 | Araştırma arşivi | metinler skor dosyasında yok | ayrıntılı görünüme bağlantı |
| F20 | Olay akışında "Sistem: canlı skorlama açıldı" | git log | yok |
| F21 | Sihirbaz adım göstergesinde etkin adım | eski render dosyaları değişmez, durum ön uçta okunamaz | adım listesi var, etkin işaret yok |
| F22 | Hakkında "Kırılma akşamı modelleri 2 899cf90c" | modeller gömülü değil (EK 5 portu ayrı) | yok |
| F23 | Kayıtlarım örnek satırı | örnek | gerçek liste |
| F24 | Sayı biçimi (`0,499`, `3,28`, `+%25,52`) | SPEC_APP §4 + format.ts | `%50`, `3.3`, `+%25.5` |

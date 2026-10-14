# Ajan D — Sade görünüm: sayı → etiket zinciri denetimi

Repo: /Users/ahmet/Desktop/BorsAi @ ee3796d (salt okunur; dosya değiştirilmedi, test koşulmadı, ağ yok).
Kaynaklar: app/src/sade/render/*.ts, app/src/sade/screens/*.ts, app/src/render/format.ts, app/src/render/accuracy.ts, app/src/i18n/tr.ts,
app/src-tauri/src/commands/{sade,sade_break,registry,scores,scenario,config,models,form}.rs, fikstürler app/tests/fixtures/ui/sade_*.json,
skor dosyaları scores/{scores,scores_post_d1,scores_break,scores_oot}.json (yalnız yapı ve hüküm alanları okundu).

İşaretler: [P] = ekrandaki metin/sayı yanıltıcı (problem); [K] = kodda gizli (bugün görünmez, veri değişince görünür) tutarsızlık;
[B] = bilgi/öneri. [ÖLÇTÜM] = dosya/fikstür/komut çıktısıyla doğrulandı; [ÇIKARIM] = kod okumasından çıkarım.
Lider denetçinin bulduğu (a) "Üretimdeki model 4", (b) birincil olmayan ufuklarda "≈ fark net değil", (c) approxTip metni burada tekrarlanmadı.

---

## 1. Bulgular (yanıltıcı etiketler önce)

### F1 [P][K] ORTA (gizli hâli KRİTİK) — post_d1 modelinin "Geçmiş test" sütunu canlı ölçekten besleniyor
- Yer: app/src-tauri/src/commands/sade.rs:1054-1056 (`gate_entry`: scores_post_d1.json için `cells_ptr = "/conditional_j1/cells"`), :1385-1386 (`ScaleSummary.backtest_verdicts = entry.verdicts`); ekran: app/src/sade/render/perf.ts:87-91 ("Üç ayrı sınav" → sütun "Geçmiş test"), app/src/sade/render/monitor.ts:138-147 ("Üretimdeki modeller" → "Geçmiş test").
- Beklenen: "Geçmiş test" sütunu geçmiş test (backtest) ölçeğinden bir hüküm göstermeli ya da "test dosyada yok" demeli.
- Gerçek [ÖLÇTÜM]: scores_post_d1.json'da `post_d1_hazard_v0` modelinin tek bloğu `conditional_j1`, `scale = "live_post_d1"`, `n_scored = 0`, `n_live = 0`, `n_retro = 7`, `cells = []`; `backtest` bloğu yok. Fikstür sade_gate.json: post_d1 girişi `is_primary = true`, `verdicts = []`, `featured = false`. Ekranda satır "Yarın tavan bozulur mu | — | ✓ geçiyor (eski dönem, 104 arz) | 0 sayılan, 0 geç kayıt / 7 geçmişe dönük" olur: izleyici modelin geçmiş testi yokmuş gibi okur.
- Gizli hâli [ÇIKARIM]: `conditional_j1` canlı aşama bloğudur (denominator sınıfları RETRO). Canlı hücreler oluşunca (n_scored ≥ 10) aynı kod bu CANLI hücrelerin `verdict`'ini "Geçmiş test" sütununa ve kapı (`featured`) kararına taşır → üç terazi kuralı (CLAUDE.md kural 3) ekranda ihlal edilir; üstelik Monitör'deki `T.prodNote` "Üç sınav ayrı tutulur, toplanmaz" cümlesinin altında.
- Öneri: post_d1 için backtest kaynağı yoksa `backtest_status = "NO_TEST"` ve metin "test dosyada yok"; canlı blok hücreleri yalnız "Canlı sicil" sütununa.

### F2 [P] ORTA — Kırılma satırlarında "✓" işareti hüküm değilken hüküm gibi
- Yer: app/src/sade/render/perf.ts:57-59 (verdict null → `P.noVerdict` + `promotionCell`), app/src/sade/render/common.ts:109-113 (`promotionCell`: `featured` ise `<span class="mark-pass">✓</span>`), app/src/i18n/tr.ts:1439-1443 (`VERDICT_MARK[geçiyor] = "✓"`, aynı işaret).
- Beklenen: "hüküm alanı yok" satırında "geçiyor" ile aynı işaret/renk kullanılmamalı; terfi (promotion) hüküm değil.
- Gerçek [ÖLÇTÜM] (sade_perf.json): iki `break_floor_v0` satırı `verdict = null`, `label = null`, `file_label = "backtest'te geçiyor (tasarıma maruz)"`, `scale = backtest_break`, n=69 (21 ay). Ekran hücresi: "hüküm alanı yok" + "✓ ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = 0". Aynı tabloda `scale = backtest` (n=87, farklı kohort) satırlarıyla yan yana; `scale`/`file_label` sade görünümde hiç yazılmıyor (`P.breakLabel` anahtarı tanımlı ama render'da kullanılmıyor). "Karşılaştırma 6" sayacı bu iki satırı "2 satır hükümsüz" diye sayıyor (doğru), ama tablo başlığı "Geçmiş test" tek kohort ima ediyor.
- Ayrıca sütun "Model daha iyi olan arz" bu satırlarda `n = 69 (21 ay)` gösteriyor (perf.ts:67 `nOnly`): başlık kazanç sayısı, hücre örnek sayısı.
- Öneri: "✓" yerine nötr işaret; satıra "yakın dönem kohortu, n=69" ve `file_label`; ya da kırılma satırları ayrı alt tablo.

### F3 [P] ORTA — Fark çubukları farklı birimleri tek eksende çiziyor
- Yer: app/src/sade/render/perf.ts:21-36 (`scaleRange`: bütün satırların diff/ci95'inden tek min/max), :65 (`intervalBar(..., min, max)`); başlık `P.colInterval = "Fark ve %95 aralık"` (birimsiz).
- Beklenen: RPS (dağılım hatası), MAE (getiri puanı) ve Brier farkları karşılaştırılamaz; ortak eksen görsel karşılaştırma ima eder.
- Gerçek [ÖLÇTÜM]: eksen −0.252 (kırılma Brier) … +0.02; RPS satırları −0.05 civarı, MAE −0.084 (= 8.4 puan). Kırılma çubuğu en uzun görünür; MAE satırı "puan" olarak yazılır ama çubuk ham 0.084 ile çizilir.
- Öneri: metrik başına eksen ya da çubuğu kaldırıp yalnız sayı+aralık.

### F4 [P] ORTA — Giriş "Özdeşlikler" notu SUM için yanlış
- Yer: app/src/i18n/tr.ts (SADE.giris.identityNote): "Tutmayan bir özdeşlik bu alanı kullanan modelleri durdurur; satır kırmızı görünür."; app/src/sade/render/giris.ts:140-141 (SUM için de `× tutmuyor`, `mark-fail`).
- Gerçek [ÖLÇTÜM]: form.rs:225 `note("shares_offered", "SHARES_SUM_MISMATCH", "warn")` — seviye warn; FORM_NOTE_TEXT.SHARES_SUM_MISMATCH: "2 ≠ 4 + 5 + 6 …; RET değil, DATA_NOTES §4". Yalnız ID-A/B/C `PB_IDENTITY` error (form.rs:248).
- Öneri: not "ID-A/B/C tutmazsa PB modelleri durur; SUM uyarıdır" olmalı; SUM satırı sarı/uyarı işaretiyle.

### F5 [P] ORTA — Canlı sicil metinleri sabit cümleyle veri olgusu ileri sürüyor
- (i) app/src/i18n/tr.ts:1963 `P.rowsNote`: "D1 sonrası ve kırılma akşamı modelleri bu arzlardan sonra donduruldu; onlarda sayılan arz yok." — i18n sabiti. Bugün doğru [ÖLÇTÜM: 7 satırda post_d1/break sınıfı RETRO]; yeni bir arz listelenince (post_d1 LIVE ya da break MACHINE_SEQUENCED olabilir) cümle yanlışlanır ama ekranda kalır [ÇIKARIM].
- (ii) tr.ts:1940 `P.liveSub(v)`: "Her aşama 30 sayılan arzda değerlendirilir" ve ilerleme "n / 30" (perf.ts:107-117): 30 = `MIN_N_VERDICT` (scores.rs:124), backtest hüküm eşiği. Canlı blokta `verdict`/`min_n` alanı yok (scores.json `live`: verdict null, min_n null [ÖLÇTÜM]). Canlı terazinin eşiği dosyadan değil sabitten; cümle bunu canlı sicilin kuralı gibi sunuyor.
- Öneri: (i) cümleyi satır sınıflarından türet; (ii) "hedef n = 30 (backtest hüküm eşiğiyle aynı sabit)".

### F6 [P] DÜŞÜK — Hüküm eşiği alt metni eksik bant bırakıyor
- Yer: tr.ts:1904 `stripMinNSub(m=10, v=30)` → "n ≥ 30 hüküm, n < 10 yalnız satır". scores.rs:254/284: n_scored < 10 iken hücre dosyada hiç yer almaz (bütünlük kuralı), "yalnız satır" değildir; 10 ≤ n < 30 bandı (ölçü var, hüküm "yetersiz örnek") anlatılmıyor.

### F7 [P] DÜŞÜK — Sicil künyesinde geç kayda yeşil "✓ push kanıtı var"
- Yer: app/src/sade/render/sicil.ts:66-68 (`mark-pass` ✓ + `S.proofYes(tarih)`). NETGL vb. ceiling sınıfı LATE_RECORD iken kanıt var (22.09.2026, D1 17.09.2026'dan sonra) [ÖLÇTÜM]. ✓ "kanıt geçerli/zamanında" diye okunur; sınıf satırı üstte "geç kayıt" dese de işaret çelişir.
- Öneri: kanıt tarihi D1'den sonraysa nötr işaret + "(ilk işlem gününden sonra)".

### F8 [P] DÜŞÜK — Gruplanmış RECORD olayının sınıfı yalnız tavan modelinden
- Yer: sade.rs:748 (`e.class = classes[CEILING_MODEL].class`), tr.ts `event.RECORD`. Ekran: "7 arz için listeleme öncesi resmi kayıt yazıldı (geç kayıt)". NETGL için v1_5_h99 sınıfı LIVE [ÖLÇTÜM]; aynı kayıt bir model için canlı, olay satırı "geç kayıt" der. Ayrı LEGACY_RECORD olayı telafi ediyor ama okur ikisini bağlamayabilir.

### F9 [P] DÜŞÜK — Sicil "Payda" alt metni toplamı kapatmıyor
- Yer: sicil.ts:28 `S.paydaSub(n_frozen, n_out_of_scope)` → "7 kayıtlı, 19 kapsam dışı" (26 = 7 + 19 bugün [ÖLÇTÜM]); `n_skipped` gösterilmiyor → atlanan arz olduğunda parçalar paydaya eşit olmaz [ÇIKARIM]. "kayıtlı" = durum FROZEN; CLAUDE.md kural 2'deki "atlandı" satırı sade sicilde görünmez.

### F10 [P] DÜŞÜK — Boş alan sıfır gibi yazılıyor
- Yer: perf.ts:95 `P.liveLine(n_live ?? 0, n_late ?? 0)`. `break_floor_v0.live_break.n_late = null` (alan yok) [ÖLÇTÜM] → "0 sayılan, 0 geç kayıt". Null ile 0 ayrımı kayboluyor.

### F11 [P] DÜŞÜK — "Tabanda kırılma … seri taban kapanışıyla bozuldu" seri olmayan arzları da sayıyor
- Yer: sade.rs:868-869 (`n_break_floor` = `b_floor == 1` sayısı), tr.ts `stripFloorSub`. BKRGY ve VEYAS `b = 1, L = 0` (ilk gün tavan yok, "seri" yok) [ÖLÇTÜM]; BKRGY b_floor = 1 → "seri … bozuldu" sayımına giriyor. Tablo hücresi "1. gün taban" doğru; şerit alt metni yanlış genelleme.

### F12 [B] Kayıtlarım "güncel kümeyle aynı" = uygulamaya gömülü INDEX
- scenario.rs:239, :284: `same_index = models_index_sha256 == embedded_index_sha`. "Güncel küme" = bu derlemenin gömülü kümesi, repo'daki models/INDEX.json değil (Ayarlar INDEX_SHA denetimi ikisini karşılaştırır). Etiket "bu sürümün kümesiyle aynı" olmalı. DÜŞÜK.

### F13 [B] OOT hükmünün "(zaman-dışı terazide)" eki Monitör'de yalnız tooltip'te
- common.ts:30-33 (`compact = true` → ek `title`'da), monitor.ts:145. Sütun başlığı "Eski dönem" bağlam verir; kabul edilebilir, not olarak.

### F14 [B] Monitör "Ertesi gün taban" (p_floor_f1) altın renkli ama bütün satırlar geçmişe dönük
- monitor.ts:59-62: altın = kapı `featured` (terfi), satır sınıfı değil. Değerin altında "geçmişe dönük" yazıyor [ÖLÇTÜM]; `featuredTip` "öne çıkar" diyor, "canlı" demiyor. Altın=canlı okunabilir; bilgi.

### F15 [B] Hüküm sözcükleri yalnız dosyadan; teraziler toplanmıyor
- Sade ekranlarda "geçiyor/geçemiyor/ayırt edilemiyor" yalnız `verdictCell(v)` ile dosyadaki `verdict` metninden yazılıyor (common.ts:23-27); Rust `cell_row` `verdict: st(c, "/verdict")` (sade.rs:1218). Kodda hüküm üretimi yok [ÖLÇTÜM]. Backtest / OOT / canlı hiçbir yerde toplanmıyor, yalnız yan yana (F1 gizli istisna).

---

## 2. Zincir tabloları (ekran öğesi | Rust komut.alan | Rust hesap | format.ts | tr.ts anahtar: metin | etiket↔tanım | not)

### 2.1 Monitör (render/monitor.ts; komutlar monitor_view, headline_gate, perf_view — screens/monitor.ts:13)

| Ekran öğesi | Rust komut.alan | Rust hesap (file:line) | format.ts | tr.ts | Uyuyor mu | Not |
|---|---|---|---|---|---|---|
| Özet "7 arz takipte. Şu an tavan serisinde olan yok." | monitor_view.counts.n_ipos, n_in_streak | sade.rs:861 `rows.len()`; :865 `streak.in_streak` sayısı; in_streak = dosya var ∧ !broken ∧ !unlabeled ∧ j<10 (sade.rs:207-221) | — | monitor.summary | Evet | n_ipos = FROZEN payda satırları ∪ etkin kaydı olanlar (sade.rs:722-740) |
| Özet "… 10. günde arz fiyatının altında kapattı." | rows[].r10_below | sade.rs:708 `is_negative(R_10)` | — | monitor.belowList | Evet | |
| Şerit "Takipteki arz 7, 18.08.2026 – 17.09.2026" | counts.n_ipos, first_d1, last_d1 | sade.rs:861-864 min/max D1 | dateTr | stripIpos, stripIposSub | Evet | |
| Şerit "Tavan serisinde 0 — bugünkü bültene göre" | counts.n_in_streak | sade.rs:865 | — | stripStreak(Sub) | Evet | "bugünkü" = data_date (en geç session_date) |
| Şerit "D10'da arz altında 2 / 7" + ad listesi | counts.n_d10_below / n_d10_known | sade.rs:866-867 (`r10_below == Some(true)` / `.is_some()`) | — | stripBelow(Sub) | Evet | payda = R_10'u bilinen arz |
| Şerit "Tabanda kırılma 3 / 7 — seri taban kapanışıyla bozuldu" | counts.n_break_floor / n_break_known | sade.rs:868-869 (`b_floor == 1` / `b_floor.is_some()`); b_floor makine kaydı `/break_day/b_floor` (sade.rs:430) | — | stripFloor(Sub) | Kısmen | F11 |
| Şerit "Üretimdeki model 4" | perf_view.n_production | sade.rs:1412 `PRODUCTION_MODELS.len()` | — | stripModels(Sub) | — | lider (a) |
| Sütun "Seri" (3) | rows[].streak.realized_l ?? j_observed | sade.rs:219-220 (`realized_l` = broken ∨ j=10 ise j) | — | colStreak | Evet | sürüyorsa j_observed |
| Sütun "Beklenen / medyan" (3.3 / 3) | rows[].ceiling.expected_l, median_l | ceiling_info sade.rs:239-262 → ceiling.rs:175 `Σ l·P_L[l]`, :197 medyan (kümülatif ≥ 0.5) | fixed1 | colExpected; groupPre | Evet | kayıttaki S'ten görüntüleme türevi; altın/≈ kapı `ceiling_hazard_v0,S` |
| Sütun "5+ gün" (%27) | rows[].ceiling.p_ge5 | sade.rs:260 `S[4]`; S_k = P(L ≥ k), k=1..10 (borsai/predict_path.py:397, report_faz1b.py:507) → S[4] = P(L ≥ 5) | pct0 | colGe5 | Evet [ÖLÇTÜM tanım] | |
| Sütun "Kırılma" ("4. gün taban" / "5. gün taban üstü" / "kırılma yok") | rows[].break_info.b, b_floor | sade.rs:409-437 ilk makine dosyası `/streak/b`, `/break_day/b_floor` | — | breakFloor/breakAbove/noBreak | Evet | b = kırılma günü (L+1) |
| Sütun "Ertesi gün taban" (%50) + sınıf notu + "D10'da arz altına inemez" | break_info.p_floor_f1, impossible_d10; classes[break_floor_v0].class | sade.rs:433 `/output/F1/p_floor`; :435 `/structural_zero_D10/impossible`; sınıf scores_break `live_break.denominator[ticker].class` (sade.rs:361-368) | pct0 | colNextFloor, groupBreak, impossibleBadge/Tip, classText | Evet | F14 |
| Sütun "Kayıt" ("geç kayıt", "getiri canlı") | classes[ceiling].class, classes[v1_5_h99].class, status | sade.rs:339-350 scores.json `live.rows[ticker].class/status` | — | classText, recordReturn, classNone, refusedShort | Evet | sınıf dosyadan |
| Seçili arz "Seri, model medyanı ve gerçek: 3 / 3 gün" | ceiling.median_l / streak.realized_l | yukarıdaki | — | selStreak, selStreakVal | Evet | |
| Seçili arz "D4 akşamı, yarın taban olasılığı %50" | break_info.b, p_floor_f1 | sade.rs:433 | pct0 | selBreak | Evet | |
| Seçili arz "D5 getiri, tahmin ve gerçek: +%25.5 / +%7.8" | returns.rows[D5].ret, realized | sade.rs:285-311 kayıt `prediction.D5.return`, gerçek outcomes `R_5` metni | pctSigned1 | selD5 | Evet | kapı `v1_5_h99,return,D5` birincil → altın |
| Üretimdeki modeller: "Geçmiş test" | perf_view.scales[].backtest_verdicts / promotion | sade.rs:1380-1390; kırılma: gate `card.promotion` (sade.rs:1049-1053) | — | colBacktest; verdictCell / promotionCell | Hayır (post_d1) | F1, F2 |
| Üretimdeki modeller: "Eski dönem" ("× geçemiyor") | scales[].oot.verdict | sade.rs:1251-1263 scores_oot `<blok>.models[m].cells` birincil hücre `verdict` | — | colOld; ootVerdictCell(compact) | Evet | F13 |
| Üretimdeki modeller: "Canlı" (0 / 1 / 0 / 0) | scales[].live.n_live | sade.rs:1265-1280 `live.n_live` / `conditional_j1.n_live` / `live_break.n_live` | — | colLive; prodNote | Evet | yalnız yan yana; toplanmıyor |
| Olay akışı metinleri | monitor_view.events[] | sade.rs:743-845 (RECORD/LEGACY/STREAK/BREAK/D10/MACHINE/MODEL_FROZEN/REGIME; gruplama :816) | dateTr, pctSigned1 | SADE.event.* | Evet | F8 |
| Rejim şeridi | monitor_view.regime.start_d1 | sade.rs:448-452 scores.json `regime` | dateTr | regimeBadge, regimeStripe | Evet | |

### 2.2 Yeni arz girişi (render/giris.ts; check_form, market20_via_python)

| Ekran öğesi | Rust komut.alan | Rust hesap | format.ts | tr.ts | Uyuyor | Not |
|---|---|---|---|---|---|---|
| Alan altı okunur tekrar ("312.5 milyon pay", "25.52 TL", "17 Eylül 2026") | (form değeri) | — | readableCount (≥1e4 bin, ≥1e6 milyon, ≥1e9 milyar), readableDate | giris.readableShares/readableTl, months, units | Evet | yalnız gösterim (format.ts:149-158) |
| Alan notları | check_form.notes[] (code, level, value, name) | form.rs:139-275 | — | FORM_NOTE_TEXT[code] | Evet | |
| "Eksik zorunlu alanlar: …" | notes code=REQUIRED_EMPTY | form.rs:268-270 | — | missingSome/None, fieldLabel | Evet | |
| Özdeşlik ID-A/B/C "✓ tutuyor / × tutmuyor" + "a = b + c" | check_form.normalized, notes PB_IDENTITY (name=ID-x) | form.rs:236-258 (dec eşitlik; error) | readableCount | giris.identity.*, identityOk/Bad | Evet | |
| Özdeşlik SUM "× tutmuyor" | notes SHARES_SUM_MISMATCH | form.rs:225 **warn** | readableCount | identity.SUM, identityNote | **Hayır** | F4 |
| "öneri: …" | check_form.suggestions[alan] | form.rs:255-258 (ID-B/C toplamı) | — | suggestion, apply | Evet | |
| Piyasa "20 seans getirisi +%x" + "S0/S20 kapanış" | market20_via_python.record.f6, S0_date, close_S0, S20_date, close_S20 | market20.rs (Python; pinli XU100) | pctSigned1, dateTr | market20, marketClose, marketNote | Evet | ret: MARKET20_REASON_TEXT |

### 2.3 Model performansı (render/perf.ts; perf_view + headline_gate — screens/perf.ts:22)

| Ekran öğesi | Rust komut.alan | Rust hesap | format.ts / accuracy.ts | tr.ts | Uyuyor | Not |
|---|---|---|---|---|---|---|
| Şerit "Üretimde 4 — kendi sorusunda ölçülen" | perf_view.n_production | sade.rs:1412 sabit | — | perf.stripProd(Sub) | — | lider (a) ile aynı kök |
| Şerit "Karşılaştırma 6 — 3 satırda model daha iyi · 1 satırda fark net değil · 2 satır hükümsüz" | counts.n_rows, n_pass, n_undecided, n_fail, n_other, n_no_verdict | sade.rs:1369-1379 verdict metni eşitliğiyle sayım | — | stripRows, stripRowsSub | Evet | hükümsüz = kırılma satırları |
| Şerit "Hüküm eşiği 30 — n ≥ 30 hüküm, n < 10 yalnız satır" | min_n_verdict, min_n_metric | scores.rs:123-124 sabitler | — | stripMinN(Sub) | Kısmen | F6 |
| Satır başlığı "Kaç gün tavan ile son 10 arzın tablosu, RPS" + çip "birincil/keşif" | rows[].question, rule_id, metric, label | sade.rs:1198-1222 `cell_row` (dosyadan) | — | perfQuestion, rule, vsRule | Evet | çip = dosyadaki `label` |
| "Hata puanı" çubukları (0.1503 / 0.1999; MAE "22.2 puan") | rows[].model_value, rule_value | dosyadan | accuracy.value (MAE/MedAE → points1, diğer metric4); fillPct | perf.model/rule, colScore | Evet | çubuk = v/max(m,k) |
| "Fark ve %95 aralık" (−0.0496; [−0.0751, −0.0219]) + çubuk | rows[].diff, ci95 | dosyadan | value, ciText, intervalBar | colInterval, guide* | Kısmen | F3 |
| "Model daha iyi olan arz" (52 / 87; kazanç 52 · kayıp 35 · eşit 0) | rows[].wins, n, losses, ties | dosyadan | — | colWins, wins, wlt | Evet | kırılma satırı: nOnly → F2 |
| "Hüküm" ("✓ geçiyor" + sade açıklama) | rows[].verdict | dosyadan aynen (sade.rs:1218) | — | verdictCell, VERDICT_PLAIN | Evet | F15 |
| "Hüküm" kırılma satırı ("hüküm alanı yok" + "✓ ön eleme …; canlı n = 0") | rows[].verdict=null; gate.label, featured | sade.rs:1224-1249 `break_row`; gate :1049-1053 `card.promotion.label/promoted` | — | noVerdict; promotionCell | **Hayır** | F2 |
| Üç ayrı sınav: Geçmiş test | scales[].backtest_verdicts / backtest_label | sade.rs:1380-1390 | — | colBacktest, scalesSub | Hayır (post_d1) | F1 |
| Üç ayrı sınav: Eski dönem ("× geçemiyor (zaman-dışı terazide) 130 arz") | scales[].oot.verdict, n | sade.rs:1251-1263 | — | colOld, oldN, VERDICT_OOT_SUFFIX | Evet | n = birincil hücre `n` |
| Üç ayrı sınav: Canlı sicil ("0 sayılan, 6 geç kayıt"; "7 geçmişe dönük") | scales[].live.n_live, n_late, n_retro | sade.rs:1265-1280 | — | colLive, liveLine, liveRetro | Kısmen | F10 |
| Canlı sicil ilerlemesi "1 / 30" | scales[].live.n_live; min_n_verdict | sade.rs:1412; sabit 30 | progressPct | liveTitle, liveSub, liveStage | Kısmen | F5(ii) |
| Canlı satırlar: Kaç gün tavan "Sınıf / Beklenen 5.8 / Gerçek 5" | live_rows[].ceiling.class, predicted, realized | sade.rs:1290-1335; predicted = kayıt S'inden expected_l (ceiling.rs:175); realized `realized.L` | fixed1 | colClass/colPredicted/colRealized, groupCeiling | Evet | |
| Canlı satırlar: 5. gün getirisi "Tahmin +%48.6 / Gerçek +%60.8" | live_rows[].d5.predicted, realized | `prediction.D5.return`, `realized.R.D5` (Decimal metin) | pctSigned1 | colForecast, groupD5 | Evet | |
| Canlı satırlar: "İlk gün akşamı" / "Kırılma akşamı" ("geçmişe dönük") | live_rows[].post_d1_status, break_class | sade.rs:1324-1331 denominator `stage_status` / `class` | — | classText, groupPostD1/groupBreak | Evet | |
| rowsNote sabit cümle | — | — | — | perf.rowsNote | Hayır (zamanla) | F5(i) |

### 2.4 Sicil (render/sicil.ts; registry_view, monitor_view, break_view, post_d1_records)

| Ekran öğesi | Rust komut.alan | Rust hesap | format.ts | tr.ts | Uyuyor | Not |
|---|---|---|---|---|---|---|
| "Payda 26 satır — 7 kayıtlı, 19 kapsam dışı" | monitor_view.counts.n_payda, n_frozen, n_out_of_scope | sade.rs:870-873 ipos.csv `status` sayımı | — | sicil.payda, paydaSub, rows | Kısmen | F9 |
| "Listeleme öncesi kayıt 7 — etkin tahmin kaydı" | counts.n_pre_listing_records | sade.rs:875 Σ etkin PREDICTION (OK ∧ !cancelled; sade.rs:662-669) | — | pre, preSub | Evet | |
| "D1 sonrası kayıt 0 — etkin" | counts.n_post_d1_records | sade.rs:876 Σ `n_post_d1_active` (registry.rs:342) | — | postD1(Sub) | Evet | |
| "Kırılma akşamı kaydı 7 — makine kaydı" | counts.n_machine_records | sade.rs:877 Σ `machine_*.json` dosya sayısı (sade.rs:390-401) | — | machine(Sub) | Evet | |
| "Zaman kanıtı dosyası 31 — registry/push_proofs" | counts.n_push_proofs | sade.rs:878 = registry.rs:154-165 dizin dosya sayısı | — | proofs(Sub) | Evet | dosya sayısı (alt metin dizini söylüyor) |
| "Repo durumu temiz / commit bekleyen …" | monitor_view.git_status ya da registry.git_status_registry | sade.rs:885 `git status --porcelain -- registry data` | — | repo, repoClean/Dirty, repoSub | Evet | |
| Tablo "✓ 1 kayıt / yok / makine kaydı" | registry.tickers[].n_active, n_post_d1_active; monitor rows[].n_machine_records | registry.rs:336-343 | dateTr | nRecords, none, machineRecord | Evet | |
| "Kapsam dışı 19 satır — hiçbir sayıma girmez" | counts.n_out_of_scope | sade.rs:872 | — | outOfScope(Sub) | Evet | |
| Künye: Kayıt zamanı + "Yerel saat beyandır; zaman kanıtı push'tur." | records[].recorded_at_istanbul | registry.rs | dateTr | at, atBasis | Evet | |
| Künye: "✓ push kanıtı var 22.09.2026 …" / "kaydı ekleyen commit …" | records[].push_proof.created_at, added_commit | registry.rs:312 (`added_commit` ↔ push_proofs/<sha>.json) | dateTr, sha12 | proofYes/No, addedBy | Kısmen | F7 |
| Künye: Sınıf satırları ("Tavan: geç kayıt / Getiri: canlı") | monitor rows[].classes | sade.rs:339-350 | — | classLines, questionShort | Evet | |
| Künye: "N model" + INDEX sha | records[].n_models, models_index_sha256 | registry.rs | sha12 | modelSetVal, indexSha | Evet | |
| Kırılma sekmesi: "Kırılma akşamı sınıfı: geçmişe dönük", "Yarın da taban olasılığı %50" | break_view.class, status, p_f1 | sade_break.rs:177-284 | pct0, dateTr | machineClass, pBreak, produced | Evet | fikstür sade_break_netgl: class RETRO, p_f1 0.499 |

### 2.5 Kayıtlarım (render/kayitlarim.ts; list_scenarios)

| Ekran öğesi | Rust komut.alan | Rust hesap | format.ts | tr.ts | Uyuyor | Not |
|---|---|---|---|---|---|---|
| "✓ güncel kümeyle aynı" / "eski küme" | list_scenarios[].same_index | scenario.rs:239 `models_index_sha256 == embedded_sha` (gömülü INDEX) | — | kayitlarim.sameSet/oldSet, note | Kısmen | F12 |
| Oluşturma, Aşama | created_at_local, stage | scenario.rs | dateTr; stageLabel (sonuc.ts) | colCreated, colStage | Evet | |

### 2.6 Ayarlar / Hakkında (render/ayarlar.ts; get_config, validate_repo, app_info)

| Ekran öğesi | Rust komut.alan | Rust hesap | format.ts | tr.ts | Uyuyor | Not |
|---|---|---|---|---|---|---|
| "Doğrulama: Repo modu açık/kapalı" | validate_repo.ok | config.rs:277 `all(ok ∨ !required)` | — | ayarlar.checks, SETTINGS.modeOn/Off | Evet | |
| Denetim satırları ✓ / × / "i" | checks[].ok, required, detail | config.rs:213-272 (REPO_DIR, DATA_DIR_OUTSIDE_REPO, INDEX_SHA, GIT_HEAD, PYTHON_IMPORT zorunlu; OUTCOMES_DIR, TUFE_TABLE, MARKET20_SOURCES bilgi) | — | SETTINGS.checkText[id] | Evet | "i" = zorunlu olmayan ve ok=false; "başarısız" yazılmıyor |
| Hakkında "Listeleme öncesi modeller N <sha12>" | app_info.embedded_models.len, index_sha256 | models.rs:234-297 (gömülü INDEX) | sha12 | preModels | Evet | `ignored_index_models` sade'de yok |
| "D1 sonrası modeller N <sha12>" | embedded_post_d1_models.len, index_post_d1_sha256 | models.rs:291 | sha12 | postModels | Evet | kırılma modeli (INDEX_POST_BREAK) Hakkında'da sayılmıyor [ÇIKARIM: AppInfo'da alan yok] |
| "Gömülü skor kopyası var/yok", "Gömülü TÜFE tablosu <ay>" | scores_embedded, tufe_embedded.through_month | models.rs:294-296 | — | embeddedScores/Tufe, yes/no | Evet | |
| "Model bütünlüğü tamam / bozuk: tahmin kapalı" | integrity_ok | models.rs:273 | — | integrity(Ok/Bad) | Evet | |

---

## 3. Hüküm tutarlılığı betiği

- Betik: /tmp/borsai_kitap_audit_4/agentD/verdict_check.py (salt okur; argüman: repo kökü).
- Çıktı: /tmp/borsai_kitap_audit_4/agentD/verdict_check.out (300 hücre satırı).
- Ne yapar: perf_view'ün hücre seçimini yeniden üretir (primary_cell + `label = birincil` + `rule_ids`; PERF_EXTRA_CELLS v1_5_h99 p_up D10 Brier base_rate; scores_break `card.backtest_info.F1_product/F1_zero`), scores_oot'ta PRODUCTION_MODELS bloklarının birincil hücresini bulur ve her hükmü kendi `ci95`/`n`'iyle sınar:
  geçiyor ⇒ ci95[1] < 0 ∧ n ≥ 30; geçemiyor ⇒ ci95[0] > 0 ∧ n ≥ 30; ayırt edilemiyor ⇒ ci95 0'ı kapsar. Ek olarak scores.json'daki TÜM backtest hücreleri taranır.
- Sonuç [ÖLÇTÜM]: `BAD TOTAL 0` — 300 hücrenin tamamı tutarlı. perf_view seçimi: 2 (ceiling, base_km_last10 / base_km_expanding; geçiyor, n=87, ci üst < 0) + 1 (v1_5_h99 return D5 MAE base_train_median; geçiyor, n=87) + 1 (p_up D10 Brier base_rate; keşif, ayırt edilemiyor, ci [−0.0756, +0.0023]) + 2 kırılma (verdict yok; ci üst < 0, n=69) = 6 = fikstür `counts.n_rows = 6`, `n_pass 3 / n_undecided 1 / n_no_verdict 2`. Ekranda "geçiyor" gösterilen hiçbir satırda ci 0'ı kapsamıyor ya da n < 30 değil.
- OOT: ceiling geçemiyor ci [+0.0124, +0.1257] n=130 ✓; v1_5_h99 ayırt edilemiyor ci [−0.0613, +0.0166] n=130 ✓; post_d1 geçiyor ci [−0.0604, −0.0173] n=104 ✓.
- Canlı: scores.json `live` bloklarında `verdict`/`min_n` yok (n_live ≤ 1); ekranda canlı hüküm gösterilmiyor ✓. post_d1 `conditional_j1` ve break `live_break` n_scored = 0, cells = [] ✓.
- Not: Rust `check_integrity` (scores.rs:218-227) aynı kuralı yükleme anında uyguluyor (fail-closed); betik bunu bağımsız doğruladı.

---

## 4. Bakılmayanlar / sınırlar
- Uygulama çalıştırılmadı, ekran görüntüsü alınmadı; zincir fikstür + kod okumasıyla kuruldu. CSS (renk/kontrast), `s-hbar` genişlikleri ve sparkline çizimi içerik dışı.
- Analiz, Tahmin sonucu, Seri hesaplayıcı ve sihirbaz ekranları kapsam dışı (altı ekran istendi).
- registry/records/*.json kayıt dosyaları ve `read_record` yolu okunmadı; CeilingInfo/ReturnInfo alanları fikstürden.
- `post_d1_records` (post_d1.rs) ve `break_view` iç hesabı (sade_break.rs:177-284) satır satır okunmadı; yalnız fikstür alanları eşlendi.
- registry/oot SEALED listeleri ve 8 haneli tarihli thb/thm bülten adları açılmadı/yazılmadı; scores_oot.json'dan yalnız blok adı, n, ci95, verdict okundu.
- Ayrıntılı (eski) görünüm ve `render/shell.ts` mod bandı metinleri denetlenmedi; sade üst bar bu bandı aynen kullanıyor (sade/render/shell.ts:46-58).
- "Üretimdeki model 4", "≈ fark net değil" ve approxTip bulguları liderde; burada yalnız bağlantı notu.

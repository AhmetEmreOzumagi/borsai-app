# SPEC_MARKET20_V0 — piyasa rejimi modeli (`v1_5_market20_v0`)

## Özet (≤ 10 satır)

1. Model = V1.5 aynen + tek ek özellik f6 = XU100(S0)/XU100(S20) − 1 (20 seanslık endeks getirisi). Izgara, ön işleme, fold kuralı V1.5 ile birebir; tek değişken değişir.
2. XU100 bir SONUÇ değil, tahmin anındaki GİRDİDİR. f6 asla impute edilmez; hesaplanamıyorsa RET.
3. **Takvim sonu hatası düzeltmesi:** takvim T − 1 gününü kapsamıyorsa, pencerenin 21 kapanışından biri eksikse ya da S0 bayatsa (referans − S0 > 12 gün) RET. Legacy kod 2026-09-30 için sessizce S0 = 2026-08-19 döndürüyordu.
4. Takvim B (910 seans, 2023-01-02…2026-08-19) kullanılır → H99'da f6 99/99 hesaplanır (Takvim A ile 93/99).
5. Canlıda S0 = **tahmin tarihinden** kesin önceki son seans (kapanışı yayımlanmış olan); backtest'te tahmin tarihi = T. Kayıt S0/S20 tarih ve değerlerini taşır.
6. 2026-08-19 sonrası XU100: resmi BIST uç noktasından, Faz 1 JSON'ları dondurulduktan SONRA indirilir; pinlenir; eski 9682 kayıtla örtüşme birebir doğrulanır.
7. Sıra kuralı arz sonuçları içindir; XU100 onun kapsamında değil. Sınırlar: THB/THM endeks kaynağı olarak kullanılamaz; XHARZ (halka arz endeksi) alınamaz; özellik yalnız `as_of` öncesi kapanışları görür.
8. Beklenti: V1.5'ten ayırt edilemez (eski tek atımlık koşuda MAE farkı < 0.001). Geriye dönük sonuç tasarıma maruzdur; asıl ölçüm prospektiftir.

İşaretler: **[ÖLÇTÜM]** / **[ÇIKARIM]**. Ölçümler: `docs/specs/ekler/m2_cikti.txt:24-32`, `m3_cikti.txt`.

---

## 1. Kimlik ve veri

- `model_id`: `v1_5_market20_v0`. Eğitim: `training_table.csv` 99 satır + f6.
- XU100: `data/raw/official_bist_xu100_graphic_pinned_through_20260819.json` (sha256 `34859d7e…`, PROVENANCE §1 satır 11): 9682 kayıt, 1986-01-31…2026-08-19, alanlar `indexName, clval, hisTs`. Ayrıştırma `json.loads(parse_float=Decimal)` (`legacy/…/v2_market20_repair_01_core.py:76-110`).
- Takvim B: `data/raw/v2_market20_official_pay_calendar_evidence_r4.csv` (sha256 `49b58029…`): 1327 ardışık takvim günü 2023-01-01…2026-08-19, 910 seans (`counts_as_official_session == "YES"`), 8 yarım gün [ÖLÇTÜM `m3_cikti.txt:1-2`]. Takvim A (H99 oturum takvimi, 728 seans) B'nin alt kümesi ve ortak aralıkta birebir aynı [ÖLÇTÜM `m2_cikti.txt:25`].
- Takvim B'nin 2023-09-22 öncesi kısmı "yeniden kurma kuralıyla" doğrulanmış; 5 seans gününde XU100 kapanışı yok (2023-02-09/10/13/14, 2023-04-24) [ÖLÇTÜM `m2:27`]. H99 pencerelerine dokunmuyor (en erken S20 = 2023-08-23; 99/99 arzda 21 kapanışın hepsi var, `m3:3`). §3'teki "21 kapanış" denetimi bu tür takvim hatasını RET'e çevirir.

## 2. Özellikler

f1–f5: V1.5 ile birebir (`borsai/features.py`, `borsai/preprocess.py`; filtre durumu argümanı dahil).

f6_market20:
```
sessions = Takvim'de counts_as_official_session olan tarihler (artan)
i  = bisect_left(sessions, ref_date) − 1          # ref_date'ten KESİN önceki son seans
S0 = sessions[i];  S20 = sessions[i − 20]          # 21 kapanış, 20 aralık
f6 = XU100[S0] / XU100[S20] − 1                    # Decimal, prec 60, ROUND_HALF_EVEN
```
- `ref_date`: backtest'te ve nihai fit'te T = `first_trading_date`. Canlı tahminde `prediction_date` (dondurma kaydının yerel tarihi, Europe/Istanbul). Yani canlıda S0, tahmin gününden önceki son seanstır; o günün kapanışı henüz yayımlanmamış olabileceği için gün içi bilgi kullanılmaz.
  - Eğitim/canlı uyumsuzluğu: canlı pencere T'ye göre ≥ 1 seans geridedir. 20 seanslık getiri yavaş değiştiği için kabul; kayıt `S0_date, S20_date, close_S0, close_S20, ref_date` taşır [ÇIKARIM].
- Ön işleme: fold içi z-skor (popülasyon std). Log yok, winsorize yok, **imputasyon yok, eksiklik göstergesi yok** (legacy repair_03 kararı; CHECKUP `detay/A2:244, 358`).
- [ÖLÇTÜM `m2:31`] H99'da f6: min −0.112, medyan +0.023, maks +0.155. T − S0: 1–3 gün (`m3:3`).

## 3. Takvim sonu düzeltmesi: geçerlilik kuralları

f6 ancak aşağıdakilerin HEPSİ tutarsa üretilir; aksi halde model o arz için RET eder (`REFUSED_MARKET20_<NEDEN>`):

| # | Kural | Neden kodu |
|---|---|---|
| 1 | Takvim, `ref_date − 1 gün`ü satır olarak içeriyor (takvim her takvim gününü listeler; `calendar_last_date ≥ ref_date − 1`) | `CALENDAR_NOT_COVERING` |
| 2 | i ≥ 20 (yeterli geçmiş) | `INSUFFICIENT_HISTORY` |
| 3 | S20…S0 arasındaki 21 seansın HEPSİNDE XU100 kapanışı var (yalnız iki uç değil) | `XU100_CLOSE_MISSING` |
| 4 | `ref_date − S0 ≤ 12` takvim günü (H99'da maks 3; 12 = en uzun bayram kapanışı + pay) | `STALE_S0` |
| 5 | Canlıda: `T − prediction_date ≤ 12` takvim günü | `PREDICTION_TOO_EARLY` |
| 6 | XU100 kayıtları yalnız `indexName == "XU100"`; aynı tarihte çelişen iki değer yok; değer > 0 | `XU100_INTEGRITY` |
| 7 | `as_of` koruması: özellik fonksiyonu `hisTs < ref_date` olmayan kayıtları hiç okumaz | (test) |

Kök neden [ÖLÇTÜM `m2:32`; CHECKUP.md:105]: `s0_s20_from_calendar` (`legacy/…repair_01_core.py:116-133`) takvimin bittiği yeri denetlemiyor; T = 2026-09-30 için S0 = 2026-08-19 dönüyor. Kural 1 bunu kapatır; kural 4 ikinci emniyettir.

## 4. 2026-08-19 sonrası XU100 ve takvim: kaynak ve sıra kuralı

**Kaynak (resmi):** `https://www.borsaistanbul.com/graphic.php?veriTuru=endeks-graphic&indexCode=XU100` — eldeki pinli dosya bu uç noktadan indirildi (kanıt: arşiv `artifacts/modeling/historical99_market_sector_microstructure_stage_a/…/market_index_source_index.csv` satır 2: `source_authority = BORSA_ISTANBUL_OFFICIAL`, `index_value_type = PRICE_INDEX_OFFICIAL_CLOSE`). Yanıt 1986'dan bugüne tüm seriyi döndürür.

Alma prosedürü (Faz 2, ağ izni olan görevde; bu görevde ağ yok):
1. Ham yanıtı değiştirmeden `data/raw/xu100/xu100_graphic_<YYYYMMDD>.json` olarak kaydet; sha256 + indirme zamanı + URL'yi `docs/PROVENANCE.md`'ye yaz. Kaynak etiketi: `BORSA_ISTANBUL_OFFICIAL`.
2. **Revizyon denetimi:** `hisTs ≤ 2026-08-19` olan 9682 kaydın hepsi eski pinli dosyayla Decimal-eşit olmalı. Değilse DUR ve raporla.
3. Yeni dosya eskisinin yerine geçmez; ikisi de kalır. f6 üretimi en yeni pinli dosyayı okur ve kayda dosya sha'sını yazar.
4. Takvim uzatması: BIST'in yıllık resmi tatil duyurusundan (`https://borsaistanbul.com/files/2026_tatil-duyurusu.pdf` biçimi; H99 takviminin `calendar_source_url` sütunundaki kalıp) 2026-08-20…2026-12-31 satırları Takvim B şemasıyla eklenir. Hafta içi + tam kapanış listesinde değil ⇒ seans; yarım gün seans sayılır. 2027 için yeni duyuru gerekir; yoksa kural 1 RET üretir (sessiz bayat değer yerine).
5. Çapraz denetim: eklenen aralıkta "XU100 kaydı olan gün kümesi" = "takvim seans günleri kümesi". Fark varsa DUR (deprem kapanışı türü ilan dışı kapanışları yakalar).

**Sıra kuralıyla ilişki.** CLAUDE.md sıra kuralı iki şeyi yasaklar: 2026-08-19 sonrası THB/THM ve 2026-08-06 sonrası arzların sonuçları. XU100 kapanışı bunların hiçbiri değildir; bir arzın getirisini ya da tavan etiketini içermez. Dolayısıyla XU100'ün alınması kuralı ihlal etmez. Yine de sınırlar:
- (a) **Yine de dondurmadan sonra al.** Parametreler yalnız ≤ 2026-08-19 verisiyle fit edilir; yeni XU100 yalnız tahmin girdisi olarak gerekir. Dondurmadan önce almak hiçbir işe yaramaz, dondurmadan sonra almak hiçbir şeye mal olmaz; PROVENANCE'taki "iki kaydı çıkar" kararıyla tutarlı.
- (b) **THB/THM endeks kaynağı olamaz.** THB bülteni tüm payların fiyatını taşır; XU100 için THB açmak 7 arzın sonuçlarını repoya sokar.
- (c) **XHARZ ve benzeri halka arz endeksleri alınmaz.** Yeni arzların getirisinin doğrudan türevidir; girdi değil sonuç vekilidir. İndirilen dosyada yalnız `indexName == "XU100"` bulunmalı (kural 6).
- (d) XU100, aynı dönemdeki arz sonuçlarıyla piyasa geneli üzerinden ilişkilidir; ama model parametreleri donmuş olduğundan bu bilgi modele sızamaz, yalnız girdi olarak girer — amaç da budur [ÇIKARIM].
- (e) Geç kayıt edilen 7 arz için f6, `ref_date` = "o arz için savunulabilir en geç tahmin tarihi" = T alınarak hesaplanır (backtest tanımıyla aynı); SPEC_SCORING §5'te `late_record` sınıfına girer.

## 5. Model sınıfı, ızgara, seçim

V1.5 ile birebir (`legacy/…/candidate_models.py:19-40`): Ridge α ∈ {0.1, 1, 10, 100}, iç LOOCV MAE, eşitlikte büyük α; Logit C ∈ {0.01, 0.1, 1, 10}, iç LOOCV ham Brier, eşitlikte küçük C; yozlaşma ve yakınsamama politikaları aynı. Genişletilmiş ızgara burada KULLANILMAZ: soru "f6 V1.5'e bilgi ekliyor mu"dur; ızgarayı da değiştirmek iki değişkeni karıştırır. (İleride `v1_6_market20` ayrı kimlik olur.)

Özellik matrisi sütun sırası: f1, f2, f3, f4, f5, f6. Sıfır varyans/eksiklik düşürme kuralları V1.5'teki gibi; f6 sıfır varyanslıysa düşer.

## 6. Parametre bütçesi

6 katsayı + sabit. Azınlık (Y = 0): D1 10, D3 19, D5 22, D10 29 (`m2:16-23`). V1.5 zaten bütçe üstünde (AUDIT §3b: "beş özellikli logit D1 için sınırda"); f6 bunu bir artırır. Gerekçe: f6'nın eklediği şey firma değil rejim bilgisi (AUDIT §2.4: D1 tavan oranı yıllara göre %95 → %82 → %67 → %83) ve tek değişkenlik karşılaştırma değeri. Logit D1'de kazanç beklenmez.

## 7. Eksik veri davranışı

| Durum | Davranış |
|---|---|
| f3 boş | **RET** (V1.5 kuralı) |
| f6 §3 kurallarından birini geçemiyor | **RET**, neden koduyla. İmputasyon yok |
| Eğitim satırında f6 yok | satır dışlanır, n yeniden sayılır, MIN_TRAIN_N bir kez uygulanır (Takvim B ile H99'da 0 satır) |
| f4 = 0, aralık dışı girdi, fiziksel sınır | V1.5 çekirdek kuralları |
| f6 eğitim aralığı [−0.112, +0.155] dışında | tahmin + uyarı |

## 8. Walk-forward ve kurallar

- Fold planı V1.5 ile **birebir**: aynı 351 fold, aynı `training_tickers_sha256` (Takvim B ile hiçbir satır düşmediği için). Bu bir kabul testidir.
- Kurallar: çekirdekteki altı basit kural + **`v1_5_h99`'un aynı fold tahminleri** (asıl karşılaştırma; eşleşik fark f6'nın katkısıdır).

## 9. Sonuç görülmeden yazılan beklenti

Bu model için "sonuç görülmeden" kısmen doğrudur: aynı özellik eski repoda tek atımlık H99 koşusundan geçti ve sonuç biliniyor: "MAE farkı her ufukta 0.001'in altında", "5 iyileşme / 3 kötüleşme", etiket `DESCRIPTIVE_INCREMENTAL_EVIDENCE` (CHECKUP.md:6, :90). O koşunun hangi takvimle yapıldığı bu oturumda doğrulanmadı (repair_01 Takvim A'yı, wiring r7 Takvim B'yi okuyor; PROVENANCE §1 notu); bu şartname Takvim B'yi sabitler. Geriye dönük sonuç hem **tasarıma maruz** hem **önceden görülmüş**tür; kanıt değeri yoktur.

Beklenti [ÇIKARIM]: 8 hücrenin hepsinde V1.5'e karşı eşleşik fark aralığı 0'ı içerir; |ΔMAE| < 0.002, |ΔBrier| < 0.005. f6 katsayısının işareti pozitif (yükselen piyasa → daha yüksek getiri), büyüklüğü küçük.
Başarı (prospektif, n ≥ 30): `v1_5_h99`'a karşı D5 MAE eşleşik farkı, aralık 0'ı dışlayarak negatif. Birincil ufuk: D5.
Başarısızlık: aynı aralık pozitif tarafta 0'ı dışlıyor, ya da prospektif RET oranı > %20 (veri hattı güvenilmez).
Ara durum: "V1.5'ten ayırt edilemiyor" — en olası sonuç. Backtest ne çıkarsa çıksın v0 bu şartnameyle dondurulur.

## 10. Sözde kod

```
def market20(ref_date, calendar_rows, xu100, *, T=None, live=False):
    if calendar_rows[-1].date < ref_date - 1d:            return Refuse(CALENDAR_NOT_COVERING)
    sessions = [r.date for r in calendar_rows if r.is_session]
    i = bisect_left(sessions, ref_date) - 1
    if i < 20:                                             return Refuse(INSUFFICIENT_HISTORY)
    window = sessions[i-20 : i+1]                          # 21 tarih
    closes = {d: v for (d, v) in xu100 if d < ref_date}    # as_of koruması
    if any(d not in closes for d in window):               return Refuse(XU100_CLOSE_MISSING)
    if (ref_date - window[-1]).days > 12:                  return Refuse(STALE_S0)
    if live and (T - ref_date).days > 12:                  return Refuse(PREDICTION_TOO_EARLY)
    with Decimal context(prec=60, ROUND_HALF_EVEN):
        f6 = closes[window[-1]] / closes[window[0]] - 1
    return f6, {S0: window[-1], S20: window[0], close_S0, close_S20, xu100_file_sha256, calendar_sha256}

fit / predict: V1.5 çekirdeği, features = [f1..f5, f6]; predict(params, inputs) f6'yı HAZIR değer olarak alır
               (stdlib predict takvim/JSON okumaz); f6 = None -> REFUSED_MARKET20_<neden>.
```
Rol ayrımı: f6'yı Python tarafı (`borsai/features.py: market20`) üretir ve dondurma girdisine yazar; uygulama yalnız hazır f6 ile `predict` çağırır.

## 11. Kabul testleri

1. **Kapsam:** Takvim B ile 99/99 arzda f6 üretilir; Takvim A ile çağrılırsa 6 arz (`HATSN, DMRGD, MEKAG, DOFER, MHRGY, BORLS`) `INSUFFICIENT_HISTORY` ile RET.
2. **Legacy paritesi:** 99 arzda f6, `legacy…repair_01_core.materialize_market20_raw` + `s0_s20_from_calendar` (Takvim B seanslarıyla çağrılmış) sonucuna Decimal-eşit.
3. **Takvim sonu (asıl düzeltme):** ref_date = 2026-09-30, takvim 2026-08-19'da bitiyor → `CALENDAR_NOT_COVERING`. ref_date = 2026-08-20 → geçerli (S0 = 2026-08-19). ref_date = 2026-08-21 → RET.
4. **Pencere içi eksik:** takvimden kopyalanmış sentetik pencerede ortadaki bir kapanış silinir → `XU100_CLOSE_MISSING` (uçlar dolu olsa da). Gerçek veri örneği: ref_date = 2023-02-20 → RET (2023-02-09…14 kapanışları yok).
5. **Bayat S0:** takvimi 13 gün tam kapanışla uzatılmış sentetik durumda `STALE_S0`.
6. **as_of:** XU100 listesine ref_date ve sonrası için saçma değerler (1e9) eklenir → f6 değişmez.
7. **Bütünlük:** `indexName = "XHARZ"` içeren kayıt → `XU100_INTEGRITY`; aynı tarihte iki farklı değer → aynı hata.
8. **Fold kimliği:** 351 fold'un `training_tickers_sha256` değeri V1.5 altın ledger'ıyla 351/351 eşit.
9. **Tek değişken:** f6 sütunu sabitlenirse (sıfır varyans → düşer) tüm fold tahminleri `v1_5_h99` ledger'ına birebir eşit (aynı makine).
10. **predict:** f6 = None → RET; f3 = None → RET; f6 aralık dışı → uyarı. JSON ↔ sklearn paritesi 99 satırda |Δ| ≤ 1e-12.
11. **Revizyon denetimi fonksiyonu:** eski pinli dosya ile bir kaydı değiştirilmiş kopyası karşılaştırılınca hata; salt ekleme yapılmış kopyada geçer.

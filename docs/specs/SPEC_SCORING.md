# SPEC_SCORING — Faz 2 skorlama tanımları

## Özet (≤ 10 satır)

1. Sonuç yalnız resmi THB (fiyat) ve THM (limit) dosyalarından; her sayı Decimal, ham metinden. Tanımlar ilk skorlamadan ÖNCE kodda (`borsai/scoring.py`) ve testte olmalı (CLAUDE.md kural 6).
2. D_h = ilk işlem gününden başlayarak payın **işlem gördüğü** h'inci resmi Pay Piyasası seansı. Yarım gün sayılır; tam kapanış sayılmaz; tam gün durdurma sayılmaz (kayar, en çok 15 seans).
3. Tavan etiketi = `Decimal(KAPANIS) == Decimal(UST LIMIT)`, o seansın THM'sinden. "%10" varsayımı yok. Seri L = D1'den başlayan kesintisiz tavan sayısı (0–10).
4. Prospektif/retrospektif ELLE etiketlenmez: git DAG'ı (model commit'i, sonuç commit'inin atası mı) + push kanıtı + ilk işlem tarihinden hesaplanır. Üç sınıf: `LIVE`, `LATE_RECORD`, `RETRO`.
5. Payda: 2026-08-07'den itibaren işlem görmeye başlayan her halka arz `registry/ipos.csv`'de; dondurma yoksa nedeniyle `SKIPPED`.
6. Legacy dondurmalar: NETGL = git+push kanıtlı; BKRGY/INTET birincil = POST_BOOKBUILD (self-reported); TKNKA = ayrı model `v1_5_full20`; f3'süz üç kayıt = geçersiz kullanım, hiçbir metriğe girmez.
7. Metrikler eşleşik fark + aylık blok bootstrap %95 aralığı (4000 tekrar, sabit seed) + n ile. "Geçiyor" ancak aralık 0'ı dışlıyorsa.
8. Küçük n: n < 10 → yalnız satır tablosu; 10 ≤ n < 30 → metrik + aralık + "yetersiz örnek"; iki terazi (backtest / canlı) asla toplanmaz.

İşaretler: **[ÖLÇTÜM]** / **[ÇIKARIM]**.

---

## 1. Kaynaklar ve alanlar

- THB günlük bülten: `https://www.borsaistanbul.com/data/thb/YYYY/MM/thbYYYYMMDD1.zip`; THM: `…/data/thm/YYYY/MM/thmYYYYMMDD1.zip` (kalıp: SESSIONS dosyası `thb_source_url`, `thm_source_url` sütunları).
- Kullanılan sütunlar (`legacy/scripts/collect_historical99_bist_raw_v1.py:170-185`): THB `ISLEM  KODU`, `TARIH`, `KAPANIS FIYATI`, `TOPLAM SOZLESME SAYISI`, `GECICI DURDURMA`; THM `REFERANS FIYATI`, `UST LIMIT FIYATI`, `ALT LIMIT FIYATI`.
- Ham zip'ler sha256 ile pinlenir; ayrıştırılmış değer ham metinden `Decimal(str)`; float'a hiç girmez.
- **Düzen:** sonuçlar arz başına TEK dosya: `data/outcomes/<TICKER>.csv` (10 satır: D1..D10). "Sonucun repoya ilk girdiği commit" = bu dosyayı ekleyen commit (§5). H99'un 99 arzı için bu commit `ff3eee6` (iskelet) sayılır.
- THB tüm payları içerir: ham zip repoya girdiği an o tarihe kadarki TÜM arzların sonucu girmiş sayılır. Bu yüzden `outcome_ingest_commit(a)` = min(arz dosyasını ekleyen commit, D1(a)…D10(a) tarihli herhangi bir ham THB/THM'yi ekleyen ilk commit).

## 2. D_h tanımı

```
official_sessions = takvimde counts_as_official_session olan günler (tam gün + yarım gün)
traded(a, s)      = THB'de (a, s) satırı var VE TOPLAM SOZLESME SAYISI > 0 VE KAPANIS FIYATI > 0
D_1(a)            = a'nın traded olduğu ilk resmi seans   (= gerçekleşen ilk işlem günü)
D_h(a)            = D_1'den başlayarak traded olan h'inci resmi seans
```
- **Yarım gün:** bir seans sayılır; kapanış o günün resmi THB kapanışıdır. H99'da 6 yarım gün seansı var (`docs/DATA.md`: EKDMR D3, MCARD D7, LXGYO D8, GENKM D10, SVGYO D10, ENTRA D4).
- **Tatil / tam kapanış:** sayılmaz. İlan dışı kapanış (THB dosyası hiç yayımlanmamış hafta içi gün) da sayılmaz; takvime `UNANNOUNCED_CLOSURE` notuyla eklenir.
- **İşlem durdurma:** tam gün durdurma (`traded` yanlış) seans SAYILMAZ, D_h kayar; satıra `shifted_by_suspension = k` yazılır. Gün içi geçici durdurma (`GECICI DURDURMA = 1` ama sözleşme > 0) seans SAYILIR; `halt_flag = 1`. Bilinmeyen kod → `UNKNOWN_OFFICIAL_CODE`, satır elle incelenene kadar skorlanmaz.
- **Üst sınır:** D_10, D_1'den itibaren 15 resmi seans içinde oluşmadıysa oluşmayan ufuklar `TARGET_UNAVAILABLE`; tüm modeller ve kurallar için aynı anda düşer, sayısı raporlanır.
- H99 ile uyum [ÖLÇTÜM, `docs/DATA.md`]: 990 seansın hepsi `ACTIVE_NOT_SUSPENDED`; bu tanım H99'da takvim tabanlı tanımla aynı D_h'leri verir (kabul testi 1).
- Dondurma kaydındaki T ile gerçekleşen D_1 farklıysa skorlamada gerçekleşen D_1 kullanılır; fark raporlanır.

## 3. Hedefler ve tavan etiketi

- `R_h = close(D_h) / ipo_price − 1` (Decimal; ipo_price = resmi kesin halka arz fiyatı, KAP). h ∈ {1, 3, 5, 10}.
- `Y_h = 1[close(D_h) > ipo_price]`.
- `ceiling_close_k = 1[Decimal(close(D_k)) == Decimal(upper_limit(D_k))]`, k = 1..10; `upper_limit` o seansın THM satırından. Sabit oran (1.10) hiçbir yerde kullanılmaz: üst limit/referans H99'da 1.09604…1.1; 4 arzda D1 referansı arz fiyatından bir adım farklı (`docs/DATA.md` "fiyat adımı notu").
- THM satırı yok ya da üst limit boş/≤ 0 → `ceiling_close_k = NA`; L ve k ≥ o gün için tavan metrikleri o arzda hesaplanmaz; sayısı raporlanır. Etiket tahmin edilmez.
- `L = ceiling_streak` = D_1'den başlayan ardışık `ceiling_close = 1` sayısı; ilk 0'da durur. Durdurma nedeniyle sayılmayan gün seriyi BOZMAZ.
- Kabul değerleri [ÖLÇTÜM, AUDIT §1.1 ve `docs/DATA.md`]: H99'da tavan kapanışı D1/D3/D5/D10 = 81/67/48/25; seri ≥ 1/3/5/10 = 81/66/41/14.

## 4. Payda ve "atlandı" satırları (kural 2)

`registry/ipos.csv`, arz başına bir satır, append-only:
`ticker, company, first_trading_date, listing_source_id (KAP/BIST duyuru no), status, skip_reason, note, added_at`.
- **Kapsam:** 2026-08-07'den (H99'un son arzı 2026-08-06'nın ertesi günü) itibaren Borsa İstanbul Pay Piyasası'nda halka arz sonucu ilk kez işlem görmeye başlayan her pay. Kapsam dışı (pazar değişimi, borsa dışından kotasyon-halka arzsız, bedelli, fon/varant) bir kayıt da satır alır: `status = OUT_OF_SCOPE` + neden. Sessiz dışlama yok.
- `status ∈ {FROZEN, SKIPPED, OUT_OF_SCOPE}`. `skip_reason ∈ {NO_RECORD_BEFORE_LISTING, PUSH_PROOF_MISSING, INPUTS_NOT_AVAILABLE, OTHER:<metin>}`.
- Model düzeyi ret (ör. `REFUSED_F3_MISSING`) atlama DEĞİLDİR: kayıt vardır, o modelin hücresi "ret + neden"dir.
- Bilinen ilk 7 satır: CITAS, VEYAS, TKNKA, KPEKS, INTET, BKRGY, NETGL (görev metni). İlk işlem tarihleri Faz 2'de resmi kaynaktan; BKRGY/INTET'inki dondurma kayıtlarında yok (PROVENANCE §3a notu).
- Her canlı metrik yanında gösterir: `n_scored / n_refused / n_skipped / n_target_unavailable`.
- Tamlık denetimi: Faz 2'de, dönemin resmi "işlem görmeye başlama" duyuruları listesiyle `ipos.csv` karşılaştırılır; eksik = hata.

## 5. Prospektif / retrospektif: tarihlerden hesap (kural 3)

Girdiler (hepsi git'ten ve kanıt dosyalarından; elle alan yok):
- `commit_frozen(m)`: `models/<m>.json`'u ekleyen commit.
- `outcome_ingest_commit(a)`: §1.
- `push_proof(c)`: `registry/push_proofs/<sha>.json` — sunucu zaman damgalı kanıt (NETGL'deki yöntem: GitHub commit status `created_at`; `registry/legacy_frozen/NETGL_20260916_V1_5/push_proof.json:4`). c'nin kendisi ya da c'yi içeren bir torun commit için olabilir; zaman = en erken kanıtın `created_at`'i.
- `record(m, a)`: §6'daki birincil kayıt; `commit_record`.
- `D_1(a)`: gerçekleşen ilk işlem günü (Europe/Istanbul tarihi).

```
model_prospective(m, a) = is_ancestor(commit_frozen(m), outcome_ingest_commit(a))      # saat kullanmaz
                          AND push_proof(commit_frozen(m)) var
record_live(m, a)       = push_proof(commit_record).created_at [Europe/Istanbul tarihi] < D_1(a)
inputs_pit_ok(rec)      = her girdi alanı için kaynak belge kimliği + yayın zamanı < D_1(a) kayıtlı
                          (f6 için ref_date ≤ D_1 ve S0 < ref_date)

class(m, a) = LIVE         if model_prospective AND record_live
            = LATE_RECORD  if model_prospective AND NOT record_live AND inputs_pit_ok
            = RETRO        otherwise
```
- **Teraziler:** "Canlı (prospektif)" = LIVE ∪ LATE_RECORD; her zaman `n_live / n_late` kırılımıyla ve ayrı alt satırlarla. "Backtest (retrospektif walk-forward)" = H99 fold ledger'ları. RETRO sınıfındaki yeni arzlar üçüncü, yalnız bilgi amaçlı bir listede; hiçbir teraziye girmez. İki terazi hiçbir tabloda toplanmaz, ortak ortalama alınmaz.
- LATE_RECORD'ın anlamı ve sınırı [ÇIKARIM]: model parametreleri sonucu göremez (DAG + push), `predict` deterministiktir; tek açık kanal girdi toplayanın sonucu biliyor olmasıdır (ör. hangi talep katı tanımı). Bu yüzden `inputs_pit_ok` zorunlu ve satır etiketi görünür. 7 arz Faz 1 modelleri için bu sınıfa girer.
- H99'un 99 arzı her model için RETRO'dur (sonuçları `ff3eee6`'da, her modelden önce).
- Push kanıtı olmayan model commit'i → o model için hiçbir arz prospektif değildir ("zaman kanıtı yok").
- Sıra kuralı denetimi (test): `outcome_ingest_commit` herhangi bir post-2026-08-06 arz için varsa, Faz 1 model JSON'larının hepsi onun atası olmalı; değilse CI kırmızı.

## 6. Hangi kayıt skorlanır (birincil kayıt, önceden ilan)

Bir (model, arz) çifti için birden çok kayıt olabilir. Skorlanacak olan, sonuç görülmeden şu kuralla belirlenir:
- f3 isteyen modeller (`v1_5_h99`, `v1_6_h99`, `v1_5_market20_v0`, `ceiling_hazard_v0`): resmi f3 içeren kayıtlar arasında, D_1'den önce push kanıtlı **en son** kayıt. Yoksa en erken LATE_RECORD.
- PB modelleri (`pb_v0`, `pb_ceiling_v0`) ve basit kurallar: **en erken** kayıt. Kayıt ilk talep toplama gününden sonra oluşturulduysa `pb_after_bookbuild_start = 1` işareti (PB girdileri planlanan yapıdır, değişmez; yine skorlanır).
- İptal edilmiş kayıt (kural 1: "iptal kaydı düşülür") skorlanmaz; iptal nedeni ve zamanı görünür. İptal, D_1'den sonra yapılamaz.
- Dondurulmuş değer asla yeniden hesaplanmaz. Aynı (model, arz) için JSON'dan sonradan üretilen değer yalnız **parite denetimidir** (beklenen |Δ| ≤ 1e-9), skora girmez.

### Legacy dondurmaların rolleri (`registry/legacy_frozen/`, PROVENANCE §3a)

| Kayıt | model_id | f3 | Zaman kanıtı | Rol |
|---|---|---|---|---|
| `NETGL_20260916_V1_5` | `v1_5_h99` | 2.84 | **git+push** (commit `5f70ace…`, status `created_at` 2026-09-16T11:32:27Z; D_1 = 2026-09-17) | birincil, LIVE |
| `BKRGY_20260827_…POST_BOOKBUILD_PRE_LISTING` | `v1_5_h99` | 1.77 | self-reported (git'e ilk giriş `d7e8453`, 2026-09-06) | birincil; sınıf `LEGACY_SELF_REPORTED` |
| `INTET_20260831_…POST_BOOKBUILD_PRE_LISTING` | `v1_5_h99` | 1.7 | self-reported | birincil; `LEGACY_SELF_REPORTED` |
| `TKNKA_20260819_V1_5_FULL20` | **`v1_5_full20`** (n = 20/20/20/19) | 6.45 | self-reported (`c2a56fb`, 2026-09-06) | birincil, ama AYRI model; `v1_5_h99` sütununa yazılmaz |
| `BKRGY_20260825_V1_5` (R1), `…_R2`, `INTET_20260825_V1_5` (PRE) | `v1_5_h99` | yok (f5 = 1) | self-reported | **geçersiz kullanım**: tabloda gri, "f3'süz; model bugün RET eder" notuyla; hiçbir metriğe, hiçbir n'e girmez |

- `LEGACY_SELF_REPORTED`: kayıt zamanı yalnız kendi beyanı; §5 formülü bunlara LIVE veremez (push kanıtı yok). Canlı tabloda ayrı alt satır; canlı metrik iki biçimde verilir: "yalnız kanıtlı (LIVE + LATE_RECORD)" birincil, "+ self-reported" ikincil.
- Legacy kayıtlar kural 1'in "tüm modeller birlikte" şartını sağlamaz (yalnız V1.5 içerir); içe aktarmada `legacy_import = true`, özgün dosya sha256'sı ve eski commit referansıyla işaretlenir, içerik değiştirilmez.
- CITAS, VEYAS, KPEKS: eski düzende dondurma yok → `v1_5_h99` için de yalnız LATE_RECORD olabilir.
- TKNKA: `v1_5_h99` ve diğer Faz 1 modelleri için LATE_RECORD; `v1_5_full20` için tek satırlık kendi listesi (n = 1, metrik yok).

## 7. Metrikler

Hepsi "model − kural" eşleşik fark olarak, aynı arz kümesinde (ikisinin de skorlandığı arzlar), negatif = model iyi. Birim: getiri hataları **puan** (0.030 = 3 puan).

| Çıktı | Birincil | İkincil |
|---|---|---|
| R_h (h = 1, 3, 5, 10) | MAE | MedAE; yön isabeti (işaret(R̂) ile Y_h) — her zaman "hep yukarı" kuralının isabetiyle yan yana |
| p_up_h | Brier | log-kayıp (p ∈ [1e-6, 1 − 1e-6] kırpılı); 0.5 eşikli isabet, taban oranıyla yan yana |
| S_k = P(L ≥ k) | **RPS = (1/10) Σ_{k=1..10} (S_k − 1[L ≥ k])²** | k ∈ {1, 3, 5, 10} için Brier; kalibrasyon: ort(S_k) ve gözlenen oran |
| P_close_ceiling_k | k ∈ {1, 3, 5, 10} Brier | — |

- Kurallar: getiri → `base_always_ceiling` (1.1^h − 1), `base_train_median`, `base_train_mean`, `base_zero`; p_up → `base_rate`, `base_last10_rate`; tavan → `base_km_expanding`, `base_km_last10`, `base_always_ceiling`, `@INF`, `v1_5_p_up_as_ceiling` (SPEC_CEILING_V0 §10). Canlıda kuralların değeri de dondurma kaydındadır (kural 1), sonradan hesaplanmaz.
- Her satırda: model değeri · kural değeri · fark · [%95 aralık] · n · kazanç/kayıp sayısı (arz bazında |hata| karşılaştırması; eşitlik ayrı sayılır).
- Ufuklar ve çıktılar birleştirilmez; "genel doğruluk" tek sayısı üretilmez.
- Her model için önceden ilan edilmiş birincil hücre (çoklu karşılaştırmaya karşı): `ceiling_hazard_v0`, `pb_ceiling_v0` → RPS; `pb_v0` → D5 MAE vs medyan; `v1_5_market20_v0` → D5 MAE vs `v1_5_h99`; `v1_6_h99` → D10 MAE vs `v1_5_h99`; `v1_5_h99` → D5 MAE vs medyan. Diğer hücreler "keşif" etiketiyle gösterilir.

## 8. Aralıklar ve küçük-n gösterim kuralları (AUDIT §1.2-c, §3d)

Blok bootstrap:
- Blok = gerçekleşen D_1'in takvim ayı (`YYYY-MM`). Bloklar yerine koyarak, blok sayısı kadar çekilir; istatistik = çekilen tüm satırların eşleşik fark ortalaması.
- B = 4000; `numpy.random.Generator(PCG64(20260921))`; yüzdelik aralık [2.5, 97.5]. Aynı girdi → aynı aralık (test).
- Koşul: n ≥ 10 **ve** ≥ 6 ayrı blok. Sağlanmıyorsa aralık ÜRETİLMEZ ("aralık için yetersiz").
- Gerekçe: arz pencereleri çakışıyor (medyan 4 komşu, AUDIT §2.5) ve rejim yıllara göre değişiyor (§2.4); iid aralık fazla dar.

Dil ve gösterim:
| Durum | Gösterilen |
|---|---|
| n < 10 | YALNIZ satır tablosu: arz, sınıf (LIVE/LATE/…), tahmin, gerçekleşen, her kuralın tahmini. Metrik, ortalama, renk yok |
| 10 ≤ n < 30 | metrik + fark + aralık (koşul tutuyorsa) + **"yetersiz örnek"** etiketi; kazanan vurgusu yok |
| n ≥ 30 | tam satır; aralık 0'ı dışlıyorsa "geçiyor" / "geçemiyor", içeriyorsa **"ayırt edilemiyor"** |
- "Geçiyor" sözcüğü başka hiçbir koşulda kullanılmaz (kural 6). Noktasal fark tek başına hüküm değildir.
- Backtest paneli başlığı: "Geçmiş veri testi (retrospektif, tasarıma maruz)"; canlı panel: "Canlı sicil (prospektif, n = k; atlanan = s)". Ayrı renk; aralarında toplam/ortalama yok.
- Model kartı: model_id, eğitim n ve kesim, param sha ilk 8 hane, `experiments/log.jsonl`'daki aynı veri sürümünde denenen varyant sayısı.
- İsabet oranı asla tek başına gösterilmez.

## 9. Sözde kod

```
def resolve_sessions(ticker, calendar, thb_by_date):
    out = []; seen = 0
    for s in calendar.sessions_from(first_thb_appearance(ticker)):
        seen += 1
        if seen > 15: break
        row = thb_by_date[s].get(ticker)
        if row and Decimal(row.trade_count) > 0 and Decimal(row.close) > 0:
            out.append(Session(date=s, h=len(out)+1, close=Decimal(row.close),
                               halt_flag=(row.gecici_durdurma == "1"), half_day=calendar.is_half(s)))
            if len(out) == 10: break
    return out                                    # eksik ufuklar TARGET_UNAVAILABLE

def ceiling_label(session, thm_by_date):
    lim = thm_by_date[session.date].get(ticker)
    if lim is None or lim.upper in ("", None) or Decimal(lim.upper) <= 0: return NA
    return int(session.close == Decimal(lim.upper))

def classify(m, a):  §5'teki formül; is_ancestor = `git merge-base --is-ancestor`

def paired_metric(model_vals, rule_vals, truth, loss):
    rows = arzlar where ikisi de skorlanmış
    d = [loss(model, t) - loss(rule, t) for rows]
    return mean(d), block_bootstrap_ci(d, blocks=month(D_1)), n, wins, losses, ties

def block_bootstrap_ci(d, blocks, B=4000, seed=20260921):
    if len(d) < 10 or len(set(blocks)) < 6: return None
    rng = Generator(PCG64(seed)); ids = sorted(set(blocks)); by = {b: [d_i ...]}
    stats = [mean(concat(by[b] for b in rng.choice(ids, size=len(ids), replace=True))) for _ in range(B)]
    return percentile(stats, [2.5, 97.5])
```
Rol ayrımı (AUDIT §3e): Python indirir + skorlar → `scores.json` (veri sürümü ve "şu tarih itibarıyla" damgalı); uygulama skor HESAPLAMAZ, yalnız gösterir.

## 10. Kabul testleri

1. **H99 yeniden üretim:** `resolve_sessions` + `ceiling_label`, H99 ham alanlarıyla (SESSIONS dosyasının `thb_raw_*`, `thm_raw_*` sütunları) çalıştırılınca: 990 seans tarihi, 396 hedef (`R_Dh` Decimal-eşit, `Y_Dh`), 990 tavan etiketi ve 99 `L` değeri `training_table.csv` ile birebir; toplamlar 81/67/48/25 ve 81/66/41/14.
2. **Yarım gün:** EKDMR D3 ve GENKM D10 yarım gün seansına düşer ve sayılır.
3. **Durdurma (sentetik):** 4. resmi seansta sözleşme = 0 → D_4 bir sonraki seansa kayar, `shifted_by_suspension = 1`, seri bozulmaz. `GECICI DURDURMA = 1` + sözleşme > 0 → sayılır, `halt_flag = 1`. 15 seans sınırı → `TARGET_UNAVAILABLE`.
4. **Tavan etiketi:** close "10.12", limit "10.120" → 1 (Decimal eşitliği); close 10.11 → 0; limit boş → NA. LILAK/BORLS D1 (R_D1 ≠ 0.1) etiketi 1.
5. **Sınıflama:** geçici bir git deposunda kurulan senaryolar: (a) model → kayıt+kanıt → sonuç ⇒ LIVE; (b) model → sonuç, kayıt sonra ⇒ LATE_RECORD; (c) sonuç → model ⇒ RETRO; (d) push kanıtı yok ⇒ RETRO; (e) `inputs_pit_ok` yanlış ⇒ RETRO. Kodda elle sınıf alanı YOK (şema testinde alan adı aranır).
6. **Birincil kayıt:** BKRGY'nin üç legacy kaydından yalnız `…20260827_POST_BOOKBUILD…` skorlanır; R1/R2 `invalid_use`; NETGL sınıfı LIVE, zaman kanıtı `git+push`; TKNKA `v1_5_h99` metriklerinde yok.
7. **Payda:** `ipos.csv`'de `FROZEN` olmayan her satırın `skip_reason`'ı dolu; bilinen 7 ticker var; metrik çıktısı `n_skipped` taşır.
8. **Bootstrap:** aynı girdi iki kez → aynı aralık; n = 9 ya da 5 blok → `None`; AUDIT §1.2-c'nin D1 MAE-medyan farkı H99 BLB ledger'ından yeniden hesaplanınca +0.0046 ve aralık [+0.0015, +0.0079]'a ±0.001 içinde (seed farkı payı).
9. **Dil:** aralık 0'ı içeren sentetik sonuçta çıktı metni "ayırt edilemiyor"; n = 7'de metrik alanları boş, satır tablosu dolu; iki teraziyi birleştiren herhangi bir fonksiyon çağrısı hata verir.
10. **Sıra kuralı bekçisi:** `data/outcomes/` altında post-2026-08-06 bir dosya varken `models/INDEX.json`'daki Faz 1 modellerinden biri onun atası değilse test kırmızı.
11. **RPS:** S ≡ 1[L ≥ k] → 0; `base_always_ceiling` ve L = 0 → 1.0; L = 10 → 0.

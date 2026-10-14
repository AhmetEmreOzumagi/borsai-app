# SPEC_OOT_PRE_H99_V0 — H99 öncesi halka arz kohortu: zaman-dışı değerlendirme protokolü (sonuç görülmeden yazılmış, bağlayıcı taslak)

Görev: BORSAI_FAZ6_FABLE_OLD_COHORT_SPEC_20260924. Tarih: 2026-09-24. Durum: **taslak; proje sahibinin §11'deki kararlarından sonra bağlayıcı olur ve push edilir.** Bu belge yazılırken 2020-01-01…2023-09-21 arasında işlem görmeye başlayan hiçbir arzın listeleme sonrası fiyat, getiri, tavan ya da hacim bilgisi okunmadı (maruziyet beyanı: `FEASIBILITY.md` §9).

İşaretler: **[ÖLÇTÜM]** (bu görevde ölçüldü, kanıt `ekler/`), **[ÇIKARIM]**, **[KARAR]** (proje sahibi onayı bekleyen tasarım kararı).

## Özet (≤ 10 satır)

1. Kohort = Borsa İstanbul Pay Piyasası'nda halka arz sonucu ilk kez işlem görmeye başlayan ve ilk işlem günü `[K_başlangıç, 2023-09-21]` aralığında olan bütün paylar; kaynak KAP'taki Borsa İstanbul "Payların İşlem Görmeye Başlaması" bildirimleri; SPK yıllık tabloları ve bülten çapraz denetimi. Üye sayısı 2020: 8, 2021: 52, 2022: 38, 2023 (09-21'e kadar): 37; toplam 135 üye + 1 kapsam dışı (GMTAS: halka arzsız kotasyon) [ÖLÇTÜM `ekler/evren_listesi.csv`]; kapsam dışı satırlar sessizce silinmez, `OUT_OF_SCOPE` + neden alır.
2. Üçüncü ölçek: **ZD (zaman-dışı) eski kohort**: tahminler donmuş modellerle, sonuç repoya girmeden yazılır (prospektif kayıt), ama dönem eğitim penceresinden öncedir (retrospektif zaman). Backtest ve canlıyla hiçbir tabloda toplanmaz; `ScaleMixError` üçüncü değeri tanır.
3. Sıra, git DAG'ı ve push kanıtıyla zorlanır: şartname → üyelik + girdiler → 19 listeleme öncesi modelin kayıtları (**kohortun tamamı için**) → D1 satırları + `post_d1_hazard_v0` → D2..D10 → skorlama. Günlük bülten bütün payları içerdiğinden kapı **kohort düzeyindedir**: tek bir pencere-içi bülten, kohortun bütün listeleme öncesi kayıtları push edilmeden repoya giremez.
4. Girdiler yalnız listeleme öncesi resmi belgelerden (KAP bildirimi, izahname/TSSD, SPK bülteni); her alan kaynak kimliği + yayın zamanı + sha256 taşır (`borsai.inputs/1` şeması aynen). Sonuç yalnız resmi THB/THM'den, `borsai/outcomes.py` tanımlarıyla.
5. Skorlama SPEC_SCORING §7–§8 ile aynı: eşleşik fark + ay-blok bootstrap + n; her modelin birincil hücresi backtest/canlıdakiyle aynı; karşılaştırıcılar H99'da donmuş basit kurallar (yeniden eğitilmez).
6. Rejim farkları önceden etiketlenir (`regime_tags`); bir modelin uygulanamadığı arz "atlandı" değil, o model için "uygulanamaz + neden" hücresidir.
7. Kasa: kohortun yıl içinde tabakalı, tohumlu %50'si mühürlenir; mühürlü arzların bültenleri, (C) için yeni bir özellik ön-kayıtlanıp push edilmeden repoya girmez.
8. Önceden yazılmış beklentiler §8'de; LLM ön bilgisi maruziyeti açıkça not edildi.
9. Açık sorular §11 (5 madde, her birine öneri).

---

## 1. Kohort üyeliği (deterministik)

**Kaynak sırası ve kural [KARAR].**
- K1: KAP'ta Borsa İstanbul A.Ş. tarafından "Payların İşlem Görmeye Başlaması" konusuyla yayımlanmış her bildirim (`byCriteria`, `subjectList = 8aca490d4ff02191014ff03637790093`, `memberType = IGS`), yayın tarihi `[K_başlangıç − 15 gün, 2023-09-21]`.
- Bildirim PDF'inden (`api/BildirimPdf/<id>`) okunan alanlar: şirket unvanı, işlem görecek nominal, baz fiyat, pazar, **İşlem Görmeye Başlayacağı Tarih** (= aday `first_trading_date`), Halka Arz Yöntemi, Halka Arz Tarihi.
- Üye = bildirimde "Halka Arz Yöntemi" alanı dolu (Borsada / Borsa Dışında) VE `first_trading_date ∈ [K_başlangıç, 2023-09-21]` VE enstrüman pay (`.E`). Düzeltme bildirimleri (`Yapılan Açıklama Düzeltme mi? = Evet` ya da özet "Baz Fiyat Düzeltmesi") aynı arzın satırını günceller, yeni satır açmaz.
- `OUT_OF_SCOPE` (satır kalır, neden yazılır): kısmi bölünme/ spin-off, pazar değişikliği, PÖİP'e geçiş, gayrimenkul sertifikası, BYF, varant, halka arzsız kotasyon, nitelikli yatırımcıya satış sonrası işlem görme, yeni pay grubu.
- Çapraz denetim: SPK "Payların İlk Halka Arzı YYYY" tabloları (2020: 8 satır; 2021: 32 satır, **Ağustos 2021'de kesilmiş, 2021 Eylül–Aralık arzları yok** [ÖLÇTÜM]; 2022: 38; 2023: 39) ve SPK haftalık bülteni "A.1 İlk Halka Arzlar" tablosu (izahname onayı). SPK'da olup KAP'ta bildirimi olmayan arz → `MEMBERSHIP_CONFLICT`, elle incelenir, çözülene kadar `PENDING`.
- `first_trading_date` = KAP bildirimindeki tarih. Skorlamada gerçekleşen D_1 (THB'de `.E` satırının sözleşme > 0 olduğu ilk resmi seans, **bildirim tarihinden önce olmamak üzere**) kullanılır; "borsada satış" arzlarında birincil piyasa günü bu kuralla dışarıda kalır (SPEC_SCORING §2 "fark raporlanır").
- `K_başlangıç` [KARAR, §11-1]: öneri **2020-01-01**. Kohort penceresi H99'un ilk üyesi HATSN'nin (2023-09-22) bir önceki günü ile biter. H99'un eksik 100. üyesi, KAP bildirimlerine göre **REEDR (Reeder Teknoloji, ilk işlem 2023-09-21)**; bir önceki ADGYO (2023-09-20) [ÖLÇTÜM: 2023-09-15…2026-08-06 aralığındaki bildirimlerde H99'un 99 üyesinin hepsi var, fazladan yalnız ADGYO ve REEDR var; H99 kurucu script REEDR'i "unresolved" diye dışarıda tutmuş, `ekler/arsiv_tarama_1.txt` §5]. REEDR ve ADGYO bu kohortun üyesidir; H99'a geri eklenmez (HISTORICAL99 dondurma kuralı).

**Payda dosyası [KARAR].** `registry/oot/cohort_pre_h99.csv` (append-only): `ticker, company, first_trading_date, listing_source_id (KAP_<id>), listing_source_sha256, sale_method, market, year, status ∈ {MEMBER, OUT_OF_SCOPE, PENDING}, reason, vault ∈ {OPEN, SEALED, EXPOSED_ARCHIVE}, regime_tags, added_at`. Sonuç verisinden ÖNCE commit edilir ve push edilir (`registry/push_proofs/`). Üyelik sonradan değişmez; hata bulunursa `CANCELLED` satırı düşülür, eski satır kalır.

**Her üye bir satırdır.** Girdisi eksik üye "atlandı" değildir: `registry/oot/inputs/<T>.json` yine yazılır, eksik alan `missing_reason` taşır; modeller kendi ret kodlarını üretir (`REFUSED_F3_MISSING`, `REFUSED_PB_PRICE_RANGE`, …). Kayıt hiç yazılamayan (ör. arz fiyatı bile resmi belgede bulunamayan) üye `SKIPPED: INPUTS_NOT_AVAILABLE` + neden alır ve `n_skipped`'e girer.

## 2. Sıra (kodla zorlanacak) ve bekçiler

Adımlar; her adım ayrı commit(ler) + push + `registry/push_proofs/<sha>.json` (GitHub commit status `created_at`; `borsai.push_proof`):

| # | Adım | Yazılan yollar | Bekçi (`tests/test_outcome_guard.py` kalıbı) |
|---|---|---|---|
| S0 | Şartname (bu belge, proje sahibi kararlarıyla) | `docs/specs_faz6/` | — |
| S1 | Üyelik + girdiler + kaynak belgeler | `registry/oot/cohort_pre_h99.csv`, `registry/oot/inputs/<T>.json`, `registry/oot/source_docs/<T>/` | G1: `registry/oot/` altında hiçbir sonuç alan adı yok (`OUTCOME_KEYS` seti); her girdi alanının `source_published_at` < `first_trading_date` (Istanbul); belge sha eşleşir |
| S2 | 19 listeleme öncesi donmuş modelin tahmin kayıtları, **kohortun her MEMBER satırı için** | `registry/oot/records/<T>/<UTC>_<sha>.json` (`borsai.oot_record/1`; `registry/records/` DEĞİL) | G2: kayıt `models/INDEX.json`'daki bütün modelleri içerir (ret hücreleri dahil); kayıt commit'i her model JSON commit'inin torunu; kayıt yeniden yazılmaz (iptal kaydı) |
| S3 | D_1 satırları (yalnız `<T>.E`, yalnız D_1 tarihli) + `post_d1_hazard_v0` kayıtları | `registry/oot/d1_rows/<T>.json`, `registry/oot/post_d1/<T>/…json` | G3: `d1_rows` dosyasında yalnız o arzın ve yalnız D_1 tarihinin alanları (şema testi); dosyanın taşıdığı zip sha'sı S5'te gelen zip ile eşleşmeli; S3 commit'i **kohortun bütün S2 kayıtlarının** torunu (kohort düzeyi kapı) |
| S4 | (isteğe bağlı, kasa yoksa atlanır) — | — | — |
| S5 | Pencere-içi ham THB/THM zip'leri (**OPEN** üyelerin D_1…D_10'unu kapsayan tarihler) + `data/outcomes_oot/<T>.csv` | `data/raw/bist/{thb,thm}/YYYY/…zip`, `data/raw/bist/MANIFEST.csv`, `data/outcomes_oot/` | G5: tarihi kohort penceresinde olan HER zip'i ekleyen commit, (a) `cohort_pre_h99.csv`'yi, (b) OPEN kümedeki her üyenin S2 kaydını ve (c) varsa S3 kaydını ekleyen commit'lerin torunu olmalı; S2 kayıt commit'inin push kanıtı `created_at`'i zip commit'inin push kanıtından **önce** olmalı. SEALED bir üyenin D_1…D_10'una denk gelen tarihli zip → kırmızı (bkz. §9) |
| S6 | Skorlama (`scores.json` → `oot_pre_h99` bloğu) | `scores/` | G6: `scale = OOT_PRE_H99` satırları başka ölçekle aynı fonksiyona giremez |

**Kohort düzeyi kapı neden zorunlu [ÇIKARIM].** THB/THM günlük bültenleri o gün işlem gören bütün payları taşır. 2021'de aynı hafta içinde birden çok arz var [ÖLÇTÜM: örn. 2021-04-26 tarihli üç bildirim, 2021-06-03 iki]. Bir arzın D_1 zip'i, ondan önce listelenen arzların D_2…D_10 kapanışlarını içerir. Bu yüzden "arz başına sıra" yeterli değildir; pencere-içi ilk zip repoya girdiği an OPEN kümenin bütün listeleme öncesi kayıtları push edilmiş olmalıdır. Aynı nedenle `post_d1` için S3 zip'i commit etmez; yalnız D_1 satırını ayıklar (ayıklama kodla; test: satır sayısı 1, tarih = D_1, kod = `<T>.E`; zip sha kayda yazılır, zip S5'e kadar repo dışında karantinada tutulur). Bu, canlı POST_D1'deki insan-körlüğünden zayıftır: makine bütün zip'i görmüştür, insan görmemiştir. Bu kayıtlar `exposure_class = MACHINE_SEQUENCED` etiketi taşır ve `post_d1` ZD sonuçları bu etiketle raporlanır (§11-5).

**Sınıf hesabı (elle etiket yok; SPEC_SCORING §5 kalıbı).**
```
oot_ingest_commit(a)   = min( data/outcomes_oot/<a>.csv'yi ekleyen commit,
                              tarihi ∈ [D_1(a), D_10(a)] olan herhangi bir THB/THM zip'ini ekleyen ilk commit )
oot_blind(m, a)        = is_ancestor(commit_frozen(m), oot_ingest_commit(a))
                         AND is_ancestor(commit_record_oot(m, a), oot_ingest_commit(a))
                         AND push_proof(commit_record_oot).created_at < push_proof(oot_ingest_commit).created_at
                         AND cohort_gate_ok(a)      # OPEN kümedeki HER üyenin S2 kaydı oot_ingest_commit(a)'nın atası
class_oot(m, a) = OOT_BLIND if oot_blind else OOT_RETRO   # OOT_RETRO yalnız bilgi listesinde, hiçbir n'e girmez
```
`post_d1` için ayrıca `d1_rows` sha'sı S5 zip'iyle eşleşmeli ve S3 commit'i zip commit'inin atası olmalı; değilse `OOT_RETRO`.

**Var olan bekçilerle uyum.** `test_outcome_guard.py` bugün 2026-08-19 sonrası bültenleri ve post-08-06 arzları denetler; 2020–2023 tarihli zip'ler bu filtreye girmez ve `data/raw/bist/` altında bulunabilir (yol testi geçer). Genişletme: `BULLETIN_FILE` tarihi kohort penceresindeyse G5 uygulanır; `test_new_ipos_appear_in_data_only_as_outcomes` kalıbı kohort kodları için `data/outcomes_oot/` ve `data/raw/bist/` dışında yasak olacak biçimde genişler; `registry/oot/` için `registry/records/` sonuç-alanı yasağı aynen (`d1_rows` ve `post_d1` istisnası SPEC_POST_D1 §7.4 kalıbıyla).

## 3. Üçüncü ölçek: ZD (zaman-dışı) eski kohort

- **Ad:** `OOT_PRE_H99` (uygulamada "Zaman-dışı test: H99 öncesi kohort (2020–2023), tahminler sonuç repoya girmeden dondurulmuş").
- **Tanım:** (model, arz) çifti için `class_oot = OOT_BLIND` olan hücreler. Backtest'ten farkı: model parametreleri bu arzlarla hiç fit edilmemiştir ve tahmin kaydı sonuçtan önce push edilmiştir (walk-forward "fold" değil, gerçek dondurma). Canlıdan farkı: dönem, eğitim penceresinden **öncedir**; kural rejimi farklıdır (§7); kayıt zamanı D_1'den yıllarca sonradır (`record_live` tanımsız). Bu yüzden ne "canlı sicil"e ne "geçmiş veri testi"ne eklenebilir.
- **Neden birleşmez [ÇIKARIM]:** (i) canlıyla toplanırsa n hızla büyür ama "ileriye dönük genelleme" iddiası dönem-dışı sonuçla karışır; (ii) backtest'le toplanırsa "tasarıma maruz" (H99 tasarım kümesi) ile "tasarıma maruz değil" karışır; (iii) rejim farkları (borsada satış, eşit dağıtım öncesi, açığa satış yasağı dönemleri) ayrı raporlanmazsa fark yorumlanamaz.
- **Kod [KARAR]:** `borsai/scoring.py`'de `Scale = Enum(BACKTEST, LIVE, OOT_PRE_H99)`; her metrik satırı `scale` taşır; birleştirme fonksiyonları (`paired_metric`, `block_bootstrap_ci`, tablo üreticileri) farklı `scale` değerli satırlar alırsa `ScaleMixError` (bugünkü iki-terazi hatası üçüncü değere genişler). `scores.json`'da ayrı üst anahtar `oot_pre_h99` (kendi `as_of`, `cohort_sha256`, `n_member / n_out_of_scope / n_open / n_sealed / n_exposed_archive`).
- **Uygulamada gösterim:** üçüncü panel, ayrı renk, başlık "Zaman-dışı test (H99 öncesi kohort, rejim farklı)"; her satırda yıl kırılımı düğmesi; canlı ve backtest panelleriyle aynı ekranda toplam/ortalama yok; model kartında üçüncü satır "ZD: n, birincil hücre farkı, aralık".

## 4. Girdiler (listeleme öncesi; şema `borsai.inputs/1` aynen)

| Alan grubu | Eski kohortta kaynak | Yayın zamanı kanıtı | Not |
|---|---|---|---|
| `ipo_price_tl`, `shares_offered`, `post_ipo_share_capital`, `capital_increase_shares`, `existing_share_sale_shares`, `additional_sale_shares` | Aracı kurumun KAP "halka arz sonuçları"/ÖDA bildirimi (kesin değerler) → yoksa BIST "Payların İşlem Görmeye Başlaması" bildirimi (nominal, baz fiyat, sermaye) → SPK bülteni A.1 tablosu (planlanan; DATA_NOTES §2 taşıma kuralıyla) | KAP PDF başlığı "KAP'ta yayınlanma tarihi ve saati" (2019'dan beri aynı biçim [ÖLÇTÜM `ekler/ornek_denetim.md`]) | 2020–2021'de "Halka Arz Sonuçları" şablonu yok ise serbest metin ÖDA; `total_demand_definition` metni satır başına saklanır |
| `total_demand_multiple` (+origin, filter_status) | Aynı sonuç bildirimi; borsada satış arzlarında çoğunlukla YOK → boş + `missing_reason = SALE_METHOD_ON_EXCHANGE_NO_BOOKBUILD_MULTIPLE` | aynı | SPK yıllık tablosundaki "Talebin Halka Arza Oranı" yalnız çapraz denetim; **girdi değeri olarak alınmaz** (ikincil derleme, yayın zamanı listeleme sonrası) |
| PB alanları (`ipo_price_try`, `planned_*`) | SPK haftalık bülteni A.1 "İlk Halka Arzlar" (2020'de de aynı sütunlar: Mevcut/Yeni Sermaye, Bedelli, Bedelsiz, Mevcut Pay Satışı, Ek Pay Satışı, Satış Fiyatı [ÖLÇTÜM 2020/6, 2020/75]) → yoksa izahname/TSSD | Bülten tarihi (başlıkta), URL ObjectId zamanı; talep toplamanın ilk gününden önce olmalı (`pit_status` H99 kuralı) | Fiyat aralığıyla arzlar (ör. 2020/75 Arzum 15,50-17) → `REFUSED_PB_PRICE_RANGE` (SPEC_PB_V0 §5, H99'da hiç yoktu; eski kohortta 2021'de en az 6 [ÖLÇTÜM SPK tablosu]) |
| `first_trading_date`, `bookbuilding_start/end` | BIST KAP bildirimi (Halka Arz Tarihi, İşlem Görmeye Başlayacağı Tarih) | aynı | — |
| f6 (`v1_5_market20_v0`) | XU100 pinli seri (1986'dan beri, 2020–2023'te her seans gününde kapanış var [ÖLÇTÜM `ekler/takvim_2020_2023.md`]) + Takvim C (2020-01-01…2023-09-21; BIST tatil tabloları + XU100 gün kümesi) | — | `ref_date = first_trading_date` (backtest tanımı; SPEC_MARKET20 §4-e). Takvim C yeni veri dosyasıdır; SPEC_MARKET20 §3 kuralları aynen |
| Tavan yolu (`ceiling_path_v0`, `pb_ceiling_path_v0`) | Arz fiyatı + **dönemin fiyat adımı tablosu** (§7) | — | JSON'daki 2026 tablosuyla dönem tablosu aynı yolu vermiyorsa o arzda model "uygulanamaz" (§7-R3) |
| D1 alanları (`post_d1_hazard_v0`) | D_1 tarihli THB/THM `<T>.E` satırı; sütun adları 2019'dan beri aynı (THB'de tek fark 2026'da eklenen `BIST KATILIM TUM ENDEKS`; THM bayt-eşit başlık) [ÖLÇTÜM `ekler/bulten_bicim_probu.txt`] | zip `Last-Modified` | S3 kalıbı (§2) |

Her `registry/oot/inputs/<T>.json` ayrıca `regime_tags` (§7) ve `vault` değerini taşır. Tahmin, türetme, ikincil kaynaktan doldurma yok (FAZ2A kuralı).

## 5. Tahmin kayıtları (`borsai.oot_record/1`)

`borsai.freeze` ile aynı üretici, yalnız dizin ve şema adı farklı: `record_type ∈ {PREDICTION, CANCELLATION}`, `record_stage = "OOT_PRE_LISTING"`, `scale = "OOT_PRE_H99"`, `ticker`, `cohort_file_sha256`, `inputs_sha256`, `models_index {path, sha256}`, `models[] {model_id, params_sha256, status ∈ {PREDICTED, REFUSED, NOT_APPLICABLE_REGIME}, refusal, output}`, `comparators` (H99'da donmuş kuralların değerleri: `base_train_median/mean/zero/always_ceiling/rate/last10_rate/km_expanding/km_last10`, kural 1 gereği kayıtta), `regime_tags`, `recorded_at_utc`, `code {git_head, borsai_source_sha256}`.

- `base_last10_rate` ve `base_km_last10` canlıda H99'un son 10 arzına göre donmuştur; eski kohortta "T'den önceki son 10 arz" o dönemin başka üyeleri olur ve onların sonucu körlük altında bilinmez. Bu yüzden ZD'de de **donmuş H99 değerleri** kullanılır ve satır `comparator_note = FROZEN_H99_LAST10_NOT_CHRONOLOGICAL` taşır [KARAR].
- Kayıt kohortun bütün MEMBER satırları için tek toplu koşuda yazılır (`python -m borsai.freeze --oot registry/oot/cohort_pre_h99.csv`); tek commit; push; kanıt. Sonradan eklenen üye (`PENDING` → `MEMBER`) yeni commit + push ile gelir; onun `oot_ingest_commit`'i ona göre hesaplanır.

## 6. Skorlama

- Tanımlar `borsai/scoring.py` (SPEC_SCORING §2–§3): D_h, tavan etiketi (o seansın THM üst limitiyle Decimal eşitliği), L, R_h, Y_h aynen. **Sabit %10 varsayımı yok**; 2020–2023'te marj kuralı değiştiyse (§7) etiket yine THM'yi izler.
- Metrikler §7: eşleşik fark, MedAE ikincil, Brier/log-kayıp, RPS, P_close_ceiling_k. Aralık §8: ay-blok bootstrap, B = 4000, aynı seed; koşul n ≥ 10 ve ≥ 6 blok. Dil kuralları aynen ("geçiyor" yalnız aralık 0'ı dışlarsa).
- **Birincil hücreler (değişmez):** `v1_5_h99` D5 MAE vs `base_train_median`; `v1_6_h99` D10 MAE vs `v1_5_h99`; `v1_5_market20_v0` D5 MAE vs `v1_5_h99`; `pb_v0` D5 MAE vs medyan; `ceiling_hazard_v0`, `pb_ceiling_v0` RPS vs `base_km_expanding`; `ceiling_path_v0` ve `pb_ceiling_path_v0` SPEC_CEILING_PATH_V0 §5 birincil hücresi; `post_d1_hazard_v0` SPEC_POST_D1_V0 §4 birincil hücresi (j = 1 koşullu). Diğer hücreler "keşif".
- **n kuralları:** birincil tablo OPEN küme (kasa dışı) üzerinde; yıl kırılımı ikincil satırlar (2020 n = 8 → yalnız satır tablosu). Rejim alt kümeleri (borsada satış / borsa dışı; eşit dağıtım öncesi/sonrası) ikincil, "keşif" etiketiyle. SEALED küme açıldığında ayrı bir koşu (`oot_pre_h99_sealed`) ve toplam (`oot_pre_h99_all`) üretilir; üçü de ayrı anahtardır, birbirine eklenmez.
- **Sayaçlar:** `n_member, n_out_of_scope, n_open, n_sealed, n_exposed_archive, n_scored, n_refused, n_not_applicable_regime, n_target_unavailable, n_oot_retro`.
- Parite: kayıttaki değerler skora girer; JSON'dan yeniden üretim yalnız |Δ| ≤ 1e-9 denetimidir.

## 7. Rejim farkı kuralları (sonuçtan önce; ayrıntı ve kaynaklar `FEASIBILITY.md` §5)

Her üyeye `regime_tags` yazılır (kaynak: BIST/SPK kural metinleri, arzın kendi belgeleri):

| Etiket | Tanım | Etkilenen model ve kural |
|---|---|---|
| `SALE_ON_EXCHANGE` | "Borsada satış" (birincil piyasa) ile arz | f3 çoğunlukla yok → f3 isteyen 5 model RET (kayıt var, hücre ret); PB modelleri ve kurallar skorlanır; D_1 = ikincil piyasa ilk günü (§1) |
| `PRICE_RANGE_BOOKBUILD` | Fiyat aralığıyla talep toplama | PB modelleri `REFUSED_PB_PRICE_RANGE`; V1.5 ailesi kesin fiyatla çalışır |
| `TICK_TABLE_EPOCH ∈ {T2015, T2023}` | Arzın D_1'inde geçerli fiyat adımı tablosu: 30/11/2015–05/11/2023 dört kademe (0,01/0,02/0,05/0,10; ≥100 TL tek adım 0,10), 06/11/2023'ten itibaren sekiz kademe (JSON'daki tablo). Kohortun tamamı T2015 [ÖLÇTÜM `ekler/kurallar_arastirma.md` §3; 2019-12-31 THM `FIYAT ADIMI` alanı `ekler/bulten_probu`] | R3: `ceiling_path_v0`/`pb_ceiling_path_v0` için C_1..C_10 dönem tablosuyla ve JSON tablosuyla ayrı hesaplanır (yalnız arz fiyatından, sonuçsuz); farklıysa o arzda bu iki model `NOT_APPLICABLE_REGIME: TICK_TABLE_MISMATCH` |
| `MARGIN_RULE ∈ {PRE_20200313, POST_20200313}` | D_1'de geçerli günlük fiyat marjı: 04/11/2019–12/03/2020 Yıldız %20 / Ana G1 %20 / Ana G2 %15; 13/03/2020'den bugüne Yıldız ve Ana %10 (Duyuru 2020/20, hâlâ "ikinci duyuruya kadar") [ÖLÇTÜM `ekler/kurallar_arastirma.md` §1] | `PRE_20200313` üyelerde (2020'de yalnız ARDYZ, D_1 2020-02-06) marj %10 değildir: `base_always_ceiling`, `@INF` ve `ceiling_path_v0` limit yolu (0.10 sabiti) o arzda `NOT_APPLICABLE_REGIME: MARGIN_NOT_10PCT`; tavan etiketi yine THM'den; hazard modelleri (L etiketi) uygulanabilir ama etiketle |
| `SHORT_SELL_BAN` | D_1…D_10 penceresi bir açığa satış yasağı dönemine düşüyor: 02/03/2020→(BIST-30 dışı kaldırılma tarihi BULUNAMADI), 06/02/2023→(yeni arzlar BIST-50 dışı; sürüyor) [`kurallar_arastirma.md` §10] | Model uygulanabilir; alt küme etiketi (keşif) |
| `ALLOC_REGIME ∈ {PRE_20211111, THRESH100_20211111, EQUAL_DIST_20230330}` | 11/11/2021 öncesi eşiksiz; 11/11/2021–29/03/2023 PD ≤ 100 mn TL → borsada satış zorunlu (59/1669); 30/03/2023'ten itibaren PD ≤ 750 mn → borsada satış zorunlu ve borsa dışında bireysele eşit dağıtım zorunlu (i-SPK.128.21) [`kurallar_arastirma.md` §6–7] | Model uygulanabilir; alt küme etiketi; (C) için aday özellik |
| `MARKET ∈ {YILDIZ, ANA, ALT, GIP}` | İşlem göreceği pazar | Alt Pazar/GİP'te marj farklıysa `MARGIN_RULE` ile birlikte |
| `EXPOSED_ARCHIVE` | Arşivde D_2…D_10'unu içeren ham bülten fiziksel olarak var (2023-09-22 ve sonrası zip'ler; D_10 tarihi ≥ 2023-09-22 olan 4 üye: TARKM, GIPTA, ADGYO, REEDR [ÖLÇTÜM, XU100 seans günleriyle]) | Kasaya alınamaz; OPEN'da kalır, `exposure_class = ARCHIVE_PRESENT_NOT_READ` |

Kural: etiketler `cohort_pre_h99.csv`'de S1'de yazılır ve push edilir; S5'ten sonra etiket değişikliği yalnız `CANCELLED` + yeni satırla ve gerekçeyle olur.

## 8. Önceden yazılmış beklenti (birincil hücreler; sonuç görülmeden)

**Maruziyet notu.** Yazar bir dil modelidir; 2020–2023 Türkiye halka arz dalgası hakkında genel bir ön bilgiye sahiptir (ör. bu dönemde ilk gün tavan sıklığının yüksek olduğu ve bireysel katılımın çok arttığı yönünde yaygın kamuoyu izlenimi). Bu, sayısal bir sonuç bilgisi değildir ama bir maruziyettir; aşağıdaki yönler bu izlenimden **bağımsız** olarak mekanizma gerekçesiyle yazılmış, aralıklar geniş tutulmuştur. Hiçbir arzın gerçekleşen değeri okunmamıştır.

| Model / hücre | Yön | Aralık (fark; negatif = model iyi) | Gerekçe |
|---|---|---|---|
| `v1_5_h99` D5 MAE − medyan | belirsiz, hafif kötü | [−0.01, +0.04] puan | f1 nominal TL'dir (SPEC_CEILING_V0 §4 "bilinen zayıflık"): 2020–2021 arz büyüklükleri 2024–2026'dan 5–20 kat küçük → f1 eğitim aralığının çok dışında, ridge çizgisel ekstrapolasyon yapar; f3 tanımları farklı (borsada satış) → ret çok. H99 backtest'te D5'te geçiyordu; dönem farkı bunu silebilir |
| `v1_6_h99` D10 MAE − `v1_5_h99` | ≈ 0 | [−0.01, +0.01] | Aynı özellikler, farklı ızgara; ekstrapolasyon ikisinde de aynı yönde |
| `v1_5_market20_v0` D5 MAE − `v1_5_h99` | ≈ 0, hafif iyi | [−0.01, +0.005] | f6 dönem içinde geniş aralıkta değişmiştir (2020 Mart, 2021 Aralık, 2023 Şubat); H99'da f6 aralığı dar ([−0.112, +0.155]) → aralık dışı uyarı sık; işaret yanlış öğrenilmişse kötüleşir |
| `pb_v0` D5 MAE − medyan | hafif kötü | [−0.005, +0.03] | pb1 (ln büyüklük) aynı ekstrapolasyon sorunu; fiyat aralıklı arzlarda ret |
| `ceiling_hazard_v0` RPS − `base_km_expanding` | belirsiz | [−0.03, +0.03] | Seri süresi dönemler arası kayarsa KM (H99 tabanı) da kayar; f3 etkisi yön olarak korunur; f1 kayması hazard'ı sistematik kaydırabilir |
| `pb_ceiling_v0` RPS − `base_km_expanding` | hafif kötü | [−0.02, +0.04] | f3'süz; pb1 kayması |
| `ceiling_path_v0` birincil | ≈ `ceiling_hazard_v0` ile aynı işaret | [−0.03, +0.03] | Aynı hazard; fiyat adımı tablosu dönemde farklıysa "uygulanamaz" sayısı artar (§7-R3) |
| `pb_ceiling_path_v0` birincil | hafif kötü | [−0.02, +0.04] | — |
| `post_d1_hazard_v0` j = 1 birincil | belirsiz, hafif iyi | [−0.03, +0.02] | D1 kilit ve el değiştirme mekaniği kural rejiminden görece bağımsızdır; `MACHINE_SEQUENCED` etiketiyle |

Başarısızlık tanımı: birincil hücre aralığı 0'ı dışlayıp pozitifse model bu kohortta "geçemiyor"; yıl alt kümelerinde tersine dönüyorsa "rejime bağlı" notu. Beklentiden sapma **modeli değiştirme gerekçesi değildir**; yalnız yeni model kimliği için bilgidir (CLAUDE.md kural 5).

## 9. Kasa (vault) önerisi

**Sorun.** (A) bütün eski arzların sonuçlarını açarsa, (C) için (D1'de tavan yapmayan / arz altına düşen azınlık sınıfını ayıran listeleme öncesi özellik var mı?) hem keşif hem doğrulama aynı, görülmüş kümede yapılır → sahte iyileşme riski. H99'da azınlık sayıları: D1 tavan yok 18, D1 arz altı 10, D10 arz altı 29.

**Seçenekler (n'ler aday listeye göre; kapsam dışı ayıklaması sonrası ±5) [ÖLÇTÜM aday sayıları, ÇIKARIM güç hesabı]:**

| Seçenek | OPEN n | SEALED n | (A) kaybı | (C) kazancı |
|---|---|---|---|---|
| K0: kasa yok | ≈137 | 0 | yok; aralık genişliği referans 1.00 | doğrulama kümesi yok; (C) ancak canlı sicille (ayda ~3 arz; azınlık olayı ayda <1) doğrulanır → yıllar |
| K1: bir yıl mühürlü (2022, n≈39) | ≈98 | ≈39 | aralık ≈1.18× | tek rejim (2022) → doğrulama sonucu o rejime bağlı; azınlık olayı beklenen ≈7/4/11 (H99 oranları aktarılırsa; bilinmiyor) |
| K2: yıl içinde tabakalı tohumlu %50 | ≈69 (2020: 4, 2021: 27, 2022: 20, 2023: 18) | ≈68 | aralık ≈1.41× | her rejimden örnek; azınlık olayı beklenen ≈12/7/20; keşif kümesi = OPEN ∪ H99 ≈ 168 (azınlık ≈30/17/49) |
| K3: tabakalı %33 | ≈92 | ≈45 | aralık ≈1.22× | azınlık ≈8/5/13 → doğrulama gücü zayıf (ikili özellik için tek yönlü test, fark 20 puan bile 45 gözlemde ayırt edilemeyebilir) |

**Öneri: K2.** Gerekçe: (A)'nın amacı "modeller rejim değişince ne kadar bozuluyor" sorusuna işaret vermektir; 69 arz + yıl kırılımı buna yeter (10 ≤ n < 30 kırılımlar "yetersiz örnek" etiketiyle görünür). (C) için doğrulama kümesinde en az ~10 azınlık olayı olmadan hiçbir özellik "geçiyor" diyemez; K2 bunu en olası sağlayan seçenektir. Tohum: `numpy.random.Generator(PCG64(20260924))`, tabaka = ilk işlem yılı, sıralama (first_trading_date, ticker); `EXPOSED_ARCHIVE` etiketliler tabakadan çıkarılıp OPEN'a yazılır (kasaya giremez). Kasa listesi S1'de push edilir. **Açılma koşulu:** `docs/specs_faz7+/SPEC_<özellik>.md` içinde (C) için özellik tanımı, eşik, birincil hücre ve beklenti push edilmiş ve bekçi bunu görmüş olmalı; açılış tek commit, tek seferlik; ikinci bir özellik için yeni kasa ancak canlı sicilden kurulur.

**Alternatif [KARAR, §11-3]:** proje sahibi (A)'yı öncelerse K3; (C)'yi öncelerse K2.

## 10. Uygulama etkisi (yalnız ana hatlar)

- `borsai/registry.py`: `OOT_DIR = registry/oot`, `read_cohort`, `validate_cohort`, `regime_tags` doğrulaması.
- `borsai/freeze.py`: `--oot` toplu kayıt; `record_stage = OOT_PRE_LISTING`; `--oot-post-d1` (S3, d1_rows'tan).
- `borsai/outcomes.py`: `download_range` kohort penceresi için `sequence_guard_oot` (kohort düzeyi kapı) ve `quarantine_dir` (S3 için repo dışı indirme + tek satır ayıklama).
- `borsai/market20.py`: Takvim C (2020-01-01…2023-09-21) yeni pinli dosya (`data/raw/pay_calendar_c_20200101_20230921.csv`); yarım günler BIST tatil tablolarından (ekler/takvim).
- `borsai/scoring.py`: `Scale` enum, `class_oot`, `oot_pre_h99` bloğu, `ScaleMixError` genişlemesi.
- `tests/test_outcome_guard.py`: G1, G3, G5, G6 (§2).
- Uygulama: üçüncü panel (§3).

## 11. Açık sorular (proje sahibine; her birine öneri)

1. **Kohort başlangıcı: 2020-01-01 mi 2021-01-01 mi?** Öneri: **2020-01-01**. 2020'de yalnız 8 arz var ve Mart–Ekim 2020 açığa satış yasağı rejimi; ama ayrı yıl tabakası olarak zarar vermez, "rejim farklıyken ne olur" sorusuna 8 ek gözlem verir. 2021 öncesi kural farkları (fiyat adımı tablosu vb.) etiketle çözülür. 2019 ve öncesi alınmaz (SPK tabloları 2019'da farklı biçimde ve BISTECH öncesi bültenler farklı olabilir; ayrı karar).
2. **CLAUDE.md kural 3 cümlesi.** Öneri: "Üç terazi, asla toplanmaz: backtest (retrospektif walk-forward), canlı (prospektif) ve zaman-dışı eski kohort (2023-09-22 öncesi arzlar: tahmin kaydı sonuç repoya girmeden push edilir, ama dönem eğitimden öncedir; sınıf tarihlerden hesaplanır). Eski kohortun pencere-içi hiçbir THB/THM bülteni, kohortun bütün listeleme öncesi kayıtları push edilmeden repoya alınmaz." Sıra kuralı satırına ek: "2020-01-01…2023-09-21 tarihli THB/THM verisi, `registry/oot/` kayıtları push edilmeden repoya alınmaz."
3. **Kasa oranı.** Öneri K2 (%50, yıl içinde tabakalı, tohum 20260924). (A) önceliklenirse K3.
4. **Eski arzların sonraki eğitimlerde kullanımı.** Öneri: OPEN küme, ZD skorları yayımlandıktan sonra yeni model kimliklerinin eğitim verisine girebilir (veri sürümü değişir → yeni `model_id`, kural 5); SEALED küme, (C) doğrulaması yayımlanana kadar hiçbir eğitime girmez; H99 tabanlı donmuş modeller değişmez. Eğitim tablosu genişlemesi yeni dosya (`data/training_table_v2.csv`), `training_table.csv` dokunulmaz.
5. **`post_d1` için `MACHINE_SEQUENCED` kabul edilsin mi ve arşivde bültenleri bulunan (EXPOSED_ARCHIVE) arzlar OPEN'da kalsın mı?** Öneri: evet, ikisi de etiketle raporlanır; `post_d1` ZD satırı birincil tabloya girmez, ayrı alt tabloda "makine sıralı" başlığıyla; EXPOSED_ARCHIVE arzlar (TARKM, GIPTA, ADGYO, REEDR; EBEBK'nin D_10'u 2023-09-20, kapsam dışı) OPEN'da kalır, kasaya giremez, `n_exposed_archive` görünür.

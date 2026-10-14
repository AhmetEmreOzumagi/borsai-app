# BORSAI_FAZ6_FABLE_S6_RECOMPUTE_20260925 — Faz 1: kör yeniden hesap

Denetçi: Claude Code (Fable 5.1). Tarih: 2026-09-25 (İstanbul). Taban: HEAD `b3f9f6f` (S5 kanıt commit'i; `77b54f7`'nin kanıt commit'inin kendisi).

**Körlük beyanı.** Bu Faz 1 boyunca `scores/scores_oot.json`, `docs/SCORES_OOT.md`, `docs/faz6/S6_RAPOR.md`, `docs/faz6/ekler/s6_*` ve `borsai/scoring.py` açılmadı, okunmadı, grep edilmedi. `borsai` import edilmedi (iki betik `python -I` ile koştu; çıktıda `borsai_imported: false`). Opus'un yolları (`borsai/`, `tests/`, `docs/SPEC_DEVIATIONS.md`, `docs/faz6/`) çalışma ağacından değil, yalnız HEAD'deki commit'li sürümlerinden `git show HEAD:…` ile okundu; okunanlar yalnız görevin işaret ettiği metinlerdir (S2_RAPOR, S3_S5_RAPOR, OOT_TANIM_ESLEME, SPEC_DEVIATIONS I10–I13, I22, I23, I28–I38 ve E-bölümü). `docs/faz6/dogrulama/EXPOSURE.md` §3 okunmadı. Hangi kodun kasada olduğu yazılmaz; kasadaki hiçbir kodun satırı aranmadı ve okunmadı. Ağ yalnız 10 bülten zip'inin resmi URL'den `/tmp/borsai_fable_s6/`'ya yeniden indirilmesi için kullanıldı; dizin sonra silindi. push, tag, amend yok.

Dosyalar: `recompute.py` (sınıf, durum, 9 hücre → `BAGIMSIZ.json`), `kaynak_denetimi.py` (adım 4 → `kaynak_denetimi_cikti.json`), bu özet.

## 0. Taban

HEAD `b3f9f6f` = `BORSAI_PUSH_PROOFS: Faz 6 S5 outcome rows (77b54f7)`; `77b54f7` HEAD'in atası. Çalışma ağacında yalnız iki görev dosyası izlenmiyordu (`docs/prompts/FAZ6_FABLE_S6_RECOMPUTE.md`, `docs/prompts/FAZ6_S6_SCORING.md`). Repoda kohort penceresi tarihli izlenen zip yok (0).

## 1. Sınıf (`class_oot`)

Hesap yalnız git DAG'ı (`git merge-base --is-ancestor`, `git log --diff-filter=A`) ve `registry/push_proofs/*.json` `created_at` değerleriyle yapıldı.

| Terim | Değer |
|---|---|
| 19 listeleme öncesi model için sonuç girişi (I10: min(outcomes csv, raw json, d1_rows, pencere zip'i)) | 71/71 üyede **`9e1e992`** (S3a; d1_rows ekleyen commit) |
| `post_d1_hazard_v0` için sonuç girişi (d1_rows hariç; zip terimi (D_1, D_10]) | 71/71 üyede **`77b54f7`** (S5) |
| Birincil kayıt (I12: en erken etkin PREDICTION) | 71/71 üyede tek kayıt, iptal 0; ekleyen commit `1dcceff`, kanıt 2026-09-24T22:39:24Z |
| POST_D1 kaydı | 71/71 tek kayıt; ekleyen commit `7ade6a8`, kanıt 2026-09-25T13:05:58Z |
| Sonuç kanıtları | `9e1e992` → 2026-09-25T13:05:56Z; `77b54f7` → 2026-09-25T13:45:54Z |
| Model commit'leri ve kanıtları | 5fa849d (7 model, kanıt 09-22T14:06:00Z), b09cab5 (9 model, 14:06:03Z), a0df5b7 (3 model, 09-22T20:17:10Z), 7c18c0f (post_d1, 09-24T14:13:55Z); 20/20 modelin kanıtı var, hepsi her iki sonuç commit'inin atası |
| Kohort kapısı (I13-b: bütün 135 MEMBER'ın S2 kaydı) | 135 MEMBER'ın kayıt commit'i tek: `1dcceff`; `9e1e992` ve `77b54f7`'nin atası → kapı açık (kasadaki üyeler dahil; ad yazılmadı) |
| POST_D1 ek koşulları (I13) | 71/71: d1_rows kanonik sha (sıralı anahtar, `(",", ":")` ayraçlı JSON) = kayıttaki `d1_rows.sha256`; D_1 THB/THM sha ve URL = MANIFEST_OOT pini = sonuç dosyası h=1 sha'ları; `base_record` = birincil S2 kaydı (yol + dosya sha'sı); d1_rows commit'i sonuç commit'inin atası |
| DAG'da toplam sıra | 71/71 üyede aday commit'ler tam sıralı (min iyi tanımlı) |

**Sayılar:**

| Küme | OOT_BLIND | OOT_RETRO |
|---|---|---|
| 19 model × 71 açık üye | **1349** | 0 |
| `post_d1_hazard_v0` × 71 | **71** | 0 |
| Toplam | **1420** | 0 |

## 2. Satır durumları (açık küme, 71 üye)

Kural: hücre `REFUSED` → REFUSED; `NOT_APPLICABLE_REGIME` → aynı; `PREDICTED` ve sonuç dosyası yok → PENDING; `PREDICTED` ve en az bir hedef gerçekleşmiş → SCORED (E10 kalıbı); hiçbiri gerçekleşmeyecek → TARGET_UNAVAILABLE; kayıt yok → SKIPPED. Sonuç: 710 satırın hepsi `OK`; TARGET_UNAVAILABLE 0, NA_LIMIT 0, PENDING 0, SKIPPED 0; 71/71 üyede gerçekleşen D_1 = `first_trading_date`.

| Model | SCORED | REFUSED | NOT_APPLICABLE_REGIME |
|---|---|---|---|
| `v1_5_h99`, `v1_6_h99`, `v1_5_market20_v0`, `ceiling_hazard_v0` | 68 | 3 | 0 |
| `ceiling_path_v0` | 67 | 3 | 1 |
| `pb_v0`, `pb_ceiling_v0` | 59 | 12 | 0 |
| `pb_ceiling_path_v0` | 58 | 12 | 1 |
| `base_always_ceiling`, `ceiling_hazard_v0@INF`, `pb_ceiling_v0@INF`, `ceiling_path_v0@INF` | 71 | 0 | 0 |
| 7 kural | 71 | 0 | 0 |
| **Toplam 19 × 71 = 1349** | **1296** | **51** | **2** |

`post_d1_hazard_v0`: SCORED **59**, REFUSED **3** (`F3_MISSING`), NOT_APPLICABLE **9** (`D1_NOT_CEILING`; rejim değil, D_1 tavan değil). S3_S5_RAPOR §6'daki 59/3/9 ile aynı.

Bilgi: gerçekleşen seri L dağılımı (71 üye): L=0: 9, 1: 11, 2: 5, 3: 4, 4: 3, 5: 8, 6: 5, 7: 6, 8: 5, 9: 6, 10: 9.

## 3. Dokuz birincil hücre

Fark = model − kural (negatif = model iyi); blok = gerçekleşen D_1'in ayı; aralık = ay-blok bootstrap (B = 4000, `numpy.random.Generator(PCG64(20260921))`, yüzdelik 2.5/97.5), koşul n ≥ 10 ve ≥ 6 blok; hüküm dili E11. Karşılaştırıcı değerleri kayıttan (`comparators` bloğu; `v1_5_h99` karşılaştırıcısı aynı kaydın model hücresi). Arz başına kayıp çiftleri `BAGIMSIZ.json` → `primary_cells.*.pairs`.

| # | Hücre | n | blok | ort. fark | %95 aralık | K/Kb/E | hüküm |
|---|---|---|---|---|---|---|---|
| 1 | `v1_5_h99` D5 MAE − `base_train_median` | 68 | 28 | −0.028153 | [−0.080703, +0.022489] | 36/32/0 | ayırt edilemiyor |
| 2 | `v1_6_h99` D10 MAE − `v1_5_h99` | 68 | 28 | +0.000415 | [+0.000259, +0.000573] | 13/40/15 | geçemiyor |
| 3 | `v1_5_market20_v0` D5 MAE − `v1_5_h99` | 68 | 28 | −0.001832 | [−0.011197, +0.005949] | 20/17/31 | ayırt edilemiyor |
| 4 | `pb_v0` D5 MAE − `base_train_median` | 59 | 28 | −0.008214 | [−0.054995, +0.035828] | 30/29/0 | ayırt edilemiyor |
| 5 | `ceiling_hazard_v0` RPS − `base_km_expanding` | 68 | 28 | +0.068627 | [+0.001088, +0.131294] | 25/43/0 | geçemiyor |
| 6 | `pb_ceiling_v0` RPS − `base_km_expanding` | 59 | 28 | +0.047639 | [−0.005001, +0.099898] | 22/37/0 | ayırt edilemiyor |
| 7 | `ceiling_path_v0` D5 MAE − `base_train_median` | 67 | 28 | −0.010073 | [−0.068775, +0.046616] | 35/32/0 | ayırt edilemiyor |
| 8 | `pb_ceiling_path_v0` D5 MAE − `base_train_median` | 58 | 28 | −0.008927 | [−0.058967, +0.039557] | 27/31/0 | ayırt edilemiyor |
| 9 | `post_d1_hazard_v0` j=1 koşullu RPS − `ceiling_hazard_v0` koşullu | 59 | 26 | −0.041797 | [−0.066410, −0.020079] | 35/24/0 | geçiyor |

Tam hassasiyetli değerler `BAGIMSIZ.json`'da. Hücre 9'da karşılaştırıcı S_k/S_1, S2 kaydındaki `ceiling_hazard_v0` S vektöründen yeniden hesaplandı; POST_D1 kaydındaki `comparators_conditional.ceiling_hazard_v0.S_cond` ile 59/59 eşit (|Δ| ≤ 1e-12).

Yıl kırılımı (bilgi; n ve ort. fark): hücre 5: 2020 (1, −0.225), 2021 (26, +0.148), 2022 (20, +0.091), 2023 (21, −0.037); hücre 9: 2020 (1, +0.002), 2021 (20, −0.046), 2022 (17, −0.041), 2023 (21, −0.041). Diğer hücreler JSON'da.

## 4. Kaynak denetimi (adım 4)

`random.Random(20260925).sample(MANIFEST_OOT satırları, 10)`: 2021: 2, 2022: 3, 2023: 5 satır; THB 5, THM 5. Her zip resmi URL'den `/tmp/borsai_fable_s6/`'ya indirildi.

| Denetim | Sayı |
|---|---|
| indirilen / sha256 pinle eşit / bayt eşit | 10 / **10** / 10 |
| o tarihe düşen açık küme üye-satırı (beklenen / bültende bulunan) | 17 / **17** |
| karşılaştırılan ham alan (THB: `close_raw`, `trade_count_raw`; THM: `upper_limit_raw`, `reference_raw`) eşit / farklı | **34 / 0** |
| sonuç dosyasındaki `thb_sha256`/`thm_sha256` = MANIFEST pini | 17 / 17 |
| geçici dizin silindi; `borsai` import | evet; hayır |

Yalnız açık küme kodlarının satırları arandı; çıktıda ad, URL ya da fiyat yok.

## 5. Tanım yorumları (şartnamede belirsiz ya da iki okumalı yerler)

1. **Getiri nokta tahmini.** Kayıttaki `output[Dh].return` skorlandı. V1.5 ailesinde fiziksel sınıra kırpma varsa `return` kırpılmış değerdir (`return_clipped` bayrağı `UPPER`/`LOWER`; `return_unclipped` ayrı alan). Açık kümede kırpılmış ufuk-hücresi: `v1_5_h99` 120, `v1_6_h99` 120, `v1_5_market20_v0` 127, `pb_v0` 106 (4 ufuk × skorlanan arz üzerinden). Backtest ledger'larında SPEC_CEILING_PATH_V0 §5 "kırpılmamış" der; canlı ve eski kohort için SPEC_CEILING_PATH_V0 §4 "`return` … `prediction_of_cell`'in ufuk-tabanlı yolu" ve SPEC_SCORING §6 "dondurulmuş değer yeniden hesaplanmaz" nedeniyle kayıttaki `return` alındı. Kod `return_unclipped` kullanıyorsa hücre 1–4 farklı çıkar; Faz 2'de bakılacak.
2. **Tavan yolu modelleri.** `return` = karışım medyanı Q(0.5) (SPEC_CEILING_PATH_V0 §4, "birincil nokta tahmini, MAE ile skorlanır"); `mean` kullanılmadı.
3. **Bootstrap örnekleme.** SPEC_SCORING §9 sözde kodu aynen: `ids = sorted(set(blocks))`, `rng.choice(ids, size=len(ids), replace=True)`, istatistik = çekilen blokların bütün satırlarının ortalaması (blok ağırlıklı değil). Yüzdelik `numpy.percentile` varsayılan (linear). Blok kimliği `YYYY-MM` metni; çekiliş sırası ids'nin sözlük sırasıdır. Kod farklı bir sıra (ör. ilk görülme sırası) ya da `rng.integers` kullanıyorsa aynı tohumla aynı çekiliş çıkar mı belirsiz; §9 kalıbında `choice(dizi)` ile `choice(n)` aynı akışı verir.
4. **RPS koşullu, j = 1.** (1/9) Σ_{k=2..10}; yalnız L ≥ 1 ve iki tarafın da PREDICTED olduğu arzlar (59: POST_D1'in 59 PREDICTED'ı, hepsi D_1 tavan; `ceiling_hazard_v0` bu 59'da PREDICTED). Karşılaştırıcı S_k/S_1 S2 kaydından (SPEC_POST_D1_V0 §4 "aynı arzın birincil listeleme-öncesi kaydından").
5. **Satır durumu ve sınıf ayrı.** Durum sayıları sınıftan bağımsız sayıldı; hücrelere yalnız OOT_BLIND girer (§3). Bugün ikisi çakışıyor (RETRO 0). POST_D1'in `NOT_APPLICABLE` (`D1_NOT_CEILING`) durumu rejim uygulanamazlığı değildir; ayrı sayıldı.
6. **Sonuç girişi "min".** DAG'da bütün adayların atası olan commit; total sıra yoksa committer tarihine düşülüp işaretlenecekti (gerekmedi: 71/71 tam sıralı). Repo zip terimi boş (D6).
7. **Kanıt kapsamı.** Bir commit'in kanıtı = kendisi ya da torunu için alınmış en erken kanıt (`created_at`); kanıt dosyasındaki not bunu söyler. Kanıt karşılaştırması UTC ISO metinleriyle.
8. **Kohort kapısı** I13-b gereği bütün MEMBER'lar (kasa dahil) üzerinden; SEALED üyelerin kayıt commit'i git'ten okundu, adları hiçbir yere yazılmadı.
9. **d1_rows "kanonik sha".** Deneme ile `sha256(json.dumps(doc, sort_keys=True, separators=(",", ":")))` kayıttaki değeri veriyor; ham bayt sha'sı vermiyor.
10. **Yıl kırılımı** yalnız bilgi amaçlı hesaplandı (§6 ikincil satır); hüküm yok.

## 6. Önceden yazılmış beklentiyle karşılaştırma (SPEC_OOT §8; yalnız bilgi, hüküm değil)

| Hücre | Beklenen aralık | Ölçülen ort. fark | Aralık içinde mi |
|---|---|---|---|
| 1 | [−0.01, +0.04] | −0.028 | hayır (beklenenden iyi yönde) |
| 2 | [−0.01, +0.01] | +0.0004 | evet |
| 3 | [−0.01, +0.005] | −0.0018 | evet |
| 4 | [−0.005, +0.03] | −0.008 | hayır (hafifçe iyi yönde) |
| 5 | [−0.03, +0.03] | +0.069 | hayır (kötü yönde) |
| 6 | [−0.02, +0.04] | +0.048 | hayır (kötü yönde) |
| 7 | [−0.03, +0.03] | −0.010 | evet |
| 8 | [−0.02, +0.04] | −0.009 | evet |
| 9 | [−0.03, +0.02] | −0.042 | hayır (beklenenden iyi yönde) |

Hücre 5/6'daki pozitif fark 2021–2022 bloklarından geliyor (yıl kırılımı §3); 2023'te işaret ters. Hücre 9'un kazancı üç yılda da aynı işarette (2021–2023 ≈ −0.04). Mekanizma yorumu Faz 2'de, Opus'un raporuyla birlikte.

## 7. Kabul (Faz 1)

- K1: bu commit Opus'un S6 çıktılarına bakılmadan atıldı (körlük beyanı yukarıda; `BORSAI_FAZ6_S6_REPORT` commit'i bu yazım sırasında repoda yok: `git log --all | grep S6_REPORT` = 0).
- K2: 9 hücre, sınıf (1420 BLIND / 0 RETRO) ve durum sayıları bağımsız hesaplandı; kaynak denetimi 10/10 sha ve 34/34 alan eşit.

# BORSAI_FAZ1B_FABLE_CONFORMITY_20260922 — uygunluk denetimi

Denetleyen: Fable (şartnameleri yazan el). Denetlenen: commit `b09cab5` (BORSAI_FAZ1B, henüz push edilmedi), şartnameler `d3fabad`. Salt okur; tek yazma bu klasör. Ağ yok. 2026-08-19 sonrası hiçbir veri okunmadı.

İşaretler: **[ÖLÇTÜM]** = bu oturumda komut/dosyadan; **[ÇIKARIM]** = yorum. Ölçüm script'leri ve ham çıktıları `ekler/`:
- `ekler/independent_repro.py` (+ `_stdout.txt`, `_output.json`): borsai/ İMPORT ETMEDEN, ham CSV/JSON'dan fold planı, ön işleme, iç CV, Newton (kendi) + scipy BFGS çapraz kontrol, KM kuralları, f6, RPS/bootstrap.
- `ekler/predict_parity.py` (+ `_stdout.txt`, `_output.json`): dondurulmuş JSON → stdlib `predict` ↔ fit tarafı (borsai numpy/sklearn nihai model) ↔ JSON parametreleriyle elle hesap; ret/uyarı uç durumları.
- `ekler/pytest_out.txt`: `.venv/bin/pytest -q -p no:cacheprovider` sonucu.

## Hüküm tablosu

| Model | Hüküm | Kısa gerekçe |
|---|---|---|
| `ceiling_hazard_v0` | **PUSH_OK** | 4 fold (erken/orta/geç + kırpmalı) sıfırdan yeniden üretildi: λ, skor tablosu, γ, β, S_k, P_close, reclose ≤ 4e-12 eşit; 87/87 fold'da eğitim ve PP kümesi hash'i bağımsız kurguyla aynı; max(eğitim seansı) < T 87/87. Sızıntı yok. −0.05 RPS gerçek backtest sonucudur (§1.6). |
| `ceiling_hazard_v0@INF` | **PUSH_OK** | 87/87 fold'da γ kapalı biçime bit-eşit; nihai JSON 97 arz, 506/83. |
| `pb_ceiling_v0` | **PUSH_OK** | 2 fold (erken/orta) sıfırdan eşit; 87/87 fold hash eşit; kesim B(k) < T doğrulandı. |
| `pb_ceiling_v0@INF` | **PUSH_OK** | 87/87 fold'da γ kapalı biçime bit-eşit. |
| `pb_v0` | **PUSH_OK** | D5\|ARMGD sıfırdan (sklearn, V1.6 ızgarası, iç LOOCV): α, C, tahmin (Δ = 0), olasılık (Δ = 1.5e-10), iki skor tablosu eşit; 345/345 fold'da eğitim kümesi B(k) kesimiyle aynı. |
| `v1_5_market20_v0` | **PUSH_OK** | f6 351/351 fold'da ve 99/99 JSON kaydında bağımsız hesapla Decimal-eşit, S0 < T; D5\|ARMGD sıfırdan eşit (Δ ≤ 6e-10); 351/351 fold V1.5 kümeleri. Tek belgelenmemiş sapma (§3, A13) H99'da etkisiz. |
| `v1_6_h99` | **PUSH_OK** | 351/351 fold V1.5 kümeleri; ızgara, uç noktalar, aday başına politika şartnameyle aynı; parite ≤ 9e-16. |
| `base_km_expanding`, `base_km_last10` | **PUSH_OK** | 87 + 87 fold'da S_k ve P_close bağımsız KM hesabıyla bit-eşit (Δ = 0). C2 (99 arzla dondurma) KABUL, koşullu (§3). |

## Özet (10 satır)

1. **Sızıntı bulunmadı.** Tavan planında 87 fold'un hepsinde eğitim kümesi, PP satır kümesi, olay/sağ kalım sayıları ve max(seans tarihi) < T bağımsız kurguyla aynı; ön işleme ve λ seçimi fold içinde; KM kuralları aynı PP kümesinden. [ÖLÇTÜM `ekler/independent_repro_stdout.txt` §A, §D]
2. `ceiling_hazard_v0`'ın RPS −0.0496 [−0.0751, −0.0219] farkı yeniden üretildi; bootstrap aralığı da aynı. Şartnamedeki −0.005…−0.02 beklentisi **yanlış çapalanmıştı**: f3'ün L ile marjinal ilişkisi güçlü (Spearman 0.55, p = 5e-9), RPS on günü toplar ve D1 Brier'i en az bilgi taşıyan hücredir. Kazanç dört yılda da aynı büyüklükte (−0.043…−0.058) → rejim tesadüfü değil. [ÖLÇTÜM + ÇIKARIM §1.6]
3. Bütün beklenti hükümleri (tuttu/kısmen/tutmadı) OPERATIONAL_RULES'a göre doğru uygulanmış; paylar bağımsız sayımla aynı. İki yorum noktası (market20 işaret: yalnız Ridge kafası; ceiling k = 1 "küçük": mutlak eşik) KÜÇÜK. [§5]
4. Şartname ↔ kod: özellik, ön işleme, model sınıfı, ızgara, seçim/eşitlik, fold planı, min-eğitim, ret/uyarı, JSON içeriği beş modelde de uyumlu. Kabul testleri (11 + 8 + 11 + 9) testlerde var ve doğru şeyi sınıyor; bağımsız sayımla da çapraz doğrulandı. [§2]
5. SPEC_DEVIATIONS'daki 27 maddenin hepsi **KABUL**; C2 koşullu (canlı tabloda KM(99) yanında @INF(97) birincil eşleşik sabit olarak gösterilsin). Belgelenmemiş bir sapma bulundu: market20'de f6'sız eğitim satırı "dışlanır" (SPEC §7) yerine `FitError` ile durur (`borsai/fit.py:501-503`); H99'da 0 satır → KÜÇÜK, belge ekle. [§3]
6. predict paritesi: 97/99 eğitim arzında ve uç girdilerde stdlib ↔ fit tarafı ≤ 1e-15, JSON'dan elle hesap ≤ 4e-16 (şartname 1e-12 ister). Ret kuralları (f3 yok, PB alan/özdeşlik/aralık, fiyat aralığı, f6 yok/neden kodu, f6 sayı değil) çalışıyor. [§4]
7. Dondurulmuş JSON'ların `borsai_source_sha256` değeri HEAD'deki `borsai/*.py` ağacının hash'ine eşit: JSON'lar tam olarak commit edilen kodla üretildi. Şartname belgesi sha'ları `specs.py` ile aynı. Push'tan önce **kod değiştirilmemeli**; aksi halde bu bağ kopar. [ÖLÇTÜM]
8. Test paketi bu makinede yeşil: 254 passed, 215 s (`ekler/pytest_out.txt`, §2.6).
9. Gözlem (hata değil): backtest'te model ve KM kuralları hepsi iyimser (ort. S_1 0.866 / gözlenen 0.816; k = 10: 0.187 / 0.126); tavan oranı yıllar içinde düştüğü için walk-forward'ın doğal gecikmesi. Prospektif kalibrasyon ölçütü (b) bunu izler. [ÇIKARIM]
10. Karar: **beş model ve iki KM kuralı olduğu gibi push edilebilir.** Kod düzeltmesi yok; yalnız belge önerileri (§3 A13, §5 iki dipnot) push'la birlikte ya da sonra.

---

## 1. Sızıntı denetimi

### 1.1 Yöntem

`ekler/independent_repro.py`: `data/training_table.csv`, SESSIONS (yalnız `ticker, session_number, target_session_date`), TARGETS (`target_session_date`), MASTER (`ipo_size_tl`), PB CSV, Takvim B ve XU100 JSON okunur. Fold planı, kişi-dönem tablosu, sağ sansür, ön işleme, iç arz-bırak CV, Newton, KM, f6 ve RPS/bootstrap yeniden yazıldı; `borsai/` import edilmedi. Karşılaştırma: `tests/reference/macos_golden_faz1b/*_fold_ledger.csv` ve `models/*.json`. Hash tanımı ledger'la aynı (`sha256("\n".join(items) + "\n")`, `borsai/provenance.py:41-44`).

### 1.2 Tüm fold'larda eğitim kümesi kimliği [ÖLÇTÜM `independent_repro_stdout.txt` §A]

| Plan / ledger | Fold | eğitim ticker hash eşit | PP satır hash eşit | max(eğitim seansı) < kesim ve ledger'daki değerle eşit | (n_ipo, olay, satır) eşit | realized_L = tablo |
|---|---|---|---|---|---|---|
| `ceiling_hazard_v0` (kesim T, f3 dolu) | 87 | 87 | 87 | 87 | 87 | 87 |
| `pb_ceiling_v0` (kesim B, 99 arz) | 87 | 87 | 87 | 87 | 87 | 87 |
| `v1_5_market20_v0` (kesim T, hedef seansı < T) | 351 | 351 | — | 351 | — | — |
| `v1_6_h99` | 351 | 351 | — | 351 | — | — |
| `pb_v0` (kesim B) | 345 | 345 | — | 345 | — | — |

Bağımsız kurguda test arzı hiçbir eğitim kümesinde değil (assert), aynı gün listelenen arz eğitime girmiyor (kesin `<`), ALBTN/ENDAE tavan planında ne test ne eğitimde (`independent_repro.py` §A; ledger'da test kümesinde yok [ÖLÇTÜM]).

Kod tarafı: `borsai/backtest.py:212-244` (`plan_ceiling_folds`: aday `first_trading_date < c`, satır `session < c`, `BacktestStop` ile kendi kendini eğitme/gelecek sızıntısı denetimi), `borsai/survival.py:55-63` (`pp_rows`: `d − 1 > L` ya da `session ≥ cutoff` → dur), `borsai/backtest.py:163-188` (`plan_folds_pb`: `target_session_date < B(k)`, `first_trading_date < B(k)` assert).

### 1.3 `ceiling_hazard_v0`: dört fold sıfırdan [ÖLÇTÜM §B]

| Fold | Konum | Kesim T | n_ipo / satır / olay | λ (benim / ledger) | maks \|Δ\| skor tablosu | maks \|Δ\| γ | maks \|Δ\| β | maks \|Δ\| S_k | maks \|Δ\| P_close | reclose | scipy BFGS − Newton |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EKOS | erken (1/87) | 2023-11-21 | 10 / 70 / 6 | 3 / 3 | 4.4e-12 | 4.4e-16 | 1.1e-16 | 0 | 0 | eşit | 4.3e-10 |
| EGEGY | orta (44/87) | 2025-01-14 | 53 / 297 / 44 | 3 / 3 | 1.1e-13 | 2.9e-15 | 2.6e-16 | 3.9e-16 | 3.9e-16 | eşit | 1.6e-9 |
| QUICK | geç (87/87) | 2026-08-06 | 96 / 505 / 82 | 10 / 10 | 1.6e-15 | 4.4e-16 | 2.2e-16 | 2.8e-16 | 2.8e-16 | eşit | 5.5e-9 |
| SERNT | orta, test f3 kırpmalı | 2025-02-04 | 57 / 303 / 48 | 3 / 3 | 7.7e-14 | 6.7e-16 | 2.2e-16 | 2.8e-17 | 2.8e-17 | eşit | 1.5e-9 |

Sorulara yanıt:
- **Eğitim PP satırları yalnız seansı < T olanlar mı?** Evet: bağımsız PP kümesi hash'i 87/87 eşit; `max(eğitim seansı) < T` 87/87. Test arzı dışarıda (hash eşitliği + assert). Sağ sansür doğru: satır (j, d) ancak `session(j, d) < T`; ilk geçmeyen d'de durulur; sansürlü satırların hepsi event = 0, bozulma günü kesimden sonraysa hiç görülmez (`survival.py:55-63`; sentetik kabul testi 3, `tests/test_ceiling.py:121-131`).
- **Ön işleme fold içinde mi?** Evet: p05/p95 (Type-7), μ, σ (ddof = 0) yalnız fold eğitim arzlarından; iç CV'de her j için kalan arzlardan yeniden (`borsai/hazard.py:199-205`; benim `select_lambda` aynı kurguyla aynı skor tablosunu veriyor, 9 λ × 4 fold ≤ 4.4e-12).
- **λ yalnız eğitim içi CV ile mi?** Evet: skor tabloları eşit ve seçilen λ tablonun argmin'i (eşitlikte büyük λ). Test satırının hiçbir bilgisi skora girmiyor; girseydi tablo farklı olurdu.
- **S_k ledger'la örtüşüyor mu?** Evet, ≤ 3.9e-16.
- **KM kuralları aynı eğitim kümesinden mi?** Evet: §1.5.

### 1.4 `pb_ceiling_v0` (kesim B) iki fold; `pb_v0` ve `v1_5_market20_v0` birer fold [ÖLÇTÜM §C, §E, §F]

| Fold | Kesim | Kesim < T | n | Seçim (benim / ledger) | Tahmin farkı | Skor tabloları maks \|Δ\| | Eğitim hash |
|---|---|---|---|---|---|---|---|
| `pb_ceiling_v0` SKYMD (erken) | B = 2023-11-30 | evet | 12 arz / 89 satır / 6 olay | λ 3 / 3 | S_k 0 | 3.8e-13 | eşit |
| `pb_ceiling_v0` KLYPV (orta) | B = 2025-02-05 | evet | 58 / 304 / 48 | λ 10 / 10 | S_k 5.7e-13 | 3.5e-14 | eşit |
| `pb_v0` D5\|ARMGD | B = 2024-12-25 | evet (T = 2025-01-03) | 52 | α 0.001 / 0.001; C 0.1 / 0.1 | getiri 0; p 1.5e-10 | MAE 1.1e-16; Brier 2.1e-11 | eşit |
| `v1_5_market20_v0` D5\|ARMGD | T = 2025-01-03 | — | 52 | α 10 / 10; C 1 / 1 | getiri 3.3e-16; p 7.2e-16 | MAE 2.8e-17; Brier 5.6e-10 | eşit |

Not: KLYPV'de γ farkı 3.5e-12 (diğerlerinde ~1e-15): benim Newton'umun durma eşiği 1e-11, borsai'ninki 1e-10; ikisi de scipy BFGS'e ≤ 1e-9. Doğrusal fold'larda sklearn aynı kütüphane; bağımsızlık fold kurgusu, ön işleme ve iç LOOCV'dedir (Brier tablosundaki 1e-10 farkı lbfgs'in başlangıç/sıra duyarlılığından; V1.5 port kabulünde de aynı düzey, `docs/MODELS.md:144`).

**market20, f6 yalnız S0 < ref kayıtlarını görüyor mu?**
- Kod: `borsai/market20.py:223` `visible = [r for r in xu100 if r.date < ref_date]`; pencere ve bütünlük denetimi yalnız `visible` üzerinde (`:225-229`). [ÖLÇTÜM]
- Veri: 351/351 ledger satırında `test_f6`, `S0_date`, `S20_date` benim as-of'lu hesabımla (yalnız `hisTs < T`) Decimal-metin olarak eşit ve `S0_date < prediction_date`; dondurulmuş JSON'un `market20_training` 99/99 kaydında aynı. [ÖLÇTÜM §F]
- Test: `tests/test_market20.py:108-115` (ref ve sonrası 40 gün 1e9 + XHARZ zehirleme → f6 değişmez). [ÖLÇTÜM]
- D5\|ARMGD fold'unda sütunlar `[f1, f2, f3, f4, f6]`: f5 sıfır varyansla düşmüş (eğitimde f3 eksik arz yok; ALBTN/ENDAE bu fold'un eğitiminde değil) — ledger'la aynı.

### 1.5 KM kuralları ve @INF, tüm fold'lar [ÖLÇTÜM §D]

| Koşu | Fold | maks \|Δ\| (S_k ve P_close) |
|---|---|---|
| `base_km_expanding` (tavan planı) | 87 | 0 |
| `base_km_last10` (tavan planı) | 87 | 0 |
| `ceiling_hazard_v0@INF` γ ↔ kapalı biçim | 87 | 0 |
| `base_km_expanding__pb_ceiling` | 87 | 0 |
| `base_km_last10__pb_ceiling` | 87 | 0 |
| `pb_ceiling_v0@INF` γ ↔ kapalı biçim | 87 | 0 |
| `base_always_ceiling__{ceiling,pb_ceiling}` S_k ≡ 1 | 87 + 87 | evet |

Kural satırları modelin PP eğitim kümesinden (`backtest.py:380-396`: `fold.training`, `fold.cutoff_date`); hash'ler modelinkiyle aynı (`tests/test_ceiling.py:326-340`).

### 1.6 Beklentiden iyi sonuç: iyi haber mi, sızıntı mı, hata mı?

**Ölçülen** [`independent_repro_stdout.txt` §H ve ek sayım]:
- RPS eşleşik fark, ledger'dan yeniden: model − `base_km_last10` −0.0496 [−0.0751, −0.0219]; − `base_km_expanding` −0.0569 [−0.0833, −0.0286]; − `@INF` −0.0503 [−0.0724, −0.0263]. MODELS.md ile aynı.
- Yıl bazında (model − km_last10): 2023 −0.045 (n 9), 2024 −0.058 (33), 2025 −0.047 (17), 2026 −0.043 (28).
- H99'da (f3 dolu 97 arz) Spearman(f3, L) = +0.55 (p = 5e-9); Spearman(f1, L) = −0.45; Spearman(f2, L) = +0.36.
- Nihai fit β (z ölçeği): f1 +0.449, f2 −0.179, f3 −0.550. f3 p95'teki bir arz (z ≈ +2.3) için hazard çarpanı exp(−1.27) ≈ 0.28.

**Çıkarım:** sızıntı ya da hata değildir. (i) Her fold'un eğitim kümesi, sansürü, ön işlemesi, λ seçimi ve KM karşılaştırıcısı bağımsız kurguyla eşleşti (§1.2–1.5); test bilgisinin girebileceği kanal kalmadı. (ii) Kazanç yıllara düzgün yayılmış; tek bir dönemden gelmiyor. (iii) Şartnamenin −0.005…−0.02 beklentisi, V1.5 Logit'in D1 Brier farkına (−0.008) çapalanmıştı; D1 taban oranı 0.82'yle en az bilgi taşıyan hücredir, oysa RPS on günü toplar ve k = 2…7'de gözlenen oran 0.38–0.75 arasındadır (bir kovaryat modelinin en çok kazanabileceği bölge). Şartname özellik–sonuç ilişkisine bakmadığı için f3'ün L ile bu kadar güçlü marjinal ilişkisini bilmiyordu; ilişkinin kendisi a priori beklenen yöndeydi. (iv) Sonuç yine de **tasarıma maruzdur** (gün grupları H99 marjinalleriyle seçildi; SPEC_CEILING §11) ve backtest terazisindedir; hüküm prospektif n ≥ 30'da verilir. Beklentiyi tutturamamak şartnamenin hatasıdır, kodun değil; MODELS.md bunu "tutmadı" olarak doğru yazıyor.

Yan gözlem [ÇIKARIM]: β_f2 < 0 (halka açıklık ↑ → hazard ↓) şartnamedeki a priori işaretin tersi; veri de marjinal olarak bu yönde (Spearman +0.36). Şartname hatası; kod doğru raporluyor ("kısmen").

---

## 2. Uygunluk: şartname ↔ kod

### 2.1 `ceiling_hazard_v0` (SPEC_CEILING_V0) [ÖLÇTÜM: dosya:satır]

| Konu | Şartname | Kod | Durum |
|---|---|---|---|
| Özellikler | f1, f2, f3; TEK tanım `features.py` | `specs.py:307` `features=["f1","f2","f3"]`; `features.py:130-167` | uyumlu (A1: f1 = kaynak `ipo_size_tl`, yoksa fiyat × pay; benim yeniden üretimim de bu tanımla eşleşti) |
| Ön işleme | arz düzeyi; f1 ln; f3 Type-7 p05/p95 kırpma; z, ddof = 0; imputasyon/f4/f5 yok | `preprocess.py:86-89` `CEILING_RECIPE(indicator=False, impute=False, missingness_drop=False)`; `:405-421` winsor; `:498-539` z; `hazard.py:175-182` arz düzeyi | uyumlu |
| Sıfır varyans | düşer, katsayı 0; üçü de düşerse yalnız sabitler | `preprocess.py:455-461`; `hazard.py:144-145` (p = 0 → kapalı biçim); `beta_by_feature` 0 yazar `:247-250` | uyumlu (A4) |
| Model / amaç | logit h = γ_g + β·z; J = −Σ w[...] + (λ/2)‖β‖²; γ cezasız; 6 pseudo-satır w = 0.5, nihai fit'te de | `hazard.py:93-99` (objective), `:105` (pen yalnız β), `:147-151` (pseudo) | uyumlu |
| Çözücü | Newton; başlangıç β = 0, γ kapalı biçim; H⁻¹∇ (`solve`); J azalmıyorsa yarıla ≤ 30; dur max\|∇\| ≤ 1e-10; 100 yineleme | `hazard.py:102-133`; `:35-37` sabitler | uyumlu; A2 tolerans (m·eps) kabul; benim Newton'um farklı toleransla ve scipy BFGS aynı optimuma (≤ 5.5e-9) |
| λ = INF | β ≡ 0; γ = logit((olay + 0.5)/(risk + 1)) | `survival.py:79-81`; `hazard.py:144-145` | uyumlu (test 5: S_1 = 1 − 18.5/100 ✓; @INF JSON 97 arzda 1 − 16.5/98) |
| Izgara | {0.1,1,3,10,30,100,300,1000,INF} | `hazard.py:34`; `specs.py:283` | uyumlu (test 7) |
| Seçim | iç arz-bırak; ön işleme yeniden; satır başına ortalama log-kayıp; h ∈ [1e-12, 1−1e-12]; en küçük; bit-eşit eşitlikte en büyük λ; yakınsamayan λ düşer, INF kalır | `hazard.py:192-228` | uyumlu (skor tabloları bağımsız hesapla ≤ 4.4e-12) |
| Fold planı | aday `ftd < T` ve f3 dolu; satır `session < T`; ≥ 10 arz / ≥ 5 olay / ≥ 5 sağ kalım; 87 fold, ilki EKOS (10/6/64) | `backtest.py:212-244`, `:83`; ledger: 87, EKOS 2023-11-21 10/6/64 | uyumlu |
| Ret/uyarı | f3 boş → RET; f1/f2 hesaplanamıyor → etiketli; aralık dışı → uyarı; f3 kırpma → `clipped` | `predict_hazard.py:97-117`; §4 uç durumlar | uyumlu |
| Çıktılar | hazard, S, P_L (Σ = 1), P_close (k = 1: S_1; k ≥ 2: S + (1−S)·r, a: 2–4, b: 5–10); r = (a + 0.5)/(n + 1), walk-forward'da seans < T | `survival.py:84-120`; `predict_hazard.py:73-76` | uyumlu; JSON r_a = 1.5/103, r_b = 61.5/430 bağımsız sayımla eşit |
| Beklenen getiri | v0'da YOK | JSON `horizons` null (B7) | uyumlu |
| Ledger sütunları (§9) | test_ticker, T, n_train_ipo, n_pp_rows, n_events, hash, λ, skor tablosu, γ(3), β(3), hazard, S, P_close, L, durum | ledger başlığı (`ceiling_hazard_v0_fold_ledger.csv:1`) | uyumlu |
| Kurallar (§10) | KM genişleyen, KM son-10, her zaman tavan, @INF, `v1_5_p_up_as_ceiling` (k ∈ {1,3,5,10}, yalnız P_close) | `backtest.py:87-103` FAZ1B_RUNS; `report_faz1b.py:551-556` | uyumlu (C1, C4, C5) |
| JSON alanları (§12) | day_groups, γ, β, λ, λ tablosu, reclose {r_a, r_b, n_a, a_a, n_b, a_b}, pseudo_rows, training.{tickers, sha, n_ipo, n_pp_rows, n_events, cutoff, data_version}, feature_ranges | `models/ceiling_hazard_v0.json` [ÖLÇTÜM]: hepsi var; 97 arz, 506/83, kesim 2026-08-19, λ = 10 | uyumlu |
| Parametre sayısı | 3 γ + 3 β = 6 | JSON: gamma[3], beta{f1,f2,f3} | uyumlu |
| Deney günlüğü | koşu satırı + belge sha | `experiments/log.jsonl`: `faz1b_acceptance_run` ve `faz1b_golden` satırları, `spec_document_sha256` | uyumlu (C6) |

Kabul testleri §13-1…11 → `tests/test_ceiling.py`: 1 (`:48-60`, 508/85, gün tablosu, gruplar, 97 → 506/83, L = 10 → 10 satır event 0), 2 (`:89-102`: 87 fold, EKOS 10/6/64, ALBTN/ENDAE yok, bağımsız `_independent_fold_count` ile eşitlik, max seans < T), 3 (`:121-131` sentetik sansür), 4 (`:167-183` 1000 rastgele + 99 eğitim, tutarlılık), 5 (`:188-202`), 6 (`:216-243` BFGS ≤ 1e-6, ∇ ≤ 1e-10, λ = 1e9 ≈ INF), 7 (`:248-268`), 8 (`:273-288` 97 arz ≤ 1e-12), 9 (`:293-311`), 10 (`:325-350`), 11 (`:355-374`). Hepsi doğru şeyi sınıyor. Zayıf nokta: test 2'nin sızıntı satırı ledger'ın kendi `training_max_session_date` sütununu kullanıyor (aynı kodun ürettiği değer); bu denetim burada bağımsız kurguyla kapatıldı (§1.2). KÜÇÜK.

### 2.2 `pb_ceiling_v0` (SPEC_PB_V0 §9)

Özellikler pb1, pb2 (`specs.py:332`), kırpmasız düz z (`preprocess.py:92-93`), eğitim 99 (`training=H99_TRAINING`), kesim B(k) (`backtest.py:219-221`), skorlanabilirlik aynı, kurallar B kesimiyle (`FAZ1B_RUNS`), f3 istenmez (`predict_hazard.py:118-127`; §4: f3 = None ile RET ETMEZ ✓). JSON: 99 arz, 508/85, 2 β + 3 γ, λ = 10. Uyumlu. Test 8 (`test_ceiling.py` parametreli: 1, 2-pb, 3–8, 9-pb, 10, 11) var. Fold sayısı 87 (şartname ölçmemişti; 84–89 bandında). [ÖLÇTÜM]

### 2.3 `pb_v0` (SPEC_PB_V0)

| Konu | Şartname | Kod | Durum |
|---|---|---|---|
| Girdi kaynağı, birleştirme | PB CSV (sha `5e52d4d2…`), ticker anahtarı; `build_training_table.py`'ye dokunulmaz | `data.py:40-41, 254-282`; git: dosya değişmedi | uyumlu |
| Özellikler | pb1 = ln(fiyat × base), pb2, pb3; pb4 özellik değil; ID-A/B/C, pozitiflik, (0, 100], pb4 ≥ 0; token denetimi taşınmaz | `features.py:264-293` | uyumlu (A6–A9). Not: pb3 ∈ (0, 100] kuralı sermaye artırımı 0 olan arzı reddeder; şartnamenin kendi kuralıdır (legacy pb_core4 ile aynı), H99'da örnek yok |
| Model / ızgara | V1.5 sözleşmesi; ızgara SPEC_V1_6 §3; azınlık < 2 → C = ZERO; aday başına yakınsamama | `fit.py:76` `PB_GRID = (…V1_6 ızgaraları, POLICY_CANDIDATE, ZERO)`; `specs.py:251` | uyumlu |
| İç LOOCV'de ön işleme yeniden | evet | `fit.py:219-243` `_InnerCache` | uyumlu (bağımsız fold: skor tabloları eşit) |
| Fold | kesim B(k), MIN_TRAIN_N 10; D1/D3/D5 87, D10 84; min n_eff 12 | `backtest.py:163-188`; ledger 345 satır; `tests/test_pb.py:70-79` | uyumlu |
| Ret | alan boş → PB_FIELD_MISSING:<alan>; özdeşlik/aralık → PB_IDENTITY:<ad>; fiyat aralığı → PB_PRICE_RANGE; aralık dışı/pb4 → uyarı; fiziksel sınır | `predict_pb.py:26-54`; §4 | uyumlu (B3: kod önekisiz + `field`) |
| Kurallar | 6 kural PB kesimiyle; `v1_5_h99` bilgi amaçlı | `FAZ1B_RUNS`; `report_faz1b.py:458-463` | uyumlu |
| JSON | 99 arz, kesim 2026-08-19, pb1–pb3 sütunları, medians {} | `models/pb_v0.json` [ÖLÇTÜM] | uyumlu |

Kabul testleri §11-1…7 → `tests/test_pb.py` (1: `:38-48` ID'ler, pb4 ≠ 0 tam 7, pb3 = 100 tam 17; 2: legacy `pb_core4` paritesi bit-eşit; 3: fold sayıları ve sızıntı; 4: yasak girdi kaydedici sözlükle; 5: ret; 6: parite ≤ 1e-12 ve INF/ZERO sentetik; 7: kurallar aynı fold'da). Doğru.

### 2.4 `v1_5_market20_v0` (SPEC_MARKET20_V0)

| Konu | Şartname | Kod | Durum |
|---|---|---|---|
| f6 tanımı | bisect_left − 1; S20 = i − 20; Decimal 60, HALF_EVEN; `parse_float=Decimal` | `market20.py:198-240`, `:152-164` | uyumlu (351/351 + 99/99 Decimal-eşit) |
| Takvim B, XU100 pinli, sha denetimi | evet | `market20.py:41-46, 119-123, 132-139, 167-172` | uyumlu |
| Geçerlilik kuralları 1–7 | CALENDAR_NOT_COVERING (`last ≥ ref − 1`), INSUFFICIENT_HISTORY, XU100_CLOSE_MISSING (21 kapanış), STALE_S0 (> 12), PREDICTION_TOO_EARLY (canlı, > 12), XU100_INTEGRITY, as_of | `:215-236`, `:175-186` | uyumlu (A12: bütünlük `visible` üzerinde + yüklemede tüm dosya) |
| Ön işleme | f1–f5 V1.5 + f6 düz z; log/winsor/imputasyon/gösterge yok | `preprocess.py:85` `MARKET20_RECIPE(extra=("f6",))`; `:397-400` eksik f6 → hata | uyumlu |
| Izgara / seçim | V1.5 ile birebir (α {0.1…100}, C {0.01…10}, fold düzeyi yakınsamama) | `specs.py:215-219` `_v1_x(V1_5_H99)` ızgarayı değiştirmez | uyumlu (bağımsız fold: α, C, tahmin eşit) |
| Sütun sırası | f1..f5, f6 | JSON `columns` `["f1","f2","f3","f4","f5","f6"]` | uyumlu |
| Fold planı | V1.5'in 351 fold'u, aynı hash | 351/351 [ÖLÇTÜM §A] | uyumlu |
| Eksik veri (§7) | f3 boş RET; f6 RET + neden; **eğitim satırında f6 yok → satır dışlanır, n yeniden sayılır**; f6 aralık dışı uyarı | `predict_market20.py:28-46`; **`fit.py:501-503`: f6'sız satır varsa `FitError` ile DURUR (dışlamaz)** | **sapma, belgelenmemiş** (§3 A13). H99 + Takvim B'de 0 satır → dondurulmuş modele etkisi yok |
| Rol ayrımı | f6 Python'da üretilir, predict hazır değer alır | `market20.py:243-247`, `predict_market20.py` | uyumlu (B1/B2) |
| Kurallar | 6 kural + `v1_5_h99` eşleşik | `report_faz1b.py:411-449` | uyumlu |
| JSON | `market20_training` 99 kayıt (S0/S20 tarih ve kapanış, dosya sha) | `models/v1_5_market20_v0.json` [ÖLÇTÜM] | uyumlu |

Kabul testleri §11-1…11 → `tests/test_market20.py` (1: 99/99 B, A ile 6 RET ve adları; 2: legacy paritesi ve legacy'nin takvim sonu hatası; 3: takvim sonu üç tarih; 4: pencere içi eksik sentetik + 2023-02-20 gerçek; 5: 13 gün kapanış → STALE, 12 → geçer; 6: as_of zehirleme; 7: XHARZ, çelişki, ≤ 0; 8: 351 hash; 9: f6 sabit → V1.5 altın ledger'ıyla eşit; 10: RET/uyarı ve parite 97 × 4; 11: revizyon denetimi). Doğru.

### 2.5 `v1_6_h99` (SPEC_V1_6)

Izgara sabitleri `fit.py:51-52` şartname §3 tablosuyla birebir; INF/ZERO kapalı biçim (`fit.py:286-289, 303-304, 316-318, 327-329, 360-361, 384-391`); sıralama INF en büyük / ZERO en küçük (`:273-283`); aday başına yakınsamama ve nihai fit'te sıradaki aday (`:342-408`); azınlık < 2 → C = 0.01 (`V1_6_GRID` fallback; A11: nihai fit yakınsamazsa ZERO); tek kod yolu iki ızgara (`GridConfig`, B6: V1.5 altın ledger'ı her test koşusunda bayt bayt); JSON `"alpha": "INF"` / `"C": "ZERO"` metin (`hp_label`), `grid_version: "v1_6"` (`specs.py:192`); fold planı 351/351 [ÖLÇTÜM]; seçim dağılımı ve kenara yapışma tablosu (`report_faz1b.py:250-287`). Kabul testleri §10-1…9 → `tests/test_v1_6.py` (1–8) ve `tests/test_report.py:49-54` (9). Test 3 hem tam ledger bayt eşitliğini hem dört fold'da iki ızgaranın aynı fonksiyonlardan geçtiğini (casus sayaç) sınıyor; test 6 hem iç adayın hem nihai fit'in yakınsamama yolunu zorluyor. Doğru.

### 2.6 Test paketi ve dondurma bütünlüğü [ÖLÇTÜM]

- `.venv/bin/pytest -q -p no:cacheprovider`: **254 passed, 0 failed, 215.6 s** (`ekler/pytest_out.txt`). Geçici günlüğe yazar; repoda hiçbir izli dosya değişmedi (`git status --porcelain`: yalnız bu klasör ve görev prompt'u izsiz).
- `models/*.json` → `code_version.borsai_source_sha256 = c873f64b…` = HEAD'deki `borsai/*.py` ağacının hash'i (aynı formülle yeniden hesaplandı). `git_commit = d3fabad`, `borsai_dirty = true`: JSON'lar b09cab5'ten önce, o commit'in kodu çalışma kopyasındayken üretildi; ağaç hash'i eşit olduğu için kod-JSON bağı sağlam.
- `specs.py:140-149` şartname belgesi sha256'ları dosyalarla eşit (4/4). `docs/specs/` d3fabad'dan beri değişmemiş (`tests/test_faz1b_guardrails.py:50-55`).
- `tests/test_faz1b_models.py:35-39`: yeniden fit dondurulmuş parametreleri (created_at/code_version dışında) birebir üretir.

---

## 3. Sapmalar (docs/SPEC_DEVIATIONS.md)

| # | Hüküm | Gerekçe / koşul |
|---|---|---|
| A1 f1 = kaynak `ipo_size_tl` | **KABUL** | Şartnamenin "tek tanım" kuralı üstündür; fark 4 arzda ≤ 0.46 TL, ln'de ~1e-9. Bağımsız yeniden üretim bu tanımla eşleşti. |
| A2 iniş toleransı m·eps | **KABUL** | Dışbükey problem; benim Newton'um (farklı tolerans) ve scipy BFGS aynı çözüm (≤ 5.5e-9). ∇ ≤ 1e-10 sağlanıyor (JSON `solver.grad_max` 6.2e-15). |
| A3 30 yarılama sonrası NOT_CONVERGED | **KABUL** | Muhafazakâr; backtest'te hiç olmadı (ledger `n_lambda_not_converged` 0). |
| A4 özellik kalmazsa kapalı biçim | **KABUL** | Pseudo-satırlı MLE'nin kendisi; test 7. |
| A5 imputasyonsuz tarifte eksik → görünür hata | **KABUL** | Sessiz imputasyondan iyi; H99'da filtre etkisiz. |
| A6/A7 pb1 kesin çarpım, 60 hane ln | **KABUL** | 99/99 legacy parite. |
| A8 fiyat aralığı tanıma | **KABUL** | "10-12", "10 – 12" RET; "-5" → VALUE_POSITIVE (§4 ölçüldü). |
| A9 aralık ihlali adları | **KABUL** | Legacy sırası. |
| A10 INF = `statistics.mean` | **KABUL** | `base_train_mean` ile aynı tanım. |
| A11 azınlık < 2 + nihai fit yakınsamazsa ZERO | **KABUL** | Şartnamenin "ZERO her zaman geçerli" cümlesinin doğal sonucu; hiç olmadı. |
| A12 bütünlük denetimi `visible` üstünde | **KABUL** | Kural 7 "hiç okumaz" ile tutarlı; yüklemede tüm dosya ayrıca denetleniyor (`market20.py:167-172`). |
| B1 f6 üreticisi `market20.py`'de | **KABUL** | `features.py` stdlib predict yolunun parçası; f6 tarih/bisect/JSON ister. Rol ayrımı (üretim Python'da, predict hazır değer) aynen korunmuş; `market20.py` de yalnız stdlib. Şartnamedeki yol adı bir yerleşim ayrıntısıdır. |
| B2 `f6_market20` + `f6_market20_refusal`; yoksa `MARKET20_NOT_PROVIDED`; çekirdek predict f6'sız → `FEATURE_NOT_PROVIDED` | **KABUL** | İmputasyon yolu yok; §4'te üç yol da ölçüldü. Öneri (KÜÇÜK): uygulama tarafı `f6_market20_refusal`'ı market20.py'nin neden koduyla doldurmalı; tanınmayan neden `NOT_PROVIDED`'a düşüyor (doğru davranış). |
| B3 ret kodu önekisiz + `field` | **KABUL** | Faz 1A sözleşmesi; `REFUSED_*` sabit adları şartnamedeki isimleri taşıyor. |
| B4 tavan predict V1.5 girdi kümesi | **KABUL** | f4 yalnız doğrulanır, kullanılmaz. |
| B5 `_fit_logistic` monkeypatch | **KABUL** | Aynı işlev. |
| B6 tek çekirdek, V1.5 bayt eşitliği her koşuda | **KABUL** | Şartnameden güçlü. |
| B7 `horizons` null | **KABUL** | Ortak şema. |
| C1 `@INF` ayrı model_id | **KABUL** | SPEC_SCORING §7 canlı kural değerlerini dondurma kaydında ister; ayrı JSON bunu sağlar. |
| **C2 KM dondurması 99, model 97** | **KABUL, koşullu** | Şartname §10 backtest için "aynı PP eğitim kümesi" der (uygulanmış: §1.5); dondurulmuş KM için sessizdir. KM girdi kullanmaz; 99 arzla kurmak kuralın doğal tanımıdır ve `pb_ceiling_v0` ile de paylaşılır. Etki: iki fazladan L = 0 arz D1 hazard'ını 16/97 → 18/99 (S_1 0.835 → 0.818) taşır; RPS'e etkisi ~1e-3 mertebesinde, model lehine yönde [ÇIKARIM]. Koşul: canlı tabloda `ceiling_hazard_v0` için eşleşik sabit karşılaştırıcı olarak **`ceiling_hazard_v0@INF` (97) birincil**, KM(99) kuralları yanında "eğitim kümesi 2 arz farklı" dipnotuyla gösterilsin; SPEC_CEILING §11 başarı ölçütü (iki KM'ye karşı) aynen kalır. Yeni kimlik gerekmez. |
| C3 kurallar P_close aynı formülle | **KABUL** | "Aynı şema". |
| C4 `base_always_ceiling` tavan planında türetilir | **KABUL** | Değer tanım gereği 1. |
| C5 `v1_5_p_up_as_ceiling` ayrı model değil | **KABUL** | Yeni parametre yok; canlıda değeri `v1_5_h99` kaydında. |
| C6 `spec_sha256` + `spec_document_sha256` | **KABUL** | İki anlam ayrıldı; günlükte ikisi de var. |
| C7 bootstrap `random.Random` (SPEC_SCORING §8 PCG64 yerine) | **KABUL (backtest tabloları için)** | Faz 1A yöntemiyle süreklilik. Ancak SPEC_SCORING §8 Faz 2 skorlama kodu için bağlayıcı kalır: `borsai/scoring.py` PCG64 kullanmalı ya da şartname değiştirilmeli (kabul testi 8 ±0.001 seed payı bırakıyor). KÜÇÜK, push'u etkilemez. |
| C8 OPERATIONAL_RULES sabitleri | **KABUL** | Sayılar makul ve raporda yazılı. "Sonuçlar görülmeden yazıldı" iddiası git'ten doğrulanamaz (kod ve sonuçlar aynı commit'te; kabul koşusu 03:44, altın koşu 13:04) — KÜÇÜK, not olarak kalır. |

**Belgelenmemiş sapma (yeni, KÜÇÜK) — A13 önerisi:** SPEC_MARKET20_V0 §7 "Eğitim satırında f6 yok → satır dışlanır, n yeniden sayılır, MIN_TRAIN_N bir kez uygulanır"; kod `borsai/fit.py:501-503` böyle bir satır varsa `FitError` ile durur. H99 + Takvim B'de 0 satır olduğundan dondurulmuş modele ve ledger'a etkisi yok; davranış daha muhafazakârdır (sessiz küçülme yerine görünür durma). Öneri: SPEC_DEVIATIONS'a A13 olarak eklensin (belge değişikliği; kod değişmesin — §2.6'daki kod-JSON hash bağı bozulmasın). Yeni kimlik gerekmez.

---

## 4. predict paritesi [ÖLÇTÜM `ekler/predict_parity_stdout.txt`]

Üç taraf karşılaştırıldı: (a) `models/<m>.json` + stdlib `predict_*`; (b) fit tarafı: `fit_with_estimators` ile yeniden kurulan numpy/sklearn nihai model; (c) JSON parametreleriyle (μ, σ, p05/p95, γ, β / katsayılar) elle hesap.

| Model | Karşılaştırılan girdi | maks \|Δ\| (a)↔(b) | maks \|Δ\| (a)↔(c) | Şartname sınırı |
|---|---|---|---|---|
| `ceiling_hazard_v0` | 97 eğitim arzı + 13 uç durum | 1.0e-15 | 3.9e-16 | 1e-12 |
| `pb_ceiling_v0` | 99 + 10 uç | 5.6e-16 | 3.3e-16 | 1e-12 |
| `pb_v0` | 99 × 4 ufuk + 6 uç | 7.8e-16 | 1.1e-16 | 1e-12 |
| `v1_5_market20_v0` | 97 × 4 (+2 RET) + 10 uç | 8.9e-16 | 1.1e-16 | 1e-12 |
| `v1_6_h99` | 97 × 4 (+2 RET) + 4 uç | 8.9e-16 | 1.1e-16 | 1e-12 |
| `@INF` ×2, `base_km_*` ×2 | girdisiz ve saçma girdiyle aynı sabit eğri | — | 0 | — |

Ret/uyarı kuralları (hepsi ölçüldü):
- `ceiling_hazard_v0`: f3 None/"" → `F3_MISSING`; f3 0.5, 1e-9 → kırpma p05'e, `clipped = true` + uyarı (S_1 0.5606); f3 50, 1e6 → p95'e (S_1 0.8966, tam 8.332 ile aynı, kırpma işareti yok); fiyat 5000 → `OUT_OF_TRAINING_RANGE`(f1) uyarısı, tahmin var (S_1 0.084, dışdeğerleme); payda 0 → `DIVISION_BY_ZERO`; pay > sermaye → `INPUT_INCONSISTENT`; negatif fiyat/f3 → `INPUT_NOT_POSITIVE`. Fit tarafı da aynı sınıra kırpıyor (`fit_clipped` eşit).
- `pb_ceiling_v0`: f3 yok / None → RET ETMEZ; alan boş → `PB_FIELD_MISSING:planned_base_offer_shares`; "10-12" ve "10 – 12" → `PB_PRICE_RANGE`; ID-B → `PB_IDENTITY:ID-B`; sermaye artırımı 0 → `PB_IDENTITY:PB3_RANGE`; fiyat 5000 / 0.01 → uyarı + tahmin; pb4 > 0 → uyarı.
- `pb_v0`: aynı ret kodları; fiyat 5000 → getiri fiziksel sınıra kırpılır ve işaretlenir; `total_demand_multiple` verilse bile okunmaz (çıktı aynı).
- `v1_5_market20_v0`: f6 None → `MARKET20_NOT_PROVIDED`; neden `CALENDAR_NOT_COVERING` / `STALE_S0` → `MARKET20_<NEDEN>`; tanınmayan neden → `NOT_PROVIDED`; "abc" → `MARKET20_NOT_NUMERIC`; f6 0.3 / −0.5 → aralık uyarısı + tahmin; f6 var f3 yok → `F3_MISSING`; çekirdek `predict` f6'sız → `FEATURE_NOT_PROVIDED:f6`.
- `v1_6_h99`: f3 None → `F3_MISSING`; f4 = 0 → `F4_ZERO_NO_TRAINING_EXAMPLE`; f3 50 → `F3_WINSORIZED`; fiyat 5000 → kırpma.

Hepsi şartnamelerdeki tabloyla (SPEC_CEILING §7, SPEC_PB §5, SPEC_MARKET20 §7, SPEC_V1_6 §6) uyumlu. Not (KÜÇÜK, gözlem): `pb_ceiling_v0` fiyat 0.01 gibi saçma girdide S_1 = 0.998 üretir; yalnız aralık uyarısı verir. Şartname "tahmin + uyarı" der; uygulama tarafı uyarıyı görünür kılmalı.

---

## 5. Beklenti tablosu (docs/MODELS.md) — hükümler doğru uygulanmış mı?

Bağımsız sayım [ÖLÇTÜM, ledger'lardan]:

| Model | Beklenti | Gerçekleşen (bağımsız) | MODELS.md hükmü | Doğru mu |
|---|---|---|---|---|
| ceiling | RPS farkı −0.005…−0.02, aralık 0'ı içerir | −0.0496 [−0.0751, −0.0219] | tutmadı | ✓ |
| ceiling | en çok kazanç k = 3…5; k = 1 küçük; k = 10 ≈ 0/hafif kötü | argmax k = 3; k1 −0.027; k10 −0.0055 | kısmen (k1, k10 tutmadı) | ✓ kurala göre. Yorum notu: "k = 1'de küçük" göreli okunursa (−0.027 < −0.094) tutmuş sayılırdı; OPERATIONAL_RULES mutlak eşik seçmiş. KÜÇÜK |
| ceiling | λ çoğu fold 10–300; erken INF sık | 38/87 = %44; ilk 20'de INF 0 | tutmadı | ✓ |
| ceiling | β_f3 < 0, β_f1 > 0, β_f2 > 0 | −0.550, +0.449, −0.179 | kısmen (β_f2) | ✓ |
| ceiling | (c) @INF'ten noktasal kötü | −0.0503 | gerçekleşmedi | ✓ |
| ceiling | (b) kalibrasyon > 0.15 | \|0.8655 − 0.8161\| = 0.049 | aşılmadı (prospektif ölçüt) | ✓ |
| pb_ceiling | KM'den ayırt edilemez; ceiling'den kötü/eşit | KM aralıkları 0'ı dışlıyor; ceiling'e karşı +0.034 [+0.018, +0.052] | kısmen | ✓ |
| pb_v0 | D1 MAE yenik/eşit; D1 p_up taban oranından ayırt edilemez | +0.0083 [+0.0047, +0.0125]; −0.0025 [−0.0080, +0.0018] | tuttu | ✓ |
| pb_v0 | D5/D10 kazanç ≤ üçte bir; aralık 0'ı içerir | D5 −0.0355 (sınır −0.028), D10 −0.0478 (sınır −0.0387); aralıklar 0'ı içeriyor | kısmen | ✓ |
| pb_v0 | V1.5'e karşı her ufukta kötü/eşit | 8/8 hücrede aralık 0'ın tamamen altında değil | tuttu | ✓ |
| pb_v0 | α çoğunlukla ≥ 100; D1'de INF sık | %27; %16 | tutmadı | ✓ |
| pb_v0 | D1 ZERO ya da C ≤ 0.001 seçilir | 39/80 = %48.75 (> %50 değil) | kısmen | ✓ kurala göre; sınırda (KÜÇÜK not) |
| market20 | 8 aralık 0'ı içerir; \|ΔMAE\| < 0.002; \|ΔBrier\| < 0.005 | 8/8; evet; D10 Brier +0.0054 | kısmen | ✓ |
| market20 | f6 katsayısı pozitif, küçük | Ridge f6: +0.003/+0.004/+0.026/+0.063 (4/4 > 0); Logit f6: +0.16/−0.26/+0.07/−0.26 | tuttu | ✓ kod yalnız Ridge kafasına bakıyor (`report_faz1b.py:437, 443`). Şartname cümlesi parantezle getiriye işaret ediyor; Logit dahil edilse "kısmen" olurdu. KÜÇÜK: MODELS.md'ye "yalnız getiri kafası; Logit'te 2/4 negatif" dipnotu önerilir |
| v1_6 | D1 α ∈ {1000,10000,INF} çoğu; MAE 0.0297–0.0332; medyana yenik | %12; 0.0297; +0.0046 | kısmen | ✓ |
| v1_6 | D3 ≈ 0; D5 küçük | +0.0000; +0.0001 | tuttu, tuttu | ✓ |
| v1_6 | D10 α ∈ {0.001, 0.01} sık; ±0.01; yön belirsiz | %67; +0.0008 [−0.0003, +0.0028] | tuttu | ✓ |
| v1_6 | Logit D1 ZERO/1e-4/1e-3 sık; Brier ~0.10; diğer \|ΔBrier\| < 0.005 | %5; 0.0944 (\|Δ\| 0.0056 > 0.005); 0/0/0 | kısmen | ✓ |
| v1_6 | kenara yapışma > %50 yok (INF/ZERO hariç) | D10 Ridge α = 0.001: 57/87 = %66 | tutmadı | ✓ |

"En iyi KM" seçimi doğru (ceiling: last10 0.1999 < expanding 0.2072; pb_ceiling: expanding 0.2144 < last10 0.2156). Prospektif birincil hücreler SPEC_SCORING §7 ile aynı (`report_faz1b.py:103-109`). Hiçbir yerde "geçiyor" aralık 0'ı içerirken yazılmamış; canlı n = 0 her bölümde "hüküm yok".

---

## 6. Bulgu listesi (önem sırasıyla)

| # | Önem | Bulgu | Kanıt | Öneri |
|---|---|---|---|---|
| 1 | KÜÇÜK | SPEC_MARKET20 §7 "f6'sız eğitim satırı dışlanır" kodda `FitError` ile durma; SPEC_DEVIATIONS'da yok | `borsai/fit.py:501-503`; H99'da 0 satır | SPEC_DEVIATIONS'a A13; kod değişmesin |
| 2 | KÜÇÜK | C2: dondurulmuş KM(99) ile `ceiling_hazard_v0`(97) eğitim kümeleri 2 arz farklı; model lehine ~1e-3 RPS | `models/base_km_*.json` n = 99; `ceiling_hazard_v0.json` n = 97 | Canlı tabloda @INF(97) birincil eşleşik sabit + dipnot |
| 3 | KÜÇÜK | market20 "işaret pozitif" yalnız Ridge kafasıyla değerlendirilmiş; Logit'te 2/4 negatif | `report_faz1b.py:437,443`; JSON katsayıları | MODELS.md dipnotu (rapor kodu değişirse kod-JSON hash bağı için §2.6 notuna bak; belge düzeyi tercih) |
| 4 | KÜÇÜK | C7: backtest bootstrap RNG SPEC_SCORING §8'den farklı | `borsai/metrics.py:108-127` | Faz 2 skorlama kodu PCG64 ya da şartname güncellemesi |
| 5 | KÜÇÜK | OPERATIONAL_RULES'ın sonuçlardan önce yazıldığı git'ten doğrulanamıyor; iki eşik (k = 1 "küçük", D1 C payı %48.75) sınırda | aynı commit; sayımlar §5 | Not olarak kalsın; hükümler değişmez |
| 6 | KÜÇÜK | Test 2'nin sızıntı satırı ledger'ın kendi sütununu kullanıyor | `tests/test_ceiling.py:100-101` | Bu denetim bağımsız kapattı (§1.2); ileride testte bağımsız tarih hesabı |
| 7 | KÜÇÜK (gözlem) | Backtest'te model ve KM kuralları sistematik iyimser (ort. S_k − gözlenen ≈ +0.05…+0.06); rejim kayması | §1.6 kalibrasyon | Prospektif ölçüt (b) izlesin; kod değişikliği yok |

KRİTİK: yok. ÖNEMLİ: yok. Push'u engelleyen bulgu yok.

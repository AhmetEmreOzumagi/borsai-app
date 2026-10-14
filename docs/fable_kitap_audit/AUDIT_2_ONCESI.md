KITAP_AUDIT_2: [P] 0 kritik, 0 orta, 2 düşük; [K] 6; [B] 3

# AUDIT_2_ONCESI — listeleme öncesi modellerin bağımsız denetimi

- Görev: `docs/prompts/FAZ9_KITAP_AUDIT_2_ONCESI.md` (TASK_ID `BORSAI_FAZ9_KITAP_AUDIT_2_20261008`). Ortak kurallar: `FAZ9_KITAP_AUDIT_ORTAK.md`.
- Denetlenen: `docs/fable_kitap_audit/kitap/04_listeleme_oncesi_modeller.md` (§4.1–§4.11) ve `models/INDEX.json`'daki 27 model. HEAD `ee3796d` (fark listesi boş; izlenmeyen dosyalar yalnız kılavuz ve görev dosyaları).
- Denetleyen: Fable (ayrı oturum). Ağ yok; `borsai` yalnız klondaki mutasyon testinde (Adım 6) import edildi; diğer her ölçüm sıfırdan yazılmış betiklerle yapıldı (`ekler/2/`).
- İşaretler: **[ÖLÇTÜM]** = bu oturumda betik/komutla; **[ÇIKARIM]** = yorum.

## 1. Özet (proje sahibi için)

1. **Listeleme öncesi modellerde doğruluk rakamını, tahmini ya da hükmü değiştiren bir hata bulunmadı.** 27 modelin dosya, şartname ve belge hash'leri tutuyor; dokuz ailenin nihai fit'i sıfırdan yeniden üretildi ve dondurulmuş katsayılarla 1e-16…1e-9 içinde eşleşti; kılavuzun 63 hüküm hücresi kendi bootstrap'ımla 4 ondalıkta birebir çıktı; 8 ailede 16 fold'luk mutasyon testinde sızıntı yok.
2. **`ceiling_hazard_v0` sıfırdan kuruldu** (ön işleme, kişi-dönem tablosu, pseudo-satırlar, Newton, iç CV): katsayı farkı 5.6e-17, λ skor tablosu farkı 1.1e-16, seçilen λ = 10. NETGL'in ekrandaki sayıları (3.3 gün, %82, %67, 1.9 gün, %45, %6) kayıt ve kılavuzla aynı.
3. **j ≥ 3'te "yarın da tavan"ın sabit %67 kalması bir hata değil, tasarımın doğrudan sonucudur:** g3 = {4..10} grubu tek sabit paylaşır (SPEC_CEILING_V0 §3). Veri bu gruplamayı destekliyor: 4–10. günlerin tehlikeleri arasındaki fark binom gürültüsünden ayırt edilemiyor (Pearson χ² = 0.46, sd 6). NETGL'in %67'si ile geçmiş arzların %80'i arasındaki fark NETGL'in girdilerinden gelir (büyük arz, ortalamanın altında talep katı): modelin j = 3'teki ortalama tahmini test arzlarında %80.3, gözlenen %76.8'dir; model bu noktada iyi kalibre, hatta hafif iyimserdir. "Profesyonel durmama" bir sunum sorunudur; modeli değiştirmek yeni model_id ister (FAZ10 kapsamı).
4. İki düşük önemli proje notu: SPEC_CEILING_PATH_V0 §2'deki "424/424" toplamı kendi satır sayımıyla (…= 423) çelişiyor, ölçüm 423/423; SPEC_CEILING_V0 §4 tablosu f1'i fiyat × pay diye yazarken kod kaynak bildirimli büyüklüğü kullanıyor (SPEC_DEVIATIONS A1'de belgeli, etkisi ≤ 1e-9).
5. Kılavuz hataları küçük: `GITLOG.txt` diye bir dosya repoda yok (iddialar git geçmişinden doğrulandı); `pb_ceiling_path_v0`'ın birincil hücresi olmaması şartnamede yazılı; (C) adaylarının `base_rate` karşılaştırıcısı V1.5 planının ledger'ından (99 arzlık eğitim) gelir, kılavuz bunu söylemiyor (hükümler değişmiyor).
6. Doğrulanmayan tek şey §4.9'un kasa sütunu (Denetim 3'ün işi) ve V1.5 port kabulünün sayıları (yeniden koşulmadı).

## 2. Bulgular tablosu

| no | tür | önem | kılavuzdaki yer | kısa tanım | kanıt | öneri |
|---|---|---|---|---|---|---|
| P1 | [P] | DÜŞÜK | §4.6.2 (kaynak: `docs/specs_faz4/SPEC_CEILING_PATH_V0.md` §2) | Şartname "C_h … **424/424** Decimal eşitlik" diyor; aynı cümledeki h = 1..10 sayıları (81, 70, 66, 53, 41, 33, 27, 21, 17, 14) toplamı **423**'tür. Bağımsız ölçüm: 423/423 (seri ≥ h olan 423 arz-günün hepsinde C_h = kapanış; ayrıca 990/990 seansta THM üst limiti = U(önceki kapanış)). | `ekler/2/s8_limit_path_out.txt`; SPEC_CEILING_PATH_V0.md:52 | Belge düzeltmesi (toplam 423). Model, kod, JSON değişmez; model_id gerekmez. |
| P2 | [P] | DÜŞÜK | §4.3.2, §4.4.4 (kaynak: `docs/specs/SPEC_CEILING_V0.md` §4 tablo) | Şartname tablosu f1 = ln(`ipo_price_tl` × `shares_offered`); kod (`borsai/features.py:146-165`) kaynak bildirimli `ipo_size_tl`'yi kullanır (99/99 arzda MASTER'da dolu; 4 arzda fiyat × paydan 0.20–0.46 TL farklı). SPEC_DEVIATIONS A1 bunu belgeler; aynı §4'ün "tek tanım" cümlesi kodla uyumludur, tablo satırı değildir. | `ekler/2/s3_out.json` → `f1_master_ne_price_x_shares`; SPEC_DEVIATIONS.md A1 | Belge: şartname tablosundaki f1 tanımı "kaynak bildirimli büyüklük, yoksa fiyat × pay" olarak düzeltilmeli. Model etkisi yok (ln farkı ≤ 1e-9); model_id gerekmez. |
| K1 | [K] | ORTA | §4.4.12 ve §4.10 "Kaynak dosyalar" | `GITLOG.txt` repoda yok (`find`, `git log --all -- GITLOG.txt` boş; yalnız `app/src-tauri/target/orch_sunum/gitlog.txt` adlı izlenmeyen derleme artığı var). Dayandırılan iki iddia doğru: commit `1869da6` "BORSAI_FAZ1B_CONFORMITY … all models PUSH_OK", commit `41f14f0` "BORSAI_APP_P34_C3: embed 27". | `git log --oneline --all` | Kılavuzda kaynak `git log` ya da ilgili commit sha'ları olmalı. |
| K2 | [K] | DÜŞÜK | §4.6.2 | "424/424" şartnameden aynen aktarılmış; doğrusu 423/423 (P1). | `ekler/2/s8_limit_path_out.txt` | — |
| K3 | [K] | DÜŞÜK | §4.11 "Belirsiz kalanlar" | "`pb_ceiling_path_v0`'ın … neden birincil hücre taşımadığını … bir belgede görmedim." Şartname bunu açıkça yazar: SPEC_CEILING_PATH_V0 §5 "Önceden ilan edilen **TEK** birincil hücre: `ceiling_path_v0`, D5 getiri MAE, `base_train_median`'a karşı … Diğer bütün hücreler keşif". | SPEC_CEILING_PATH_V0.md:141 | — |
| K4 | [K] | DÜŞÜK | §4.8.4, §4.9 (`fall_d10_v0_*` − `base_rate`) | Karşılaştırıcı `base_rate`, (C) planının 94 arzlık eğitim kümesinden değil, V1.5 planının altın ledger'ından (99 arz, sha pinli; `borsai/backtest.py:1390-1394`) okunur; test arzları aynı, kuralın eğitim kümesi farklı. Kılavuz bunu söylemiyor. Ölçüm: (C) planının kendi taban oranıyla fark ≤ 0.0006 puan (h99 −0.0430 [−0.0772, −0.0044]; pooled −0.0488 [−0.0662, −0.0296]; addsale −0.0061 [−0.0289, +0.0154]); iki taban oranı arasındaki fark en çok 0.011; hükümler değişmez. | `ekler/2/s4_out.txt` son blok | Kılavuzda karşılaştırıcının kaynağı yazılmalı; proje tarafında SPEC_C_V0 §5.1 bu seçimi açıkça söylemiyor (kod ve MODELS.md söylüyor) — belge notu, model_id gerekmez. |
| K5 | [K] | DÜŞÜK | §4.2.6 | "%95 aralık, sıralanmış 4000 değerin 100. ve 3899. elemanıdır": kod 0 tabanlı indeks 100 ve 3899'u alır (`borsai/metrics.py:32-33`), yani 1 tabanlı sayımla 101. ve 3900. değer. Aynı ifade MODELS.md'de de var; hesap doğru, sözcük belirsiz. | metrics.py:32-33, 123-125 | Belge: "0 tabanlı indeks" ya da "101. ve 3900." yazılmalı. |
| K6 | [K] | DÜŞÜK | §4.1.5 | `base_km_last10` için "her gün d için … son 10 arz": doğru; ek olarak `base_km_*`'nin dondurulmuş JSON'u 99 arzla (ALBTN, ENDAE dahil), `ceiling_hazard_v0` 97 arzla eğitilir (SPEC_DEVIATIONS C2); kılavuz bu farkı §4.4.2'de dolaylı anlatıyor, kural tablosunda söylemiyor. | `ekler/2/s3_out.json` (`km_expanding_maxdiff` = 0, 99 arz) | — |
| B1 | [B] | — | §4.9 "Kasa birincili (bilgi)" sütunu | Zaman-dışı terazi Denetim 3'ün kapsamı; ölçülmedi. | — | — |
| B2 | [B] | — | §4.3.1 | V1.5 port kabulü (351/351 eğitim kimliği, α 351/351, C 350/351, BETAE sapması) MODELS.md'den iddia olarak alındı; legacy koşusu yeniden yapılmadı. Yeni repodaki nihai fit'in bağımsız yeniden üretimi (bu rapor §5) bunu dolaylı destekler. | MODELS.md "Port kabulü" | — |
| B3 | [B] | — | §4.4.12 "koşullu keşif" satırları | Koşullu RPS keşif hücreleri (j = 1..9) yeniden üretilmedi (keşif; hüküm değil). | — | — |

Hüküm kontrolü (CLAUDE.md kural 6): kılavuzda "geçiyor" denen 20 hücrenin hepsinde kendi aralığım 0'ın altında ve yön doğru; "ayırt edilemiyor" denen hücrelerin hepsinde aralık 0'ı içeriyor; "kural daha iyi / bozuyor" denenlerde aralık 0'ın üstünde. **Aralığı 0'ı içerip "geçiyor" denen ya da tersi hücre yok** (`ekler/2/s4_out.txt`, 63 hücre).

## 3. Bölüm bölüm kontrol listesi

| § | Kontrol edilen iddia | Tutan | Tutmayan / not |
|---|---|---|---|
| 4.1 Harita, kimlikler | 27 giriş; ad/algoritma/n/dondurma tarihi tablosu; hash'ler; kural değerleri (median/mean/rate/last10, KM eğrileri); `v1_5_p_up_as_ceiling` n'leri | 27 model × 3 hash + 24 kural sabiti + 20 KM değeri | — |
| 4.2 Araç kutusu | L2 ölçeği ve C eşlemesi; sabit terim cezasız; Type-7; ddof = 0; bootstrap tanımı; hüküm sözcükleri | 7 | K5 (indeks sözcüğü) |
| 4.3 V1.5/V1.6/market20 | ön işleme parametreleri; D1–D10 α/C; D5 katsayıları; NETGL z ve tahminleri; 6 + 5 backtest hücresi; V1.6 8 hücre; seçim dağılımı (73/89, 57/87, %12); market20 8 hücre; f6 işaretleri; 19 sınır dışı; 8 f3-eksik fold | 61 | — |
| 4.4 `ceiling_hazard_v0` | PP tabloları (508/85, 506/83, gün tablosu, grup toplamları); ön işleme; γ, β, λ tablosu, yineleme; @INF; reclose; NETGL adım adım; RPS'ler; 4 RPS + 6 Brier hücresi; kalibrasyon; λ sayımı (9/40/38); azınlık sayıları; beklenti tablosu | 70+ | P2 (f1 tanımı, şartname tablosu) |
| 4.5 PB | pb1–pb3 tanımları; `pb_v0` α/C, z parametreleri, NETGL; 5 + 4 hücre; `pb_ceiling_v0` fit, @INF, NETGL S; 4 hücre; λ sayımı (1/23/62/1); ilk fold SKYMD | 30 | — |
| 4.6 Tavan yolu | adım tablosu, snap/U; C_h eşitliği; 4 snap arzı; NETGL C_h/ρ; hücre sayıları ve medyanları (567; 18×10; 67…11); 8/18; 7 + 3 hücre; D1 beraberlik 84/87 (bit-eşit 52) | 40 | K2 (424 → 423) |
| 4.7 v1 ailesi | 4 modelin katsayıları, kırpma sınırları, δ; 4 yakın dönem hücresi ve etiketleri; merdiven; 3 KM hücresi; pooled Brier k = 1, 3, 5; NETGL f1r | 25 | — |
| 4.8 (C) ailesi | eğitim kümeleri (94/161/165); katsayılar; @ZERO oranları; NETGL olasılıkları; birincil + 7 ikincil + merdiven hücresi | 22 | K4 (karşılaştırıcı kaynağı) |
| 4.9 Hüküm tablosu | 14 satırın backtest hücreleri ve hükümleri | 14 | kasa sütunu bakılmadı (B1) |
| 4.10 Üretimde ne var | NETGL kaydı 16 model; öne çıkarma kuralı §5.5 (şartname metni); "embed 27" commit'i | 3 | K1 (kaynak yolu) |
| 4.11 Sınırlar | varyant sayaçları 23 / 2 059; 2 054 keşif satırı; ay blokları 22–24; D1 azınlık 10; beklentiden çok iyi kuralı ve FREEZE_OK; bilinen zayıflıklar (β_f2, kalibrasyon, L = 10 yoğunlaşması, nominal f1); şartnamelerin maruziyet bölümleri | 12 | K3 |

## 4. Adım adım ölçümler

### Adım 1 — Harita ve kimlikler [ÖLÇTÜM `ekler/2/s1_hashes.py`, `s1_hashes_out.txt`]

- `models/INDEX.json`: `borsai.model_index/1`, 27 giriş; her girişte `sha256` = dosya baytlarının sha256'sı (27/27), `spec_sha256` = JSON içindeki kanonik `spec` sözlüğünün sha256'sı ve dosyadaki `spec_sha256` alanı (27/27), `spec.spec_document.sha256` = `docs/specs*/…md` dosyasının sha256'sı (20/20; Faz 1A'nın 7 modelinde belge alanı yok, `v1_5_h99` legacy şartnameyi `1245bf0f…` ile pinler, `legacy/config/model_v1_5_spec.json` sha256'sı aynı).
- Kılavuz §4.1.3 tablosu INDEX ile birebir (ad, algoritma, n, dondurma günü, kesim 2026-08-19; `base_always_ceiling` ve `base_zero` kesimsiz).
- Kural sabitleri (§4.1.5) tablodan yeniden hesaplandı: medyan 0.1000/0.3297/0.3738/0.2471; ortalama 0.0774/0.2097/0.3121/0.4725; taban oranı 0.8990/0.8081/0.7778/0.7071; son-10 0.6/0.5/0.4/0.5 — dondurulmuş JSON'larla aynı. KM eğrileri (99 arz) JSON ile |Δ| = 0.

### Adım 2 — Ortak araç kutusu (şartname cümlesi ↔ kod satırı)

| Konu | Şartname | Kod | Hüküm |
|---|---|---|---|
| L2 cezası, hazard | SPEC_CEILING_V0 §5: `J = −Σ_r w_r[…] + (λ/2)·‖β‖²`, "γ cezasız" (toplam, n'e bölünmez) | `borsai/hazard.py:117-123` `value = Σ w·(logaddexp(0,η) − eη)`; `value += 0.5 * lam * (beta @ beta)`; `:130` `pen = [0]*n_free + [λ]*p` | Aynı; ölçek n'den bağımsız |
| L2 cezası, lojistik (V1.5/V1.6/PB/(C)) | `legacy/config/model_v1_5_spec.json` logistic.objective_function: `0.5·wᵀw + C·Σ_i log(1 + exp(−ỹ_i(x_iᵀw + c)))`, "intercept c is NOT penalized" | `borsai/fit.py:108` `_LOGIT_KWARGS = dict(l1_ratio=0.0, solver="lbfgs", fit_intercept=True, …)`; `:363, :392` `LogisticRegression(C=C, **_LOGIT_KWARGS)` | sklearn'ün amacı tam bu biçimdir; C'ye bölünce Σ NLL + (1/(2C))‖w‖² → **λ = 1/C, n'e göre düzeltme gerekmez** (kılavuz §4.2.2 doğru). Doğrulama: bu amaçla kendi Newton'ım, sklearn'ün lbfgs sonucunu D1–D10'da 3.5e-9 … 4.4e-8 içinde üretti (`s5_out.json`) |
| Ridge | legacy spec ridge.objective_function: `‖y − Xw − c·1‖² + α‖w‖²`, "RSS is NOT divided by n", "intercept NOT penalized" | `fit.py:306, 319` `Ridge(alpha=…, fit_intercept=True, solver="svd")` | Aynı (sklearn Ridge RSS'yi n'e bölmez, sabiti merkezleyerek cezasız bırakır); kapalı biçimle |Δ| ≤ 1.1e-16 |
| Sabit terim cezasız | yukarıdaki ikisi | `hazard.py:130` (`pen[:n_free] = 0`), `fit_intercept=True` | Aynı |
| Type-7 kantil | SPEC_CEILING_V0 §4 "p05/p95 Type-7 doğrusal kantil" | `preprocess.py:228` `quantile_type7`: `h = (n−1)p + 1` (Fraction) | Aynı; f3 [1.14870997716, 8.332] birebir |
| z dönüşümü ddof = 0 | §4 "popülasyon std'si (ddof = 0)" | `preprocess.py:545-548` (log sütunu: `Σ(v−mean)² / n`), `:565` (`variance_frac = Σ(...)/n`) | Aynı; ortalama/std 97 arzda |Δ| = 0 |

### Adım 3 — `ceiling_hazard_v0` sıfırdan [ÖLÇTÜM `ekler/2/s3_hazard_scratch.py` → `s3_out.json`; `borsai` import edilmedi]

Kurulum: ham tablo + MASTER (`ipo_size_tl`) + seans tarihleri → f1/f2/f3 (Decimal, 10 ondalık HALF_UP yüzde) → f3 Type-7 winsor, ln f1 (60 hane), z (ddof = 0) → kişi-dönem tablosu, g1/g2/g3 → 6 pseudo-satır (w = 0.5) → Newton (başlangıç kapalı biçim γ, tol 1e-10) → iç arz-bırak CV (97 × 9 fit).

| Ölçüm | Benim | Repo | |Δ| |
|---|---|---|---|
| PP, 99 arz: risk/olay gün tablosu | 99/81/70/66/53/41/33/27/21/17; 18/11/4/13/12/8/6/6/4/3; 508 satır, 85 olay | SPEC §2, kılavuz §4.4.2 | 0 |
| PP, 97 arz (ALBTN, ENDAE hariç; ikisi L = 0) | 506 satır, 83 olay, 423 sağ kalım; gruplar 97/16, 151/15, 258/52 | JSON `training`, kılavuz | 0 |
| Ön işleme (winsor, μ, σ) | f1 21.17172714170336 / 0.709158677133166 … | JSON `preprocessing` | 0.0 |
| Nihai fit λ = 10 | γ = [−1.80946107, −2.14701490, −1.00708906]; β = [+0.44894966, −0.17873211, −0.54985106]; 5 yineleme, max\|∇\| 8e-15 | JSON | **5.6e-17** |
| λ = INF kapalı biçim | γ = [−1.59724264, −2.17548459, −1.36948724] | `ceiling_hazard_v0@INF.json` | 0.0 |
| İç CV skor tablosu (9 λ) | 0.406423 / 0.406178 / 0.405782 / **0.405426** / 0.407665 / 0.417609 / 0.430269 / 0.439370 / 0.444816 | JSON `lambda_score_table` | 1.1e-16; seçilen λ = 10 |
| Yeniden tavan oranları | n_a 102, a_a 1, n_b 429, a_b 61 → r_a 0.014563, r_b 0.143023 | JSON | 0 |
| KM (99 arz) genişleyen / son-10 | S = [0.8182 … 0.1414] / [0.5000 … 0.0587] | `base_km_*.json` | 0.0 |

S_k = Π_{d≤k}(1 − h_d) ve RPS = (1/10)Σ_k(S_k − 1[L ≥ k])²: SPEC_CEILING_V0 özet 1 ve 7, SPEC_SCORING §7 ↔ `survival.py` `survival()` (soldan çarpım) ve `rps()` (aynı formül); `backtest.py:904-910` `ceiling_loss` aynı tanım, kırpmasız. Kılavuz §4.2.5/§4.4.1 ile aynı.

**NETGL** (girdi: 2 233 000 000 TL, f2 = 28, f3 = 2.84; kırpma yok): z = (0.50043, 0.59618, −0.34814); β·z = +0.30954; η = (−1.49993, −1.83748, −0.69755); h = (0.18244, 0.13735, 0.33235). S = [0.81756, 0.70527, 0.60840, 0.40620, 0.27120, 0.18106, 0.12089, 0.08071, 0.05388, 0.03598] — kayıttaki S ile |Δ| = 5.6e-16.

| Ekrandaki sayı (kılavuz §1.5, §8.14, §8.16) | Tanım | Benim | Tutuyor |
|---|---|---|---|
| ortalama 3.3 gün | E[L] = ΣS_k | 3.2811 | ✓ |
| en olası yol 3 gün, 4. gün bozulma | argmax P(L = l) = 3 (0.2022), kümülatif ≥ 0.5 ilk l = 3 | 3 | ✓ |
| D1'de tavan %82 | S_1 | 0.8176 | ✓ |
| j = 3 ve j = 6'da "yarın da tavan" %67 | S_4/S_3, S_7/S_6 | 0.66765, 0.66765 | ✓ (j = 4, 5, …, 9'da da aynı: 1 − h_g3) |
| j = 3'te kalan 1.9 gün | Σ_{k≥4} S_k / S_3 | 1.8900 | ✓ |
| koşullu medyan 4 | P(L = l \| L ≥ 3) kümülatif ≥ 0.5 | 4 | ✓ |
| P(L ≥ 5 \| L ≥ 3) %45; P(L = 10 \| L ≥ 3) %6 | S_5/S_3; S_10/S_3 | 0.4458; 0.0591 | ✓ |
| geçmiş arzlar j = 3: %80 (66'dan 53); j = 6: %82 (33'ten 27); j = 0: %82 (99'dan 81) | KM genişleyen S_{j+1}/S_j; risk_d − olay_d | 0.8030 = 53/66; 0.8182 = 27/33; 81/99 | ✓ |
| NETGL (L = 3) RPS: model 0.0570, @INF 0.0953, KM 0.0968, KM-10 0.1244 | rps(S, 3) | 0.05701 / 0.09528 / 0.09681 / 0.12437 | ✓ |

**j ≥ 3'te sabitlik — hüküm [ÖLÇTÜM + ÇIKARIM]:** η_d = γ_{g(d)} + β·z olduğu ve g3 = {4,…,10} tek γ taşıdığı için h_4 = … = h_10 ve S_{j+1}/S_j = 1 − h_g3 her j ≥ 3'te aynıdır; altın ledger'ın 87 fold'unun hepsinde hazard_4..hazard_10 bit-eşit (`ledger_g3_constant_all_folds = true`). Bu SPEC_CEILING_V0 §3'ün açık kararıdır (olay bütçesi: gün başına 3–13 olay), hata değildir. Verinin bu gruplamayı destekleyip desteklemediğini ölçtüm: 97 arzlık eğitim kümesinde 4–10. günlerin ham tehlikeleri (0.197, 0.226, 0.195, 0.182, 0.222, 0.190, 0.176) ortak 0.2016 oranına karşı Pearson χ² = **0.46 (sd 6)**: günler arası fark gürültü düzeyinde; g2'de χ² = 2.60 (sd 1). Yani j ≥ 3'te günden güne değişen bir devam olasılığı bu veriden öğrenilemez; sabitlik modelin dürüst çıktısıdır. Sunum sorunu olarak kalır; FAZ10'un işi.

**%67 ile %80 farkı — kalibrasyon [ÖLÇTÜM, altın ledger 87 fold, walk-forward]:**

| j (seri sürüyor) | n | model ort. S_{j+1}/S_j | gözlenen devam | sayım |
|---|---|---|---|---|
| 0 | 87 | 0.865 | 0.816 | 71/87 |
| 1 | 71 | 0.909 | 0.845 | 60/71 |
| 2 | 60 | 0.917 | 0.933 | 56/60 |
| **3** | 56 | **0.803** | 0.768 | 43/56 |
| 4 | 43 | 0.818 | 0.767 | 33/43 |
| 5 | 33 | 0.815 | 0.788 | 26/33 |
| 6 | 26 | 0.839 | 0.846 | 22/26 |

Grup düzeyinde (fold dışı): g1 ortalama tahmin tehlikesi 0.135 / gözlenen 0.184; g2 0.087 / 0.115; g3 0.176 / 0.215. Örneklem içinde (nihai fit) skor denklemi gereği 0.169/0.165, 0.102/0.099, 0.2025/0.2016.
[ÇIKARIM] Modelin j = 3'teki **ortalama** tahmini (%80.3) geçmiş arzların oranıyla (%80.3) aynı, gerçekleşenden (%76.8) biraz yüksektir; yani model g3'te tehlikeyi olduğundan **düşük** görür (seriyi hafifçe uzun; MODELS.md'nin kalibrasyon satırıyla aynı yön). NETGL'in %67'si ise kalibrasyon değil, kovaryat etkisidir: z_f1 = +0.50 (büyük arz) ve z_f3 = −0.35 (düşük talep) tehlikeyi 0.27'den (ortalama arz, σ(γ_g3)) 0.33'e çıkarır. Ekranda yan yana duran iki sayı farklı soruların cevabıdır: "bu arz için" ve "bütün arzlar için". Kılavuz §4.4.12 ve §8.16 bunu doğru anlatıyor.

### Adım 4 — Hüküm tablosu, kendi bootstrap'ımla [ÖLÇTÜM `ekler/2/s4_bootstrap.py`, `s4_fix_inf.py` → `s4_out.txt`, `s4_out.json`]

Bootstrap: ilk işlem ayı blokları (ilk görünüş sırası), `random.Random(20260921)` her hücrede ayrı, `choices` ile blok sayısı kadar iadeli çekim, 4000 tekrar, sıralı dağılımın 100 ve 3899 indeksli elemanları (C7, MODELS.md). Eşleştirme ticker (+ ufuk) ile, iki tarafın da skorlandığı fold'larda; MAE kırpılmamış tahminle; V1.5/PB/tavan yolu Brier'i [0.01, 0.99] kırpmasıyla, Faz 7/7C Brier'i kırpmasız; RPS kırpmasız.

**63 hücre, 63/63 kılavuzla 4 ondalıkta birebir** (fark, alt uç, üst uç, n): §4.3.6 (6 MAE + 5 Brier), §4.3.7 V1.6 D10 birincil (+0.0008 [−0.0003, +0.0028], 87; diğer 7 hücre de ayırt edilemiyor, D3/D5/D10 Brier farkı tam 0), §4.3.8 market20 D5 birincil (−0.0008 [−0.0178, +0.0137], 87; D10 Brier +0.0054), §4.5.3 `pb_v0` 5 + 4 bilgi hücresi, §4.4.12 4 RPS + 6 Brier(k) + kalibrasyon satırı, §4.5.4 4 hücre, §4.6.6 7 + 3 hücre (D1 beraberlik: bit-eşit 52, |fark| < 0.001 84/87), §4.7.4 4 birincil + 2 merdiven + 3 KM + 3 Brier(k), §4.8.4 1 birincil + 7 ikincil + 1 merdiven. Tek ilk uyuşmazlık (`ceiling_path_v0` − `@INF`) benim eşleştirme hatamdı (V1.5 fold kümesiyle 85 yerine tablo getirisiyle 87); düzeltince −0.1033 [−0.1462, −0.0628], 87 (`s4_fix_inf.py`).

Yakın dönem etiketleri (kurallar: alt > 0 "bozuyor"; üst ≤ 0.010 / 0.008 "tolerans içinde"): clip tolerans içinde, real bozuyor, pooled bozuyor, pooled@INF bozuyor; (C) pooled − h99 belirsiz — kılavuz ve `scores.json` ile aynı.

Karşılaştırıcılar aynı arzlarda mı: evet, her hücre ticker kesişimiyle kurulur; n'ler kılavuzla aynı. Tek nüans K4: (C) adaylarının `base_rate`/`v1_5_h99` değerleri V1.5 planının ledger'ından gelir (test arzları aynı, kuralın eğitim kümesi 99 arz); (C) planının 94 arzlık kendi taban oranıyla yeniden hesap hükümleri değiştirmedi.

### Adım 5 — Diğer aileler: şartname ↔ kod ↔ JSON ve nihai fit'ler [ÖLÇTÜM `ekler/2/s5_refits.py` → `s5_out.json`]

Ön kayıt sırası (git DAG) [ÖLÇTÜM `git merge-base --is-ancestor`]: `d3fabad` (Faz 1 şartnameleri, 2026-09-22 02:55) → ilk koşular aynı commit'te (`experiments/log.jsonl`, 03:43–03:46); `52e1567` (tavan yolu şartnamesi, 18:32) → `50c62da` koşusu (19:02) ATA; `6a16c16` (v1 şartnamesi, 09-25 19:51) → `2a21a96` kod (09-26 03:10) → `70b67d1` backtest ATA; `4fe4e51` ((C) şartnamesi, 09-27 17:12) → `3c93f9c` kod (20:45) → `acaca2d` backtest ATA. Yedi şartname dosyasının git geçmişinde yalnız ilk commit'i var (sonradan değişmemiş); birincil hücre tanımları `scores.json` `primary_cell` alanlarında şartnamelerle aynı (`v1_5_h99` D5 MAE − medyan; V1.6 D10 − V1.5; market20 D5 − V1.5; `pb_v0` D5 − medyan; iki tavan modeli RPS − iki KM; `ceiling_path_v0` D5 − medyan; v1 ve (C) kasa birincili). Birincil tanım sonradan değişmemiş.

| Aile / model | Yeniden üretim | Sonuç |
|---|---|---|
| `v1_5_h99` (öne çıkan D5 getirisi) | 99 arz; f1 ln, f3 winsor + medyan imputasyon (3.24), f5; Ridge kapalı biçim (α = 100/10/10/0.1), lojistik Newton (λ = 1/C, C = 0.1/1/1/1) | ön işleme Δ = 0; Ridge Δ ≤ 5.5e-17 (4 ufuk); lojistik Δ ≤ 4.4e-8; NETGL D5: 0.255152 / p_up 0.797011 (kayıt 0.25515244 / 0.79701082) |
| `v1_6_h99` | D10 Ridge α = 0.001 | Δ = 1.1e-16; seçim dağılımı ledger'dan: D1 α = 100 73/89, {1000, 10000, INF} 11/89 = %12; D10 α = 0.001 57/87 |
| `v1_5_market20_v0` | 8 hücre (Adım 4); NETGL f6 = −0.09243 (S0 2026-09-16 13122.58, S20 2026-08-19 14458.98) kayıttan; Ridge f6 katsayıları +0.0033/+0.0035/+0.0259/+0.0630 (JSON) | tutuyor; f6'nın yeniden üretimi Denetim 1'in işi |
| `pb_v0` | pb1 = ln(fiyat × baz pay) 60 hane, pb2/pb3 kesin rasyonel; ID-A/B/C 99/99; z; Ridge (α 10/1/0.001/0.001) + lojistik (C 0.1) | ön işleme Δ = 0; Ridge Δ ≤ 1.1e-16; lojistik Δ ≤ 2.6e-8 |
| `pb_ceiling_v0`, `@INF` (öne çıkan: f3 yokken) | 99 arz, 508 satır, 85 olay, pb1/pb2, λ = 10 | γ Δ = 0, β Δ = 5.6e-17; @INF γ Δ = 0; NETGL z (0.4910, 0.5847), β·z 0.1328, S [0.8079 … 0.0793] — kılavuzla aynı |
| `ceiling_hazard_v1_clip` | 97 arz, f1/f2/f3 ham kırpma, λ = 10 | ön işleme (kırpma sınırları dahil) Δ = 0; γ Δ 2.2e-16, β Δ 1.1e-16 |
| `ceiling_hazard_v1_real` | f1r = büyüklük / (TÜFE[T − 2 ay]/100), 60 hane | Δ = 0 / 4.4e-16 / 5.6e-17; NETGL f1r = 1 687 703 121 (2026-07 endeksi 132.31, yayım 2026-08-03) |
| `ceiling_hazard_v1_pooled`, `@INF` | v2 tablosu, 165 arz (97 + 68), 880 satır, 142 olay, r = 1 olan 53 arz, cezasız δ | γ Δ = 0, β Δ 1.7e-16, δ 0.9111035924105237 (JSON …239); @INF γ Δ 4.4e-16, δ 0.227664 |
| `fall_d10_v0_h99` / `pooled` / `addsale` / `@ZERO` | 94 / 161 / 165 arz; f1r ve f3 kırpma + ln, add_sale bayrağı; C = 1 → λ = 1; @ZERO = eğitim oranı | ön işleme Δ = 0; katsayı Δ 5e-10 … 2.2e-9 (lbfgs tol 1e-10); @ZERO 0.7578 / 0.8199 birebir; NETGL P(D10 ≤ arz) 0.163 / 0.171 / 0.193 / 0.242 (kılavuz §4.8.3 aynı) |
| Tavan yolu (`ceiling_path_v0`, `@INF`, `pb_ceiling_path_v0`) | limit yolu bağımsız (adım tablosu, HALF_UP snap, aşağı adım): C_h = kapanış 423/423, THM üst limiti = U(önceki kapanış) 990/990, snap ≠ P 4 arz (BORLS, AVPGY, ARTMS, LILAK); NETGL C = 28.06, 30.86, 33.94, 37.32, 41.04; hücreler JSON'dan: 567 gözlem, Z 18 × 10, B 67/64/60/54/48/40/28/15/11, medyanlar ve Z m = 1'de 8/18 kılavuzla aynı; gömülü seri modeli sha `caa4dc86…` = `ceiling_hazard_v0.json` | tutuyor; P1 (424 → 423). Karışım/kuantil mekaniği Faz 4 denetiminde bit-eşit üretilmişti (iddia olarak alındı) |

Şartname-kod-JSON üçlüsünde çelişki: yalnız P2 (f1 tanım satırı). Diğer sapmalar SPEC_DEVIATIONS A–K'da belgeli ve değer değiştirmiyor.

### Adım 6 — Model düzeyinde sızıntı [ÖLÇTÜM `ekler/2/s6_mutation.py`, klon `/tmp/borsai_kitap_audit_2/clone`, `.venv` bağı `.git/info/exclude`'da; çıktı `s6_compare.txt`, `s6_*.json`]

Sekiz ailede ikişer fold (ilk skorlanabilir fold + son arz QUICK): `ceiling_hazard_v0` (EKOS, QUICK), `pb_ceiling_v0` (SKYMD, QUICK), `v1_5_h99` D5 (SKYMD, QUICK), `pb_v0` D5 (SKYMD, QUICK), `ceiling_hazard_v1_clip` (EKOS, QUICK), `ceiling_hazard_v1_pooled` (HATSN, QUICK), `fall_d10_v0_h99` D10 (SKYMD, QUICK), `fall_d10_v0_pooled` D10 (HATSN, QUICK). Her fold için:
- test arzı eğitim kümesinde yok (16/16); planın `training_tickers_sha256`'sı altın ledger'daki ile aynı (16/16);
- eğitim satırlarının kullandığı etiketin son seansı < kesim (T, PB'de B(k)) (16/16);
- temiz klonda proje koduyla koşulan fold altın ledger'la aynı (16/16);
- **mutasyon:** test arzının etiketleri (L, tavan bayrakları, R_D5/R_D10, Y_D5/Y_D10; tablo, v2 tablosu, TARGETS ve iki veri sürümü dosyasının sha'ları) tek tek değiştirildi (QUICK; EKOS; SKYMD; HATSN ayrı turlar). Kendi etiketi değişen arzın fold'u **16/16 bit-eşit** kaldı; değişen arzın eğitimine girdiği sonraki fold'lar her turda değişti (mutasyonun etkili olduğunun kanıtı, örneğin QUICK'in v0 fold'unda S_5 0.0362 → 0.0255).
- Yan bulgu: (C) ailesinin eğitim-kümesi bekçisi (`backtest.fall_training_rows(check=True)`, şartnamede pinli n / olay sayısı / veri sürümü sha'sı) mutasyonlu tabloyu durdurdu (`BacktestStop … eğitim kümesi şartnameyle tutmuyor`); test için kapatıldı.
- Tavan yolu modelleri için mutasyon yapılmadı; üç ledger'da `cells_max_session_date` < kesim 87/87 (Faz 4 denetimi iddiası; bu oturumda ledger sütunundan doğrulandı).

### Adım 7 — Tahmin kodunun bağımsızlığı [ÖLÇTÜM `ekler/2/s7_imports.py` → `s7_imports_out.txt`, AST kapanışı]

`predict.py`, `predict_hazard.py`, `predict_path.py`, `predict_pb.py`, `predict_market20.py`, `predict_fall.py`, `predict_post_d1.py`, `predict_break.py` ve ulaştıkları `features.py`, `horizons.py`, `survival.py`: stdlib dışı import **yok**; kullanılan modüller yalnız `math`, `decimal`, `dataclasses`, `typing` (+ `__future__`). Eğitim tarafı: `fit.py` numpy + scikit-learn, `hazard.py` yalnız numpy, `ceiling_path.py`/`backtest.py`/`freeze.py` stdlib. Kılavuz §4.3.5 ("yalnız stdlib"), §4.4.5 ("numpy ile yazılmış Newton") ve "eğitim kodu numpy ve scikit-learn kullanıyor" anlatımı doğru; ince ayrım: tavan ailesinin eğitimi scikit-learn kullanmaz (kılavuz bunu §4.4.5'te doğru söylüyor).

### Adım 8 — §4.11 sınırlar ve dürüstlük notları [ÖLÇTÜM]

- Varyant sayaçları: `scores.json` `card.n_variants_same_data` 23 (ilk veri sürümü modelleri) ve 2 059 (v2 modelleri); `experiments/log.jsonl` 2 146 satır, 2 054'ü `kind: exploration` ✓.
- Ay blokları 22–24 ✓ (Adım 4 n_blocks); D1 azınlık 10 ✓ (`base_rate` D1 0.899 → 10/99).
- "Beklentiden çok iyi" kuralı SPEC_CEILING_PATH_V0 §6 (fark < −0.120 ya da üst uç < −0.060) ✓; MODELS.md "Dondurma" ve `docs/fable_faz4_audit/AUDIT.md` FREEZE_OK ✓; L = 10 yoğunlaşması Faz 4 denetimi §… ("dört L = 10 arz toplamın %33'ü") ✓.
- Bilinen zayıflıklar belgede: β_f2 işareti (MODELS.md beklenti tablosu), kalibrasyon S_5 0.4342 / 0.3793 (MODELS.md, bu rapor Adım 4), nominal f1 (SPEC_CEILING_V0 §4) ✓.
- Maruziyet beyanları: SPEC_CEILING_V0 §3/§11, SPEC_CEILING_PATH_V0 §10, SPEC_HAZARD_V1 §10, SPEC_C_V0 §10 var ✓.
- Kılavuzun kaynak yolları: 4. bölümde geçen 63 repo yolundan yalnız `GITLOG.txt` yok (K1).

## 5. Bağımsız yeniden hesaplananlar (betik → sonuç ↔ repo)

| Betik | Ne | Benim | Repo |
|---|---|---|---|
| `s1_hashes.py` | 27 model: dosya sha / spec sha / belge sha | 27/27, 27/27, 20/20 | INDEX.json |
| `s3_hazard_scratch.py` | v0 γ, β; λ tablosu; KM; NETGL S; E[L]; koşullular | Δ 5.6e-17; 1.1e-16; 0; 5.6e-16; 3.2811; 0.6676 / 1.890 / 0.4458 / 0.0591 | JSON, kayıt, kılavuz |
| `s4_bootstrap.py` + `s4_fix_inf.py` | 63 hüküm hücresi | 63/63 4 ondalıkta aynı | kılavuz §4.3–§4.9, `scores.json`, MODELS.md |
| `s5_refits.py` | 8 ailenin nihai fit'i | Δ 0 … 2.2e-9 | 20 model JSON'u |
| `s6_mutation.py` | 16 fold: kimlik, kesim, altın eşitlik, mutasyon | 16/16, 16/16, 16/16, 16/16 | altın ledger'lar |
| `s7_imports.py` | predict import kapanışı | stdlib dışı 0 | — |
| `s8_limit_path.py` | C_h eşitliği, üst limit, NETGL C_h | 423/423, 990/990, 28.06… | SPEC_CEILING_PATH_V0 §2 (424 → P1) |

## 6. Bakılmayanlar

- §4.9 kasa sütunu ve §4.7.5/§4.8.4 kasa hücreleri (zaman-dışı terazi; Denetim 3).
- V1.5 legacy port kabulü (351 fold eşitliği) yeniden koşulmadı; market20 f6'nın XU100/takvimden üretimi (Denetim 1).
- Koşullu keşif hücreleri (j = 1..9), P_close ikincil hücreleri, v1 ailesinin Brier k = 10 hücreleri (keşif; bootstrap'ımla üretilmedi).
- Tavan yolu karışım/kuantil mekaniğinin (medyan, p_up, q10/q90) fold düzeyinde yeniden üretimi (Faz 4 Fable denetimi bit-eşit üretmişti; iddia olarak alındı); tavan yolu için mutasyon testi.
- Uygulamanın (Rust/UI) bu sayıları nasıl gösterdiği (Denetim 4).

## 7. Proje sahibine açık sorular

1. SPEC_CEILING_V0 §4 tablosundaki f1 satırı (fiyat × pay) kodla (kaynak bildirimli büyüklük) hizalansın mı? Değer değişmez; yalnız belge düzeltmesi önerilir (P2).
2. (C) adaylarının yakın dönem `base_rate` karşılaştırıcısı V1.5 planının 99 arzlık kümesinden geliyor; §5.1'e bir cümle eklenmesi istenir mi? Hükümler 94 arzlık taban oranıyla da aynı (K4).
3. j ≥ 3'teki sabit "yarın da tavan" verinin desteklediği bir tasarım seçimi (χ² = 0.46). FAZ10'da gün başına sabitler ya da düzgün bir zaman eğrisi düşünülürse, bu, olay bütçesini (gün başına 3–13 olay) aşan yeni bir model_id olur; mevcut v0 değişmemeli.

## 8. Koruma ve hijyen sayımları

- Koruma: `ekler/2/koruma_once.txt` ve `koruma_sonra.txt` — dokuz ağaç sha'sı iki ölçümde aynı (`diff` boş); korunan yollarda `git status` çıktısı iki ölçümde de boş.
- Klon mutasyonları yalnız `/tmp/borsai_kitap_audit_2/clone` altında yapıldı ve `git checkout -- data` ile geri alındı; asıl repoda `borsai/`, `data/`, `models/`, `registry/`, `scores/`, `tests/` dokunulmadı.
- Hijyen: rapor ve `ekler/2/` içinde `thb`/`thm` + 8 haneli tarih kalıbı: **0**; SEALED kodu: **0** (kasa dosyaları hiç okunmadı; v2 tablosunun açık küme ticker'ları hiçbir eke yazılmadı, yalnız sayılar).
- Ek boyutu: ≈ 0.27 MB (< 3 MB).

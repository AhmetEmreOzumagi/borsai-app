**REPRO_OK**

# BORSAI_FAZ8_FABLE_REPRO_AUDIT_20261002 — `break_floor_v0` backtest'inin bağımsız yeniden üretimi, N20 sağlamlığı, sızıntı/sıra denetimi ve mutasyonlar

Görev: `docs/prompts/FAZ8_FABLE_REPRO_AUDIT.md`. Yazım: 2026-10-02, Fable. Denetlenen: `7d78d43` (şartname), `5d84e88` (K), `fa623df` (A), `df338c2` (B), `c84ba64` (R; HEAD). Şartname `docs/specs_faz8/SPEC_BREAK_V0.md` (sha256 `da98351c2b1b…`, 7d78d43'ten beri değişmedi) ve `KARARLAR.md` (sha256 `8d8bbc971b01…`; §C yalnız K'de). Ağ yok; yalnız okuma git komutları; `registry/`, `data/`, `scores/`, `models/`, `app/` dokunulmadı (`ekler/koruma_once.txt` / `koruma_sonra.txt`). Yeniden üretim betiği `ekler/repro_break.py` `borsai` paketini import etmez (dosyada import satırı yok; `-v` import izinde `borsai` 0 satır; betiğin sonundaki `sys.modules` denetimi boş; `ekler/repro_run.txt`). Çözücü olarak şartnamenin tanımladığı scikit-learn `LogisticRegression` (L2, lbfgs, `tol=1e-10`, `max_iter=10000`, `l1_ratio=0`, sabit cezasız) doğrudan çağrıldı; optimumun çözücüden bağımsızlığı kendi Newton çözümümle gösterildi. Ürün karşılaştırıcısı (`PRODUCT_BREAK_FLOOR`) SPEC_CEILING_PATH_V0 §2–§4, §7'den kendi hücre/merdiven/atom kodumla (Faz 4 denetim betiğimin kalıbı) kuruldu.

İşaretler: **[ÖLÇTÜM]** = bu oturumda betik/komut çıktısı; **[ÇIKARIM]** = yorum. Sayılar backtest terazisindedir (H99 walk-forward, tasarıma maruz); canlı terazi (`live_break`) bu belgede yoktur. Fark = model − karşılaştırılan (Brier, kırpmasız); negatif = model iyi.

## 0. Hüküm

1. **REPRO_OK.** Resmi ledger (`docs/faz8/backtest/break_floor_v0_fold_ledger.csv`, sha `730a4e3cc75d…`), üç duyarlılık ledger'ı ve iki nihai fit önizlemesi sıfırdan yeniden üretimle **bit-eşit**: 29 sayısal sütun ve iki iç tablonun (skorlar, ön işleme, katsayılar, sabitler) hepsinde maks |Δ| = 0.000e+00 (eşik 1e-9); durum, seçilen C, sınıf sayıları, `training_*` ve kimlik sha'ları birebir; `zero_F1/F2` ve `by_type_F1` Fraction'la bit-eşit; `product_F1/F2` bit-eşit; Faz 4 ledger'ıyla hücre paritesi 87/87 (K1).
2. **Hücreler ve §6:** birincil F1 − `PRODUCT_BREAK_FLOOR` = **−0.1904 [−0.2520, −0.1247]**, n = 69 (21 ay); F1 − `@ZERO` = **−0.0281 [−0.0453, −0.0074]**; bütün ikincil, bilgi ve keşif hücreleri ile kalibrasyon satırları günlük satırıyla tam hassasiyette (maks |Δ| 0) ve MODELS.md'nin basılı sayılarıyla eşit. §6'nın 13 satırının hükmü (9 tuttu / 4 tutmadı) MODELS.md ile aynı; "çok iyi" iki ayakla tetiklenir (birincil fark < −0.160; üst uç < −0.080); k1 sağlanır.
3. **N20 sağlamlık (K2):** kod §5.1 eşiğini aynen uyguluyor (bağımsız kodum aynı değerleri verir). Eşik bir fiyat adımı toleranslı olunca ürün Brier'i 0.3781 → **0.3489**, fark **−0.1611 [−0.2193, −0.1013]**; yarım adım 0.3576 / −0.1698; %1 göreli tolerans 0.3426 / −0.1549 [−0.2284, −0.0810]; yuvarlamasız nominal 0.9 eşiği 0.3930 / −0.2052. Orkestratörün kaba tahmini (≈ 0.335, ≈ −0.15) yakın ama biraz iyimser. **Birincil "aralık 0'ın altında" hükmü bütün tanımlarda sağlam**; "çok iyi" tetiği de her tanımda üst uç ayağıyla kalır (−0.1013, −0.1086, −0.0810 < −0.080). Farkın ≈ 0.03–0.04'ü eşik yuvarlamasındandır; asıl büyüklük ürünün taban üstü kırılmalara ≈ 0.57 vermesinden gelir (gözlenen 0.122) ve bu tanımdan bağımsızdır.
4. **Sızıntı, sıra, uygunluk (K3):** test arzının alanları hiçbir fold'da ön işlemeye ya da eğitime girmiyor (Opus'un koduyla 3 fold'da override: fit bit-eşit; kendi kodumda da); 6 243 eğitim satırının hepsinde etiket seansı < T, 82 fold'da hücre max tarihi < D_1(k); D_b sonrası satırlarda okunan anahtarlar tam olarak {ticker, session_number, target_session_date, thb_raw_close, thm_raw_lower_limit}; koşu boyunca `data/outcomes/`, `data/outcomes_oot/`, `scores/`, `registry/` dosyası açılmadı (§3-iii). Atalık zinciri ve "A'da sonuç yok" komutla; şartname 7d78d43'ten beri bayt-eşit; KARARLAR yalnız K'de ve yalnız §C; §6 kuralları A'da sabit (specs.py blob'u A/B/R'de aynı); `git diff fa623df df338c2 -- borsai` boş; CLAUDE.md cümlesi §9.4 ile birebir (662 karakter).
5. **Mutasyonlar:** 13 mutasyonun (a)–(m) hepsi kırmızı (§6). **Testler:** tam `pytest` ve `bash app/scripts/test.sh` yeşil (§5). **Koruma:** ağaç sha'ları ve `git status` koşu öncesi/sonrası eşit (§7).
6. **Dondurma önerisi (§8):** `break_floor_v0` ve `break_floor_v0@ZERO` bu şartnameyle dondurulabilir. Kartta öne çıkan durum şartname §8 aşama 1 (k1 sağlandı; etiket "ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = 0") — ancak §8'de sıralanan uyarılarla.

## 1. Sıfırdan yeniden üretim [ÖLÇTÜM] — `ekler/repro_break.py`, çıktı `ekler/repro_stdout.txt`, `ekler/repro_output.json`, `ekler/repro_ledgers/`

Betik yalnız şartnameden kodlandı: SPEC_BREAK_V0 §1.2, §2, §3, §4, §5.1, §5.2, §6, §7, §13 (sözde kod); KARARLAR §A–§C; SPEC_V1_6 §3, §4, §9; SPEC_CEILING_PATH_V0 §2, §3, §4, §7; SPEC_SCORING §2, §3, §8; SPEC_DEVIATIONS C7, H11, N2, N3, N5, N6, N7. Opus'un kodu yeniden üretimde kullanılmadı (okunması yalnız §3–§6 denetimi içindir; betik ondan önce yazıldı ve kilitlendi — betiğin ilk koşusundaki sha `b6b825bf7662…`, son sürüm `69fa70e8057c…`; aradaki üç düzeltme yalnız karşılaştırıcı tarafındadır, aşağıda). Girdiler: `data/training_table.csv` (P, `shares_offered`, ilk işlem günü, `ceiling_streak_L` yalnız çapraz denetim), SESSIONS CSV (ham `thb_raw_*` / `thm_raw_*`). Süre 27 sn (6 işçi). Ortam: Python 3.12.14, scikit-learn 1.9.0, numpy 2.5.2, scipy 1.18.0 (Opus'un koşusuyla aynı).

### 1a. Kırılma tablosu (§13-1) ve özellikler (§13-2)

| Sayı | Şartname / profil | Yeniden üretim |
|---|---|---|
| Kırılma akşamı (b ≤ 9) | 82 | 82 |
| b dağılımı 1…9 | 18/11/4/13/12/8/6/6/4 | 18/11/4/13/12/8/6/6/4 |
| L = 10 / b = 10 | 14 / 3 | 14 / 3 |
| `b_floor` = 1 (2 ≤ b ≤ 9; b = 1) | 35 (31; 4) | 35 (31; 4) |
| Yarım gün / durdurma (D_b) | 1 / 0 | 1 / 0 |
| referans_b == kapanış_{b−1}; Lo(referans_b) == alt limit_b | 67/67; 85/85 | 67/67; 85/85 |
| Gün boyu taban kilidi; bant uyuşmazlığı | 8; 0 | 8; 0 |
| Yapısal sıfır (b = 7/8/9); yaklaşık kuralla aynı | 16 (6/6/4); 82/82 | 16 (6/6/4); 82/82 |
| Yakın dönem / 2023; F2 birimi; olay F1 / F2 | 69 / 13; 78; — | 69 / 13; 78; 25 / 11 |
| Son etiket seansı F1 / F2 (≤ 2026-08-19) | — | 2026-08-07 / 2026-08-10 |
| El değiştirme kantilleri (2 ≤ b ≤ 9, Type-7, `{:.4g}`) | 0.06236 / 0.1134 / 0.8542 / 1.632 / 2.228 / 2.897 / 3.219 | aynı |
| `b_turnover` aralığı (`feature_ranges`) | [−2.774809265822848, 1.1691103406911647] | aynı |

Etiket `Decimal(kapanış) == Decimal(alt limit)` ham metinle; ham `thb_raw_close`/`thm_raw_lower_limit` düzeltilmiş `close`/`lower_limit` sütunlarıyla 990/990 Decimal-eşit (N7 denetimi). `b_turnover` = 60 haneli Decimal `ln(hacim_b / shares_offered)` → bir kez binary64; kırpma ln ölçeğinde Type-7 kesin Fraction; z = (x − μ)/σ (σ popülasyon, 60 haneli Decimal) → float (H11 kalıbı).

### 1b–1c. Fold planı (§7.2; N2 formül aynen)

T = D_b tarihi; F1 eğitim satırı j ancak `date(D_{b_j+1}) < T`, F2 `date(D_{b_j+2}) < T`; ≥ 10 satır, ≥ 5 olay, ≥ 5 olay-dışı; b = 9'da F2 başlığı `TARGET_UNDEFINED_F2`. Sonuç: 82 fold; F1 FIT_OK 69 (hepsi yakın dönem; INSUFFICIENT 13 = 2023 fold'larının hepsi); F2 FIT_OK 52, INSUFFICIENT 26, UNDEFINED 4; seçilen C F1 {0.01: 7, 0.1: 32, 1.0: 27, ZERO: 3}, F2 {0.1: 43, 1.0: 9}; ürün `POST_BREAK_INSUFFICIENT` 5 (hepsi 2023). Opus'un sayılarıyla birebir.

**N2 ("aynı gün") etkisi [ÖLÇTÜM]:** H99'da aynı gün listelenip etiketi T'den önce olan tek çift KBORU (D_1 2023-12-14, b = 5, T = 2023-12-20) ← SURGY (aynı D_1, b = 2; F1 etiketi 2023-12-18, F2 2023-12-19). KBORU fold'u zaten `INSUFFICIENT_TRAINING_HISTORY` (2023); hiçbir hücreye girmez. Aynı gün kırılan 12 çift formülle dışarıda kalır. Yani N2 kararının skorlara etkisi sıfırdır.

### 1d. Ledger karşılaştırması (`docs/faz8/backtest/break_floor_v0_fold_ledger.csv`, 82 satır × 47 sütun)

Birebir karşılaştırılan sütunlar (82/82 eşit): `fold_id, ticker, first_trading_date, b, break_date, training_n, training_events, training_nonevents, training_max_label_date, training_tickers_sha256, selected_C_F1, selected_C_F2, columns, dropped, test_b_floor, test_b_turnover_clipped, test_floor_lock_allday, test_half_day, product_status, cells_max_session_date, structural_zero_D10, realized_F1, realized_F2, status`; `zero_F1`, `zero_F2`, `by_type_F1` Fraction'dan float olarak bit-eşit; iç tablolarda (`inner_table_F1/F2`) `status`, `n`, `events`, `score_status`, `final_attempts`, `inner_fold_n` birebir. Kimlik sha'sı `training_tickers_sha256` = sha256("\n".join(plan sırasındaki eğitim arzları) + "\n") — 82/82 plan sırasıyla eşleşti (sıralı kipi hiç gerekmedi).

Sayısal sütunlar (eşik 1e-9), maks |Δ| [ÖLÇTÜM]:

| Sütun | maks \|Δ\| | Sütun | maks \|Δ\| |
|---|---|---|---|
| `p_F1` | 0.000e+00 | `p_F2` | 0.000e+00 |
| `product_F1` | 0.000e+00 | `product_F2` | 0.000e+00 |
| `coef_floor_F1`, `coef_turn_F1`, `intercept_F1` | 0.000e+00 | `coef_floor_F2`, `coef_turn_F2`, `intercept_F2` | 0.000e+00 |
| `clip_p05`, `clip_p95` | 0.000e+00 | `mean_floor`, `std_floor`, `mean_turn`, `std_turn` | 0.000e+00 |
| `test_b_turnover_ratio` (Decimal) | 0.000e+00 | `inner_F1.scores` (8 C × 69 fold) | 0.000e+00 |
| `inner_F2.scores` (8 C × 52 fold) | 0.000e+00 | `inner_F1/F2.prep.{winsor, mean, std}` | 0.000e+00 |
| `inner_F1/F2.coef`, `inner_F1/F2.intercept` | 0.000e+00 | | |

Bit-eşitliğin nedeni [ÇIKARIM]: aynı sklearn 1.9.0 / numpy 2.5.2 ortamı, aynı eğitim satır sırası (tablo sırası `(first_trading_date, ticker)`), aynı kesin Fraction/Decimal ön işleme ve aynı `1/n` ağırlıklı atom toplamı. Bağımsız bir çözücüyle (Newton, aşağıda) fark 1e-8 düzeyindedir; |Δ| = 0 ortak çözücünün sonucudur, "kopya"nın değil (betik §1 başında kilitlendi; Opus'un kodu sonra okundu).

**İlk koşuda çıkan dört "uyuşmazlık" ve kök nedenleri [ÖLÇTÜM]** (hepsi benim karşılaştırıcı tarafımda; Opus'un kodunda ve şartnamede hata yok):
1. `training_max_label_date` (61 satır): ledger iki başlığın etiket tarihlerinin maksimumunu yazıyor (F2'nin D_{b+2} tarihi F1'inkinden geç olabilir); ben yalnız F1'i almıştım. Şartname sütunu tek ve tanımı yazmıyor; iki okuma da "< T" koşulunu sağlar (82/82). Betik Opus'un okumasına göre düzeltildi; F1'inki ayrıca saklanıyor.
2. `zero_F2` ve `inner_table_F2.{n, events}` (b = 9 olan 3 fold): b = 9'da F2 tanımsız olduğundan Opus F2 eğitim kümesini kurmuyor (n = 0, `zero_F2` boş); ben kuruyordum. Şartname bu sütun için b = 9'da bir şey demiyor; hiçbir hücre etkilenmez (F2 hücreleri b ≤ 8'dir). Betik düzeltildi.
3. `inner_table_F1.scores` '10.0' (3 fold: METEN, ALBTN, MASFN): her iki tarafta da C = 10 adayı bir iç bölmede yakınsamadı (`CANDIDATE_NOT_CONVERGED`; ledger'da skor `null`); karşılaştırıcım `null`'u "eksik" saymıştı. Durum sütunları zaten eşitti. Karşılaştırıcı düzeltildi; sonuç: davranış aynı (adaylar aynı yerde düşüyor, seçilen C = 1.0 aynı).
4. Günlük satırı süzgecim JSON biçimini (`"kind":"backtest"`, boşluksuz) yanlış varsaymıştı (çökme); düzeltildi.

### 1e. Ürün karşılaştırıcısı (`PRODUCT_BREAK_FLOOR`), bağımsız

Hücreler SPEC_CEILING_PATH_V0 §3'ten: kesim D_1(k), seans tarihi < kesim; baz = P (L = 0) ya da kapanış(D_L); havuzlama merdiveni (kendi, diğer grup aynı m, sonra m∓1, m∓2, …; N_MIN = 10; havuzlanınca fiziksel sınırlara kırpma). Durum-2 atomları (§7): h = b + 1 için (kapanış(D_L)/P)·(1 + v) − 1, v ∈ hücre(g(L), 2), ağırlık 1/n (L = 0'da ölçek 1). Eşik §5.1 aynen: Lo(kapanış_b)/P − 1 (F1), Lo(Lo(kapanış_b))/P − 1 (F2), tolerans 1e-12; Lo = alt limit işlevi (adım yuvarlanacak değerin kendi seviyesinden, yukarı). Sonuç: `product_F1/F2` 82/82 bit-eşit, `product_status` ve `cells_max_session_date` birebir; `cells_max_session_date < D_1(k)` 82/82; Faz 4 `ceiling_path_v0` altın ledger'ının (sha `1f45365ee2d8…`) 87 OK fold'unda `cells_n_Z_1..10`, `cells_n_B_1..9` ve `cells_max_session_date` birebir (87/87).

### 1f. Hücreler (§5.2; C7: ay blokları, 4000, `random.Random(20260921)`, indeks 100/3899)

Yakın dönem (ilk işlem ≥ 2024-01-01) [ÖLÇTÜM; günlük satırı `near_era` ile tam hassasiyette maks |Δ| 0]:

| Hücre | n (ay) | model | karş. | fark | %95 aralık | iyi / kötü / eşit (≤ 1e-12) |
|---|---|---|---|---|---|---|
| **F1 − `PRODUCT_BREAK_FLOOR` (birincil)** | 69 (21) | 0.1878 | 0.3781 | **−0.1904** | **[−0.2520, −0.1247]** | 48 / 21 / 0 (0) |
| F1 − `@ZERO` | 69 (21) | 0.1878 | 0.2158 | −0.0281 | [−0.0453, −0.0074] | 49 / 17 / 3 (3) |
| F1 − `base_floor_by_type` | 69 (21) | 0.1878 | 0.1771 | +0.0106 | [−0.0047, +0.0282] | 17 / 52 / 0 (0) |
| F2 − `PRODUCT_BREAK_FLOOR` | 52 (16) | 0.0955 | 0.1527 | −0.0572 | [−0.0847, −0.0239] | 32 / 20 / 0 (0) |
| F2 − `@ZERO` | 52 (16) | 0.0955 | 0.0956 | −0.0001 | [−0.0131, +0.0179] | 38 / 14 / 0 (0) |
| bilgi: `PRODUCT − @ZERO` (F1) | 69 (21) | 0.3781 | 0.2158 | +0.1623 | [+0.1087, +0.2139] | 22 / 47 / 0 (0) |

Keşif: 2023 fold'ları n = 0 (hepsi yetersiz eğitimli); "bütün fold'lar" yakın dönemle aynı; b = 1: F1 − ürün −0.1288 [−0.3000, +0.0393] (n 17, 8 ay), F1 − `@ZERO` −0.0122 [−0.0457, +0.0117]; 2 ≤ b ≤ 9: −0.2105 [−0.2826, −0.1311] (n 52, 19 ay), −0.0333 [−0.0609, −0.0044]. Kalibrasyon: yakın dönem +0.0417 (0.3315 − 0.2899, n 69); b_floor = 1: −0.0858 (n 28); b_floor = 0: +0.1287 (n 41); 2024 −0.0151 (27), 2025 +0.2037 (16), 2026 +0.0009 (26). MODELS.md'nin basılı satırlarıyla (4 ondalık) hepsi eşit.

**§6 satır satır** (kurallar MODELS.md'deki `OPERATIONAL_RULES_FAZ8` metninden kendi kodumla uygulandı): birincil altında — beklentiden çok iyi → **tutmadı (daha iyi)**; `@ZERO` aralık içinde → tuttu; `by_type` tuttu; F2 − ürün tuttu; F2 − `@ZERO` tuttu; bilgi satırı üstünde → tutmadı (daha kötü); kalibrasyon +0.0417 tuttu; β_floor nihai +0.9867, fold'larda 66/66 → tuttu; β_turn nihai +0.0629 → tutmadı (> 0); C nihai 1.0 tuttu; ZERO payı %4 tuttu; n F1 69 tuttu; n F2 52 → tutmadı (az). Dizi MODELS.md ile aynı (9 / 4). Tetikler: birincil fark < −0.160 **evet**, üst uç < −0.080 **evet**, `@ZERO` farkı < −0.090 hayır. Başarısızlık (a)–(d) hayır; k1 sağlandı.

### 1g. Nihai fit önizlemeleri (§4.4)

F1 82 arz / 25 olay, F2 78 / 11 (b ≤ 8), eğitim satırlarının etiketleri ≤ 2026-08-10 (`cutoff_date` 2026-08-10 = F2'nin son etiketi; F1'inki 2026-08-07; ikisi de ≤ 2026-08-19). Karşılaştırma `docs/faz8/backtest/break_floor_v0_final_fit_preview.json` ve `@ZERO` önizlemesiyle [ÖLÇTÜM]:

| Başlık | C (benim / önizleme) | sabit | b_floor | b_turnover | kırpma [p05, p95] | iç LOOCV Brier (8 C) | maks \|Δ\| |
|---|---|---|---|---|---|---|---|
| F1 | 1.0 / 1.0 | −1.0006869 | +0.9866556 | +0.0628689 | [−2.178886, 1.057949] | ZERO 0.21719 … 1.0 0.18407 (en iyi) … 100 0.18443 | 0.000e+00 (katsayı, sabit, μ, σ, kırpma, iç Brier) |
| F2 | 0.1 / 0.1 | −1.8948516 | +0.2872180 | −0.3079898 | [−2.183673, 1.061365] | 0.1 0.11863 (en iyi) | 0.000e+00 |

`@ZERO`: F1 25/82 = 0.3048780487804878, F2 11/78 = 0.14102564102564102 (bit-eşit, Fraction); `by_type_F1`: sınıf 1 19/35 = 0.5428…, sınıf 0 6/47 = 0.1276… birebir; `tickers_sha256` (F1 ve F2) eşit; `break_fields_sha256` biçimi şartnamede yazılı değil — `ticker|b|kapanış_b|alt limit_b|hacim_b` ham metin satırlarının `\n` birleşimi önizlemedeki değeri (`e0cbf778f2c6…`) verir; `feature_ranges` eşit.

### 1h. Duyarlılıklar (`__sens_floor_only`, `__sens_turnover_only`, `__sens_with_group_Z`)

Üç ledger de aynı kurallarla yeniden üretildi; her birinde bütün sayısal sütunlar ve iç tablolar maks |Δ| 0, durum/C/kimlik sütunları birebir (`group_Z` katsayısı iç tablonun `coef` sözlüğünden karşılaştırıldı). Yakın dönem hücreleri (IMPL_RAPOR §9 ile aynı): yalnız b_floor F1 − ürün −0.1968 [−0.2648, −0.1255], F1 − `@ZERO` −0.0345 [−0.0545, −0.0106]; yalnız b_turnover −0.1567 [−0.2058, −0.1053], +0.0056 [−0.0094, +0.0296]; + Z/B grubu −0.1801 [−0.2389, −0.1175], −0.0178 [−0.0314, −0.0000]. Okuma [ÇIKARIM]: bilgi `b_floor`'dadır; el değiştirme tek başına `@ZERO`'yu geçmez ve b_floor'a eklenince farkı küçültür (−0.0345 → −0.0281); `by_type` hücresinin (+0.011, 0'ı içerir) söylediğiyle tutarlı.

### 1i. Çözücü bağımsızlığı

Ana modelin C ≠ ZERO olan 66 FIT_OK F1 fold'unda kendi Newton çözümüm (sabit cezasız L2 amacı; adım < 1e-14'e kadar) ile sklearn arasında maks |Δp| = **6.3e-9**, maks |Δβ| = 4.2e-8, maks |Δα| = 2.1e-8 (eşik 1e-6) [ÖLÇTÜM].

## 2. N20 ve birincil hükmün sağlamlığı [ÖLÇTÜM] (bilgi; birincil tanım değişmez)

### 2a. Kod §5.1 eşiğini aynen uyguluyor; yuvarlama atom düzeyinde

`predict_break.product_thresholds`: `lo1 = lower_limit(kapanış_b)`; eşik_F1 = `ratio_minus_one(lo1, P)` (60 hane → binary64), eşik_F2 = `ratio_minus_one(lower_limit(lo1), P)`; `product_from_cells`: `Σ{w : r ≤ eşik + 1e-12}`, atomlar `predict_path.mixture_atoms(None, [(L, 1.0, kapanış(D_L)/P)], hücreler, h)`. Benim şartnameden yazdığım aynı tanım 82/82 bit-eşit değer verdi; yani kod = şartname.

Yakın dönemin 28 taban kırılmasında (F1, model FIT_OK): kesin eşiğin saydığı atom payı ort. **0.1150**; hücrenin "çift tabana yakın" payı (v ≤ −0.185) ort. **0.2728** (Opus: 0.115 / 0.273). Mekanizma: kaynak arzın çift taban getirisi v = Lo(Lo(c))/c − 1 kendi fiyat seviyesinde adıma **yukarı** yuvarlanır ve −0.19'dan seviyeye bağlı bir miktar yüksek kalır; test arzının eşiği de (kendi seviyesinde) −0.19'dan yüksek ama farklı bir miktarla; kaynaktaki yuvarlama payı test arzınınkinden büyükse atom eşiğin **hemen üstünde** kalır ve sayılmaz. Üç örnek (hepsi taban kırılması; atomların kaynak kapanışı kendi seviyesinde tam Lo(Lo(baz))):

| Test arzı | b / L / P | kapanış_L → kapanış_b | Lo(kapanış_b) (adım) | eşik r (kesin) | +1 adım eşiği | atom n | P_ürün kesin → +1 adım | eşik ile +1 adım arasında kalan atomlar (kaynak, v, test seviyesindeki fiyat karşılığı) |
|---|---|---|---|---|---|---|---|---|
| DURKN | 4 / 3 / 17 | 22.60 → 20.34 | 18.31 (0.01) | 0.077059 | 0.077647 | 30 | **0 → 0.20** | KBORU (52.95→42.90; v −0.18980; 18.3105), ONRYT (96.25→78.00; −0.18961; 18.3148), CATES (83.6→67.75; −0.18959; 18.3152), MHRGY (7.6→6.16; −0.18947; 18.3179), OZATD (168.9→136.90; −0.18946; 18.3182), HRKET (102.4→83.00; −0.18945; 18.3184) — altısı da kaynağında **çift taban**, eşiğin 0.0005–0.0084 TL (< 1 adım) üstünde |
| SERNT | 5 / 4 / 12 | 17.56 → 15.81 | 14.23 (0.01) | 0.185833 | 0.186667 | 35 | **0.0571 → 0.2571** | ONRYT, CATES, MHRGY, OZATD, HRKET, ALKLC (30.54→24.76; −0.18926) — 14.2304…14.2366 TL |
| ATATR | 6 / 5 / 11.2 | 18.02 → 16.22 | 14.60 (0.01) | 0.303571 | 0.304464 | 50 | **0.04 → 0.20** | SERNT (17.56→14.23; −0.18964), ONRYT, CATES, VAKFA (18.89→15.31; −0.18952), MHRGY, OZATD — 14.6028…14.6059 TL |

Yani "ürünün yarın taban deme payı" taban kırılmalarında kesin eşikle 0.115, bir adım toleransla 0.199'dur; ikisi de gözlenen 0.536'nın çok altında.

### 2b. Duyarlılık: alternatif eşik tanımlarıyla birincil hücre (yakın dönem F1, n = 69, 21 ay; model Brier sabit 0.1878)

| Ürün tanımı | ürün Brier | fark model − ürün | %95 aralık | ürün ort. p: taban kırılması (n 28) / taban üstü (n 41) | ürün − `@ZERO` |
|---|---|---|---|---|---|
| §5.1 kesin eşik (resmi) | 0.3781 | **−0.1904** | [−0.2520, −0.1247] | 0.115 / 0.568 | +0.1623 [+0.1087, +0.2139] |
| yarım adım tolerans (Lo + adım/2) | 0.3576 | −0.1698 | [−0.2281, −0.1086] | 0.172 / 0.568 | +0.1417 [+0.0923, +0.1906] |
| **bir adım tolerans (Lo + adım)** — görevin tanımı | **0.3489** | **−0.1611** | **[−0.2193, −0.1013]** | 0.199 / 0.569 | +0.1330 [+0.0847, +0.1826] |
| %1 göreli tolerans (Lo × 1.01) | 0.3426 | −0.1549 | [−0.2284, −0.0810] | 0.313 / 0.604 | +0.1268 [+0.0630, +0.1927] |
| yuvarlamasız nominal (kapanış_b × 0.9) | 0.3930 | −0.2052 | [−0.2665, −0.1375] | 0.053 / 0.566 | +0.1771 [+0.1228, +0.2272] |
| F2, kesin / bir adım | 0.1527 / 0.1515 | −0.0572 / −0.0560 | [−0.0847, −0.0239] / [−0.0848, −0.0226] | — | — |

Kazanç/kayıp sayıları beş tanımda da 48 / 21 / 0 (aynı arzlarda model iyi). Orkestratörün kaba tahmini (bir adım toleransla ürün ≈ 0.335, fark ≈ −0.15): ölçülen 0.349 / −0.161 — yön ve büyüklük doğru, tahmin ≈ 0.01 iyimser.

### 2c. Hüküm

- **"Aralık 0'ın altında" sağlam:** beş tanımın beşinde de üst uç < 0 (en zayıfı %1 göreli toleransta −0.0810). Birincil hücrenin işareti tanım artefaktı değildir.
- **"Çok iyi" tetiği tanım artefaktı değil, ama büyüklüğünün bir kısmı öyle:** kesin eşikte iki ayak da tetikler; bir adım toleransta her iki ayak sınırda kalmaya devam eder (fark −0.1611 < −0.160, üst uç −0.1013 < −0.080); %1 toleransta yalnız üst uç ayağı (−0.0810 < −0.080, sınırda). Farkın ≈ 0.03–0.04'ü (−0.190 → −0.155…−0.161) eşik yuvarlamasındandır. Asıl büyüklük tanımdan bağımsızdır: ürün taban üstü kırılmalara her tanımda ≈ 0.57–0.60 verir (gözlenen 0.122) — SPEC_CEILING_PATH_V0 §7 durum-2 karışımı kırılma türünü kullanmaz ve taban üstü kapanışta eşik daha gevşektir (§0.1'de önceden yazılmıştı). 41 taban üstü fold'un ürün Brier'ine katkısı tanımlar arasında değişmez; 28 taban fold'unun katkısı 0.19 → 0.16'lık farkı yapar [ÇIKARIM, tablodan].
- Sonuç: birincil hücre "model çok iyi" değil, "ürünün türetilmiş cevabı bu soruda zayıf" demektir; §5.1'in kendisi bunu öngörmüştü ("ters yönlü"). Model tarafındaki kanıt `@ZERO` ve `by_type` hücreleridir: −0.028 (dışlar) ve +0.011 (içerir): lojistik, iki hücreli taban oranı tablosuna bir şey eklemiyor; kazanç `b_floor` sınıf ayrımındadır.

### 2d. Öneri (kart; şartname değişmez)

- Ürün satırı kartta §5.1 tanımıyla kalır (karşılaştırıcı tanımı değişirse yeni model_id — görev kuralı). Yanına iki kısa not: (i) "ürün türevi kesin eşikle; bir adım toleransla taban kırılmasında ≈ 0.20 (kesin 0.12) — fark aralığı yine 0'ın altında"; (ii) "ürün taban üstü kırılmaya ≈ 0.57 der; gözlenen 0.12" (yapısal). Bu notlar kart metnidir, hücre değildir; MODELS.md'ye girmesi proje sahibinin kararı (açık soru 1).
- **`@ZERO` hücresi k1'in ikinci ayağını tek başına taşır** (üst uç −0.0074 < 0) ve ürün tanımından bağımsızdır; birinci ayak (ürün) her tanımda sağlanır. Yani k1 = "sağlandı" sağlamdır. Ama `@ZERO` farkı küçüktür (−0.028; §6 beklentisi −0.040), F2 − `@ZERO` ≈ 0 ve `by_type` 0'ı içerir: öne çıkarma etiketine "ürüne karşı büyük fark karşılaştırıcının zayıflığından; tek orana karşı küçük" okuması eklenmelidir.

## 3. Sızıntı, sıra ve uygunluk [ÖLÇTÜM] — `ekler/leak_checks.py` (Opus'un koduyla), `ekler/leak_checks_out.txt`, `ekler/sira_kanitlari.sh` → `ekler/sira_kanitlari.txt`

**(i) Test arzı.** Opus'un `backtest_ledger(..., override={ticker: {...}})` yoluyla 3 FIT_OK fold'da (ilk BORSK, orta DSTKF, son QUICK) test arzının `b_turnover` (+3.0) ve `b_floor` (tersine) değerleri değiştirildi (temel koşu, workers = 1, resmi ledger'la bayt-eşit): o fold'un eğitim n/olay, kimlik sha'sı, seçilen C, katsayılar, sabit, kırpma sınırları, μ/σ, iç LOOCV skorları, `@ZERO`, ürün ve durum **bit-eşit** (3/3); yalnız `p_F1` değişti (0.3146 → 0.3855; 0.2944 → 0.4080; 0.1398 → 0.5649); o arzı eğitimde gören sonraki FIT_OK fold'ların katsayıları değişti (BORSK: 65/68 fold; DSTKF: 31/31; QUICK son arz: 0/0) — beklenen. Kendi kodumda da aynı deney (BORSK, OBAMS, MOGAN): fit, ön işleme, iç skorlar, `@ZERO`, ürün bit-eşit; yalnız p (ve `by_type`, sınıf değiştiği için) değişti. **(ii) Kesimler.** Opus'un planından 82 fold'un 6 243 eğitim satırında (F1 + F2) etiket seansı < T: ihlal 0; hücre max tarihi < D_1(k): 82/82; ledger'daki `training_max_label_date` ve `cells_max_session_date` sütunlarıyla tutarlı; bütün etiketler ≤ 2026-08-19. **(iii) Yükleyici beyaz listesi (çalışma zamanı izi).** Erişim sayan `DictReader` ile `load_break_table`: D_b'den sonraki satırlarda okunan anahtarlar tam olarak **{ticker, session_number, target_session_date, thb_raw_close, thm_raw_lower_limit}**; D_{b+3}..D_10 satırlarında yalnız {ticker, session_number, target_session_date}; seri satırlarında kapanış + üst limit; D_b satırında `BREAK_DAY_FIELDS` + iki durum sütunu. Dosya izi (builtins/io/os.open sarmalı, `borsai` import edilmeden önce; backtest + 3 duyarlılık + 2 nihai fit; 355 sn): depo içi 68 açılış; `data/outcomes/` **0**, `data/outcomes_oot/` **0**, `scores/` **0**, `registry/` **0**, `models/` **0**. Açılanlar: `data/training_table.csv`, `data/data_version.json`, SESSIONS, H99'un dört ham kaynak dosyası (`HISTORICAL99_FROZEN_COHORT_V1_*` üçlüsü ve `…_d1_d3_d5_d10_targets.csv` — hepsi `load_dataset`'in veri sürümü sha denetimi ve `IPORow` kurulumu; H99'un ≤ 2026-08-19 verisi, canlı sonuç değil), `tests/reference/macos_golden_faz4/ceiling_path_v0_fold_ledger.csv` (hücre paritesi), `docs/specs_faz8/*` (sha pini), `docs/faz8/backtest/break_floor_v0_fold_ledger.csv` (benim karşılaştırmam), `borsai/*.py` (kaynak hash'i) ve `.venv` paket meta verileri — listesi `ekler/leak_checks_out.txt`.

**(iv) Sıra** (`ekler/sira_kanitlari.txt`): `git merge-base --is-ancestor` 7d78d43 → 5d84e88 → fa623df → df338c2 → c84ba64 dördü de YES, first-parent zinciri aynı; A ağacında `docs/faz8/backtest/` 0 dosya, MODELS.md'de "## Faz 8" 0, log.jsonl 2142 satır ve `break_floor_v0` 0 (B'de 2146 / 4; A → B yalnız ekleme: önek EVET); `git diff 7d78d43 c84ba64 -- docs/specs_faz8/SPEC_BREAK_V0.md` 0 bayt (sha `da98351c…` her iki uçta); KARARLAR yalnız 7d78d43..5d84e88'de (+9 −5), tek hunk (@@ −38,5 +38,9 @@) §C tablosunun C1–C5 karar sütunları ve orkestratör notu, başka commit'te 0; `borsai/specs.py` blob'u A/B/R'de aynı (`97cdc39e…`; `OPERATIONAL_RULES_FAZ8` A'da var), `report_faz8.py` de aynı; `git diff fa623df df338c2 -- borsai` 0 bayt; B yalnız sonuç dosyaları + MODELS.md + SPEC_DEVIATIONS N20 + `test_faz8_golden.py` + log; R yalnız IMPL_RAPOR. **(v) CLAUDE.md:** §9.4 cümlesi 662 karakter, CLAUDE.md'deki satırla birebir, kural 1'in devam satırında (3 boşluk girinti; N14); değişiklik yalnız K'de (+1 −0).

**(vi) N1–N20** — §4. **(vii) Kasa ve hijyen** (`ekler/hijyen.py`; SEALED küme bellekte, 64 kod): `docs/faz8/**`, `docs/specs_faz8/**`, `borsai/{post_break,predict_break,report_faz8}.py`, `tests/test_faz8_*.py`, `tests/faz8_support.py`, iki görev dosyası ve bu denetimin dizini (39 dosya) + MODELS.md Faz 8 bölümü + log.jsonl'ın 4 Faz 8 satırı: SEALED kod **0**, bülten adı kalıbı (`th[bm]YYYYMMDD` ve `thb`/`thm` + 8 hane) **0** → TEMİZ (son tarama bu belge yazıldıktan sonra yinelendi).

## 4. N1–N20 değerlendirmesi [ÖLÇTÜM kod/diff; ÇIKARIM hüküm]

| # | Davranışı değiştiriyor mu? | Lafza aykırı mı? | Kabul |
|---|---|---|---|
| N1 kod yerleşimi (tarif `post_break.py`'de, `specs.py` yalnız ekleme, fit `fit_fall_horizon`) | Hayır (eski tarifler/altınlar bayt-eşit; `test_5c`) | Hayır (§9.6 "ya da eşdeğeri") | Evet |
| N2 aynı gün: formül aynen | H99'da 1 fold 1 çift (KBORU ← SURGY), fold yetersiz eğitimli → skorlara etkisi 0 | Cümlenin ikinci yarısına ("aynı gün listelenen … eğitmez") lafzen aykırı; proje sahibi kararı (N19) | Evet (kararla); bilgi T akşamı kamuya açık |
| N3 ön işleme başlık başına | Evet (tanım gereği; F1 82 / F2 78 satır) | Hayır (§4.1 "bağımsız" başlıklar; §7.2 "fold içinde") | Evet; bağımsız kodumla bit-eşit |
| N4 `status` = F1, F2 iç tabloda; `MODEL_NOT_FIT_DID_NOT_CONVERGE` adı | Hayır (biçim) | Hayır | Evet |
| N5 `@ZERO` ledger sütunları, tek günlük satırı, sayaç +1 | Hayır | Hayır (§4.2 kural satırı) | Evet |
| N6 `by_type` sınıf yoksa çift düşer | Yakın dönemde hiç olmadı (n = 69) | Şartname sessiz | Evet |
| N7 atomlar `mixture_atoms`'tan; Faz 4 paritesi | Hayır | Hayır | Evet; bağımsız kodumla bit-eşit |
| N8 b = 10 arzının D_b alanları yalnız sayım için | Hayır (modele girmez) | Hayır | Evet |
| N9 k_b Decimal; rozet gizleme | Hayır (gösterim) | Hayır | Evet |
| N10 §6 satır 6 parantezi hükme girmez | Bilgi satırı | Sözcük/parantez çelişkisi; sözcükler seçildi, sonuçtan önce | Evet |
| N11 §6 kuralları (`FAZ8_RULES`, `OPERATIONAL_RULES_FAZ8`) | Hüküm kuralı; A'da sabit, B/R'de değişmedi (blob eşit) | Hayır (H16/T6 kalıbı) | Evet; kendi uygulamam aynı 13 hükmü verdi |
| N12 `class_break` saf formül | Hayır (skorlama görevi) | Hayır | Evet |
| N13 çıktılar `docs/faz8/backtest/` | Hayır | Hayır (görev metni) | Evet |
| N14 CLAUDE.md cümlesi devam satırında | Hayır | Hayır (birebir) | Evet |
| N15 bant doğrulaması | Hayır | Hayır; çekince: ±%10'un bütün pazarlarda uygulanması dipnot duyurularına dayanır (açılmadı); H99'da 85/85 ve canlı `BAND_RULE_MISMATCH` korur | Evet |
| N16 `tests/test_faz8_support.py` adı | Hayır | Görev kuralı | Evet |
| N17 günlük alanları | Hayır | Hayır | Evet |
| N18 rejim etiketi sabitleri | Hayır (kart görevine) | Hayır | Evet |
| N19 (1) kasa testi `git_head` kalıbı | Testin kuralı değişti: kaynak hash'i "bugünkü ağaç" yerine "dosyayı yazan commit'in ağacı" | Görev kuralına (var olan test salt okunur) aykırı; proje sahibi onayı var | Evet — bekçi gevşemedi: dosya hâlâ (a) kendi commit'inin atası olan git_head, (b) `ff49828`'deki borsai/ ağacı hash'ine eşit kaynak hash'i (**doğrulandı: eşit**), (c) bugünkü kodun bellek koşusuyla iki kod alanı dışında bayt-eşitlik ister; mutasyon testi `test_scores_oot_code_rule_mutations` dört sapmayı yakalar; (m) mutasyonunda bekçi kapatılınca test kırmızı (§6) |
| N19 (2) `report.py` kancası + sayaç/duyarlılık istisnası | MODELS.md'ye Faz 8 bölümü (dizin yoksa bayt-eşit); 7 testte istisna | Görev kuralına aykırı; onaylı | Evet — istisna **tam olarak** `faz8_variants` (= 1; günlükteki (model_id, spec_sha256) çiftleri, duyarlılık sayılmaz) kadar ve **yalnız** `scores/scores.json` ile `scores_post_d1.json` 87434ff'teki halleriyle bayt-eşitken (**doğrulandı: EVET/EVET**; `scores/` 87434ff'ten beri değişmedi); duyarlılık sayısı 16 + {0, 3} ile sınırlı; skorlar yeniden üretilince istisna kendiliğinden düşer |
| N19 (3) formül aynen | = N2 | = N2 | Evet |
| N20 ürün eşiği yuvarlama bulgusu | Hayır (değişiklik yok) | Hayır (§5.1 "eşik tanımı yine de budur") | Evet; §2'de ölçüldü |

Hiçbir N maddesi modelin tanımını (olay, özellik, dönüşüm, ızgara, eğitim kümesi, fold kuralı, karşılaştırıcı) şartnameden farklı yapmıyor; bu yüzden model_id değişmez.

## 5. Tam test [ÖLÇTÜM] — `ekler/test_out.txt`

HEAD `c84ba64`, temiz ağaç (bu denetimin dosyaları dışında):
- `.venv/bin/pytest -q -p no:cacheprovider` (sıralı): **906 passed** in 1221.35 s (0:20:21); başarısız/hata yok. Opus'un son kabul koşusuyla aynı sayı (906).
- `bash app/scripts/test.sh`: **exit 0** — cargo test bölümleri hepsi `ok` (ör. golden 9 passed: `golden_parity`, `fall_parity`, `post_d1_parity`, `conditional_path_parity`…; records_parity ok), npm **305 passed** (20 dosya), parite **8 passed**, `golden_unchanged: YEŞİL (U46, U55, U80; EK 3 P2, P4)`.
- Koşu sırasında korunan dizinler temiz (`git status --porcelain -- registry data scores models app`: boş).

## 6. Mutasyon denetimi [ÖLÇTÜM] — `ekler/mutate.sh`, `ekler/mutasyon_ciktilari.txt` (klon `/tmp/borsai_faz8_audit/clone`, HEAD `c84ba64`, `.venv` bağlı)

Her mutasyon klonda ayrı uygulandı, hedef test(ler) koştu, geri alındı (klon sonda temiz: `git status --porcelain` 0 satır). Taban: 15 hedef test mutasyonsuz **yeşil** (15 passed, 50 sn). Çıktılarda kasa kodu maskesi uygulandı (geçiş: 0).

| # | Mutasyon (dosya) | Hedef test(ler) | Sonuç |
|---|---|---|---|
| a | `b_floor` float eşitliğiyle (`predict_break.evaluate_break_day`) | `test_2_b_floor_is_raw_text_decimal_equality` | **KIRMIZI** (assert 1 == 0) |
| b | etiket "en düşük == alt limit" (`post_break._label` → `thb_raw_low`) | `test_3_loader_whitelist_access_counter`, `test_b3`, `test_b4` | **KIRMIZI** (3/3; beyaz liste kümesi değişti, gerçekleşen sütunları ve ledger baytları değişti) |
| c | eğitim kesimi `<=` (`plan_break_folds`) | `test_4_plan_counts_and_cutoffs`, `test_4b_same_day_rule_synthetic`, `test_b4` | **KIRMIZI** (3/3; `'2023-11-02' < '2023-11-02'`) |
| d | hücre kesimi D_1 yerine T (`backtest_ledger`: `cache.get(f.break_date)`) | `test_b4`, `test_15c` (sentetik) | **KIRMIZI** — `test_b4` bekçiyle durdu (`BreakError: TABGD|2023-11-01: hücre gözlemi D_1(k)'dan önce değil`); sentetik tabloda arzlar 31 gün aralıklı olduğundan bekçi tetiklenmez (`test_15c` yeşil kaldı; H99 koşusu yakalar) |
| e | beyaz liste dışı sütun okuma (D_{b+1} satırında `thb_raw_low`) | `test_3_loader_whitelist_access_counter` | **KIRMIZI** |
| f | yapısal sıfırda 10 − b yerine 9 − b | `test_7_structural_zero_on_h99`, `test_7b`, `test_b3` | **KIRMIZI** (`assert 24 == 16`; sentetik sınır testi de kırmızı) |
| g | ürün eşiği bir adım kaydırılmış (`product_thresholds`: Lo + adım) | `test_b4`, `test_b6` | **KIRMIZI** — `test_b4` (ledger baytları farklı); `test_b6` yeşil kaldı çünkü MODELS.md ledger dosyalarından üretilir, yeniden koşmaz (bilgi) |
| h | yakın dönem sınırı 2023-12-01 (`FAZ8_NEAR_ERA_START`) | `test_4`, `test_b3`, `test_b6` | **KIRMIZI** (3/3; `assert 76 == 69`; MODELS.md render farklı) |
| i | `@ZERO` test satırını içerir (`"zero_F1": train_rate(ys1 + [y_test])`) | `test_5b_zero_rate_is_exact_fraction`, `test_b3`, `test_b4` | **KIRMIZI** (`test_5b` sentetik: `0.333… == 0.0`; `test_b4` ledger baytları farklı); `test_b3` yeşil kaldı çünkü commit'li ledger DOSYASINI okur, yeniden koşmaz (bilgi) |
| j | el değiştirmede pay yerine sermaye (`post_ipo_share_capital`) | `test_1b`, `test_2b`, `test_b4` | **KIRMIZI** (3/3) |
| k | kırpma sınırları (ve μ/σ) test arzını içerir (`fit.fit_fall_horizon`, ortak yol) | `test_b4` | **KIRMIZI** (ledger baytları farklı) |
| l | §6 "çok iyi" eşiği −0.16 yerine −0.20 (`FAZ8_RULES`) | `test_10_too_good_triggers`, `test_b6` | **KIRMIZI** (2/2; `assert [] == ['birincil fark < -0.160']`; MODELS.md render farklı) |
| m | N19 kasa bekçisinde kaynak-hash denetimi kapalı (`scores_oot_code_problems`) | `test_scores_oot_code_rule_mutations` | **KIRMIZI** (`assert [] == ['borsai_source_sha256']`) — mutasyon testi bekçiyi gerçekten yakalıyor |

13/13 mutasyon kırmızı (K3). Not: (g)'de MODELS.md'nin yeniden koşmadan üretilmesi tasarım gereğidir (ledger'lar dondurulmuş çıktıdır); eşik mutasyonunu H99 bit-eşitlik testi (`test_b4`) yakalar.

## 7. Koruma [ÖLÇTÜM]

`ekler/koruma_once.txt` / `ekler/koruma_sonra.txt`: HEAD `c84ba64…`; `registry` `8a82b86e…`, `data` `383d0098…`, `scores` `e5719e0f…`, `models` `dec45410…`, `app` `93799e97…`; `git status --porcelain --untracked-files=all` koşu öncesi yalnız görev dosyası (+ bu dizin), sonrası yalnız bu denetimin dosyaları ve görev dosyası. Geçici işler `/tmp/borsai_faz8_audit/` altında yapıldı ve sonda silindi. `ekler/` boyutu < 3 MB.

## 8. Dondurma önerisi

- **`break_floor_v0` ve `break_floor_v0@ZERO` bu şartnameyle dondurulabilir** (K1–K4 sağlandı; uygulama hatası ya da sızıntı bulunmadı; kod = şartname). Dondurma temiz ağaçta, `fa623df` koduyla (B ve R `borsai/`'yi değiştirmedi) `python -m borsai.freeze --post-break …` (henüz yazılmadı; N1) ile; `models/INDEX_POST_BREAK.json` yeni; `INDEX.json`/`INDEX_POST_D1.json` değişmez (uygulama pinleri kırılmaz).
- **Kartın öne çıkan durumu (§8, k1):** aşama 1 — k1 sağlandı (iki üst uç < 0) → `break_floor_v0`'ın p_F1'i öne çıkarılabilir, zorunlu etiket **"ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = 0"**; `@ZERO` oranı ve ürün türevi yan yana; aşama 2 (canlı n ≥ 30) yalnız canlı hücrelerle.
- **Gösterilecek uyarılar:** (1) birincil farkın büyüklüğü karşılaştırıcının zayıflığındandır (ürün taban üstü kırılmaya ≈ 0.57 der; eşik yuvarlaması ≈ 0.03 ekler) — "tek orana karşı kazanç küçük: −0.028 [−0.045, −0.007]"; (2) β_turn işareti beklentinin tersi (+0.063; düşük güvenle yazılmıştı) ve el değiştirme bilgi eklemiyor (duyarlılık, `by_type`); (3) F2 − `@ZERO` ≈ 0 (iki ardışık taban için model tek orandan ayırt edilemiyor); (4) kalibrasyon sınıfa göre: taban üstü kırılmada model yüksek (+0.129), taban kırılmasında düşük (−0.086); 2025 kohortunda +0.204 (n 16); (5) rejim: `FON_KRIZI_2026` (D_1 ≥ 2026-09-16; bitiş açık, C4) — önceden yazılı okuma "model tabanı az tahmin eder"; (6) `BAND_RULE_MISMATCH` olunca yastık rozeti gizli; (7) eski dönem terazisi yok (A2), n F2 52 < 55 beklentisi.

## 9. Açık sorular (proje sahibine; en çok 3)

1. **Ürün satırının kart/MODELS.md notu.** §2d'deki iki not (eşik toleransında ürün 0.12 → 0.20; taban üstüne ≈ 0.57) kart metnine ve MODELS.md Faz 8 bölümüne "bilgi" olarak eklensin mi? Hücre tanımı değişmez (yeni model_id gerektirmez); yalnız metin. Öneri: evet, `report_faz8.py` ile dondurma görevinde.
2. **b = 9 fold'larında `zero_F2` sütunu ve nihai JSON.** Opus F2 tanımsızken F2 eğitim kümesi kurmuyor (ledger'da boş); dondurulmuş JSON'un `@ZERO` F2 değeri 78 arzlık kümeden (0.1410). Canlı skorlamada b = 9 satırı için F2 yazılmayacak; bu okuma onaylansın (varsayılan: evet, değişiklik yok).
3. **N15 çekincesi.** ±%10'un bütün pazarlarda uygulanmasını dayandıran duyurular (2020/20, 2020/21, 2020/50, 2025/38860) açılmadı; dondurmadan önce orkestratör bir kez bakmak ister mi? Canlı koruma (`BAND_RULE_MISMATCH`) zaten var; öneri: dondurmayı bekletmesin.

## 10. Ekler

| Dosya | İçerik |
|---|---|
| `ekler/repro_break.py` | sıfırdan yeniden üretim betiği (borsai import yok) |
| `ekler/repro_run.txt`, `ekler/repro_stdout.txt`, `ekler/repro_output.json`, `ekler/repro_ledgers/*.csv` | koşu kaydı, rapor, bütün sayılar (hücreler, §6, N20 atom örnekleri, Newton, sızıntı), kompakt ledger'lar (4 varyant) |
| `ekler/leak_checks.py`, `ekler/leak_checks_out.txt`, `ekler/leak_checks_out.json` | Opus koduyla sızıntı/kesim/beyaz liste/dosya izi |
| `ekler/sira_kanitlari.sh`, `ekler/sira_kanitlari.txt` | sıra ve uygunluk komut çıktıları |
| `ekler/hijyen.py` | SEALED/bülten taraması (yalnız sayı) |
| `ekler/mutate.sh`, `ekler/mutasyon_ciktilari.txt` | mutasyon sürücüsü ve çıktıları |
| `ekler/test_out.txt` | tam pytest ve `app/scripts/test.sh` |
| `ekler/koruma_once.txt`, `ekler/koruma_sonra.txt` | koruma ölçümleri |

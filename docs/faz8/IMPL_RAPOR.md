# Faz 8 uygulama raporu — kırılma akşamı modeli (`break_floor_v0`, kural satırı `break_floor_v0@ZERO`)

Görev: BORSAI_FAZ8_BREAK_IMPL_20261001 (`docs/prompts/FAZ8_BREAK_IMPL.md`). Uygulama: Opus 5.5, 2026-10-01/02. Şartname
`docs/specs_faz8/SPEC_BREAK_V0.md` ve `KARARLAR.md` (Fable, `7d78d43`). Kapsam: şartnamenin A + B kısmı (§0.4).
**Dondurma, canlı skorlama, makine kayıt yazıcı ve uygulama bu görevde yoktur. Push yapılmadı.**

## 0. Özet

1. **Birincil hücre** (F1 Brier, `break_floor_v0 − PRODUCT_BREAK_FLOOR`, yakın dönem): **−0.1904 [−0.2520, −0.1247]**, n = 69,
   21 ay. Aralık 0'ın altında. §6 beklentisi −0.080 [−0.140, −0.020] idi; gerçekleşen fark aralığın altında.
2. **"Beklentiden çok iyi" tetiklendi:** birincil fark < −0.160 ve birincil aralığın üst ucu < −0.080. Şartname gereği dondurmadan
   önce Fable'ın bu şartnameden bağımsız, sıfırdan yeniden üretimi zorunludur (ledger'lar |Δ| ≤ 1e-9).
3. **`@ZERO` hücresi** (F1 Brier, model − fold eğitim oranı): **−0.0281 [−0.0453, −0.0074]**, n = 69, 21 ay. Aralık 0'ın altında;
   §6 aralığı [−0.080, 0.000] içinde → tuttu.
4. **Ön eleme (k1, §8) sağlandı:** iki hücrenin de üst ucu < 0. Etiket "backtest'te geçiyor (tasarıma maruz)"tır; asıl sınav canlı
   sicildir (n ≥ 30).
5. Birincil farkın büyüklüğünün bir kısmı karşılaştırıcıdan gelir. Ürün taban kırılmalarına ort. 0.115, taban üstü kırılmalara
   ort. 0.568 veriyor (gerçekleşen 0.536 / 0.122). Şartnamenin "ters yönlü" dediği şey bu, ama türetmesinden (≈ 0.30 ve
   ≈ 0.35–0.50) daha uç. Taban kırılmalarındaki düşüklüğün ölçülen nedeni §5.1 eşiğinin adım yuvarlamasına duyarlılığıdır (§5,
   N20). Kod şartnameyi aynen uygular.
6. §6 tablosu: **13 satırın 9'u tuttu, 4'ü tutmadı.** Tutmayanlar: birincil (daha iyi), bilgi satırı `PRODUCT − @ZERO` (ürün
   beklenenden kötü), β_turn işareti (nihai fit +0.063), F2 yakın dönem n'i (52 < 55).
7. Bant ve baz fiyat kuralı rev. 54'te değişmedi → **doğrulandı** (`docs/faz8/BANT_DOGRULAMA.md`).
8. Proje sahibinin üç kararı (N19) ile var olan altı test dosyası, `borsai/report.py` (kanca) düzenlendi; `scores/` değişmedi.
9. Son sıralı pytest, `bash app/scripts/test.sh` ve `gen_golden --check` yeşil (§12).

## 1. Hash'ler ve commit'ler

| Öğe | Değer |
|---|---|
| Taban (`origin/main`) | `7d78d43` |
| Commit K (kararlar, CLAUDE.md eki, bant doğrulaması) | `5d84e88` |
| Commit A (kod ve testler; sonuç yok) | `fa623df` |
| Commit B (resmi koşu, MODELS.md, altın testler) | `df338c2` |
| Commit R (bu rapor) | bu commit |
| `SPEC_BREAK_V0.md` sha256 | `da98351c2b1bb4d7ef3c9ee5954ff4daade0960eab0ec44daa0b4ba540001f31` |
| `KARARLAR.md` sha256 (§C yazıldıktan sonra) | `8d8bbc971b01472f498cc96d5eddd26cdb868406512426a355df213e74d89ce7` |
| `break_floor_v0` spec_sha256 (kanonik sözlük) | `8ada9ccf77dc12caa5e9ea00b5bd028456dc8ce7d6857665358737c4b7a84e50` |
| Veri sürümü (H99) | `a0c7d082dacdbde03f53d1c4af1ce9f7983f9946abc80062de570f4a1df1f977` |
| SESSIONS dosyası sha256 | `eca620d3a5e8fed0b118bab556da5ce519257a4b2e14efcd22065f5bcdc93da9` |
| Resmi koşunun kodu | `git_commit` `fa623df`, `borsai_dirty` false, `borsai_source_sha256` `0e13b6be356c…` |
| Günlük satırları | 2143 (`kind: backtest`), 2144–2146 (`kind: sensitivity`); `context: official`, 2026-10-02 11:35–11:36 (+03:00) |

## 2. Bant doğrulaması (adım 0b, C5)

Pay Piyasası Prosedürü rev. 54 ve Pay Piyasası Yönergesi rev. 18 (ikisi de 21.09.2026) yalnız pazar belirleme kriterlerini
değiştirdi (likidite, volatilite, özsermaye). Fiyat marjı tablosu, içe yuvarlama, fiyat adımı tablosu ve ilk gün baz fiyatı aynı.
**Sonuç: doğrulandı.** Görevin DUR koşulu tetiklenmedi.

Çekince: belgedeki genel marj kuralı pazara göredir (Yıldız ±%20, Ana ±%15, Alt ±%10). ±%10'un bütün pazarlarda uygulanması
dipnottaki "ikinci bir duyuruya kadar" geçerli duyurulardan gelir. Bu duyurular ağ izni dışındaydı ve açılmadı.

Dosya sha256'ları, sayfa atıfları ve alıntılar `docs/faz8/BANT_DOGRULAMA.md`'de. PDF'ler repoya girmedi. Metin macOS PDFKit ile
çıkarıldı (bu makinede `pdftotext` yok).

## 3. Kırılma tablosu kabul sayıları (§13-1)

Hepsi `ekler/profil_kirilma.txt` ile birebir (`tests/test_faz8_break.py::test_1_*`):

| Sayı | Değer |
|---|---|
| Kırılma akşamı (b ≤ 9) | 82 |
| b dağılımı 1…10 | 18 / 11 / 4 / 13 / 12 / 8 / 6 / 6 / 4 / 3 |
| L = 10 (seri bozulmadı) | 14 |
| b = 10 | 3 |
| `b_floor = 1` | 35 (2 ≤ b ≤ 9: 31; b = 1: 4) |
| Kırılma günü yarım gün / durdurma | 1 / 0 |
| referans_b == kapanış_{b−1} | 67/67 |
| Lo(referans_b) == alt limit_b | 85/85 |
| Gün boyu taban kilidi (`WARN_B_FLOOR_LOCK_ALLDAY`) | 8 |
| Bant kuralı (`BAND_RULE_MISMATCH`) | 0 (82/82 tutuyor) |
| Yastık kuralı, D10 ≤ arz mekanik olarak imkânsız | 16 (b = 7: 6, b = 8: 6, b = 9: 4); yaklaşık kural 82/82 aynı |

Yükleyici beyaz listesi (H20 kalıbı) erişim sayacıyla sınandı. D_b'den sonraki satırlarda erişilen anahtarlar tam olarak
{ticker, session_number, target_session_date, thb_raw_close, thm_raw_lower_limit}.

## 4. Fold sayıları

| | F1 | F2 |
|---|---|---|
| Fold | 82 (yakın dönem 69, 2023 13) | 78 tanımlı (b = 9: 4 `TARGET_UNDEFINED_F2`) |
| `INSUFFICIENT_TRAINING_HISTORY` (≥ 10 satır, ≥ 5 olay, ≥ 5 olay-dışı) | 13 (2023 fold'larının hepsi) | 26 |
| FIT_OK | 69 (hepsi yakın dönem; 2024: 27, 2025: 16, 2026: 26) | 52 (hepsi yakın dönem) |
| Yakın dönem FIT_OK ay bloğu / olay | 21 / 20 | 16 / 5 |
| Seçilen C (FIT_OK) | 0.1: 32, 1.0: 27, 0.01: 7, ZERO: 3 | 0.1: 43, 1.0: 9 |

Diğer sayılar:
- Ürün karşılaştırıcısı `POST_BREAK_INSUFFICIENT`: 5 fold, hepsi 2023 ve model tarafında da yetersiz eğitimli (yakın dönem
  eşleşmesini etkilemez).
- Test arzının b_turnover'ı kırpılan fold (F1 ön işlemesi): 11. Sıfır varyansla düşen kolon: 0.
- Faz 4 ledger'ıyla hücre sayısı paritesi: 87/87 OK fold birebir.
- Aynı gün listelenen arz (N2, formül aynen): 1 fold'da 1 çift.

## 5. Birincil hücre ve `@ZERO` hücresi

| Hücre | n (ay) | model | karş. | fark | %95 aralık | model iyi / karş. iyi / eşit |
|---|---|---|---|---|---|---|
| **F1 − `PRODUCT_BREAK_FLOOR` (birincil)** | 69 (21) | 0.1878 | 0.3781 | **−0.1904** | **[−0.2520, −0.1247]** | 48 / 21 / 0 |
| **F1 − `@ZERO`** | 69 (21) | 0.1878 | 0.2158 | **−0.0281** | **[−0.0453, −0.0074]** | 49 / 17 / 3 |

Aralıklar SPEC_DEVIATIONS C7 ile hesaplandı: ilk işlem ayı blokları, 4000 tekrar, `random.Random(20260921)`. Brier kırpmasız.

**Karşılaştırıcı üzerine not (Fable ve orkestratör için; SPEC_DEVIATIONS N20).** Ürün, taban kırılmasında ertesi gün taban
olasılığını §5.1 eşiğiyle sayar: Lo(Lo(kapanış_L))/P − 1 (test arzının kendi fiyat seviyesi, kesin adım yuvarlaması, tolerans 1e-12).

Yakın dönemin 28 taban kırılmasında:
- hücrenin (B, m = 2) "çift tabana yakın" payı (v ≤ −0.185) ort. **0.273**; şartnamenin "≈ 20/67" türetmesiyle uyumlu.
- kesin eşiğin saydığı pay ort. yalnız **0.115**.

Bu, birincil farkın şartname beklentisinden büyük çıkmasının nedenlerinden biridir (çıkarım). Çift taban getirileri başka arzların
fiyat seviyelerinde oluşur ve adım yuvarlamaları farklıdır; yarıdan fazlası bu eşiğin hemen üstünde kalır. Taban üstü kırılmalarda
da ürün şartnamenin varsaydığından (≈ 0.35–0.50) yüksektir (0.568). Şartname bu sınır
davranışını not edip eşiği bağlayıcı tutmuştur (§5.1); kod aynen uygular, değiştirmek yeni karar ister.

Gerçekleşenler sınıfa göre:

| Sınıf | n | Ürün ort. | Gözlenen y_F1 | Model ort. |
|---|---|---|---|---|
| Taban kırılması | 28 | 0.115 | 0.536 | 0.450 |
| Taban üstü kırılma | 41 | 0.568 | 0.122 | 0.251 |

`@ZERO` hücresi bu karşılaştırıcı davranışından bağımsızdır. Modelin tek orana karşı kazancı −0.028'dir (§6 beklentisi −0.040,
aralığı içinde).

## 6. §6 tablosu: beklenen ile gerçekleşen (satır satır)

Kurallar commit A'da sabitlendi (`specs.OPERATIONAL_RULES_FAZ8`, `FAZ8_RULES`; SPEC_DEVIATIONS N10, N11). Tablo `docs/MODELS.md`
Faz 8 bölümündedir (aynen satırlar).

| # | Hücre | Beklenen (aralık; 0'ı) | Gerçekleşen | Konum / hüküm |
|---|---|---|---|---|
| 1 | F1 − `PRODUCT_BREAK_FLOOR` (BİRİNCİL) | −0.080 [−0.140, −0.020]; dışlaması olası | −0.1904 [−0.2520, −0.1247] | altında — beklentiden çok iyi / **tutmadı (daha iyi)** |
| 2 | F1 − `@ZERO` | −0.040 [−0.080, 0.000]; dışlaması olası, garanti değil | −0.0281 [−0.0453, −0.0074] | aralık içinde / **tuttu** (üst uç < 0 da tuttu) |
| 3 | F1 − `base_floor_by_type` | −0.005 [−0.025, +0.015]; içerir | +0.0106 [−0.0047, +0.0282] | aralık içinde / **tuttu** |
| 4 | F2 − `PRODUCT_BREAK_FLOOR` | −0.050 [−0.110, +0.010]; içerir ya da negatif dışlar | −0.0572 [−0.0847, −0.0239] (n 52, 16 ay) | aralık içinde / **tuttu** |
| 5 | F2 − `@ZERO` | −0.030 [−0.070, +0.010]; içerir | −0.0001 [−0.0131, +0.0179] (n 52) | aralık içinde / **tuttu** |
| 6 | bilgi: `PRODUCT − @ZERO` (F1) | +0.040 [0.000, +0.090]; pozitif dışlar ya da içerir | +0.1623 [+0.1087, +0.2139] | üstünde / **tutmadı (daha kötü)** |
| 7 | Kalibrasyon \|ort(p_F1) − gözlenen\| ≤ 0.06 | — | +0.0417 (0.3315 − 0.2899; n 69) | **tuttu** |
| 8 | β_floor (F1) > 0; nihai ve ZERO olmayan fold'ların ≥ %90'ı | — | nihai +0.987; fold'larda 66/66 | **tuttu** |
| 9 | β_turn (F1) < 0 (düşük güven) | — | nihai **+0.063** (fold'larda 52/66 negatif) | **tutmadı (> 0)** |
| 10 | Seçilen C, nihai F1: 0.1–1 | — | 1.0 | **tuttu** |
| 11 | ZERO payı ≤ %20 (yakın dönem F1 FIT_OK) | — | %4 (3/69) | **tuttu** |
| 12 | n, F1 birincil eşleşik: 60–69 | — | 69 | **tuttu** |
| 13 | n, F2 yakın dönem: 55–65 | — | 52 | **tutmadı (az)** |

Başarısızlık tanımları (§6): (a) basit kuraldan ayırt edilemiyor **hayır**; (b) zarar veriyor **hayır**; (c) özellikler bilgi
eklemiyor **hayır**; (d) düzey kayması **hayır**.

## 7. Katsayı işaretleri ve seçilen C'ler (nihai fit önizlemesi; dondurulmadı)

| Başlık | Eğitim (arz / olay) | C | sabit | b_floor | b_turnover | b_turnover kırpma [p05, p95] (ln) |
|---|---|---|---|---|---|---|
| F1 | 82 / 25 | 1.0 | −1.0007 | +0.9867 | +0.0629 | [−2.1789, 1.0579] |
| F2 | 78 / 11 | 0.1 | −1.8949 | +0.2872 | −0.3080 | [−2.1837, 1.0614] |
| `@ZERO` F1 / F2 | 82 / 25; 78 / 11 | ZERO | p = 0.3049 / 0.1410 | — | — | — |

Notlar:
- Dondurulmuş karşılaştırıcı oranları (canlıda `@ZERO` ve `by_type`): F1 0.3049; b_floor = 1 sınıfında 0.5429 (19/35), b_floor = 0
  sınıfında 0.1277 (6/47). Bu son oran orkestratörün 6/47 notuyla aynı.
- numpy nihai model ile stdlib `predict_break` eğitim satırlarında: F1 |Δp| ≤ 1.1e-16, F2 ≤ 5.6e-17.
- Eğitim etiketlerinin son seansı 2026-08-10 (≤ 2026-08-19 kesimi).
- β_turn işaret değiştiriyor: fold'ların çoğunda negatif, nihai fit'te küçük pozitif. `base_floor_by_type` hücresi (+0.011, 0'ı
  içeriyor) ve duyarlılıklar (§9) el değiştirmenin b_floor'a anlamlı bilgi eklemediğini gösteriyor. Model yine yazıldığı gibi.

## 8. Yakın dönem ve 2023 ayrımı

- 2023 fold'larının 13'ü de `INSUFFICIENT_TRAINING_HISTORY` (erken fold'larda < 5 olay); 2023 keşif hücreleri boştur.
- Yakın dönem = bütün FIT_OK fold'lar (69). "Bütün fold'lar" keşif hücreleri yakın dönemle aynı sayıları verir.
- b kırılımı (keşif):

  | Küme | n (ay) | F1 − ürün | F1 − `@ZERO` |
  |---|---|---|---|
  | b = 1 (L = 0) | 17 (8) | −0.1288 [−0.3000, +0.0393] | −0.0122 [−0.0457, +0.0117] |
  | 2 ≤ b ≤ 9 | 52 (19) | −0.2105 [−0.2826, −0.1311] | −0.0333 [−0.0609, −0.0044] |

- Kalibrasyon (F1, model FIT_OK): yakın dönem +0.042. b_floor = 0 sınıfında +0.129 (model yüksek: 0.251 / 0.122), b_floor = 1
  sınıfında −0.086 (0.450 / 0.536). Lojistik sınıf ayrımını yarım yapıyor; tek oranlı sınıf tablosundan (by_type) iyi değil.

## 9. Duyarlılıklar (`kind: sensitivity`, model değil; MODELS.md'ye girmez)

| Duyarlılık | F1 − ürün (yakın dönem) | F1 − `@ZERO` | F2 − ürün | F2 − `@ZERO` | ledger sha256 (ilk 12) |
|---|---|---|---|---|---|
| `__sens_floor_only` (yalnız b_floor) | −0.1968 [−0.2648, −0.1255] | −0.0345 [−0.0545, −0.0106] | −0.0618 [−0.0836, −0.0395] | −0.0048 [−0.0106, +0.0004] | `1900f9101512` |
| `__sens_turnover_only` (yalnız b_turnover) | −0.1567 [−0.2058, −0.1053] | +0.0056 [−0.0094, +0.0296] | −0.0519 [−0.0802, −0.0208] | +0.0051 [−0.0105, +0.0231] | `228822983914` |
| `__sens_with_group_Z` (+ Z/B grubu) | −0.1801 [−0.2389, −0.1175] | −0.0178 [−0.0314, −0.0000] | −0.0596 [−0.0822, −0.0355] | −0.0025 [−0.0091, +0.0054] | `0e7fa3a7758f` |

Okuma (hüküm değil):
- Bilgi taban kapanışından (b_floor) geliyor. El değiştirme tek başına `@ZERO`'yu geçmiyor ve b_floor'a eklendiğinde fark küçülüyor
  (−0.0345 → −0.0281).
- Z/B grubu da eklemiyor.
- Şartnameye göre model değişmez; bu sayılar v1 tartışması için kayıttır.

## 10. Ledger ve çıktı sha'ları (`docs/faz8/backtest/`)

| Dosya | sha256 |
|---|---|
| `break_floor_v0_fold_ledger.csv` (82 satır, 47 sütun; `zero_F1`/`zero_F2` = `@ZERO`'nun backtest'i) | `730a4e3cc75d007cf66306294a0b9c0dcc58840d82968864ab87357ee170098e` |
| `break_floor_v0__sens_floor_only_fold_ledger.csv` | `1900f91015123db87b9ed6b7fda9e4aff3ca18d62fe54f00886df8915a6f175c` |
| `break_floor_v0__sens_turnover_only_fold_ledger.csv` | `228822983914039b6dbd19f76c8e1156d8d231e89660c8b3d1a10cb92b53f199` |
| `break_floor_v0__sens_with_group_Z_fold_ledger.csv` | `0e7fa3a7758fb4ccd87aabb21ab6457ba05c524be29fb065de04e1504325f141` |
| `break_floor_v0_final_fit_preview.json` | `eab46afb1b052f4727ccb0eaaed0aa0e90ac95185e7a94be9a9daf6f08e118fa` |
| `break_floor_v0@ZERO_final_fit_preview.json` | `d63f8f55b896c199a6df121f27dcd79b131d4f7cddc12dd15fa3b59c722a373e` |

`MANIFEST.json` ve `SHA256SUMS` aynı dizinde. Resmi ledger bu makinede yeniden koşuyla bayt-eşit üretiliyor
(`tests/test_faz8_golden.py::test_b4`); önizlemeler yeniden fit'le `created_at` / `code_version` / `runtime` dışında aynı.

## 11. Sapmalar ve yorumlar (SPEC_DEVIATIONS N)

N1–N18 commit A'da, sonuç görülmeden yazıldı. N19 (proje sahibi kararları) ve N20 (B bulgusu) sonradan eklendi. Özetle:

| # | Konu |
|---|---|
| N1 | `BREAK_V0_RECIPE` `post_break.py`'de; var olan modüller (preprocess, fit, scoring, freeze, registry) değişmedi; `specs.py`'ye yalnız ekleme; fit yolu `fit.fit_fall_horizon` |
| N2 | Aynı gün kuralı: formül aynen (proje sahibi kararı) |
| N3–N4 | Ön işleme başlık başına (F1 82, F2 78); F2'nin durumu ve ön işlemesi `inner_table_F2` JSON'unda; 47 sütun şartnamedeki sırada |
| N5 | `@ZERO`'nun ayrı koşusu yok; ledger sütunları + günlükte `rule_rows_in_ledger`; varyant sayacı H99'da +1 |
| N7 | Ürün atomları `mixture_atoms` ile; `conditional_after_break` özetleriyle bit-eşit (testli); Faz 4 paritesi 87/87 |
| N10–N11 | §6 hüküm kuralları; satır 6 parantezi |
| N13 | Çıktılar `docs/faz8/backtest/` (tests/reference yazılamaz) |
| N14 | CLAUDE.md cümlesi kural 1'in devam satırında |
| N19 | Kasa testi kod-sha kuralı (`git_head` kalıbı) + mutasyon testi; `report.py` kancası (Faz 4 ile 7C arası); 7 testte varyant sayacı/duyarlılık istisnası (`tests/faz8_support.py`; skor dosyaları 87434ff'teki halleriyle kaldıkça) |
| N20 | Ürün eşiğinin adım yuvarlamasına duyarlılığı (bulgu, değişiklik yok) |

Görev kuralı dışına çıkan yazımlar yalnız N19 onayıyla yapıldı:
- `borsai/report.py`
- `tests/test_faz7_vault.py`, `test_scoring.py`, `test_faz5_live.py`, `test_faz4_ceiling_path.py`, `test_faz7c_golden.py`,
  `test_experiment_log.py`
- yeni `tests/faz8_support.py`
- §13 gereği yeni `tests/test_faz8_*.py` (yardımcı `test_faz8_support.py` dahil)

## 12. Test koşuları (ayrıntı `docs/faz8/test_runs.txt`)

| Koşu | Sonuç |
|---|---|
| Taban, paralel | 866 passed |
| A, sıralı (commit öncesi) | 898 passed, 1 deselected; o test commit sonrası 1 passed |
| B, paralel | 906 passed |
| Son kabul, sıralı | 906 passed (18:46) |
| `bash app/scripts/test.sh` | exit 0: cargo 151 / 0 failed, npm 305, parity 8, golden_unchanged yeşil |
| `gen_golden --check` | 35 dosya, fark yok |

§13 kabul testlerinin kapsamı:
- 1–10, 14, 15: `tests/test_faz8_break.py` (16), `tests/test_faz8_model.py` (16), `tests/test_faz8_golden.py` (7).
- 11–13 canlı skorlama görevine, 16 uygulamaya kaldı.

## 13. Sıradaki görevler için notlar

**Fable bağımsız yeniden üretim (zorunlu; "çok iyi" tetiklendi)**
- Girdi: şartname + KARARLAR + `docs/faz8/backtest/` ledger'ları ve önizlemeler; eşleşme |Δ| ≤ 1e-9.
- Özellikle denetlenmesi gerekenler:
  - (i) §5.1 ürün eşiği ve N20 (birincil farkın büyüklüğü);
  - (ii) plan formülü (N2) ve yetersiz eğitim kuralı (≥ 5 olay / olay-dışı başlık başına);
  - (iii) başlık başına ön işleme (N3);
  - (iv) b_turnover ln ölçeğinde Type-7 kırpma;
  - (v) `@ZERO` = Fraction oranı.
- Bağımsız yeniden fit'ler bit-eşit eşitlik üretmeyebilir: |fark| ≤ 1e-12 sayıları ledger'dan okunmalı.
- Faz 7C denetiminde olduğu gibi aynı sklearn 1.9.0 ortamı bit-eşitliği kolaylaştırır.

**Dondurma**
- `python -m borsai.freeze --post-break break_floor_v0 break_floor_v0@ZERO` henüz yok. `freeze_post_break`, `model_kind →
  post_break` dalı ve `models/INDEX_POST_BREAK.json` bu görevde yazılmadı (N1).
- Dondurma temiz ağaçta, kod değişikliğinden önce yapılmalı (borsai_dirty).
- Kasa testi artık kaynak hash'ini scores_oot.json'ı yazan commit'e göre denetliyor (N19); yeni `borsai/` kodu bu testi kırmaz.
- MODELS.md Faz 8 bölümüne dondurma notu `report_faz8.py` ile eklenmeli (bölüm `report.py` kancasıyla Faz 4 ile 7C arasında).

**Canlı skorlama / makine kayıt (S görevi)**
- `record_problems_through`, `outcome_ingest_commit_after`, makine kayıt yazıcısı ve `scores_break.json` yok.
- `predict_break.class_break` saf formülü ve `product_break_floor` canlı biçimi hazır.
- Bugünkü 7 arz RETRO; NETGL b = 4, `b_floor = 1` (şartname §13-12).
- Rejim uyarısı `FON_KRIZI_2026` (D_1 ≥ 2026-09-16, bitiş yok — C4).
- Skorlar yeniden üretilince `tests/faz8_support.py` istisnası kendiliğinden devre dışı kalır. H99 kart sayacı bir artar; o görev
  `faz8_variants`'ı RHS'e ekleyen dalların yeşil kaldığını görmeli.

**Uygulama (EK 5)**
- Rust `predict_break` altın vektörleri `parity_rows` kalıbıyla.
- Kartta yastık rozeti `structural_zero_badge(…, band_rule_ok)`.
- Öne çıkarma k1'i (sağlandı) "ön eleme (tasarıma maruz)" etiketiyle.
- MODELS.md'de duyarlılık kimlikleri yasak (`test_experiment_log`).

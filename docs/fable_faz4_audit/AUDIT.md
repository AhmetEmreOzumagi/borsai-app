# BORSAI_FAZ4_FABLE_REPRO_AUDIT_20260922 — tavan yolu modelleri: sıfırdan yeniden üretim ve denetim

Denetleyen: Fable (şartnameyi yazan el; ilk uygulamayı görmeyen ayrı oturum). Denetlenen: commit `2d0c98e` (BORSAI_FAZ4; HEAD bu oturumda `0b67f5d`, `borsai/` 2d0c98e'den beri değişmedi). Şartname: `docs/specs_faz4/SPEC_CEILING_PATH_V0.md` (commit `52e1567`, sha256 `07983660…`). Salt okur; tek yazma bu klasör. Ağ yok. `data/outcomes/`, `data/raw/bist/`, `scores/` ve `docs/SCORES.md` okunmadı; 2026-08-19 sonrası hiçbir veri okunmadı. Git yalnız okuma komutlarıyla ve `GIT_OPTIONAL_LOCKS=0` ile.

İşaretler: **[ÖLÇTÜM]** = bu oturumda komut/dosyadan; **[ÇIKARIM]** = yorum. Ekler (`ekler/`):
- `repro_ceiling_path.py` (+ `repro_stdout.txt`, `repro_output.json`, `repro_<model>_fold_ledger.csv` ×3): **`borsai` import etmeden**, yalnız stdlib ile ve yalnız şartnameden yazılmış yeniden üretim. Betikte `borsai` import satırı yok (`grep -c "import borsai\|from borsai"` → 0) ve çalışma sonunda `sys.modules`'ta `borsai` olmadığı assert edilir.
- `compare_with_report_faz4.py` (+ `_out.txt`): karşılaştırma harnessi (Opus'un rapor kodunu çalıştırır; yeniden üretimin parçası DEĞİLDİR): 36 satırın tam hassasiyetli fark/aralık/n değerleri ↔ bağımsız değerler; MODELS.md metni (4 hane).
- `runtime_file_trace.py` (+ `_out.txt`): Faz 4 backtest ve nihai-dondurma parametre yolu çalışırken açılan her dosya (`builtins.open`/`io.open`/`os.open` sarılarak; günlük geçici dizine).
- `write_sensitivity_log.py` → `sensitivity_runs.jsonl` (5 satır, `experiments/log.jsonl` biçimi, `kind: sensitivity`) ve `sens_<ad>_fold_ledger.csv` ×5.
- `pytest_out.txt`: `.venv/bin/pytest -q -p no:cacheprovider` tam koşu.

## Hüküm tablosu

| Model | Hüküm | Kısa gerekçe |
|---|---|---|
| `ceiling_path_v0` | **FREEZE_OK** | 87 fold'un her h'sinde return, p_up, q10, q90, mean bağımsız betikle **bit-eşit** (maks \|Δ\| = 0); C_h, ρ_h, hücre sayıları, havuz kaynakları, atom sayıları birebir. 36 §6 satırının farkı ve aralık uçları tam hassasiyette Δ = 0. Sızıntı yok (§2). Birincil hücre −0.1158 [−0.1611, −0.0738], n = 85 gerçek backtest sonucudur; "çok iyi" denetiminin 10 koşulu aynen yeniden üretildi. |
| `ceiling_path_v0@INF` | **FREEZE_OK** | Aynı ölçüde bit-eşit; S_k kaynak ledger'la metin düzeyinde aynı (870/870). |
| `pb_ceiling_path_v0` | **FREEZE_OK** | Aynı ölçüde bit-eşit; kesim B(k) < T her fold'da; PB planlanan fiyat = kesin fiyat 99/99. |

Dondurma koşulları (engelleyici değil, dondurma görevine): (1) `registry.F3_MODELS`'e `ceiling_path_v0` eklensin (SPEC_DEVIATIONS F9); (2) dondurma commit'i için push kanıtı alınsın; (3) JSON'lar temiz ağaçta, commit edilecek kodla üretilsin (§6 bulgu 1). Duyarlılık ne çıkarsa çıksın dondurulacak model şartnamedeki v0'dır.

## Özet (10 satır)

1. **Yeniden üretim tam.** Üç ledger'da 870 (fold × h) hücrenin hepsinde return, p_up, q10, q90, mean için maks |Δ| = **0.0** (eşik 1e-9); S_k dizeleri, C_h (Decimal), ρ_h (float), 1653 hücre sayısı, `cells_max_session_date`, `cells_ipos_sha256`, 870 `pooled_cells` (n, pooled, kaynak listesi) ve 870 `n_atoms` birebir. [ÖLÇTÜM `repro_stdout.txt` (a)]
2. §6'nın 36 satırı: eşleşik fark, %95 aralık uçları, n, ay sayısı ve kazanç/kayıp/eşit sayıları Opus'un rapor koduyla tam hassasiyette **Δ = 0 (36/36)**; MODELS.md metniyle 4 hanede 36/36. [ÖLÇTÜM `compare_with_report_faz4_out.txt`]
3. Birincil hücre: fark **−0.115845 [−0.161139, −0.073821], n = 85 (23 ay)**, model 0.184196, kural 0.300041, 63/22/0. "Beklentiden çok iyi" denetimi bağımsız hesapla da **10 koşulla tetikleniyor**; D1 beraberlik 52 bit-eşit / 84 (< 0.001) / 87; başarısızlık (a)–(d) gerçekleşmedi (ort. p_up_3 0.8307, gözlenen 0.8046). [ÖLÇTÜM]
4. **Sızıntı bulunmadı.** Her fold'da hücredeki en son seans < kesim (87/87 × 3, assert), test arzı hücreye katkı vermiyor (assert), PB'de kesim B(k) < T. Faz 4 kodu çalışırken açılan dosyalar listelendi: `data/outcomes/`, `data/raw/bist/`, `scores/` altından **0** okuma; yazma yalnız geçici dizine. [ÖLÇTÜM `runtime_file_trace_out.txt`]
5. Sıra: 52e1567 push kanıtı `created_at` 2026-09-22T15:32:22Z (= 18:32:22+03:00) < altın koşu 19:02:44+03:00 < 2d0c98e commit 19:16:27+03:00; `git merge-base --is-ancestor 52e1567 2d0c98e` doğru; `git diff 52e1567 HEAD -- docs/specs_faz4` boş (0 bayt). [ÖLÇTÜM]
6. S_k yeniden fit edilmemiş: üç ledger'ın S_1..S_10 dizeleri kaynak Faz 1B ledger'larıyla 870/870 aynı; kaynak ledger sha'ları şartname/`specs.py` sabitleri ve Faz 1B `SHA256SUMS` ile aynı. [ÖLÇTÜM]
7. Kod ↔ şartname: §2 limit yolu ve D1 HALF_UP, §3 hücreler/merdiven/kırpma, §4 karışım/kuantil/p_up, §7 koşullu formüller, §8 ledger sütunları, §12 sözde kod uyumlu; SPEC_DEVIATIONS F1–F12'nin hiçbiri değer değiştirmiyor (F1/F5 hassasiyet seçimleri: benim 28 haneli varsayılan Decimal sürümüm bit-eşit çıktı). [§2.5]
8. Tanı: D5 kazancının %83'ü S_5 < 0.5 olan 48 arzdan (ortalama fark −0.170), %17'si S_5 ≥ 0.5 olan 37 arzdan (22'sinde AE = 0: tahmin = gerçekleşen = ρ_5). Dört yılda da aynı büyüklükte (−0.097 … −0.125). Sıfır modele karşı −0.103'ün −0.075'i yine S_5 < 0.5 grubundan: kazanç, `ceiling_hazard_v0`'ın (f3) S_5 ayrımının iki rejimli sonuca (limit yolu ≈ +0.61 / kırılma sonrası ≈ 0) medyanla eşlenmesinden geliyor. [§3]
9. Duyarlılık (yalnız birincil hücre; model DEĞİL): N_MIN 5/20, tek grup ve havuzsuz varyantlarda fark −0.112 … −0.122, aralık üst ucu −0.070 … −0.077; sonuç tasarım seçimlerine (grup, N_MIN, havuzlama) duyarsız. Havuzsuz varyantta 7 erken fold reddedilir (n = 80). [§4]
10. Test paketi bu makinede yeşil: **421 passed, 242.9 s** (`ekler/pytest_out.txt`). Yeni dosya yalnız `docs/fable_faz4_audit/` altında (git durumundaki `app/` değişiklikleri paralel oturuma ait).

---

## 1. Sıfırdan yeniden üretim

### 1.1 Yöntem [ÖLÇTÜM `ekler/repro_ceiling_path.py`]

Girdiler (hepsi ≤ 2026-08-19; sha256'ları `repro_output.json: inputs_sha256`): `data/training_table.csv` (`b307cd0e…`), H99 SESSIONS CSV (`eca620d3…`; `close`, `upper_limit`, `lower_limit`, `reference_price`, `target_session_date`), H99 takvimi (`15d4d975…`; yalnız her seansın resmi seans günü ve D1 = ilk işlem günü denetimi), PB CSV (`5e52d4d2…`; `first_bookbuilding_date`, `ipo_price_try`). S_k üç Faz 1B altın ledger'ından metin olarak (`976b4dce…`, `90b61046…`, `c92ce859…`). Karşılaştırmalar Faz 1A altınları (`base_always_ceiling`, `base_train_median`, `base_rate`, `base_last10_rate`, `v1_5_h99`) ve Faz 1B PB altınlarından (`pb_v0`, `…__pb`).

Bağımsız hesaplananlar: fiyat adımı tablosu, U/Lo/snap, C_h ve ρ_h; hücre kurulumu (99 arz, kesim `prediction_date`, kesin `<`), sıralama; havuzlama merdiveni (kendi → diğer grup aynı m → m−1, m+1, m−2, …; adım sonunda n ≥ 10) ve hedef m sınırına kırpma; P(L = t); atom listesi, kararlı sıralama, alt kuantil kuralı (1e-12), p_up (kesin >), mean; gerçekleşen R_h/Y_h/L; eşleşik farklar, [0.01, 0.99] Brier kırpması, aylık blok bootstrap (`random.Random(20260921)`, `choices`, 4000, sıralı dağılımın 100. ve 3899. elemanı; C7). Decimal hassasiyeti varsayılan 28 hane (Opus 60 hane, F5): sonuç bit-eşit.

Şartnamenin kendi kabul ölçümleri de bağımsız betikle tuttu: U(referans) = üst limit **990/990**, Lo(referans) = alt limit **990/990**; C_h = seri ≥ h olan her arzın kapanışı **81/70/66/53/41/33/27/21/17/14** (424/424); snap ≠ P yalnız BORLS, AVPGY, ARTMS, LILAK; tam kohort hücreleri Z 18 × 10, B [67, 64, 60, 54, 48, 40, 28, 15, 11], 567 gözlem, katkı veren 85 arz; PB planlanan fiyat = kesin fiyat 99/99; ilk fold EKOS (2023-11-21) Z = 0, B = [6, 6, 5, 4, 3, 2, 0, 0, 0], (Z,1) havuzu {Z1, B1, Z2, B2} → n = 12.

### 1.2 (a) Fold ledger'ları ↔ `tests/reference/macos_golden_faz4/` [ÖLÇTÜM `repro_stdout.txt`, `repro_output.json: ledger_compare`]

| Ledger | fold | maks \|Δ\| return / p_up / q10 / q90 / mean | maks \|Δ\| ρ_h, P_L, realized_R | S_1..S_10 dize | C_h (Decimal) | cells_n (Z 10 + B 9) | max_session_date, ipos_sha256, status | n_atoms, post_break_status, pooled_cells (n, pooled, sources) | realized_Y, L | \|Δ\| > 1e-9 |
|---|---|---|---|---|---|---|---|---|---|---|
| `ceiling_path_v0` | 87 | **0 / 0 / 0 / 0 / 0** | 0 / 0 / 0 | 870/870 | 870/870 | 1653/1653 | 87/87, 87/87, 87/87 | 870/870, 870/870, 870/870 | 870/870, 87/87 | **0** |
| `ceiling_path_v0@INF` | 87 | **0 / 0 / 0 / 0 / 0** | 0 / 0 / 0 | 870/870 | 870/870 | 1653/1653 | 87/87 ×3 | 870/870 ×3 | 870/870, 87/87 | **0** |
| `pb_ceiling_path_v0` | 87 | **0 / 0 / 0 / 0 / 0** | 0 / 0 / 0 | 870/870 | 870/870 | 1653/1653 | 87/87 ×3 | 870/870 ×3 | 870/870, 87/87 | **0** |

ρ_h float olarak 870/870 birebir eşit (== karşılaştırması). Tek birebir olmayan şey `C_h`'nin **dize** gösterimi (T planlarında 844/870): ör. SKYMD C_1 altın "7.70", benim "7.7" — Decimal üs takibi farkı; sayısal eşitlik 870/870, hiçbir hesaba girmiyor (kozmetik, §6 bulgu 4).

### 1.3 (b) §6'nın 36 satırı [ÖLÇTÜM `repro_stdout.txt` (b), `compare_with_report_faz4_out.txt`]

Bağımsız değerler (fark = model − karşılaştırılan; aralık C7; n ve ay). Opus'un `report_faz4` çıktısıyla tam hassasiyette **maks |Δ| fark 0.000, alt uç 0.000, üst uç 0.000**; n / ay / kazanç-kayıp-eşit sayıları 36/36 aynı; MODELS.md tablosuyla (4 hane) 36/36 aynı.

| Model | Ufuk | Çıktı | Karşılaştırılan | Beklenen (§6) | Fark | %95 aralık | n (ay) | model / kural | Etiket (Opus kuralıyla) | Çok iyi? |
|---|---|---|---|---|---|---|---|---|---|---|
| `ceiling_path_v0` | D1 | MAE | `base_always_ceiling` | 0.000 … +0.005 | +0.0002 | [−0.0002, +0.0010] | 87 (24) | 0.0225 / 0.0223 | tuttu | |
| `ceiling_path_v0` | D1 | MAE | `base_train_median` | 0.000 … +0.005 | +0.0002 | [−0.0002, +0.0010] | 87 (24) | 0.0225 / 0.0223 | tuttu | |
| `ceiling_path_v0` | D1 | MAE | `v1_5_h99` | −0.007 … −0.002 | −0.0058 | [−0.0087, −0.0025] | 87 (24) | 0.0225 / 0.0284 | tuttu | |
| `ceiling_path_v0` | D1 | MAE | sıfır model | \|fark\| < 0.001 | +0.0004 | [+0.0000, +0.0012] | 87 (24) | 0.0225 / 0.0222 | tuttu | |
| `ceiling_path_v0` | D1 | Brier | `base_rate` | −0.005 … +0.005 | −0.0097 | [−0.0176, −0.0008] | 87 (24) | 0.0759 / 0.0855 | daha iyi | |
| `ceiling_path_v0` | D1 | Brier | `base_last10_rate` | −0.010 … +0.002 | −0.0167 | [−0.0264, −0.0079] | 87 (24) | 0.0759 / 0.0926 | daha iyi | |
| `ceiling_path_v0` | D1 | Brier | `v1_5_h99` | −0.002 … +0.010 | −0.0118 | [−0.0226, −0.0016] | 78 (22) | 0.0741 / 0.0860 | daha iyi | |
| `ceiling_path_v0` | D1 | Brier | sıfır model | \|fark\| < 0.003 | −0.0084 | [−0.0157, −0.0006] | 87 (24) | 0.0759 / 0.0843 | daha iyi | |
| `ceiling_path_v0` | D3 | MAE | `base_always_ceiling` | −0.020 … +0.005 | −0.0200 | [−0.0411, −0.0054] | 86 (24) | 0.1091 / 0.1290 | tutmadı | |
| `ceiling_path_v0` | D3 | MAE | `base_train_median` | −0.020 … +0.005 | −0.0194 | [−0.0404, −0.0049] | 86 (24) | 0.1091 / 0.1284 | tutmadı | |
| `ceiling_path_v0` | D3 | MAE | `v1_5_h99` | −0.010 … +0.020 | −0.0087 | [−0.0301, +0.0131] | 86 (24) | 0.1091 / 0.1177 | tuttu | |
| `ceiling_path_v0` | D3 | MAE | sıfır model | −0.015 … 0.000 | −0.0188 | [−0.0397, −0.0044] | 87 (24) | 0.1078 / 0.1266 | daha iyi | |
| `ceiling_path_v0` | D3 | Brier | `base_rate` | −0.040 … −0.005 | −0.0362 | [−0.0553, −0.0163] | 86 (24) | 0.1315 / 0.1677 | tuttu | |
| `ceiling_path_v0` | D3 | Brier | `base_last10_rate` | −0.040 … −0.005 | −0.0386 | [−0.0628, −0.0113] | 86 (24) | 0.1315 / 0.1701 | tuttu | |
| `ceiling_path_v0` | D3 | Brier | `v1_5_h99` | −0.010 … +0.030 | −0.0085 | [−0.0332, +0.0154] | 78 (23) | 0.1337 / 0.1422 | tuttu | |
| `ceiling_path_v0` | D3 | Brier | sıfır model | −0.025 … 0.000 | −0.0349 | [−0.0536, −0.0161] | 87 (24) | 0.1300 / 0.1649 | daha iyi | |
| `ceiling_path_v0` | D5 | MAE | `base_train_median` **(BİRİNCİL)** | −0.090 … −0.020 | **−0.1158** | **[−0.1611, −0.0738]** | 85 (23) | 0.1842 / 0.3000 | daha iyi | üst uç < −0.060 |
| `ceiling_path_v0` | D5 | MAE | `base_always_ceiling` | −0.110 … −0.040 | −0.1379 | [−0.2085, −0.0683] | 85 (23) | 0.1842 / 0.3221 | daha iyi | |
| `ceiling_path_v0` | D5 | MAE | `v1_5_h99` | −0.020 … +0.050 | −0.0360 | [−0.0579, −0.0176] | 85 (23) | 0.1842 / 0.2202 | daha iyi | |
| `ceiling_path_v0` | D5 | MAE | sıfır model | −0.050 … −0.005 | −0.1033 | [−0.1462, −0.0628] | 87 (24) | 0.1800 / 0.2832 | daha iyi | evet |
| `ceiling_path_v0` | D5 | Brier | `base_rate` | −0.030 … 0.000 | −0.0452 | [−0.0704, −0.0168] | 85 (23) | 0.1495 / 0.1947 | daha iyi | |
| `ceiling_path_v0` | D5 | Brier | `base_last10_rate` | −0.035 … −0.005 | −0.0539 | [−0.0819, −0.0197] | 85 (23) | 0.1495 / 0.2034 | daha iyi | |
| `ceiling_path_v0` | D5 | Brier | `v1_5_h99` | 0.000 … +0.040 | −0.0166 | [−0.0414, +0.0052] | 79 (23) | 0.1389 / 0.1555 | daha iyi | |
| `ceiling_path_v0` | D5 | Brier | sıfır model | −0.020 … +0.005 | −0.0407 | [−0.0631, −0.0159] | 87 (24) | 0.1462 / 0.1869 | daha iyi | |
| `ceiling_path_v0` | D10 | MAE | `base_train_median` | −0.100 … −0.010 | −0.1746 | [−0.2756, −0.0709] | 85 (23) | 0.3921 / 0.5668 | daha iyi | evet |
| `ceiling_path_v0` | D10 | MAE | `base_always_ceiling` | −0.750 … −0.550 | −0.7888 | [−1.0102, −0.5617] | 85 (23) | 0.3921 / 1.1809 | daha iyi | evet |
| `ceiling_path_v0` | D10 | MAE | `v1_5_h99` | −0.020 … +0.100 | −0.0595 | [−0.1447, +0.0157] | 85 (23) | 0.3921 / 0.4517 | daha iyi | evet |
| `ceiling_path_v0` | D10 | MAE | sıfır model | −0.050 … +0.010 | −0.1327 | [−0.2152, −0.0538] | 87 (24) | 0.4095 / 0.5422 | daha iyi | evet |
| `ceiling_path_v0` | D10 | Brier | `base_rate` | −0.020 … +0.010 | −0.0667 | [−0.1070, −0.0298] | 85 (23) | 0.1841 / 0.2508 | daha iyi | evet |
| `ceiling_path_v0` | D10 | Brier | `base_last10_rate` | −0.070 … −0.020 | −0.1165 | [−0.1702, −0.0645] | 85 (23) | 0.1841 / 0.3006 | daha iyi | evet |
| `ceiling_path_v0` | D10 | Brier | `v1_5_h99` | +0.010 … +0.060 | −0.0311 | [−0.0695, +0.0032] | 79 (23) | 0.1555 / 0.1866 | daha iyi | evet |
| `ceiling_path_v0` | D10 | Brier | sıfır model | −0.010 … +0.005 | −0.0522 | [−0.0830, −0.0241] | 87 (24) | 0.1801 / 0.2323 | daha iyi | evet |
| `ceiling_path_v0@INF` | D5 | MAE | `base_train_median` | −0.040 … +0.010 | −0.0101 | [−0.0221, −0.0026] | 85 (23) | 0.2899 / 0.3000 | tutmadı | |
| `ceiling_path_v0@INF` | D10 | MAE | `base_train_median` | −0.060 … +0.020 | −0.0366 | [−0.0887, +0.0048] | 85 (23) | 0.5302 / 0.5668 | tuttu | |
| `pb_ceiling_path_v0` | D5 | MAE | `pb_v0` | −0.040 … +0.030 | −0.0124 | [−0.0391, +0.0162] | 87 (23) | 0.2627 / 0.2751 | tuttu | |
| `pb_ceiling_path_v0` | D5 | MAE | `ceiling_path_v0` | +0.000 … +0.050 | +0.0728 | [+0.0421, +0.1088] | 85 (23) | 0.2570 / 0.1842 | daha kötü | |

Etiket sütunu Opus'un `OPERATIONAL_RULES_FAZ4` kuralının çıktısıdır; benim betiğim yalnız "aralık içinde / alt ucun altında / üst ucun üstünde" ayrımını verir ve bu ayrım 36/36 aynıdır (tuttu/tutmadı ayrımı ek olarak Opus kodunda; harness bu etiketleri de yazdırır).

### 1.4 (c) Birincil hücre ve "çok iyi" denetimi [ÖLÇTÜM]

- Birincil: fark **−0.11584504**, aralık **[−0.16113889, −0.07382122]**, n = 85, 23 ay; model MAE 0.18419640, kural 0.30004144; model iyi / kural iyi / eşit 63 / 22 / 0. Opus'la Δ = 0.
- Çok iyi koşulları (bağımsız): **10** — birincil aralığın üst ucu −0.0738 < −0.060; D5 MAE − sıfır model −0.1033 < −0.080; D10 MAE − medyan −0.1746 < −0.130; D10 MAE − tavan −0.7888 < −0.780; D10 MAE − V1.5 −0.0595 < −0.050; D10 MAE − sıfır −0.1327 < −0.080; D10 Brier − `base_rate` −0.0667 < −0.050; D10 Brier − son-10 −0.1165 < −0.100; D10 Brier − V1.5 −0.0311 < −0.020; D10 Brier − sıfır −0.0522 < −0.040. MODELS.md'deki 10 koşulla aynı.
- D1 beraberlik: 87 fold'un 52'sinde fark bit-eşit 0, 84'ünde 0 ya da |fark| < 0.001 (≥ 80 → tuttu).
- Başarısızlık (a) yalnız mekanik: hayır (altı hücrenin hepsi 0'ı dışlıyor); (b): hayır; (c): hayır (D1 aralığı [−0.0002, +0.0010]); (d): hayır (|0.8307 − 0.8046| = 0.026).

### 1.5 Tutmayan bir şey var mı?

Yok. Kök neden analizi gerektiren uyuşmazlık bulunmadı. Bağımsız betiğin üç yerde şartnameyi Opus'tan farklı okuma serbestliği vardı ve üçünde de sonuç aynı çıktı: (i) Decimal hassasiyeti (28 ↔ 60 hane), (ii) kırpma sınırlarının kesin Decimal'den float'a alınması (F1; kırpma yalnız m = 1 hedefinde, 1050 olay, en büyük değişim 0.0895 — m = 2 hücresinden ödünç alınan −0.19'a kadar değerlerin −0.1'e çekilmesi; şartnamenin "hedef m'nin fiziksel sınırı" kuralı), (iii) `sources` listesine boş hücrelerin de yazılması (F2). Bootstrap için blok sırası model ledger'ının fold sırasıdır (ilk görünüş sırası); farklı bir sıra aralığı değiştirirdi, Opus'unkiyle aynı sırayı kullandım ve aralıklar bit-eşit.

---

## 2. Sızıntı ve uygunluk denetimi

### 2.1 Fold düzeyi (bağımsız kurgu) [ÖLÇTÜM `repro_ceiling_path.py: run_plan` assert'leri; `repro_output.json: ledger_compare`]

| Denetim | `ceiling_path_v0` | `@INF` | `pb_ceiling_path_v0` |
|---|---|---|---|
| Hücredeki en son seans tarihi < kesim (`cells_max_session_date < prediction_date`) | 87/87 | 87/87 | 87/87 |
| Test arzı hücreye katkı vermiyor (`ticker ∉ contributors`) | 87/87 | 87/87 | 87/87 |
| Kesim ≤ ilk işlem günü (PB: B(k) < T) | 87/87 | 87/87 | 87/87 (B(k) < T) |
| Katkı veren arz kümesi hash'i altınla aynı (`cells_ipos_sha256`) | 87/87 | 87/87 | 87/87 |
| Hücre büyüklükleri altınla aynı | 1653/1653 | 1653/1653 | 1653/1653 |
| Fold kümesi ve sırası = kaynak ledger; `survival_fold_status` FIT_OK | 87/87 | 87/87 | 87/87 |

Hücre kuralı bağımsız betikte kesin önceliklidir: `if session_date(j, t+m) >= T: break` (ilk geçmeyen seansta durulur); kırılma günü D_{t+1} ≥ T ise arz hiç girmez (seri sürüyor sayılır). Kod tarafı aynı: `predict_path.build_cells` (`d >= cutoff → break`). Sentetik test `test_8` (T'den 2 seans önce kırılmış arz tam 1 gözlem; kırılma günü kesimde 0 gözlem) bu davranışı sınıyor.

### 2.2 Faz 4 kodu yasak veri okumuyor

- **Kod taraması** [ÖLÇTÜM `grep -n "outcomes\|raw/bist\|scores\|SCORES\|bist/" borsai/ceiling_path.py borsai/predict_path.py borsai/report_faz4.py tests/test_faz4_ceiling_path.py`]: `borsai/ceiling_path.py`, `predict_path.py`, `report_faz4.py`'de eşleşme yok. Yalnız `tests/test_faz4_ceiling_path.py` `scores/scores.json`'u okur — Faz 1 bloklarının değişmezliğini sınayan bekçi testte (`test_scores_json_faz1_blocks_unchanged_since_f1f9d44`, `test_new_models_are_not_in_live_n_and_have_no_records`); model/backtest kodu değil.
- **Çalışma zamanı kanıtı** [ÖLÇTÜM `ekler/runtime_file_trace_out.txt`]: `builtins.open`/`io.open`/`os.open` sarılarak `load_dataset` + `run_backtest` (3 koşu) + `fit(…)` (3 modelin nihai-dondurma parametreleri, repoya yazılmadan) koşuldu. Okunan repo dosyaları: `data/data_version.json`, `data/training_table.csv`, H99 `*_FROZEN_COHORT_*` (3), H99 `*_OFFICIAL_BIST_OUTCOME_*` session ve targets CSV'leri, PB CSV, `docs/specs_faz4/SPEC_CEILING_PATH_V0.md`, üç Faz 1B kaynak ledger'ı, `models/INDEX.json` + üç seri modeli JSON'u, `borsai/*.py`. `data/outcomes/`, `data/raw/bist/`, `scores/` altından okuma: **0**. Yazma: yalnız geçici dizindeki günlük (3 satır) ve bir geçici dosya; `experiments/`, `models/`, `tests/`, `data/`, `registry/`, `scores/` altına yazma yok (assert).
- Okunan hiçbir dosyada 2026-08-19 sonrası veri yok: SESSIONS en son seans 2026-08-19 (assert), `training_table` kesim 2026-08-19, kaynak ledger'lar H99. Takvim B uzantısı (`pay_calendar_b_extension_…`) Faz 4 yolunda açılmadı.

### 2.3 Sıra [ÖLÇTÜM]

```
$ cat registry/push_proofs/52e15679….json | grep created_at   → "created_at": "2026-09-22T15:32:22Z"   (= 18:32:22+03:00)
$ GIT_OPTIONAL_LOCKS=0 git show -s --format=%cI 2d0c98e     → 2026-09-22T19:16:27+03:00
$ GIT_OPTIONAL_LOCKS=0 git merge-base --is-ancestor 52e1567 2d0c98e && echo ok   → ok
$ GIT_OPTIONAL_LOCKS=0 git diff 52e1567 HEAD -- docs/specs_faz4 | wc -c   → 0
$ shasum -a 256 docs/specs_faz4/SPEC_CEILING_PATH_V0.md   → 0798366047247c750a3cf6160e06bf7c0ff833628815d31ea1dd9dbe0ebfee5d (= specs.py, günlük satırları, MODELS.md)
```
52e1567 şartnameyi ve üç ekini ekler (335 + 49 + 155 + 174 satır); push kanıtı 18:32:22'de, altın koşu 19:02:36–19:02:44'te, commit 19:16:27'de. Şartname uygulamadan önce push edilmiş ve sonra değişmemiştir.

### 2.4 S_k gerçekten yeniden fit edilmemiş [ÖLÇTÜM]

Üç Faz 4 ledger'ının `S_1..S_10` sütunları, kaynak Faz 1B ledger'larının aynı fold satırlarıyla **metin olarak** 870/870 aynı (`ledger_compare.exact.S_str`); `survival_ledger_sha256` sütunu ve `specs.py`'deki sabitler Faz 1B `SHA256SUMS` ile aynı (`976b4dce…`, `90b61046…`, `c92ce859…`). Kod: `ceiling_path.read_source_ledger` sha'yı şartname sabitine karşı denetler, `fold_row` S'i `float(src["S_k"])` ile okur; fit yolu yok. Nihai dondurma yolunda seri modeli JSON'u INDEX sha'sıyla denetlenip gömülür (`load_survival_model`), `test_5` gömülü kopyanın sha'sını INDEX'le sınar.

### 2.5 Kod ↔ şartname uygunluğu [ÖLÇTÜM: dosya:satır]

| Konu | Şartname | Kod | Durum |
|---|---|---|---|
| §2 adım tablosu, U (aşağı adıma, adım limit seviyesinden), Lo, snap **HALF_UP** | §2, §12 | `predict_path.py:38-44, 73-101`; `_EXACT` 60 hane + Inexact tuzağı | uyumlu; 990/990, 424/424, 4 snap arzı (`test_1`, `test_2`; bağımsız betik aynı) |
| §2 ρ_h = C_h/P − 1, C_t/P ölçekleri Decimal'den bir kez float | §4 | `ratio`, `ratio_minus_one` (`:104-113`), `limit_path` (`:116-125`) | uyumlu; bit-eşit |
| §2 uyarı `IPO_PRICE_NOT_ON_TICK_GRID` | §2 | `predict:381-385` | uyumlu (`test_11`) |
| §3 hücreler: 99 arz, L = t < 10, baz P / kapanış(D_t), `session ≥ T → break`, (değer, ticker) artan | §3, §12 | `build_cells` (`:170-193`); `ceiling_path.path_units` baz fiyat `ipo_price_tl` (F4) | uyumlu; sayımlar birebir |
| §3 merdiven: kendi → diğer grup aynı m → m−1, m+1, … (iki grup); adım sonunda n ≥ N_MIN = 10 | §3, §12 | `ladder` (`:231-239`), `pool` (`:242-260`), `N_MIN = 10` | uyumlu; 870/870 `sources` birebir |
| §3 kırpma yalnız hedef m'nin sınırına; kendi hücresinde tetiklenmez | §3 | `pool:255-256` (bütün liste kırpılır; kesin sınırlarla kendi hücresinde no-op, `test_9` sınar) | uyumlu (F1) |
| §3 POST_BREAK_INSUFFICIENT: S ve P_L üretilir, getiri/p_up/kuantil üretilmez | §3 | `_horizon:299-306`, `fold_row:161-166` | uyumlu (backtest'te 0 fold) |
| §4 atomlar, ağırlık P(L=t)/n, kararlı sıralama, Q(q) = F ≥ q − 1e-12, return = Q(0.5), p_up kesin >, mean | §4, §12 | `mixture_atoms:265-279`, `summarize:282-296` | uyumlu; bit-eşit |
| §4 predict çıktı alanları; ret aynen geçer; sıfır model ret etmez | §4 | `predict:359-391` (fiyat yoksa etiketli ret: F3) | uyumlu; `test_11` |
| §7 koşullu: S_k/S_j, P(L=t\|L≥j), gözlenen kapanış ölçekleri (t ≤ j), `limit_path_mismatch`, durum 2 S'siz; RPS_j, Brier | §7 | `conditional_weights:396-407`, `conditional:437-466`, `conditional_after_break:469-493`, `conditional_rps/brier:410-423` | uyumlu (`test_7`: j = 0 kimliği, ağırlık toplamı, formüller) |
| §8 S_k kaynak ledger'dan; kesim = `prediction_date`; ledger sütunları listedeki sırayla | §8 | `read_source_ledger:129-138`, `fold_row:141-182`, `ledger_columns:115-126` (sıra denetimi `:180-181`) | uyumlu; başlık 169 sütun şartnamedeki sırayla |
| §8 günlük satırı (`survival_ledger_sha256`, `spec_document(_sha256)`, metrikler) | §8 | `backtest.py` (2d0c98e diff) `entry_extra`; günlükte 6 backtest + 1 `conditional_eval` satırı | uyumlu (`test_12`, `test_official_log_…`) |
| §8 nihai dondurma: hücreler 99 arz, kesim 2026-08-19, gömülü seri modeli, JSON alanları | §4, §8 | `fit_params:241-276` (`max_session_date ≤ 2026-08-19` denetimi `:249-250`) | uyumlu (`test_would_be_frozen_json_fields`; çalışma zamanı izi §2.2) |
| §9 kabul testleri 1–13 | §9 | `tests/test_faz4_ceiling_path.py`: test_1 … test_13, 13b, 6b + altın bayt eşitliği, günlük, dondurma kararı, scores.json değişmezliği, MODELS.md | var; 421/421 yeşil |
| §12 sözde kod | §12 | yukarıdaki fonksiyonlar birebir aynı akış | uyumlu |
| Stdlib predict yolu | §1 | `test_6b`: `predict_path` kapanışı {math, typing, decimal, dataclasses} + `.predict_hazard/.features/.survival`; alt süreçte numpy/sklearn yüklenmiyor | uyumlu |

**SPEC_DEVIATIONS F bölümü — davranış değiştiriyor mu?**

| # | Hüküm | Gerekçe |
|---|---|---|
| F1 kesin Decimal sınırlar | **KABUL, değer değiştirmez** | Benim bağımsız sürümüm de kesin sınır kullandı; bit-eşit. binary64 `0.9**m − 1` ile fark en çok 1 ulp olurdu (≪ 1e-9). |
| F2 `sources` boş hücreler dahil | **KABUL, raporlama** | Tahmin değerlerine girmez; §9-8 metniyle uyumlu. |
| F3 sıfır modelde fiyat yoksa etiketli ret | **KABUL** | Şartnamenin tanımlamadığı girdi durumu; çıplak exception yasağının doğal sonucu. Fiyatı olan her girdide davranış §4. |
| F4 PB varyantı limit yolu fiyatı `ipo_price_try`; hücre bazı kesin arz fiyatı | **KABUL** | H99'da 99/99 eşit (ölçtüm). Canlıda planlanan fiyat kesin fiyattan farklı olursa PB varyantının C yolu planlanan fiyata göredir; bu, modelin talep toplama öncesi tanımının doğal sonucu. Uygulama kartında "planlanan fiyat" notu önerilir (§6-5). |
| F5 60 hane + Inexact tuzağı | **KABUL, değer değiştirmez** | 28 haneli varsayılan bağlam aynı float'ları verdi. |
| F6 ledger sütunları, `cells_ipos_sha256` = katkı verenler, `contributors_sha256` | **KABUL** | Sütun listesi aynen; hash tanımı bağımsız hesapla 87/87 aynı. |
| F7 etiket kuralları kodda | **KABUL** | C8 ile aynı yaklaşım; etiketler bağımsız üç-yollu ayrımla tutarlı. |
| F8 `conditional_eval` günlük satırı | **KABUL** | Şartname §7 satırı ister; `model_id: null` doğru. |
| F9 `F3_MODELS` dondurma günü | **KABUL, dondurma koşulu** | Eklenmezse birincil kayıt seçimi ret kaydına düşebilir (`test_13b` bekçi). |
| F10–F12 | **KABUL** | Sayaç tanımı, kayıt yokluğu, sabit kimlik listeleri; değer değiştirmez. |

### 2.6 Testler [ÖLÇTÜM `ekler/pytest_out.txt`]

`PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q -p no:cacheprovider` → **421 passed in 242.86 s**, çıkış 0. (Faz 1B denetiminde 254; Faz 2A/2B/3/4 testleri eklendi.)

---

## 3. "Neden bu kadar iyi?" — tanı (model seçimine GİRMEZ) [ÖLÇTÜM `repro_stdout.txt` "Tanı"; `repro_output.json: diagnosis`]

**D5 (birincil), `ceiling_path_v0` − `base_train_median`, n = 85, toplam eşleşik fark −0.1158 (fark toplamı −9.85):**

| Kesit | n | ortalama fark | toplam fark | pay |
|---|---|---|---|---|
| S_5 < 0.5 | 48 | −0.1703 | −8.17 | %83 |
| S_5 ≥ 0.5 | 37 | −0.0452 | −1.67 | %17 |
| 2023 / 2024 / 2025 / 2026 | 7 / 33 / 17 / 28 | −0.097 / −0.125 / −0.125 / −0.104 | −0.68 / −4.14 / −2.12 / −2.91 | |

- Model tahmini = ρ_5 olan fold 37/85; bunların 22'sinde gerçekleşen de ρ_5 (AE = 0). AE = 0 sayısı: model 23, V1.5 0, medyan kuralı 0. AE kuantilleri (p10/30/50/70/90): model 0.000/0.025/0.145/0.285/0.509; V1.5 0.032/0.125/0.192/0.275/0.457; medyan kuralı 0.002/0.130/0.291/0.406/0.679.
- Sıfır modele karşı (özellik bilgisinin payı): −0.1033, n = 87; S_5 < 0.5 grubunda −0.157 (n = 48, toplam −7.52), S_5 ≥ 0.5 grubunda −0.038 (n = 39, toplam −1.46). Sıfır modelin kendisi medyan kuralına karşı yalnız −0.0101 [−0.0221, −0.0026] (38/85 fold'da tahmin = ρ_5, ayrım yok).
- En çok katkı veren 10 arz: AVPGY, KOTON, YIGIT, LILAK, BINBN, KOCMT, ARMGD, AHSGY, QUICK, AKFIS — hepsi L ≤ 3 ve S_5 ∈ [0.04, 0.28]; model tahmini −0.04 … +0.16, medyan kuralı **+0.36 … +0.61** (erken fold'larda eğitim medyanı ρ_5'e eşit: eğitim kümesi hemen hep tavan serisi), gerçekleşen −0.30 … +0.11; fark −0.40 … −0.53.
- V1.5'e karşı D5: −0.0360 [−0.0579, −0.0176], n = 85; V1.5'in hatası model gibi iki uçlu değil (AE = 0 yok), orta bölgede daha iyi (p30 0.125 ↔ 0.025 değil; p50 0.192 ↔ 0.145), uçlarda daha kötü.

**D10 (keşif):** toplam −0.1746 (fark toplamı −14.84). S_10 < 0.5: n = 75, −0.150 (−11.22, %76); S_10 ≥ 0.5: n = 10, −0.362 (−3.62, %24). Yıllara göre 2023 **−0.484** (n = 7), 2024 −0.175, 2025 −0.142, 2026 −0.117. En büyük dört katkı L = 10 arzlar (SVGYO, PATEK, ARTMS, ALVES: ρ_10 ≈ 1.58 = gerçekleşen, medyan kuralı 0.25–0.39; fark −1.20 … −1.33; toplamın %33'ü); geri kalanı L ≤ 1 arzlarda medyan kuralının +0.74 … +1.08 tahminine karşı modelin ≈ 0 tahmini. D10 kazancı D5'ten daha yoğunlaşmış ve 2023'e daha bağımlı [ÇIKARIM: kırılganlık D10'da daha yüksek; D10 zaten keşif hücresidir].

**Mekanizma (bir paragraf) [ÇIKARIM]:** R_5 iki rejimlidir: seri sürüyorsa getiri tam olarak ρ_5 ≈ +0.61 (mekanik, sıfır hata), kırıldıysa kırılma sonrası kütle −0.3 … +0.1 çevresindedir. Eğitim medyanı bu iki rejimin arasında (erken fold'larda ρ_5'in kendisi, sonra 0.36–0.49) durur ve iki rejime de uzaktır; her arzda 0.3 civarı hata verir. Karışım medyanı ise S_5'e göre rejim seçer: S_5 ≥ 0.5'te ρ_5 (22/37'de hata 0), S_5 < 0.5'te kırılma sonrası hücrelerin ölçeklenmiş medyanı (≈ 0). Rejimi seçtiren bilgi `ceiling_hazard_v0`'ın S_5 ayrımıdır (f3 ağırlıklı; Faz 1B'de bağımsız üretildi ve RPS'te beklentiyi zaten aşmıştı); sıfır model aynı mekaniği S ayrımı olmadan kullandığından yalnız −0.010 kazanır. Yani kazanç = (Faz 1B'de doğrulanmış S ayrımı) × (MAE'nin iki rejimli sonuçta medyan eşlemesini ödüllendirmesi). Kırılma sonrası bileşenin tasarım seçimleri (grup, N_MIN, havuzlama) kazancın kaynağı değil: §4 varyantları −0.112 … −0.122 arasında.

**§6 beklentim neden düşük kaldı; 1B ile ortak neden var mı? [ÇIKARIM]** Beklentiyi (−0.090 … −0.020) V1.5'in D5 MAE'sine (0.222) ve medyan kuralının 0.306'sına çapalayıp karışım medyanının "0.2–0.6 arasında ayrışan" bir uzlaşma tahmini olacağını varsaydım; iki şeyi küçümsedim: (i) sonucun ne kadar keskin iki rejimli olduğunu ve medyan kuralının erken fold'larda fiilen "her zaman tavan" olduğunu (medyan kuralı D5'te 0.300 değil, 2023–24 fold'larında ≈ 0.61 tahmin ediyor), (ii) S_5 ayrımının gücünü. (ii) Faz 1B'deki tavan modeli beklentisinin düşük kalmasıyla aynı köktür: şartname, tasarımı gereği özellik–sonuç ilişkisine bakmadan yazıldı ve sayılar daha zayıf modellerin (V1.5 D1 Brier, V1.5 D5 MAE) hücrelerine çapalandı; f3'ün L ile marjinal ilişkisi (Spearman 0.55) iki kez de tahmin edilenden güçlü çıktı. Ortak neden budur; rejim tesadüfü değildir (dört yılda da −0.10 … −0.13). Bu bir şartname kalibrasyon hatasıdır, kod ya da veri hatası değil.

---

## 4. Duyarlılık (bilgi amaçlı; bunlar MODEL DEĞİLDİR, şartname değişmez) [ÖLÇTÜM `ekler/sensitivity_runs.jsonl`, `sens_*_fold_ledger.csv`]

Yalnız birincil hücre (`ceiling_path_v0` D5 MAE − `base_train_median`, aynı S_k, aynı fold'lar, C7 aralığı):

| Varyant (`model_id` soneki) | Değişiklik | fark | %95 aralık | n | model MAE | POST_BREAK_INSUFFICIENT fold |
|---|---|---|---|---|---|---|
| `__sens_v0_ref` (kontrol) | yok (şartname v0) | −0.1158 | [−0.1611, −0.0738] | 85 | 0.1842 | 0 |
| `__sens_nmin5` | (i) N_MIN = 5 | −0.1146 | [−0.1588, −0.0733] | 85 | 0.1854 | 0 |
| `__sens_nmin20` | (ii) N_MIN = 20 | −0.1118 | [−0.1576, −0.0695] | 85 | 0.1883 | 0 |
| `__sens_single_group` | (iii) Z/B ayrımı yok, tek grup G(m) | −0.1123 | [−0.1577, −0.0707] | 85 | 0.1878 | 0 |
| `__sens_nearest_only` | (iv) havuzlama yok; küçük hücre → aynı gruptaki en yakın yeterli m (yoksa öteki grubunki) | −0.1220 | [−0.1715, −0.0765] | 80 | 0.1748 | 7 (EKOS, AGROT, SKYMD, CATES, BEGYO, KBORU, SURGY) |

Okuma: fark −0.112 … −0.122, aralık üst ucu −0.070 … −0.077; hiçbir varyant hükmü ("aralık 0'ın altında") ya da "çok iyi" tetiklemesini değiştirmiyor. Sonuç, tasarıma maruz seçimlere (grup, N_MIN, havuzlama) duyarsızdır; havuzlama merdiveninin işlevi erken fold'ları skorlanabilir kılmaktır (havuzsuz varyantta 7 fold reddedilir). Günlük satırları `experiments/log.jsonl` biçimindedir (`kind: sensitivity`, `is_model: false`, `ledger_file`/`ledger_sha256`, birincil hücre metrikleri); dondurma görevi bunları deney günlüğüne ekleyebilir.

---

## 5. Uygulama gösterimi (bir cümle)

"Geçmiş veri testi (retrospektif, tasarıma maruz)" panelinde birincil hücre şöyle gösterilmeli: **"D5 getiri MAE, medyan kuralına karşı −0.116 [−0.161, −0.074], n = 85 — geçmiş veride geçiyor; tasarıma maruz (hücre tanımı H99 görüldükten sonra seçildi); bağımsız yeniden üretim 2026-09-22 |Δ| = 0; tasarım varyantlarında −0.112…−0.122; canlı sicil n = 0, hüküm yok"** — "geçiyor" sözcüğü yalnız backtest panelinde ve bu etiketle; canlı panelde n ≥ 30 olana kadar hüküm yazılmaz.

---

## 6. Engelleyici olmayan bulgular ve öneriler

1. **Altın ledger'ların kod hash'i commit edilen kodla aynı değil.** [ÖLÇTÜM] `macos_golden_faz4/MANIFEST.json` ve altı Faz 4 günlük satırı `borsai_source_sha256 = f96dbd02…`, `git_commit = 50c62da`, `borsai_dirty = true`; koşullu keşif satırı `f65e714c…`; HEAD'de (`borsai/` 2d0c98e'den beri değişmedi) `code_version()` → `51a35452…`. Yani altın koşudan sonra, commit'ten önce `borsai/*.py` değişti (rapor/test düzeltmeleri olabilir). Davranış eşitliği `test_backtest_byte_identical_to_faz4_golden` ile HEAD'de kanıtlı (421 yeşil) ve benim bağımsız üretimim de bit-eşit; bu yüzden engelleyici değil. Ama Faz 1B'deki "JSON'lar tam olarak commit edilen kodla üretildi" bağı burada altın ledger'lar için kurulamıyor. **Öneri (dondurma görevine):** model JSON'ları ve (gerekirse) altın ledger'lar temiz ağaçta, commit edilecek kodla üretilsin; `borsai_dirty = false` ve `borsai_source_sha256` = commit'teki ağaç olsun; kabul testi olarak `code_version()["borsai_source_sha256"] == JSON["code_version"]["borsai_source_sha256"]` eklensin.
2. **`registry.F3_MODELS` (F9) ve SPEC_SCORING §6 listesi.** `ceiling_path_v0` f3'süz reddeder; dondurulduğu gün `F3_MODELS`'e girmeli (Opus'un F9 notu ve `test_13b` bekçisi). SPEC_SCORING §6 metni dört modeli adıyla sayar; `docs/specs/` değişmeyeceğine göre SPEC_DEVIATIONS'a bir satırla ("f3 isteyen modeller listesi = kodda `F3_MODELS`; `ceiling_path_v0` dahil") yazılsın.
3. **Push kanıtı.** 2d0c98e ve 0b67f5d için push kanıtı yok (yalnız 52e1567'ye kadar). Dondurma commit'i için kanıt alınmadan hiçbir arz bu modeller için prospektif olmaz (SPEC_SCORING §5). Dondurma görevi bunu ilk yeni arzın D_1'inden önce yapmalı.
4. **Kırpma yoğunluğu (bilgi).** Havuzda kırpılan gözlemlerin hepsi hedef m = 1 hücrelerinde (1050 olay, üç koşu × 87 fold × (Z,1)/(B,1) çağrıları; en büyük değişim 0.0895: m = 2 hücresinden ödünç −0.19'a kadar değerler −0.1'e çekiliyor). Şartnameye uygun ve yalnız D1–D2 atomlarını etkiliyor; ama ledger'daki `pooled_cells` JSON'u `n_clipped`'i yazmıyor (`PooledCell.n_clipped` var, `as_json` dışarıda bırakıyor). **Öneri:** dondurma görevinde altın ledger yeniden üretilecekse `n_clipped` alanı eklensin (altın bayt değişir; şimdi değil).
5. **C_h dize gösterimi (kozmetik).** T planı ledger'larında `C_h` "7.70" gibi iki haneli, PB planında girdi "76.60" olduğundan aynı; sayısal olarak sorun yok. Uygulama C'yi Decimal olarak okumalı, dize karşılaştırması yapmamalı. PB varyantı kartında limit yolunun **planlanan** fiyata göre olduğu yazılsın (F4).
6. **D10 kazancı yoğunlaşmış** (2023'ün 7 fold'u −0.48; dört L = 10 arz toplamın %33'ü). D10 keşif hücresidir; MODELS.md'de D10 satırlarının yanına "kazanç L = 10 arzlarında yoğunlaşıyor" dipnotu önerilir; hüküm değişmez.
7. **`pb_ceiling_path_v0` spec'inde `features = ["pb1", "pb2"]`.** Tavan yolu modelinin kendi özelliği yoktur; alan gömülü seri modelininkini yansıtıyor. Kart "özellik: gömülü `pb_ceiling_v0`'ınki" desin (kozmetik).
8. **Rapor tarafı şartname metnini ayrıştırıyor** (`report_faz4.expectation_rows` markdown tablosunu okur). Test var (`test_expectation_rows_are_read_verbatim_from_spec`); şartname dosyası değişmeyeceği için risk yok, not olarak kalır.

## 7. Açık konular (proje sahibine)

1. Dondurma görevi: üç modeli `fit_params` yoluyla (99 arz, kesim 2026-08-19, gömülü seri modelleri) dondurup `INDEX.json`'a sona eklemek; `F3_MODELS` güncellemek; temiz ağaçta üretip commit + push kanıtı (bulgu 1–3). Bu denetim o görevin ön koşulunu (bağımsız yeniden üretim |Δ| ≤ 1e-9) **sağlar**.
2. Duyarlılık satırlarının (`ekler/sensitivity_runs.jsonl`, 5 satır) `experiments/log.jsonl`'a eklenip eklenmeyeceği (görev metni "dondurma görevi ekleyecek" diyor; `kind: sensitivity` satırları `tests/test_experiment_log.py`'nin `kind` denetimine takılır — test bu türü de kabul edecek biçimde genişletilmeli).
3. §11 soru 1 (HALF_UP) proje sahibi kararı olarak uygulanmış; canlıda ilk çelişen örnek `limit_path_mismatch` ile görünür. Karar metni SPEC_DEVIATIONS'ta yok; bir satır önerilir.
4. Bu klasördeki altı büyük CSV (yeniden üretilen 3 ledger + 5 duyarlılık ledger'ı, toplam ≈ 5 MB) repoda kalsın mı? Kanıt değeri var (bağımsız üretimin ham çıktısı); istenirse yalnız sha'ları (`SHA256SUMS`) tutulup dosyalar silinebilir.

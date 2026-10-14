# BORSAI_FAZ7_FABLE_V1_REPRO_AUDIT_20260926 — `ceiling_hazard_v1` ailesinin bağımsız yeniden üretimi ve uygunluk denetimi

Görev: `docs/prompts/FAZ7_FABLE_V1_REPRO_AUDIT.md`. Denetlenen: Opus'un uygulaması (A `2a21a96`, B `70b67d1`, R `f5d7609`; görev `docs/prompts/FAZ7_HAZARD_V1_IMPL.md`). Bağlayıcı metinler: `docs/specs_faz7/SPEC_HAZARD_V1.md` (`6a16c16`, sha256 `25229cea8f6f…`, push kanıtı 2026-09-25T18:09:45Z) ve `docs/specs_faz7/KARARLAR.md` (K1–K5); SPEC_DEVIATIONS J10 ve J16 proje sahibi kararı olarak şartname sayıldı. Denetim HEAD `f5d7609`'da başladı; koşunun ortasında paralel oturumun `4e081d8` (BORSAI_FAZ7_PROSPECTUS) commit'i geldi, o commit `borsai/`, `data/`, `scores/`, `models/`, `app/`, altın dizinleri, `docs/MODELS.md` ve `experiments/log.jsonl`'ı değiştirmedi (`git diff --stat f5d7609 4e081d8 -- …` boş). Tam test o commit'ten sonra koştu.

Yöntem: yeniden üretim betiği `ekler/repro_hazard_v1.py` (stdlib + numpy; `borsai` import satırı yok, betik başında ve sonunda `sys.modules` denetimi: `borsai_in_sys_modules = False`) şartnameden sıfırdan kodlandı; Opus'un kodu yalnız okundu ve (madde 2-vi, mutasyonlar, canlı rejim değeri için) ayrı süreçlerde ÇALIŞTIRILDI, yeniden üretimde kullanılmadı. İşaretler: **[ÖLÇTÜM]** dosyadan/komuttan; **[ÇIKARIM]** yorum. Hijyen: kasa (SEALED) kümesi yalnız `registry/oot/records/` kayıtlarındaki `vault` alanından bellekte kuruldu; hiçbir kasa üyesinin girdi/sonuç dosyası okunmadı (dosya izi: 0); hiçbir çıktıya kasa kodu yazılmadı (bütün ek dosyalar tarandı: 0 eşleşme). `docs/faz6/dogrulama/EXPOSURE.md` §3 ve karantina dizini okunmadı. Ağ: yalnız `veriportali.tuik.gov.tr` (tablo indirme + 10 bülten API kaydı + 4 JS parçası, API yolunu bulmak için). git: yalnız okuma, `GIT_OPTIONAL_LOCKS=0`; push/tag/amend yok. Rapor Türkçe; `thb`/`thm` + tarih kalıbı yazılmadı.

## 0. Hüküm

| model_id | Hüküm | Dayanak |
|---|---|---|
| `ceiling_hazard_v1_clip` | **FREEZE_OK** | 87 fold ledger'ı, nihai fit önizlemesi ve bütün MODELS.md hücreleri bağımsız betikle eşleşti (λ birebir 87/87; sayısal maks\|Δ\| 4.3e-11); sızıntı yok; kod §3.1/§4/§5 lafzına uygun. Ön koşul: bulgu B1'in düzeltmesi (ledger `test_clipped` sütunu; aynı model_id) dondurma görevinin kod commit'ine girmeli. |
| `ceiling_hazard_v1_real` | **FREEZE_OK** | 87/87 birebir; maks\|Δ\| 3.6e-11; TÜFE dosyası, ay kuralı, PIT bekçisi ve f1r aritmetiği bağımsız doğrulandı; D1 iç tutarlılığı bağımsız kurulumda bit-eşit. Etiket "bozuyor" hükmü etkilemez (§6.4). Aynı ön koşul (B1). |
| `ceiling_hazard_v1_pooled` | **FREEZE_OK** | 97/97 birebir; maks\|Δ\| 3.1e-15; havuz planı, J10 dışlaması, rejim terimi (r = 0 test/canlı), KM kuralları ve D2 iç tutarlılığı bağımsız doğrulandı. Etiket "bozuyor" hükmü etkilemez. Aynı ön koşul (B1) + J10'un davranışının belgelenmesi (B4; kod değişikliği istemez). |
| `ceiling_hazard_v1_pooled@INF` | **FREEZE_OK** | 97/97 birebir; maks\|Δ\| 1.1e-11; (γ, δ) Newton çözümü ve önizleme (maks\|Δ\| 4.4e-16) eşleşti. |

Hükümler yalnız uygulamanın şartnameye uygunluğuna dayanır (görev kuralı); etiketler (clip "tolerans içinde", real ve pooled "bozuyor") hükme girmez ve §6.4 gereği üç aday da dondurulur. KRİTİK bulgu yok. ÖNEMLİ bulgular (B1–B4) dondurmayı engellemez; ikisi (B2, B3) test eksiği, biri (B1) betimleyici bir sütun/sayı hatası, biri (B4) proje sahibi kararının belgelenmemiş davranışıdır. Hepsi "kodu/testi şartnameye uydurmak = aynı model_id" sınıfındadır; hiçbiri şartname değişikliği istemez.

## 1. Yeniden üretim (K1)

Betik: `ekler/repro_hazard_v1.py` → `ekler/repro_stdout.txt`, `ekler/repro_output.json`, `ekler/repro_ledgers/` (kompakt; tam ledger'lar `/tmp` altında üretildi, silindi). Toplam 447 s (önbellekli ikinci koşu; ilk tam koşu ~11 dk). Karşılaştırma eşiği |Δ| ≤ 1e-9; kimlik/metin sütunları birebir.

| Adım | Karşılaştırılan | Sonuç | maks \|Δ\| |
|---|---|---|---|
| 1a TÜFE | İndirilen xls (`/tmp`) sha256 = PROVENANCE pini `6f7ee8e4…ff86`; repodaki xls aynı | eşit | — |
| 1a TÜFE | Kendi OLE2/BIFF8 okuyucumla xls düzeyleri ↔ `tufe_genel_2025_100.csv` `index` (binary64 eşitliği) | 82/82 eşit (2019-11…2026-08, kesintisiz) | 0 |
| 1a TÜFE | 2025 ortalaması (CSV ve xls) | 100.000000; \|−100\| ≤ 0.05 | 0 |
| 1a TÜFE | `release_date` izleyen ayın ≥ 3'ü; CSV ↔ bülten listesi (`tufe_bultenleri.csv`) tarih ve sayı | 82/82 | — |
| 1a TÜFE | 10 örnek ay (`random.Random(20260926).sample`): TÜİK bülten API (`/api/tr/press/<id>`, `date`, `number`, `period`) ↔ dosya | 10/10 (2020-01, 2020-03, 2020-04 (04.05), 2020-08, 2021-01, 2021-10, 2022-04 (05.05), 2023-10, 2025-03, 2026-02) | — |
| 1a TÜFE | Ay kuralı T − 2 (kendi `month_for`): v2'nin 170 satırının `tufe_month`/`tufe_index`; `release_date < T` | 170/170; eğitim 11 118/11 118 PP-arz, test 97/97 | — |
| 1b v2 | H99 99 satırı: `training_table.csv` ile 31 paylaşılan sütun hücre-eşit ve satır öneki bayt-eşit | 99/99, 99/99 | — |
| 1b v2 | Açık 71 satır: S2 kayıtlarının `model_inputs` + `data/outcomes_oot/<T>.csv` (L: ceiling_close'u Decimal(close) == Decimal(üst limit) ile yeniden hesapladım) ↔ v2 (f1, f2, f3, filtre modu, `alloc_regime`, ilk işlem günü, L, D1..D10 kapanışları, TÜFE ayı/endeksi, ipo_size_tl) | 23 sütun/denetimde 0 uyuşmazlık | — |
| 1b v2 | L dağılımı açık 71; PP H99/açık/havuz; grup olay/risk | {0:9,1:11,2:5,3:4,4:3,5:8,6:5,7:6,8:5,9:6,10:9}; 506/83, 374/59, 880/142; (25,165),(31,258),(86,457) | — |
| 1b rejim | `alloc_regime(talep toplama başlangıcı)` (J2) ↔ kohort etiketi: açık 71/71; ilk işlem günü okuması etiketten 135 üyede 4'ünde ayrışır, ikili r 135/135 aynı (yalnız kohort dosyası, sayı) | tuttu | — |
| 1c plan | PLAN_CEILING 87 skorlanabilir fold, v0 ile aynı ticker ve sıra; PLAN_POOLED 97, 87'yi içerir; yakın dönem 78 fold / 22 ay, iki planda aynı; J10: 44 fold'da 3 birim dışlandı, mod {UNFILTERED 44, NOT_SPECIFIED 53} | tuttu | — |
| 1c ledger | `ceiling_hazard_v1_clip` (87): status, λ, columns, `test_clipped_features`, kimlik sha'ları, training_n_*, realized_* birebir 87/87; γ, β, hazard, S, P_close, reclose, λ skor tablosu | birebir | **4.3e-11** (gamma_g1); skor tablosu 3.5e-13 |
| 1c ledger | `ceiling_hazard_v1_real` (87) | birebir 87/87 | **3.6e-11**; skor 4.9e-13 |
| 1c ledger | `ceiling_hazard_v1_pooled` (97; + `training_n_oot_open`, `training_n_filter_excluded`, `training_filter_excluded_sha256`, `test_tufe_*`, `test_r_pre_equal`, δ) | birebir 97/97 | **3.1e-15**; skor 2.2e-13 |
| 1c ledger | `ceiling_hazard_v1_pooled@INF` (97) | birebir 97/97 | **1.1e-11** |
| 1c ledger | `base_km_expanding__pooled`, `base_km_last10__pooled` (97) | birebir; hazard/S/P_close/reclose | **0** |
| 1c ledger | Altın dosya sha256 = MANIFEST = SHA256SUMS (6 ledger) | 6/6 | — |
| 1d önizleme | `v1_clip`: λ 10 birebir; 97/506/83; γ, β, kırpma sınırları, μ/σ, skor tablosu, reclose sayıları, feature_ranges, kohort/dışlama | birebir | 3.6e-15 |
| 1d önizleme | `v1_real` | birebir | 3.6e-15 |
| 1d önizleme | `v1_pooled`: λ 10; 165/880/142 (H99 97, açık 68); δ +0.9111 | birebir | 1.1e-15 |
| 1d önizleme | `v1_pooled@INF`: λ INF; δ +0.2277 | birebir | 4.4e-16 |
| 1e hücreler | 51 hücre (4 birincil, 8 ikincil RPS, 16 Brier, 3 merdiven, 8 keşif, 12 havuz-KM) benim ledger'ımdan ↔ Opus ledger'ından aynı hesap (C7 aralık, tam hassasiyet); n/ay/kazanç/kayıp/eşit | 51/51 sayımlar aynı | **3.2e-13** |
| 1e hücreler | Günlükteki `near_era` (4 model; tam hassasiyet; etiket) | 4/4 etiket aynı | ≤ 8.6e-14 |
| 1e MODELS.md | Faz 7 bölümünün 52 basılı hücresi (4 hane, aynı yuvarlama; n, ay, sayımlar, etiket, §6.2 konumu dahil) | 52/52 | ≤ 5e-5 (basılı hassasiyet) |
| 1e v0 | Faz 1B v0 ledger'ı sha `976b4dcea981…` pinli; 87-fold ortalama RPS | 0.1503154629 | — |

Birincil hücreler (benim ledger'ımdan; MODELS.md ile aynı): `v1_clip` −0.0011 [−0.0066, +0.0049] n = 78 (22 ay), 46/32/0 → **tolerans içinde**, §6.2 aralık içinde; `v1_real` +0.0104 [+0.0028, +0.0183], 24/54/0 → **bozuyor**, üstünde; `v1_pooled` +0.0289 [+0.0089, +0.0518], 25/53/0 → **bozuyor**, üstünde; kural satırı `@INF` +0.0547 [+0.0287, +0.0806]. Merdiven: kırpma −0.0011 [−0.0066, +0.0049]; deflasyon +0.0115 [+0.0045, +0.0190]; havuz + rejim +0.0185 [+0.0005, +0.0389]. `v1_pooled` − KM −0.0253 [−0.0386, −0.0099] (§6.2 aralık içinde).

D1/D2 (IMPL_RAPOR §8) bağımsız kurulumda: real'in fold hesabı f1r := f1 ile clip'e (λ ve S bit-eşit, maks|ΔS| 0); havuz planı yalnız H99 satırları + rejimsiz ile real'e (plan sha'ları ve S bit-eşit) → merdiven basamaklarının farkı yalnız deflatörden ve açık küme + rejim teriminden geliyor.

Tutmayan şey yok; kök neden aranmadı. Sayısal farkların en büyüğü (4e-11, clip/real γ) benim Newton'umun durma kriterinden (∇ ≤ 1e-11) ve ön işlemenin float/Decimal farkından geliyor; bit-eşitlik beklenmiyordu (§7.1: |Δ| ≤ 1e-9).

## 2. Sızıntı ve sıra kanıtları (K2)

| Madde | Komut / kaynak | Çıktı |
|---|---|---|
| (i) test arzı | `repro_hazard_v1.py` §2(i): 3 fold'da (clip BORSK 2024-02-15, clip CGCAM 2024-12-17, pooled VSNMD 2025-02-11) test arzının f1/f1r/f2/f3/L/kapanışları değiştirilip fit yeniden kuruldu | λ, γ, β, kırpma sınırları, μ/σ, reclose, iç CV skorları **bit-eşit** 3/3; ayrıca plan kurulumu test arzının eğitimde olmadığını her fold'da assert eder (87 + 97) |
| (ii) eğitim kesimi | betik, her fold: max(eğitim seans tarihi) < T; her PP satırı seans < T | ceiling 87/87, pooled 97/97; kod tarafı: `plan_ceiling_folds`/`plan_pooled_folds` "gelecek sızıntısı" assert'i ve `test_fold_plans_same_tickers_near_era_78_and_no_leakage` |
| (iii) havuz planı | betik: açık küme PP satırları seans < T | 35 686/35 686 satır; açık üyesi sansürlenen fold 2 (T = 2023-09-22 ve 2023-09-25; açık son seans 2023-10-04); J10: dışlanan her birim moda açıkça zıt (44 fold × 3 birim; hepsi açık kümenin FILTERED 3 üyesi); dışlamalı fold'lar 2023-09-22…2025-01-17 arasında, 25'i yakın dönemde (B4) |
| (iv) rejim | betik: test r = 0 assert (97/97, ledger `test_r_pre_equal` 0.0); eğitim r kohort etiketinden (açık f3'lü 68: r=1 53, r=0 15; H99 0); `ekler/vault_check.py` alt süreçte Opus'un stdlib tahmini önizleme JSON'uyla | canlı (anahtar yok): `regime_value_used = 0`, `LIVE_VALUE`; `alloc_regime` = PRE/THRESH → 1, EQUAL → 0 (S canlıyla aynı), bilinmeyen → `REGIME_UNKNOWN`; `predict_hazard` numpy/scipy import etmiyor |
| (v) kasa | `ekler/vault_check.py` (SEALED kümesi kayıtlardan, 64 = kohort dosyası) → `ekler/vault_check_out.txt` | `data/` 177 dosya: kasa kodu geçen 1 (J18 istisnası: `data/outcomes/COMPLETENESS.csv`, kohort penceresi dışı 1 satır, pencere içi 0) + H99 PB kanıt dosyasında bilinen unvan-sözcüğü istisnası (Faz 6 bekçisinde tanımlı); `macos_golden_faz7/` 11 dosya 0; `docs/MODELS.md` 0; `experiments/log.jsonl` 0; `docs/faz7/` (prospectus hariç) 45 dosya 0; `docs/SPEC_DEVIATIONS.md` 0; `docs/fable_faz7_audit/` 0; v2'de açık kod 71/71, kasa 0 |
| (vi) sonuç dosyaları | `ekler/runtime_file_trace.py` (Opus'un `run_backtest_v1` × 4, workers=1, geçici günlük; `final_fit_v1` pooled; `open`/`io.open`/`os.open` sarmalı) → `ekler/runtime_file_trace_out.txt/json` | okunan sonuç dosyaları: `data/outcomes_oot/` **açık 71, kasa 0** (yalnız `load_dataset_v2`'de); `registry/oot/inputs/` 71 (girdi; kasa 0); H99 SESSIONS; **`data/outcomes/`, `data/raw/bist/`, `scores/`, `registry/` canlı kayıtları okunmadı (0)**; repoya yazma 0; in-process ledger'lar altınla bayt-eşit 4/4 (workers sayısından bağımsız) |
| sıra 1 | push kanıtı `registry/push_proofs/6a16c16…json` `created_at` 2026-09-25T18:09:45Z (GitHub status) < A `2a21a96` 2026-09-26T00:10:01Z | EVET |
| sıra 2 | `git diff 6a16c16 f5d7609 -- docs/specs_faz7/SPEC_HAZARD_V1.md` | 0 bayt; sha256 6a16c16 = HEAD `25229cea…`; KARARLAR tek commit (2a21a96), sonra değişmedi |
| sıra 3 | `git ls-tree 2a21a96 -- tests/reference/macos_golden_faz7` 0 dosya; `git show 2a21a96:docs/MODELS.md \| grep -c "Faz 7"` 0; `git show 2a21a96:experiments/log.jsonl \| grep -c faz7_golden` 0 | A'da sonuç yok; B (`70b67d1`) altın dizin + 4 günlük satırı + MODELS.md +135 |
| sıra 4 | `git diff 2a21a96 f5d7609 -- borsai data` | 0 bayt (kurallar ve eşikler sonuçtan sonra değişmedi); günlük satırları ve MANIFEST `git_commit = 2a21a96`, `borsai_dirty = false` |
| sıra 5 | T2: `gen_golden --check` {"checked": 25, "different": []}; `git diff --stat 6a16c16 f5d7609 -- macos_golden{,_faz1b,_faz4,_faz5} app/parity/golden` yalnız `MANIFEST.json` pin satırı (`predict_hazard.py` `a1523ac8…` → `6ceeeb46…`); v0/@INF/PB tavan ledger sha'ları pinlerle aynı | tuttu |
| sıra 6 | `git merge-base --is-ancestor 77b54f7 2a21a96` rc 0; tersi rc 1 | açık küme sonuçları v1 kodundan önce → v1 için OOT_RETRO (§7.2) |

Ayrıntı: `ekler/sira_kanitlari.txt` (üretici `ekler/sira_kanitlari.sh`).

## 3. Kurallar ↔ şartname, kod ↔ şartname

**`OPERATIONAL_RULES_FAZ7` (report_faz7.py) ve `near_era_label` (backtest.py):** §5.1 birincil hücre tanımı (v1 − v0, RPS, ilk işlem ≥ 2024-01-01, v0 altın ledger'ı sha `976b4dcea981…` ticker eşleşmesi) aynen; karar kuralı (alt > 0 → bozuyor; üst ≤ +0.010 → tolerans içinde; diğer → belirsiz; öncelik "bozuyor") aynen, ek "alt = 0 dışlamaz" §11-9 ile tutarlı; aralık C7 (ay blokları, 4000, `random.Random(20260921)`, 100/3899) aynen; RPS/Brier kırpmasız SPEC_SCORING §7 ile tutarlı. §5.4 merdiven: yalnız "… payı: fark [aralık]" dili, hüküm sözcüğü yok (MODELS.md satırları denetlendi). §6.2 tablosu şartname dosyasından aynen okunuyor (test `test_expectation_62_parsed_verbatim_and_position_rule`); T6 konum kuralı (kapalı aralık) uygulanmış. Uymayan satır: yok. Eksik belgelenme: ikincil Brier k ∈ {1, 3, 5, 10} hücrelerinin karşılaştırıcısı şartnamede adlandırılmamış (§5.1 "k ∈ {1, 3, 5, 10} Brier"); kod v0'ı seçiyor — makul, ama SPEC_DEVIATIONS J'de satırı yok (B5).

**Kod ↔ şartname:**
- §3.1 kırpma: `Recipe.winsor` üç sütun, Type-7 kesin Fraction, ham değerde (f1/f1r log öncesi), tahminde aynı sınırlar; `FEATURE_CLIPPED_TO_TRAINING_P05_P95` (feature, value, used) — stdlib tahminde `clipped` = herhangi bir sütun ✓. **Backtest ledger'ında `test_clipped` = yalnız f3** (`hazard.TrainingResult.predict`: `clipped = bool(t["f3_winsorized"])`) ✗ → B1.
- §3.2 f1r: `real_size` Decimal 60 hane, `size_TL` tek tanım (`compute_features`), ay kuralı `month_for`, `release_date < T` bekçisi, önek pini (J4) ✓; §11-5 k-katı değişmezliği testli ✓.
- §3.3 r: ikili, cezasız, z-skorlanmaz, pseudo-satırda 0, H99'da assert 0, canlıda `live_value` 0 ✓; λ = INF'te (γ, δ) Newton ✓ (§11-6 gerçek veride testli; benim @INF önizlemem 4e-16). `alloc_regime` günü: şartname lafzı ilk işlem günü, uygulama talep toplama başlangıcı (J2) — r 135/135 aynı [ÖLÇTÜM], tahmine etkisiz.
- §3.4 v2: 170 satır, sıra, kaynaklar, SESSIONS iki kaynaktan, kasa satırı 0 ✓; ek sütunlar (J19) zararsız.
- §4 tasarım matrisi [G | R | Z], pseudo 6 satır, Newton başlangıcı, A2 yarılama toleransı, iç CV'de ön işleme yeniden kurulur ✓; ceza yalnız β'da (mutasyon d1/d2 kırmızı).
- §5.1 planlar ve §11-7 fold kümeleri ✓ (benim planım birebir).
- §8: bu görevde `freeze.py`, `scoring.py`, `app/` Rust yok (T1) — dondurma görevine kalıyor (§10 notları).
- §9 retler: `TUFE_MISSING` (ay `reason`'da ve `TufeRefusal.month`'ta), `TUFE_NOT_PIT`, `TUFE_FILE_MISMATCH`, `REGIME_UNKNOWN` — yazım şartnamenin `REFUSED_TUFE_MISSING:<YYYY-MM>` biçiminden farklı, mevcut `F3_MISSING` kalıbıyla tutarlı (J5) ✓; kırpma ve aralık dışı uyarıları ✓; canlı r `regime_value_used: 0` ✓.
- §12 sözde kod: λ seçimi (eşitlikte büyük), etiket, η sırası (γ + δ·r) + β·z ✓.
- §11 kabul testleri: 1–11, 14, 15 A/B testlerinde; 12, 13 dondurma/skorlama görevlerine ait (kapsam dışı).

## 4. SPEC_DEVIATIONS J1–J22 hükümleri (K4)

| # | Davranış değiştiriyor mu | Lafza aykırı mı | Hüküm |
|---|---|---|---|
| J1 (yerleşim) | hayır | hayır (T1 kapsamı) | kabul |
| J2 (rejim günü = talep toplama başlangıcı) | hayır: r 135/135 aynı [ÖLÇTÜM]; etiket 4 üyede farklı | evet, lafız `alloc_regime(first_trading_date)`; I8 ile tutarlı | kabul; §11-1 "135/135 eşit" şartı bu okumada tutuyor, öbüründe tutmazdı |
| J3 (TÜFE yayım tarihi/kaynak) | hayır | hayır | kabul; 82 bülten + 10 örnek API ile doğrulandı |
| J4 (önek pini) | hayır | §9 "dosya sha" lafzını ay ekleme cümlesiyle bağdaştırır | kabul (mutasyon n kırmızı) |
| J5 (ret kodu yazımı; predict saf) | hayır | biçim farkı | kabul |
| J6 (canlı/OOT ayrımı anahtarla) | hayır | hayır | kabul; risk notu B7 (anahtarı unutan OOT kaydı sessizce r = 0) |
| J7 (f1r aritmetiği, Decimal 60) | hayır | hayır | kabul (benim Decimal 60 hesabım hücre hücre eşit) |
| J8 (`Recipe.log`) | hayır (eski tarifler bayt-eşit) | hayır | kabul |
| J9 (cezasız sütunlar, INF Newton) | hayır | hayır | kabul |
| **J10** (f3 filtre dışlaması) | **evet**: 44 fold'da 3 açık üye eğitim dışı; yakın dönem hücresine etkisi +0.0289 → +0.0279 (J10 kapalı), etiket aynı | SPEC_HAZARD_V1 §5.1 "bütün kişi-dönem satırları" ve §2 n = 165 lafzına aykırı; SPEC_CEILING_V0 §4/§7 lafzıyla gerekçeli; proje sahibi kararı | kabul (şartname sayılır); davranışı monoton değil ve nihai fit'te dışlama yok → B4 belgelenme |
| J11 (havuz planı sütunları) | hayır | hayır | kabul |
| J12 (havuz KM kuralları aynı günlük satırında) | hayır | §5.1 "ayrı ledger satırı" lafzını sha ile karşılar | kabul |
| J13 (birincil hücre eşleşme) | hayır | hayır | kabul |
| J14 (T6 konum kuralı) | hayır | görev kararı | kabul |
| J15 (`spec_sha256` anlamı) | hayır | C6/H15 kalıbı | kabul |
| **J16** (varyant sayacı istisnası, 4 test) | testi gevşetmez: yalnız `scores.json` 8e3a623 ile bayt-eşitken ve fark **tam** `faz7_variants` (H99 sürümünde 2) kadar | H22 kalıbı; proje sahibi kararı | kabul |
| J17 (Faz 7 bölümünün yeri) | hayır | hayır | kabul |
| J18 (COMPLETENESS istisnası, sayı pinli) | hayır | bekçi güçlendirildi | kabul; maruziyet notu doğru |
| J19 (v2 ek sütunlar) | hayır | hayır | kabul |
| J20 (`final_fit_v1`) | hayır | hayır | kabul (önizlemeler 4/4 eşleşti) |
| J21 (ayrı sözlük) | hayır | hayır | kabul |
| J22 (T2 pini) | hayır | hayır | kabul (25/0; mutasyon l kırmızı) |

**A/B'de değişen testler:** `test_outcome_guard.py` — T4: bekçi `data/`'nın tamamında kasa kodunu yasaklıyor (yeni assert), açık kodlar yalnız v2'de, COMPLETENESS istisnası sayıya pinli, mutasyon testi eklendi → **güçlendirme**, gevşetme yok (mutasyon m kırmızı). `test_scoring.py` (2 test), `test_faz4_ceiling_path.py` (1), `test_faz5_live.py` (`test_l9`): fark tam `faz7_variants(dv)` kadar ve yalnız `scores.json` 8e3a623 haliyle bayt-eşitken; başka alan gevşemedi. **Beşinci istisna** (`test_faz5_live.py::test_committed_post_d1_scores_match_recomputation`, B commit'i, `faz7_support.scores_post_d1_is_pre_faz7`): koşul iki dosyanın da (`scores.json`, `scores_post_d1.json`) 8e3a623 ile bayt-eşit olması; yalnız POST_D1 modelinin kartındaki `n_variants_same_data` alanı, tam `faz7_variants(H99 dv) = 2` kadar düşülüyor; `_stable_post` karşılaştırması ve `render_doc` eşitliği aynen sürüyor → **kalıba uyuyor, korumasız bir şey bırakmıyor**; `scores/` yeniden üretilince kendiliğinden devre dışı. SPEC_DEVIATIONS J16 listesine bu test eklenmeli (IMPL_RAPOR §9 zaten söylüyor; B/R yollarında SPEC_DEVIATIONS yoktu).

## 5. Mutasyon denetimi (K3)

Klon `/tmp/borsai_faz7_audit/clone` (HEAD f5d7609), sürücü `ekler/mutate.sh`, çıktılar `ekler/mutasyon_ciktilari.txt` (kasa kodu taraması 0). 21 koşu; her mutasyon ayrı uygulandı ve geri alındı (klon temiz).

| # | Mutasyon | Test(ler) | Kırmızı |
|---|---|---|---|
| a | kırpma sınırları test arzını içerir (`_run_hazard_v1` raw + `fit_training_set` prep) | golden bayt-eşitlik | evet (1 failed) |
| b | kırpma ln ölçeğinde (log özellikleri için sınır log uzayında Type-7, exp) | `test_winsor_bounds_…`, golden | evet |
| c1 | f1r T − 1 ayı | `test_month_for_examples`, `test_index_for_is_pit…`, `test_tufe_month_and_index_in_ledgers` | evet (3) |
| **c2** | **`release_date ≤ T` kabul** (`if row.release_date > T`) | `test_refusals_…`, `test_index_for_is_pit…`, `test_tufe_refusals_in_predict`, bütün `test_faz7_tufe.py` | **HAYIR (10 passed)** → B2 |
| d1 | γ cezalandırılır | `test_6_gamma_is_not_penalized`, `test_regime_lambda_1e9…` | evet |
| d2 | δ cezalandırılır | `test_regime_lambda_1e9…` (sentetik + gerçek) | evet |
| e | λ eşitliğinde küçük λ | `test_7_tie_goes_to_largest_lambda…` | evet |
| f | eğitim kesimi `<=` | `test_fold_plans_…no_leakage`, `test_3_censoring…`, golden | evet |
| g1 | canlı r = 1 | `test_regime_values_live_and_oot_inputs`, `test_pooled_at_inf_differs…` | evet |
| g2 | test tahmininde r = 1 | `test_log_entries_and_ledgers_synthetic`, golden | evet |
| h | J10 dışlaması kapalı | `test_f3_filter_exclusion_rule`, `test_pooled_plan_filter_exclusion…`, golden | evet |
| i | yakın dönem sınırı 2023-12-01 | 3 test (78 ticker, v0 kendine karşı, günlük near_era) | evet (3) |
| **j** | **etiket eşiği +0.015** | `test_near_era_label_rule_synthetic`, `test_near_era_cells…`, `test_models_md_faz7_section`, `test_report.py` | **HAYIR (12 passed)** → B3 |
| k1 | v0 ledger sha pini atlanır | `test_v0_comparator_ledger_pinned…` | evet |
| k2 | v0 yerine @INF ledger'ı (tutarlı pinle) | 3 test | evet (3) |
| l | `predict_hazard` v0 η'sı 1e-7 değişir (T2) | `gen_golden --check` → 8 dosya farklı; `test_8_json_matches_numpy_final_model` | evet |
| m | v2'ye bir kasa kodu satırı (T4; kod bellekte) | `test_cohort_codes_appear_in_data_only_as_outcomes` | evet ("kasa kodu (1 farklı)") |
| n | TÜFE 2019-11 değeri değişir (önek pini) | 3 test | evet (3) |
| o1 | bootstrap tohumu 20260922 | `test_near_era_cells…` | evet |
| o2 | ay bloğu anahtarı YYYY | `test_near_era_cell_of_v0_against_itself`, `test_near_era_cells…` | evet |

Kırmızı olmayan iki mutasyon: **c2** (bekçi `release_date == T` durumunu hiç sınamıyor; kod doğru, koruma yok) ve **j** (δ = 0.010 sabiti hiçbir testte assert edilmiyor; §11-9 sentinel aralıklarının hiçbirinin üst ucu (0.010, 0.015] içinde değil; MODELS.md'deki "+0.010" metni sabitten bağımsız bir dize). İkisi de test eksiği; davranış şu an doğru.

## 6. Tanı (model seçimine girmez; şartname değişmez)

Yakın dönem 78 fold, ort. S_k / gözlenen P(L ≥ k) [ÖLÇTÜM]:

| k | Gözlenen | v0 | clip | real | pooled | @INF | KM |
|---|---|---|---|---|---|---|---|
| 1 | 0.808 | 0.856 | 0.853 | 0.875 | 0.905 | 0.888 | 0.879 |
| 3 | 0.641 | 0.685 | 0.675 | 0.719 | 0.743 | 0.717 | 0.748 |
| 5 | 0.385 | 0.420 | 0.408 | 0.467 | 0.530 | 0.518 | 0.512 |
| 10 | 0.115 | 0.184 | 0.185 | 0.229 | 0.243 | 0.232 | 0.198 |

1. **Düzey vs ayırma:** RPS farkını "düzey" (her k'de ort. S_k − gözlenen kaydırılınca kapanan pay) ve kalan (ayırma/şekil) olarak ayırdım: real − v0 = +0.0104 = düzey **+0.0074** + ayırma +0.0031; pooled − v0 = +0.0289 = düzey **+0.0145** + ayırma **+0.0144**. Brier k = 3 ayrışımı (10 kutu): pooled çözünürlük 0.072 (v0 0.121), güvenilirlik 0.048 (v0 0.045) → pooled hem fazla uzun seri tahmin ediyor hem de yakın dönemde arzları ayırt etmiyor; real'de sorun ağırlıkla düzey.
2. **Yıl kırılımı** (aday − v0): pooled 2024 +0.043 (n 33), 2025 +0.046 (17), **2026 +0.002 (28)**; real 2024 +0.014, 2025 +0.001, 2026 +0.012; clip −0.000/−0.001/−0.002. En çok katkı veren 10 fold pooled'da işaret değiştiriyor (toplamın −2'si): kayıp geniş tabana yayılmış, birkaç fold'dan gelmiyor. real'de de 10 fold toplamın −17'si.
3. **pooled, "2023'ün uzun serileri bugünkü rejim diye öğreniliyor" hipotezi:** açık f3'lü 68 = r = 1 53 + r = 0 15; ham P(L ≥ 10): r = 1 0.08, r = 0 açık (2023-04…09) **0.33**, H99 0.14, yakın dönem 0.12. δ = +0.911 r = 1 satırlarının kısa serisini emiyor; γ (r = 0 sabiti) 15 uzun 2023 arzı + H99 ile öğreniliyor ve nihai fit'te r = 0 gün-grubu hazard'ları 0.108/0.096/0.176 (real: 0.146/0.106/0.253) → daha uzun seri. Duyarlılık (i) bu 15 arz çıkarılınca fark +0.0289 → **+0.0178** (etiket yine bozuyor): hipotez farkın yaklaşık üçte birini açıklıyor; kalan, yakın dönemde f3'ün eğitim p95'inin 8.3'ten 18.0'a çıkması ve β'ların 165 arzda öğrenilmesi (ayırma kaybı) [ÇIKARIM].
4. **λ sınırı:** görev metnindeki "97/97 fold'da ızgaranın üst ucunda (10)" öncülü yanlış: ızgara 0.1…1000, INF; 10 **iç nokta** (97/97 fold'da skor(3) > skor(10) < skor(30); nihai 0.42352/0.42337/0.42384). Duyarlılık (iii) yoğun/genişletilmiş ızgara: seçilen 7 (37 fold), 10 (59), 15 (1); hücre +0.0287 [+0.0087, +0.0516] — sorun değil, şartnamenin beklenen sonucu.
5. **real:** H99 97'de ln f1 ile zaman sırası korelasyonu +0.31, ln f1r ile −0.13; Spearman(f1, f1r) 0.889; nihai β_f1 +0.463 → β_f1r +0.265 (fold ortalaması 0.69 → 0.61). Nominal f1 H99 içinde "yakın tarih = kısa seri" bilgisini de taşıyor (2024–2026'da seriler kısa, nominal büyüklük yüksek); deflasyon bu bileşeni çıkarınca β düşüyor ve S düzeyi yükseliyor (S_10 0.185 → 0.229) [ÇIKARIM].
6. **clip:** v0'dan fark, test arzı kırpılan 33 fold'da −0.0057, kırpılmayan 45'te +0.0023 (eğitim kümesinde de kırpma olduğundan sıfır değil); 87 fold'da herhangi-sütun kırpılan 35 (yalnız f3 20).
7. **§6.2 neden tutmadı:** beklenti, deflasyonun ve havuzun H99 içindeki düzey etkisini küçümsedi: (b) için "yön belirsiz" yazılmıştı ama f1'in dönem bileşeni hesaba katılmadı; (c) için "γ bugünkü rejimden" varsayımı 15 uzun 2023 arzının r = 0 sabitine girmesini gözden kaçırdı. Uygulama hatası değil (D1/D2 bağımsız kurulumda bit-eşit; ledger'lar |Δ| ≤ 1e-9).

**Duyarlılıklar** (`ekler/sensitivity_runs.jsonl`, `ekler/repro_ledgers/sens_*.csv`; model değil, dondurulmaz; hepsi bağımsız betikle):

| Koşu | Yakın dönem − v0 [%95] | Etiket | − KM | λ (fold) |
|---|---|---|---|---|
| `__sens_drop_post_20230330_open` (r = 0 açık 15 arz havuz dışı) | +0.0178 [+0.0018, +0.0354] | bozuyor | −0.0365 [−0.0534, −0.0172] | 10: 50, 3: 47 |
| `__sens_no_regime` (rejim terimsiz havuz) | +0.0283 [+0.0089, +0.0482] | bozuyor | −0.0260 [−0.0446, −0.0030] | 30: 51, 100: 39, 300: 5, 1000: 2 |
| `__sens_lambda_grid_dense_and_extended` (…, 5, 7, 10, 15, 20, …, 3000, 10000, INF) | +0.0287 [+0.0087, +0.0516] | bozuyor | −0.0256 [−0.0390, −0.0099] | 7: 37, 10: 59, 15: 1 |
| `__sens_j10_exclusion_off` (bilgi; B4) | +0.0279 [+0.0082, +0.0507] | bozuyor | −0.0264 [−0.0402, −0.0108] | 10: 84, 3: 13 |

## 7. Bulgular ve öneriler

| # | Önem | Bulgu | Sınıf | Öneri |
|---|---|---|---|---|
| B1 | ÖNEMLİ | Ledger sütunu `test_clipped` yalnız f3 kırpmasını yansıtıyor (`hazard.TrainingResult.predict`, `clipped = bool(t["f3_winsorized"])`); şartname §3.1 "herhangi bir sütun kırpıldıysa". MODELS.md ve IMPL_RAPOR "test arzı kırpılan fold: 20 / 20 / 7" bu yüzden yanlış (herhangi-sütun: **35 / 36 / 23**; `test_clipped_features` sütunu doğru). Sayısal çıktılar, stdlib tahmin (`clipped` doğru) ve nihai fit etkilenmiyor. | kodu şartnameye uydurmak = aynı model_id | `predict`'te `clipped = bool(clipped_features)`; dondurma görevinin kod commit'inde düzelt, altın ledger'ları yeniden üret (deterministik; yalnız bu sütun değişir, sha'lar ve günlük satırı yenilenir; `faz7_variants` (model_id, spec) sayımı değişmez), MODELS.md fold özetini yeniden render et; T2 pini gerekmez (`hazard.py` pinli değil). |
| B2 | ÖNEMLİ | Mutasyon c2 yeşil: `index_for` bekçisi `release_date == T` durumunda test edilmiyor. | test eksiği (aynı model_id) | `test_faz7_tufe.py`'ye `release_date == T → TUFE_NOT_PIT` sentetik satırı. |
| B3 | ÖNEMLİ | Mutasyon j yeşil: δ = 0.010 sabiti hiçbir testte assert edilmiyor; sentinel aralıklar (0.010, 0.015] üst ucunu kapsamıyor; MODELS.md'deki "+0.010" sabitten bağımsız bir dize. | test eksiği | `assert bt.NEAR_ERA_TOLERANCE == 0.010` + sentinel `[−0.02, +0.012] → belirsiz`; `OPERATIONAL_RULES_FAZ7` metnini sabitten üret. |
| B4 | ÖNEMLİ | J10 dışlaması monoton değil: mod 2023-09…2025-01 arasında UNFILTERED ↔ NOT_SPECIFIED arasında gidip geliyor (NOT_SPECIFIED 89, UNFILTERED 71 birim; eşitlikte alfabetik); 3 FILTERED açık üye 44 fold'da (25'i yakın dönemde) eğitim dışı, 53 fold'da ve nihai fit'te içeride. SPEC_HAZARD_V1 §5.1 "bütün kişi-dönem satırları" / §2 n = 165 lafzına aykırı, proje sahibi kararıyla kabul edilmiş; hücreye etkisi +0.0289 → +0.0279. | belgelenme (kod değişmez); kuralın değişmesi = yeni model_id | SPEC_DEVIATIONS J10'a mod salınımı, fold aralığı ve etki sayılarını yaz; MODELS.md fold özeti zaten 44 / [65, 68] yazıyor. Proje sahibi monoton bir kural isterse (ör. filtre adımı v1'de kapalı), bu şartname değişikliğidir → yeni kimlik. |
| B5 | KÜÇÜK | İkincil Brier hücrelerinin karşılaştırıcısı (v0) şartnamede adlandırılmamış, J'de satırı yok. | belgelenme | SPEC_DEVIATIONS J'ye bir satır. |
| B6 | KÜÇÜK | J16 beşinci istisna (`test_committed_post_d1_scores_match_recomputation`) SPEC_DEVIATIONS J16 listesinde yok (IMPL_RAPOR §9'da). | belgelenme | J16'ya ekle. |
| B7 | KÜÇÜK | J6: OOT kaydında `alloc_regime` anahtarı unutulursa tahmin sessizce canlı (r = 0) sayılır; `regime_source` bunu yazar ama bekçi yok. | dondurma görevi bekçisi | `freeze.build_record`: `record_stage == OOT_PRE_LISTING` ve rejimli model → `alloc_regime` zorunlu (test). |
| B8 | KÜÇÜK | Görev/orkestratör öncülü "λ 97/97 fold'da ızgaranın üst ucunda" yanlış: 10 iç nokta. | bilgi | Tanı 4; dondurma notunda düzeltilmiş cümle. |
| B9 | KÜÇÜK | Kasa kodu taraması: `data/raw/PREBOOKBUILD…R2_99.csv`'de bir kasa üyesinin kodu bir H99 unvanının sözcüğü olarak geçiyor (Faz 6 bekçisinde tanımlı istisna); bu sözcük bekçi test dosyasının docstring/sabitinde ve T4 testinin pytest çıktısında görünüyor. Bu görevden önce var. | hijyen (bilgi) | İleride bekçi metnini sözcüğü yazmadan (sha/uzunluk) ifade et; kod adı zaten "kasa üyesi" olarak işaretlenmiyor. |
| B10 | KÜÇÜK | `test_faz7_golden` `rerun` fikstürü 4 koşuyu 9 süreçle ~45–100 s'de yeniden koşuyor; mutasyon (b), (f), (h)'de fikstür hata verince golden testi "error" olarak kırmızı oldu (yine kırmızı). | bilgi | — |

KRİTİK: yok. Sızıntı: yok. Şartname değişikliği gerektiren bulgu: yok (B4 yalnız proje sahibi isterse).

## 8. Dondurma görevi için notlar

- **Önce kod commit'i (B1 + B2/B3 testleri + B7 bekçisi), sonra temiz ağaçta dondurma** (IMPL_RAPOR §14 "borsai_dirty" tuzağı). B1 sonrası altın ledger'lar yeniden üretilir; yalnız `test_clipped` sütunu değişir (S/hazard/λ aynı; bu denetimin ledger'ları doğrulama için `ekler/repro_ledgers/`'da); MODELS.md yeniden render.
- **INDEX.json'a 4 giriş** (`FAZ7_MODEL_IDS` sırası); JSON'lar `final_fit_v1` ile (önizlemeyle `created_at`, `code_version`, `runtime` dışında bit-eşit; bu denetimde 4/4 eşleşti). `v1_clip@INF`/`v1_real@INF` kayıtlı değil (v0@INF ile bit-eşit; testli).
- **Rust (`borsai_predict`):** `family = ceiling_hazard_v1`, `features ∈ {[f1,f2,f3],[f1r,f2,f3],[]}`; `preprocessing.winsor` üç sütun; **f1r = f1 / (tufe_index / 100)** Decimal 60 hane ROUND_HALF_EVEN (iki işlem: `idx/100` sonra bölme; Python ile aynı sıra), sonra binary64 ve ln; kırpma genel: `clipped` = herhangi bir sütun, `clipped_features`, uyarı `FEATURE_CLIPPED_TO_TRAINING_P05_P95` {feature, value, used}; v0'ın `F3_CLIPPED_…` kodu v0'da aynen; **r**: `alloc_regime` girdisi yoksa `regime.live_value` (0), varsa etiket → r (bilinmeyen → `REGIME_UNKNOWN`); η_d = (γ_{g(d)} + δ·r) + β·z toplama sırası; retler `TUFE_MISSING` (alan `tufe_index`), `TUFE_NOT_PIT`/`TUFE_FILE_MISMATCH` (`tufe_refusal` girdisi), `F3_MISSING`; yeni çıktı alanları `clipped_features`, `f1r_raw`, `tufe_index_used`, `regime_value_used`, `regime_source`. **TÜFE tablosu** uygulamaya gömülürse önek pini (`through_month`, `prefix_sha256`) ve `release_date < T` denetimi de gömülmeli; aylık ekleme = dosyanın sonuna satır, eski satırlar bayt-eşit (B2'nin testi bunu da korur).
- **Altın vektör planı 19 → 23:** `gen_golden.py` `PINNED_MODEL_IDS` INDEX sırasıyla; `bit_equal_floor.json` 4 taban; U46 için 16 eski dosya bayt-eşit (yeni girdi satırları yalnız yeni modellere; Faz 4 kalıbı). Önerilen satırlar: H99 99 arz + `tufe_index` (f3'süzler RET); açık 71 arz + `tufe_index` + `alloc_regime` (r = 1 satırları); canlı satırlar (anahtarsız); uç durumlar p05/2, 2·p95, `tufe_index` eksik/sayı değil/≤ 0, `tufe_refusal` kodları, bilinmeyen etiket; `@INF` özelliksiz. Kasa girdileri girmez.
- **Eski kohort ikinci kayıtları (`--only-missing-models`, §7.1-3, §11-12):** 135 üyede tam 4 modelli ikinci kayıt; girdiler ilk kayıtla bayt-eşit (test); `tufe` bloğu (`tufe.index_for(T)`, `release_date < T`), `model_inputs["tufe_index"]`, **`model_inputs["alloc_regime"]` = kohort satırının etiketi** (J2 okuması; ilk işlem günü okumasıyla r aynı, 135/135); kasa üyeleri için yalnız listeleme öncesi girdiler, sonuç yok; commit + push + kanıt kasa açılışından **önce**. Model başına kapı (§7.3): (model, üye) başına en erken aktif kayıt, kanıt ingest'ten önce; `download_gate` aynı kural; sentetik test (bir üyenin ikinci kaydı eksikken kırmızı).
- **Skorlama:** açık küme satırları v1 için formülle OOT_RETRO (`n_oot_retro = 71`, bilgi); `oot_pre_h99_all` yeni modeller için üretilmez; var olan 7 canlı kayıt v1 için RETRO. `scores.json` yeniden üretilince H99 kartları 22 varyant yazar, J16 istisnaları (5 test) kendiliğinden düşer.
- λ notu: 10 iç noktadır (B8); ızgara değişikliği gerekmez.

**Uygulama için bir cümle:** "Tavan serisi" kartında `ceiling_hazard_v0` öne çıkarılmaya devam eder; üç aday yan yana, her biri için yakın dönem satırı "v1 − v0 (H99, ilk işlem ≥ 2024-01-01, n = 78): fark [%95] → **tolerans içinde / bozuyor**" sözcükleriyle (backtest, tasarıma maruz uyarısıyla), altında "kasa: bekliyor ((C) şartnamesiyle birlikte açılır)" ve "canlı: n = 0" satırları; "geçiyor" sözcüğü kullanılmaz.

## 9. Açık konular, tam test, ekler

- **Açık konular:** (1) B1 düzeltmesinin zamanı (öneri: dondurma görevinin kod commit'i); (2) B4 için proje sahibi belgelenmeyle yetiniyor mu; (3) B2/B3 testleri.
- **Tam test** (`ekler/test_out.txt`; HEAD `4e081d8`, paralel commit sonrası, deselect yok): `.venv/bin/pytest -q` **712 passed, 726.9 s**; `bash app/scripts/test.sh` yeşil (`set -e`; `golden_unchanged` U46 yeşil; özet satırları dosyanın sonunda).
- **Koruma:** `ekler/koruma_once.txt` / `koruma_sonra.txt`: `registry/`, `data/`, `scores/`, `models/`, `app/` çalışma ağacında değişiklik yok; HEAD'deki tek fark paralel oturumun `4e081d8` commit'i (`registry/oot/candidate_features_faz7/`, `registry/oot/source_docs_faz7/`; hariç tutuldu).
- **Ekler** (`ekler/`, toplam < 1 MB; `SHA256SUMS`): `repro_hazard_v1.py`, `repro_stdout.txt`, `repro_output.json`, `repro_ledgers/` (6 yeniden üretim + 4 duyarlılık, kompakt), `sensitivity_runs.jsonl`, `runtime_file_trace.py` + `_out.txt/json`, `vault_check.py` + `_out.txt`, `mutate.sh`, `mutasyon_ciktilari.txt`, `sira_kanitlari.sh/.txt`, `test_out.txt`, `koruma_once/sonra.txt`, `tufe_bulten_ornek.json` (10 bültenin id/tarih/dönem alanları). Geçici dizin `/tmp/borsai_faz7_audit/` silindi.

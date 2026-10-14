# TASK_ID: BORSAI_FAZ7_FABLE_V1_REPRO_AUDIT_20260926

Model: Fable · yüksek. Klasör: ~/Desktop/BorsAi.
- **Ağ:** yalnız TÜİK veri portalı (`veriportali.tuik.gov.tr`); adım 1a'daki TÜFE denetimi için. Başka ağ yok.
- **Git:** YALNIZ okuma komutları ve her zaman `GIT_OPTIONAL_LOCKS=0` öneki (`log`, `show`, `diff`, `status --porcelain`, `merge-base --is-ancestor`, `clone --local`). Sonda tek commit, yalnız kendi yollarınla. push/tag/amend yok.
- **Yazma:** YALNIZ `docs/fable_faz7_audit/` (AUDIT.md ve `ekler/`) ve bu görev dosyası. Geçici işler (klon, mutasyon kopyaları, indirmeler, büyük çıktılar) `/tmp/borsai_faz7_audit/` altında; sonda silinir. `ekler/` toplamı ≤ 3 MB.
- **Paralel:** Bir Sonnet oturumu `docs/prompts/FAZ7_PROSPECTUS_INTAKE.md`'yi koşuyor. Yalnız şu yollara yazar ve commit eder: `registry/oot/candidate_features_faz7/`, `registry/oot/source_docs_faz7/`, `docs/faz7/prospectus/`, `tests/test_faz7_prospectus.py`, `docs/PROVENANCE.md` (yalnız ekleme) ve beş Faz 7 izahname görev dosyası. Bu yolları koruma ölçümünden ve bulgulardan hariç tut. Onun `BORSAI_FAZ7_PROSPECTUS` commit'i senin koşunun ortasında gelebilir. Tam testi (adım 2 sonu) o commit'ten sonra koş; `git log`'da yoksa bekle ya da testi en sona bırak. Temizlik bekçisi yalnız onun commit edilmemiş yolları yüzünden kırmızıysa bu bulgu değildir; commit'ten sonra yeniden koş.
- **Koruma:** koşu öncesi ve sonrası `git status --porcelain` ile `registry/`, `data/`, `scores/`, `models/`, `app/` ağaç sha'larını ölç; eşit olmalı.

## Bağlam
- **Şartnamen** `docs/specs_faz7/SPEC_HAZARD_V1.md`: commit `6a16c16`, push kanıtı `created_at` 2026-09-25T18:09:45Z. Proje sahibi kararları `docs/specs_faz7/KARARLAR.md` K1–K5 (çeliştiği yerde bağlayıcı).
- **Uygulama Opus'a ait** (görev `docs/prompts/FAZ7_HAZARD_V1_IMPL.md`):
  - `2a21a96` (A, 2026-09-26T03:10:01+03:00): kod, TÜFE dosyası, `training_table_v2`, kurallar (`borsai/report_faz7.py: OPERATIONAL_RULES_FAZ7`, `borsai/backtest.py: near_era_label`), SPEC_DEVIATIONS J1–J16. Sonuç yok.
  - `70b67d1` (B): walk-forward, altın ledger'lar `tests/reference/macos_golden_faz7/`, nihai fit önizlemeleri (dondurulmadı), `experiments/log.jsonl` 4 satır, MODELS.md "Faz 7: tavan serisi v1" bölümü.
  - `f5d7609`: rapor `docs/faz7/IMPL_RAPOR.md`.
- **Opus'un sonuçları** (backtest, H99, tasarıma maruz; yakın dönem = ilk işlem ≥ 2024-01-01, n = 78, 22 ay; aday − `ceiling_hazard_v0`, RPS):

  | Aday | Fark [%95] | Etiket | §6.2 konumu |
  |---|---|---|---|
  | `ceiling_hazard_v1_clip` | −0.0011 [−0.0066, +0.0049] | tolerans içinde | aralık içinde |
  | `ceiling_hazard_v1_real` | +0.0104 [+0.0028, +0.0183] | bozuyor | üstünde |
  | `ceiling_hazard_v1_pooled` | +0.0289 [+0.0089, +0.0518] | bozuyor | üstünde |
  | `ceiling_hazard_v1_pooled@INF` (kural satırı) | +0.0547 [+0.0287, +0.0806] | — | — |

  - Fold'lar: clip ve real 87/87 FIT_OK; pooled ve @INF 97/97.
  - Pooled'da λ, 97 fold'un hepsinde ızgaranın üst ucunda (10); δ (rejim) 97/97 fold'da > 0.
  - Nihai fit önizlemesi λ: clip 10, real 10, pooled 10, @INF INF.
  - Yakın dönem düzeyleri (78 arz, ort. S_k / gözlenen P(L ≥ k)):

    | k | Gözlenen | v0 | clip | real | pooled |
    |---|---|---|---|---|---|
    | 5 | 0.385 | 0.420 | 0.408 | 0.467 | 0.530 |
    | 10 | 0.115 | 0.184 | 0.185 | 0.229 | 0.243 |
- **Orkestratör kontrolü:** dört birincil hücrenin nokta tahminlerini ve yaklaşık aralıklarını Opus'un ledger'larından ve Faz 1B v0 ledger'ından kendi betiğiyle yeniden hesapladı; basılı hassasiyette tuttu, etiketler aynı. Bu, Opus'un kendi ledger'ından hesaptır; **bağımsız yeniden üretimin yerini TUTMAZ.**
- **Şartname §7.1:** dondurmadan önce senin sıfırdan yeniden üretimin zorunlu; ledger'lar **|Δ| ≤ 1e-9** eşleşmeli.
- **§6.4:** etiket ne olursa olsun üç aday (ve kural satırı) dondurulur; yakın dönemde "bozuyor" olan aday k3 ile uygulama birincili olamaz. Senin FREEZE hükmün yalnız uygulamanın şartnameye uygunluğuna dayanır, etikete değil.
- **Oturum içi proje sahibi kararları:** SPEC_DEVIATIONS J10 (bir eğitim kümesinde f3'ü filtre moduna açıkça zıt olan birim o kümede kullanılmaz; havuz fold'larının 44/97'si) ve J16 (varyant sayacı istisnası, H22 kalıbı). İkisi de şartname sayılır; lafza uygunluklarını ve davranış etkilerini sen değerlendir.
- **Hijyen:** hangi kodun SEALED olduğu hiçbir dosyaya, çıktıya ya da rapora yazılmaz ve ekrana basılmaz; kasa denetimleri yalnız sayı basar. `docs/faz6/dogrulama/EXPOSURE.md` §3 okunmaz. Karantina dizinine (`~/Desktop/BorsAi_quarantine`) dokunulmaz.

## Kurallar (baştan)
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** Sen kodu düzeltmezsin; bulguyu ve öneriyi yazarsın.
- Mevcut hiçbir dosyayı değiştirme. Salt okunur: `borsai/`, `tests/`, `models/`, `docs/specs*/`, `docs/app/`, `experiments/`, `registry/`, `data/`, `scores/`, `app/`.
- Yeniden üretim betiği `borsai`'yi import etmez. Kanıt: betikte `borsai` geçen import satırı yok ve alt süreçte `sys.modules` denetimi.
- Metinde `thb`/`thm` + 8 haneli tarih kalıbı yazma (`tests/test_outcome_guard.py`).
- Rapor Türkçe.

ÖNCE OKU:
- CLAUDE.md
- docs/specs_faz7/SPEC_HAZARD_V1.md (tamamı) ve KARARLAR.md
- docs/specs/SPEC_CEILING_V0.md, docs/specs/SPEC_SCORING.md §2, §3, §7, §8
- docs/SPEC_DEVIATIONS.md: A2, C6, C7, H22, J
- docs/prompts/FAZ7_HAZARD_V1_IMPL.md (T1–T6), docs/faz7/IMPL_RAPOR.md, docs/MODELS.md "Faz 7" bölümü, docs/PROVENANCE.md §11
- Kendi önceki bağımsız betiklerin (kalıp; parça kullanabilirsin):
  - docs/fable_conformity_20260922/ (Faz 1B, `independent_repro.py`: ana model ön işlemesi, PP satırları, Newton);
  - docs/fable_faz5_audit/ekler/ (`repro_post_d1.py`, mutasyon sürücüsü);
  - docs/fable_faz6_s6/ (`recompute.py`).
- Denetlenecek kod (yeniden üretimde KULLANILMAZ): borsai/tufe.py, preprocess.py, hazard.py, specs.py, data.py, backtest.py, predict_hazard.py, report_faz7.py, report.py; data/build_training_table_v2.py, data/raw/tuik/build_tufe_csv.py; tests/test_faz7_*.py, faz7_support.py, test_outcome_guard.py ve A/B'de değişen test_faz4_ceiling_path.py, test_faz5_live.py, test_scoring.py.

## Adım 0
- `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -4`: HEAD `f5d7609` ya da yalnız push kanıtı commit'i eklenmiş torunu. `git status --porcelain`.
- İzinli izlenmeyen: bu görev dosyası ve `docs/prompts/FAZ7_CODEX_PROSPECTUS_B1..B4.md`, `docs/prompts/FAZ7_VERIFY_PROSPECTUS.md` (paralel oturum bunları commit edebilir), ayrıca paralel oturumun yolları ve `docs/prompts/FAZ7_PROSPECTUS_INTAKE.md`. Başka bir şey varsa DUR.
- Koruma ölçümü: `registry/`, `data/`, `scores/`, `models/`, `app/` → `ekler/koruma_once.txt`; sonda `koruma_sonra.txt`.

## Adımlar

**1. Sıfırdan yeniden üretim** — `docs/fable_faz7_audit/ekler/repro_hazard_v1.py` (stdlib; gerekirse numpy)

**1a. TÜFE.**
- `PROVENANCE.md` §11'deki TÜİK tablosunu resmi adresten `/tmp/borsai_faz7_audit/`'e indir. sha256, `data/raw/tuik/tufe_degisim_oranlari_bulten_58290.xls` pininle eşit olmalı.
- Endeks değerlerini kendi okuyucunla çıkar ve `data/raw/tuik/tufe_genel_2025_100.csv` ile karşılaştır.
- `tufe_bultenleri.csv`'den `random.Random(20260926).sample` ile 10 ay seç. Her birinin bülten sayfasındaki yayım tarihini oku ve dosyadakiyle karşılaştır.
- Ayrıca denetle:
  - 2025 ortalaması 100.00 ± 0.05;
  - ay kuralı T − 2 (şartname §3.2);
  - her kullanımda `release_date < T`: 170 eğitim arzı ve bütün test arzları.

**1b. Eğitim tablosu v2.**
- **H99'un 99 satırı:** `data/training_table.csv` ile paylaşılan sütunlarda bayt-eşit.
- **Açık kümenin 71 satırı birincil kaynaklardan:**
  - listeleme öncesi girdiler: yalnız açık üyelerin `registry/oot/records/` S2 kayıtları;
  - L ve seans günleri: `data/outcomes_oot/<T>.csv` (L tanımı: SPEC_CEILING_V0).
  - Kendi değerlerini `data/training_table_v2.csv` ile karşılaştır: f1, f2, f3, f3 filtre modu, `alloc_regime`, ilk işlem günü, L.
- **Beklenen sayılar:**
  - L dağılımı {0: 9, 1: 11, 2: 5, 3: 4, 4: 3, 5: 8, 6: 5, 7: 6, 8: 5, 9: 6, 10: 9};
  - PP satır/olay: H99 f3'lü 506/83, açık f3'lü 374/59, havuz 880/142.

**1c. Fold ledger'ları.** Altı ledger:
- `ceiling_hazard_v1_clip` ve `_real` (PLAN_CEILING, 87 fold);
- `ceiling_hazard_v1_pooled` ve `@INF` (PLAN_CEILING_POOLED, 97 fold);
- `base_km_expanding__pooled` ve `base_km_last10__pooled`.

Bağımsız hesaplanacaklar:
- fold planı ve eğitim kümeleri (J10 dışlaması dahil);
- ham değerde Type-7 [p05, p95] kırpma, ln, z;
- cezasız γ (ve δ) ile L2 lojistik Newton;
- iç CV ve λ seçimi (eşitlikte büyük λ);
- test tahmini: hazard, S, P_close, reclose.

`tests/reference/macos_golden_faz7/` ile karşılaştır:
- `status`, `selected_lambda`, `test_clipped`, kimlik ve metin sütunları birebir;
- `training_n_*` birebir;
- diğer bütün sayısal sütunlar |Δ| ≤ 1e-9 (`solver_iterations` ve `solver_grad_max` hariç).

**1d. Nihai fit önizlemeleri (4).**
- λ birebir;
- γ, β, δ, kırpma sınırları, μ/σ ve skor tablosu |Δ| ≤ 1e-9;
- arz / satır / olay: 97/506/83 ve 165/880/142.

**1e. MODELS.md Faz 7 hücreleri.** Hepsini ledger'larından hesapla:
- birincil (3 aday + kural satırı);
- ilan edilmiş ikinciller;
- merdiven (3);
- keşif tablosu.

Her hücrede fark, %95 aralık, n, blok, kazanç / kayıp / eşit. Aralık C7'ye göre: ilk işlem ayı blokları, 4000, `random.Random(20260921)`, alt/üst indeks 100/3899. Hepsi MODELS.md ile |Δ| ≤ 1e-9. Etiketler (§5.1) ve §6.2 konumları doğru olmalı.
- v0 karşılaştırıcısı: Faz 1B ledger'ı sha `976b4dcea981…`; 87-fold ortalama RPS 0.1503.

Tutmayan her şeyin kök nedenini ölç: senin kodun mu, Opus'unki mi, şartname belirsizliği mi. Tahmin etme.

**2. Sızıntı ve uygunluk** (her madde komut ve çıktıyla)
- **(i) Test arzı:** özellikleri ve L'si hiçbir fold'da eğitime, kırpma sınırlarına ya da z istatistiklerine girmiyor.
- **(ii) Eğitim kesimi:** her eğitim PP satırında seans < T.
- **(iii) Havuz planı:** açık küme satırlarının hepsi < T. J10 dışlaması yalnız filtre moduna zıt birimleri etkiliyor (sayılar: fold başına dışlanan).
- **(iv) Rejim terimi:** test ve canlı tahminde r'nin kaynağı ve değeri doğru. Canlıda r = 0 (şartname §3.3).
- **(v) Kasa:**
  - SEALED kod sayısı 0 olmalı: `data/`, `tests/reference/macos_golden_faz7/`, `docs/MODELS.md`, `experiments/log.jsonl`, `docs/faz7/` (`docs/faz7/prospectus/` hariç: orada 135 üyenin hepsi tanım gereği geçer), `docs/SPEC_DEVIATIONS.md`.
  - SEALED kümesini bellekte kur (`registry/oot/records/` kayıtlarından) ve yalnız sayı bas.
- **(vi) Sonuç dosyaları:** kodun okuduğu sonuç dosyaları yalnız `data/outcomes_oot/` altındaki açık küme dosyaları ve H99 SESSIONS. `data/outcomes/`, `scores/` ve `registry/` altındaki canlı sonuçlar okunmuyor (çalışma zamanı dosya izi, Faz 4 `runtime_file_trace.py` kalıbı).
- **Sıra kanıtları:**
  - şartname push kanıtı < A commit zamanı;
  - `git diff 6a16c16 f5d7609 -- docs/specs_faz7/SPEC_HAZARD_V1.md` boş;
  - `2a21a96` ağacında faz7 altın dizini, MODELS.md Faz 7 bölümü ve günlükte `faz7_golden` satırı YOK;
  - `git diff 2a21a96 f5d7609 -- borsai data` boş, yani kurallar ve eşikler sonuçtan sonra değişmedi.
- **Kurallar ↔ şartname:** `OPERATIONAL_RULES_FAZ7` ve `near_era_label` şu bölümlerin lafzına uyuyor mu: §5.1 (birincil hücre, δ = 0.010, üç etiket), §5.4 (merdiven, hüküm dili yok), §6.2 (beklenti tablosu aynen). Uymayan her satır bulgudur.
- **Kod ↔ şartname:** §3.1–§3.4, §4, §8, §9 (ret kodları), §12. Ayrıca şunlar:
  - T2: 19 modelin altın vektörleri ve 16 eski dosya bayt-eşit (`gen_golden --check` 25/0); v0, `@INF` ve PB tavan ledger'ları bayt-eşit.
  - T4: bekçi uyarlaması ve mutasyonu.
- **J1–J16'nın her biri:** davranış değiştiriyor mu, lafza aykırı mı, kabul edilebilir mi. Özellikle J10 ve J16.
- **A ve B'de değişen testler** (`test_outcome_guard.py`, `test_faz4_ceiling_path.py`, `test_faz5_live.py`, `test_scoring.py`, `faz7_support.py`): hiçbir bekçi gevşetilmedi. İstisna yalnız J16 kalıbında olabilir ve fark tam olarak günlükteki Faz 7 varyant sayısı kadar olmalı. B'de Opus, J16 istisnasını kendi kararıyla beşinci bir teste genişletti: `test_faz5_live.py::test_committed_post_d1_scores_match_recomputation`, `faz7_support.scores_post_d1_is_pre_faz7` (IMPL_RAPOR §9). Bunu ayrıca hükme bağla: kalıba uyuyor mu, bir şeyi korumasız bırakıyor mu?
- **IMPL_RAPOR §8'deki iç tutarlılık denetimleri** (D1: deflatör clip ile real arasındaki tek fark; D2: havuz planı yalnız H99 satırlarıyla real'i veriyor): bağımsız üretiminde de kur.
- **Tam test:** `.venv/bin/pytest -q` ve `bash app/scripts/test.sh` → `ekler/test_out.txt` (sayı, süre).

**3. Mutasyon denetimi**
Klonda çalış: `git clone --local` → `/tmp/borsai_faz7_audit/clone`, `.venv`'i bağla. Her mutasyon ayrı uygulanır, ilgili test koşar, KIRMIZI olduğu gösterilir, geri alınır. Sürücü `ekler/mutate.sh`, çıktılar `ekler/mutasyon_ciktilari.txt`. En az şunlar:
- (a) kırpma sınırları test arzını da içerir;
- (b) kırpma ham değer yerine ln ya da z ölçeğinde yapılır;
- (c) f1r T − 1 ayını kullanır ya da `release_date ≤ T` kabul edilir;
- (d) γ ya da δ cezalandırılır;
- (e) λ eşitliğinde küçük λ seçilir;
- (f) eğitim kesimi `<` yerine `<=`;
- (g) test ya da canlı tahminde r = 1;
- (h) J10 dışlaması kapatılır;
- (i) yakın dönem sınırı 2024-01-01 yerine 2023-12-01;
- (j) etiket eşiği +0.010 yerine +0.015;
- (k) v0 karşılaştırıcı ledger'ının sha pini atlanır ya da başka ledger okunur;
- (l) `predict_hazard`'da v0 çıktısını değiştiren küçük bir değişiklik (T2 bekçisi);
- (m) `data/` altına bir kasa kodu eklenir (T4). Kod bellekte seçilir; betik ve çıktı kodu yazmaz.
- (n) TÜFE dosyasında eski bir satırın değeri değişir (prefix pini);
- (o) bootstrap tohumu ya da ay bloğu anahtarı değişir.

Kırmızı olmayan her mutasyon ÖNEMLİ ya da KRİTİK bulgudur; hangi davranışın korumasız kaldığıyla birlikte yazılır.

**4. Tanı** (model seçimine GİRMEZ; şartname değişmez)
- **real ve pooled neden "bozuyor"?** Yakın dönem kaybını ayrıştır:
  - düzeyin payı (ort. S_k − gözlenen, k = 1, 3, 5, 10) ile ayırma gücünün payı (Brier güvenilirlik/çözünürlük);
  - yıl kırılımı 2024 / 2025 / 2026;
  - en çok katkı veren 10 fold.
- **pooled:** 2023-03-30 sonrası (r = 0) açık küme arzlarının payı. Hipotez: model 2023'ün uzun serilerini "bugünkü rejim" diye öğreniyor.
- **λ sınırı:** λ'nın 97/97 fold'da ızgaranın üst ucunda olması bir sorun mu, yoksa şartnamenin beklenen sonucu mu?
- **real:** deflasyon H99 içinde sıralamayı ya da ölçeği nasıl değiştiriyor? β_f1r ve β_f1 farkı.
- **clip:** v0'dan farkın nereden geldiği (test arzı kırpılan 20 fold).
- **§6.2:** beklentin real ve pooled için neden tutmadı?
- **Duyarlılıklar** (bilgi; model DEĞİL):
  - (i) havuzdan 2023-03-30 sonrası açık küme arzları çıkarılır;
  - (ii) rejim terimsiz havuz;
  - (iii) λ ızgarası üstten genişletilir.
  
  Her koşu `ekler/sensitivity_runs.jsonl`'a `experiments/log.jsonl` biçiminde yazılır: model_id `ceiling_hazard_v1_pooled__sens_<ad>`, `kind: sensitivity`. Dondurma görevi bunları günlüğe ekler.

**5. Hüküm** — `docs/fable_faz7_audit/AUDIT.md`
- Dört model_id için ayrı ayrı `FREEZE_OK` ya da `FREEZE_BLOCKED` + neden.
- Yeniden üretim tablosu: her karşılaştırma için maks |Δ|.
- Sızıntı ve sıra kanıtları.
- Mutasyon tablosu: mutasyon · test · kırmızı mı.
- Tanı paragrafı ve duyarlılık tablosu.
- Bulgular önem derecesiyle (KRİTİK / ÖNEMLİ / KÜÇÜK) ve her biri için öneri. Her bulguda "kodu şartnameye uydurmak" mı, "şartname değişikliği = yeni model_id" mi olduğu açıkça yazılır.
- **Dondurma görevi için notlar:**
  - uygulamanın (Rust) v1 için gerekenleri: f1r, TÜFE tablosu ve aylık ekleme yolu, r, genel kırpma uyarısı;
  - altın vektör planı: 19 → 23;
  - eski kohort ikinci kayıtları (`--only-missing-models`) ve model başına kapı (§7.3) için dikkat noktaları.
- **Uygulama için bir cümle:** yakın dönem sonucu ve "kasa: bekliyor" kartta nasıl gösterilmeli.

**Tek oturumda bitmezse:** 1–3 tamamsa hükmü yaz, 4'ü açık bırak. 1 bitmediyse hüküm `FREEZE_BLOCKED (denetim tamamlanmadı)`. Her durumda eldekini `(partial)` mesajıyla commit et.

## Commit
`git add -A` yok.
```
git add docs/fable_faz7_audit docs/prompts/FAZ7_FABLE_V1_REPRO_AUDIT.md
git commit -m "BORSAI_FAZ7_FABLE_REPRO_AUDIT: independent reproduction and conformity audit of ceiling hazard v1 family, mutation run, diagnosis" -- docs/fable_faz7_audit docs/prompts/FAZ7_FABLE_V1_REPRO_AUDIT.md
```
`index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.

## Teslim (rapor)
- Commit hash'i ve `git show --stat`; `docs/fable_faz7_audit/` dosyaları ve sha256'ları (`SHA256SUMS`).
- Dört FREEZE hükmü.
- Yeniden üretim maks |Δ| tablosu (1a–1e).
- Sızıntı ve sıra kanıtları.
- Mutasyon tablosu.
- Tanı özeti (5 satır) ve duyarlılık tablosu.
- Bulgular ve öneriler; açık konular; dondurma notları.

## Kabul kapısı
- **K1** Yeniden üretim:
  - TÜFE (sha, değerler, 10 yayım tarihi), v2'nin 71 açık satırı, altı ledger, dört nihai fit önizlemesi ve MODELS.md Faz 7 hücreleri bağımsız betikle eşleşti (durum ve λ birebir, sayılar |Δ| ≤ 1e-9);
  - ya da eşleşmeyen her şeyin kök nedeni yazılı ve ilgili hüküm `FREEZE_BLOCKED`.
- **K2** Sızıntı (i)–(vi) ve sıra kanıtlarının her biri komut ve çıktıyla yazılı; kasa denetimleri yalnız sayı basıyor.
- **K3** En az 15 mutasyon koşuldu, her birinin sonucu çıktıyla; kırmızı olmayanlar bulgu olarak yazılı.
- **K4** J1–J16, beşinci J16 istisnası ve A/B'de değişen testlerin her biri hükümlü.
- **K5** Commit yalnız `docs/fable_faz7_audit/` ve bu görev dosyası; `registry/`, `data/`, `scores/`, `models/`, `app/` önce/sonra eşit.

KITAP_AUDIT_3: [P] 0 kritik, 2 orta, 1 düşük; [K] 5; [B] 3

# AUDIT_3_SONRASI — Listeleme sonrası modeller, ölçüm ve kuralların bağımsız denetimi

Görev: `docs/prompts/FAZ9_KITAP_AUDIT_3_SONRASI.md` (TASK_ID `BORSAI_FAZ9_KITAP_AUDIT_3_20261008`). Kapsam: `kitap/05_listeleme_sonrasi_modeller.md` ve `kitap/06_olcum_ve_kurallar.md`. Denetçi: Fable (Claude Code), 2026-10-11/12. HEAD `ee3796d`; ağ yok; git yalnız okuma (`GIT_OPTIONAL_LOCKS=0`). Kılavuz iddia listesi olarak kullanıldı; kanıt yalnız repodaki dosyalar, git geçmişi ve bu denetimin kendi hesaplarıdır. Bütün betikler `ekler/3/betikler/` altındadır ve **`borsai` import etmez** (yalnız stdlib; `s6b` ve `s7` ayrıca numpy); çıktıları `ekler/3/*.txt|json`.

İşaretler: **[ÖLÇTÜM]** kendi hesabım / komut çıktısı; **[ÇIKARIM]** yorum.

## 1. Özet

1. **Yayımlanan skorlar kayıtlardan yeniden üretilebiliyor.** Canlı sicilin 27 model × 7 arz = 189 (model, arz) çiftinin sınıfı SPEC_SCORING §5–§6 formülüyle git DAG'ı ve kanıt dosyalarından sıfırdan hesaplandı: `scores.json` ile 189/189 aynı (111 LATE_RECORD, 1 LIVE, 77 RETRO), sayaçlar aynı [ÖLÇTÜM `s2`]. 7 POST_BREAK makine kaydı pinli bültenlerden sıfırdan üretildi: p_F1/p_F2 maks |Δ| = 0, yastık aritmetiği birebir, 7/7 RETRO [ÖLÇTÜM `s6`]. `post_d1_hazard_v0` nihai fit'i sıfırdan kuruldu: λ = 30, δ bit-eşit, iç CV tablosu 9/9 eşit [ÖLÇTÜM `s6b`].
2. **Kesim kuralı sızıntısız.** 27 ledger'ın bütün fold'larında eğitim kümesi hash'i ya da PP hash'i bağımsız kurguyla aynı (351/351 × 9 ledger, 345/345 × 3, 87/87 × 12, 82/82 kırılma); hiçbir eğitim satırının etiket seansı kesime eşit ya da sonra değil; 89/88/87/87 ve n = 87 yeniden çıktı [ÖLÇTÜM `s3`].
3. **Bootstrap ve hüküm dili.** 19 hücre (5 aile) kendi `random.Random(20260921)` blok bootstrap'ımla ledger'lardan yeniden üretildi; fark ve aralık uçları `scores.json` / `scores_break.json` ile bit-eşit. `scores*.json`'daki 1 974 hücrenin hepsinde hüküm sözcüğü kural 6'ya uygun (0 ihlal) [ÖLÇTÜM `s4`].
4. **İki proje hatası (ORTA), ikisi de belge/süreç düzeyinde; hiçbir sayı, tahmin ya da sınıf değişmez.** (P1) CLAUDE.md'nin andığı iki belge (`docs/checkup_20260921/CHECKUP.md`, `docs/fable_audit_20260921/AUDIT.md`) repoda yok ve hiç commit edilmemiş; kodun ve şartnamenin bootstrap gerekçesi olarak atıfladığı "AUDIT §1.2-c" repodan doğrulanamıyor. (P2) CLAUDE.md "kodla zorlanır" der; kural 1'in "ilk işlem gününden önce commit edilir ve push edilir" cümlesi ile "push/tag/amend yalnız proje sahibi" ilkesi kodla zorlanmıyor (yalnız sınıflama yansıtıyor: 7/7 kayıt LATE); push kanıtı dosyası çevrimdışı yalnız iç tutarlılık denetiminden geçiyor, iç tutarlı sahte bir kanıt hiçbir testi kırmızı yapmıyor [ÖLÇTÜM mutasyon m].
5. Mutasyon denetimi (klonda): 16 mutasyon koşusu (görevin (a)–(i) + c2, g2, i2, j, k, l, m, n), hepsi klonda commit'lenerek; 15 hedef kümesinde kırmızı. (i) günlük satırı silme ilk hedef kümesinde (`test_experiment_log`, `test_faz8_golden::test_b7`) **yeşil kaldı**, Faz 8 altın testleriyle (`test_b1`, `test_b2`, `test_b6`) kırmızı: append-only genel bir bekçiyle değil, faz başına altın/manifest testleriyle korunuyor. (m) iç tutarlı sahte push kanıtı: `test_push_proof` 8/8 yeşil; yalnız commit'li skor pini (`test_committed_scores_json_matches_recomputation`) kırmızı.
6. Kılavuz hataları küçük: `experiments/log.jsonl`'daki farklı `model_id` sayısı 48 (kılavuz 49); `training.cutoff_date` belirsizliği ölçülerek çözüldü (2026-08-13 = eğitim arzlarının son D10 seansı; 2026-08-05 = son d ≥ 2 PP satırı).

## 2. Bulgular tablosu

| no | tür | önem | kılavuzdaki yer | kısa tanım | kanıt | öneri |
|---|---|---|---|---|---|---|
| P1 | P | ORTA | §6.16 son paragraf; §6.7.3 ("AUDIT §2.5"), §6.7.5 ("AUDIT §1.2-c") | `CLAUDE.md:20` iki belgeye yol verir: `docs/checkup_20260921/CHECKUP.md`, `docs/fable_audit_20260921/AUDIT.md`. İkisi de repoda yok; `git log --all` bu yollar için boş (hiç commit edilmemiş). `borsai/metrics.py`, `borsai/report.py`, `borsai/report_faz1b.py`, `docs/specs/SPEC_SCORING.md` §8 ve `SPEC_PB_V0.md` bootstrap yöntemini ve blok gerekçesini "AUDIT §1.2-c / §2.5"e dayandırır; bu kaynak repodan doğrulanamaz. | `git ls-files docs/checkup_20260921 docs/fable_audit_20260921` → 0; `git log --oneline --all -- <yollar>` → boş [ÖLÇTÜM]. Kılavuz bunu "belirsiz" diye bırakmış; repo içi çelişki (proje belgesi var olmayan dosyaya işaret ediyor) proje hatasıdır. | Belgede: CLAUDE.md yolunu düzelt ya da iki belgeyi (yalnız metin; kasa kodu ve bülten adı içermeden) repoya ekle. Model_id gerekmez. |
| P2 | P | ORTA | §6.1 ("her kuralın arkasında … kırmızıya dönen bir test vardır"), §6.2 kural 1 ve genel ilkeler | CLAUDE.md "kodla zorlanır" der. Zorlanmayanlar: (a) kural 1 "İlk işlem gününden önce commit edilir ve push edilir" — hiçbir bekçi geç kaydı engellemez ya da kırmızı yapmaz; sonuç yalnız sınıflamada LATE_RECORD olur (bugün 7/7 kayıt LATE, LIVE 0 — yalnız eski repodan gelen NETGL kaydı LIVE). (b) "git push, tag ve amend yalnız proje sahibi" — kodda hook ya da test yok. (c) Push kanıtının gerçekliği: `push_proof.validate_proof` yalnız şema, sha biçimi, `created_at` biçimi ve URL eşitliğini denetler; `created_at` iki alanda da değiştirilmiş iç tutarlı bir kanıt dosyası sınıfları değiştirir ve `test_push_proof` 8/8 yeşil kalır; yalnız commit'li `scores.json` pini (`test_committed_scores_json_matches_recomputation`) kırmızı olur — skorlar bir kez yeniden üretilip commit'lenirse sahte kanıtın verdiği sınıf dosyaya yerleşir ve hiçbir test kalmaz. | `borsai/push_proof.py:validate_proof`; `s2` (7/7 LATE); mutasyon `m_m_forged_proof_consistent` [ÖLÇTÜM]. | Belgede: CLAUDE.md'de hangi maddenin bekçisi olduğunu, hangisinin yalnız sınıflamayla yansıdığını yazmak; isteğe bağlı kodda: `push_proof --verify <sha>` (GitHub status API'den `id`/`created_at` yeniden çekip dosyayla karşılaştırma) ve pre-push hook. Model_id gerekmez. |
| P3 | P | DÜŞÜK | §6.13.2 | `experiments/log.jsonl`'daki 72 backtest satırının 4'ü (`faz7_golden` bağlamı, dört v1 kimliği) HEAD'de var olmayan ledger sha'larını adlandırır: dosyalar `faz7_golden_b1` koşusunda yeniden üretilip üzerine yazıldı (SPEC_DEVIATIONS J23). Eski ledger'lar yalnız `70b67d1` ağacından geri alınabilir. Günlük append-only kalmış, satır silinmemiş; ama "günlükteki her resmi koşu HEAD'deki bir dosyayla eşleşir" iddiası bu dört satır için tutmaz. | `s8`: ledger sha'sı HEAD'de bulunan 69/72; eksik 4'ü `git show 70b67d1:…` ile doğrulandı [ÖLÇTÜM]. | Belgede (experiments/README.md ya da MODELS.md): üzerine yazılan altın dosyaların eski sha'larının hangi commit'te olduğu notu. Model_id gerekmez. |
| B1 | B | — | §6.10.4 (NETGL × `v1_5_h99` LIVE) | Sınıf CLAUDE.md kural 3'ün lafzına uygun: `v1_5_h99.json`'u ekleyen `5fa849d` (kanıt 2026-09-22T14:06:00Z), NETGL sonucunu getiren `f1f9d44`'ün atası; kayıt (eski repo, kanıt 2026-09-16T11:32:27Z) D_1 = 2026-09-17'den önce. Ruhu: model JSON'u bu repoya D_1'den 5 gün sonra girdi; "aynı model" bağı yalnız port paritesine (`test_port_vs_legacy`, legacy spec sha `1245bf0f…` JSON'da ve `specs.py`'de pinli) ve girdi eşitliğine (`test_inputs_agree_with_legacy_frozen_packets`) dayanır. Kural "sonuç repoya girmeden önce" diyor, "D_1'den önce" demiyor; tanım gereği uygun. Yorum gerektirir. | `s2` çıktısı; `models/v1_5_h99.json:359`; `borsai/specs.py:47` [ÖLÇTÜM] | Karar proje sahibinin: lafız yeterli mi, yoksa kural 3'e "model push kanıtı D_1'den önce" eki mi? Eklenirse tek LIVE satırı LATE olur (skor tanımı değişir → SPEC değişikliği). |
| B2 | B | — | §6.3.4 ("Kanıt sahte ya da eski olabilir mi?") | 175 commit'in 162'si en az bir kanıtla kapsanıyor; 13 kapsanmıyor (hepsi `4d3c9a2`'den sonraki Faz 8 canlı / Faz 9 arayüz commit'leri; HEAD dahil). Makine kayıtları (`7ee0027`) ve bugünkü `scores_break.json` kanıtsız; şartname gereği (§9.1) bu beklenen, ama "en son durum push edilmiş" iddiası HEAD için gösterilemez. | `s8`/komut [ÖLÇTÜM] | Bilgi. HEAD için `push_proof` alınınca kapanır. |
| B3 | B | — | §5.2.4 (`training.cutoff_date` "belirsiz") | Ölçüldü: 2026-08-13 = 81 eğitim arzının 10. seansının en geç tarihi (JSON `training.cutoff_date`, H43 metniyle aynı); 2026-08-05 = d ≥ 2 PP satırlarının son tarihi (Fable Faz 5 denetiminin sayısı). İki sayı iki tanımdır, ikisi de doğru; repo içinde çelişki yok. | `s6b` + komut [ÖLÇTÜM] | Kılavuz notu; proje değişikliği gerekmez. |
| K1 | K | DÜŞÜK | §6.13.2 | "Günlükte 49 farklı model_id geçiyor": `model_id` dolu satırlarda 48 farklı değer; `null` sayılırsa 49. | `s8` [ÖLÇTÜM] | — |
| K2 | K | DÜŞÜK | §6.5.6 tablo ("`test_acceptance_backtest.py::test_1`") | Tek test yok; üç test `test_1_fold_plan_counts`, `test_1_training_tickers_sha256_351_of_351`, `test_1_fold_metadata_equal`. | `grep` [ÖLÇTÜM] | — |
| K3 | K | DÜŞÜK | §6.15.6 tablo (`test_predict.py` "predict yalnız stdlib") | Testin adı `test_k2_predict_import_list_is_stdlib_only` (+ `test_k2_predict_runs_without_numpy_or_sklearn`); kılavuz adı yazmıyor, satır doğru. | `grep` | — |
| K4 | K | DÜŞÜK | §6.9.5 | "kartta 23, günlükte 24" doğru; ek olarak v2 veri sürümü kartları 2 059 (5 backtest çifti + 2 054 keşif) — kılavuz yalnız H99 sürümünü anlatıyor. | `s8` [ÖLÇTÜM] | — |
| K5 | K | DÜŞÜK | §6.5.3 son paragraf; §6.5.4 PLAN_FALL satırı | Düşen arz `h99` planının eğitim kümesi "f3 dolu 97" değil, f3 **ve** ek satış alanı dolu arzlardır (K6: 94). D5\|QUICK fold'unda bu iki arzı dışlar (ledger 93, saf f3 kuralı 95); sızıntı değil, küme tanımı. Kılavuz PLAN_FALL satırında kümeyi yazmıyor. | `s3`: 163/164 fold saf f3 kuralıyla, 1 fold küme tanımıyla açıklanıyor [ÖLÇTÜM] | — |

## 3. Bölüm bölüm kontrol listesi

Her satır: kontrol edilen iddia sayısı / tutan / tutmayan. "Tutmayan" yalnız yukarıdaki bulgularla sınırlıdır.

**Bölüm 5**

| § | İddia | Tutan | Tutmayan | Not |
|---|---|---|---|---|
| 5.1 | 9 | 9 | 0 | Lo zinciri 7 kayıtta birebir; teraziler/sınıflar kodla aynı; push kanıtı yöntemi dosyalarla aynı |
| 5.2.1–5.2.3 | 8 | 8 | 0 | Kapsam, özellikler, ofset (γ, β değerleri JSON ile aynı) |
| 5.2.4 | 12 | 12 | 0 (B3) | 81/409/67/342, λ tablosu 9/9, δ, μ/σ, p05/p95, çözücü 4 yineleme — sıfırdan aynı (`s6b`) |
| 5.2.5 | 7 | 7 | 0 | NETGL: z_base, η, u, kayma +0.016, h_2 0.1392 (ana 0.1373), S_cond tablosu, RPS_1 0.0576/0.0587 — birebir (`s6b`) |
| 5.2.6 | 10 | 10 | 0 | 87 fold: FIT_OK 70 / INSUFFICIENT 1 / NOT_APPLICABLE 16; λ 3→22, 10→14, 30→32, INF→2; δ_lock < 0 63/63, δ_turn > 0 68/68; RPS_1 −0.0105 [−0.0264, +0.0058]; Brier k = 2 −0.0512 [−0.1010, −0.0097]; k = 10 +0.0095 [−0.0034, +0.0233]; kalibrasyon 0.1556/0.1571 (`s4`) |
| 5.2.7–5.2.8 | 8 | 8 | 0 | Sınıf formülü kodla aynı (`class_post_d1`); 7/7 RETRO, `registry/post_d1/` yok; `7c18c0f` `f1f9d44`'ün torunu (`s2`, git) |
| 5.3.1–5.3.4 | 9 | 9 | 0 | Kırılma tablosu b dağılımı 18/11/4/13/12/8/6/6/4, b = 10: 3, L = 10: 14 (`s3`) |
| 5.3.5–5.3.6 | 8 | 8 | 0 | JSON katsayıları, iç LOOCV tablosu, @ZERO 25/82 ve 11/78 (Fraction), by_type 6/47, 19/35 |
| 5.3.7–5.3.9 | 11 | 11 | 0 | Yakın dönem 6 hücre fark ve aralık bit-eşit (`s4`); C dağılımı 32/27/7/3; F2 n 52 (16 ay); kalibrasyon 0.3315/0.2899, sınıf içi 0.251/0.122 ve 0.450/0.536 |
| 5.3.10–5.3.11 | 5 | 5 | 0 | `promotion` k1 doğru (`scores_break.json`); rejim ve bant sabitleri JSON ile aynı |
| 5.3.12 | 9 | 9 | 0 | NETGL kaydı adım adım yeniden hesaplandı: oran 0.103669, ln −2.26656, kırpma, z, p_F1 0.4990578…, p_F2 0.3043277… bit-eşit (`s6`) |
| 5.4 | 9 | 9 | 0 | 7 kaydın min10/k_b/r_b/impossible birebir; TKNKA imkânsız; NETGL 16.29 gerçekleşti |
| 5.5 | 12 | 12 | 0 (B2) | Mükerrer anahtar, içerik adresli ad, bekçi kuralları kodla aynı; DAG: `4d3c9a2` iki sonuç commit'inin torunu; sınıf kanıtı 7/7 `scores_break.json` ile aynı; bilgi tablosu y_F1/y_F2 THM alt limitiyle 7/7 aynı |
| 5.6 | 10 | 10 | 0 | Faz 5: 87/87, λ 70/70, 1.5e-11, 12 mutasyonun 11'i (18 koşunun 17'si); Faz 8: REPRO_OK, 13/13, N20 tablosu — AUDIT dosyalarıyla aynı |
| 5.7 | 10 | 10 | 0 | — |

**Bölüm 6**

| § | İddia | Tutan | Tutmayan | Not |
|---|---|---|---|---|
| 6.1 | 2 | 1 | 1 (P2) | "Her kuralın arkasında kırmızıya dönen test" bütün maddeler için doğru değil |
| 6.2 | 14 | 12 | 2 (P1, P2) | ipos.csv 7 FROZEN + 19 OUT_OF_SCOPE; `e469a93` `f1f9d44`'ün atası; `sequence_guard`/`sequence_violations` var; `test_guardrails` legacy hash'leri |
| 6.3 | 12 | 12 | 0 (B2) | 31 kanıt; ilk 5fa849d 14:06:00Z, son 4d3c9a2; NETGL legacy kanıtı; INDEX sha'ları 7e636e8b…/94ac36fa…/899cf90c… |
| 6.4 | 6 | 6 | 0 | Tanımlar kodla aynı |
| 6.5 | 15 | 15 | 0 (K5) | 89/88/87/87; 97 f3; 87 fold 24 ay; hash'ler 351/351 ve 87/87 bağımsız kurguyla aynı; BacktestStop bekçileri kodda |
| 6.6 | 12 | 12 | 0 | NETGL örnekleri: D5 tahmin 0.2552, medyan 0.3738, R_D5 0.0784; D10 p 0.6023, taban 0.7071, son-10 0.5; RPS 0.057/0.097/0.124/0.095 — `scores.json` satırından birebir; kırpma yerleri kodla aynı |
| 6.7 | 10 | 10 | 0 | İki uygulama (random/numpy) kodla aynı; v1_5 birincil hücre bit-eşit (`s4`); indeks 100/3899 |
| 6.8 | 8 | 8 | 0 | `verdict` kodu; 1 974 hücrede 0 ihlal; yakın dönem etiketleri üç v1 için `s4` ile aynı |
| 6.9 | 16 | 16 | 0 (K4) | 28 hücre 15/2/11; 293 hücre 168 geçiyor; birincil tablo 9 satır `scores.json` ile aynı; şartname commit'leri uygulama commit'lerinin atası 6/6; PRIMARY_CELLS eski girdileri e469a93'ten beri aynı |
| 6.10 | 14 | 14 | 0 (B1) | Sınıf formülü, 189 çift, self-reported ve invalid_use satırları, 77 RETRO çifti |
| 6.11 | 17 | 17 | 0 | Kayıt alanları, `borsai_dirty = true` 7/7, kural 1 kapsaması 419 kayıtta 0 sorun (7 canlı, 7 makine, 270 eski kohort, 135 eski kohort POST_D1), Faz 2 sıra tablosu kanıt zamanları birebir |
| 6.12 | 20 | 20 | 0 | 135/66/64/4/1/71; 914 pin, MANIFEST_OOT 1 168; sıra: 135/135 ilk kayıt commit'i (`1dcceff`, kanıt 09-24T22:39:24Z) sonuç commit'lerinin (`9e1e992`/`2f914dd`) atası ve kanıtı önce; ek kayıtlar (`28aaa3b`, kanıt 09-29T06:40:55Z) kasa ingest'inden (`2f914dd`, 15:30:41Z) önce, açık küme ingest'inden sonra → 8 yeni model açıkta RETRO, kasada BLIND (tablo ile aynı); v1_5/ceiling/pb_v0 açık ve kasa birincil hücreleri numpy PCG64 ile bit-eşit (`s7`); tablo öteki satırları `scores_oot.json` ile aynı |
| 6.13 | 10 | 9 | 1 (K1) | 2 146 satır, tür ve bağlam sayıları aynı; append-only (her commit'li sürüm sonrakinin bayt öneki); spec/karar belge sha'ları 2 136/2 136 eşit (P3 ledger notu) |
| 6.14 | 5 | 5 | 0 | 312 numaralı satır, bölüm sayıları 12/7/8/20/17/12/47/47/31/23/12/24/33/19; kural 5 taraması: model_id değiştirmeden davranış değiştiren madde yok (J23 ve K14 uygulama düzeltmeleri bayt-eşit ya da sayısal değişmez kanıtlı) |
| 6.15 | 12 | 11 | 1 (K2/K3) | 952 test toplandı; 56 dosya + 9 yardımcı + reference = 66 girdi (ls 67, `__pycache__` dahil); dosya başına `def test_` sayıları örneklenen 10 dosyada aynı |
| 6.16 | 10 | 10 | 0 (P1) | Hükümler AUDIT dosyalarıyla aynı (PUSH_OK, FREEZE_OK ×3/×4/×4, S2_OK 14/16, S6_OK 1349, VAULT_SCORE_OK 34/34, REPRO_OK 13/13) |
| 6.17 | 1 | 1 | 0 | — |

## 4. Kurallar kodla zorlanıyor mu? (adım 1; §6.2)

Mutasyonlar klonda (`/tmp/borsai_kitap_audit_3/clone`, HEAD `ee3796d`, `.venv` bağlı) commit'lenerek uygulandı, hedef testler koştu, klon `reset --hard` ile sıfırlandı. Sürücü `ekler/3/betikler/mutations.sh`, çıktılar `ekler/3/mutasyon/*.txt`.

| # | Mutasyon (klonda commit'li) | Hedef testler | Sonuç |
|---|---|---|---|
| 0 | yok (taban) | `test_guardrails`, `test_registry_ipos`, `test_experiment_log`, `test_push_proof`, `test_9d`, `test_9e` | 22 geçti (yeşil taban) |
| a | CITAS kaydından son model çıkarıldı (özet sayaçları düzeltildi) | `test_committed_record_consistency`, `test_committed_scores_json_matches_recomputation` | **KIRMIZI** 2/8 |
| b | NETGL kaydında bir `params_sha256` yanlış | aynı | **KIRMIZI** 2/8 |
| c | `pair_class`: `live = True` (kanıtsız kayıt LIVE) | `test_scoring -k test_5` | **KIRMIZI** 2/10 (`test_5b`, `test_5e`) |
| c2 | aynı mutasyon | skor pini | **KIRMIZI** 1/1 |
| d | `_one_scale` farklı ölçekleri kabul eder | `test_9d`, `test_scoring_conditional`, `test_13_13_scale_mix_is_refused`, `test_scale_mix_post_d1` | **KIRMIZI** 3/19 |
| e | `models/v1_5_h99.json` D5 katsayısı +0.001, aynı model_id | `test_models`, `test_faz1b_guardrails::…unchanged`, kayıt tutarlılığı | **KIRMIZI** 3/33 |
| f | `legacy/scripts/__init__.py` sonuna bir bayt | `test_guardrails` | **KIRMIZI** 1/3 |
| g | `data/outcomes/NETGL.csv` h = 5 kapanışı 27.52 → 27.50 | `test_l5_outcomes_regenerate_byte_equal`, Faz 8 canlı yeniden hesap, skor pini | **KIRMIZI** 2/3 |
| g2 | aynı satırın THB sha'sı bozuk | `test_l5…`, `test_outcome_rows_h_ge_2_follow_bulletin_commits`, makine kaydı testi | **KIRMIZI** 1/3 |
| h | `registry/records/CITAS/*.json` `git rm` | `test_each_frozen_ipo_has_an_active_record…`, `test_sequence_rule_outcomes_follow_models_and_records`, skor pini | **KIRMIZI** 3/3 |
| i | `experiments/log.jsonl`'dan Faz 8 resmi backtest satırı silindi | `test_experiment_log`, `test_faz8_golden::test_b7` | **YEŞİL** 5/5 |
| i2 | aynı mutasyon | `test_faz8_golden` (tamamı), `test_faz8_model`, skor pini, `test_l9`, Faz 8 canlı | **KIRMIZI** 3/26 (`test_b1`, `test_b2`, `test_b6`) |
| j | `registry/ipos.csv`'den NETGL satırı silindi | `test_registry_ipos`, `test_7_denominator` | **KIRMIZI** 3/6 |
| k | `sequence_violations` hedef listesi boşaltıldı | `test_outcome_guard -k test_10` | **KIRMIZI** 7/8 |
| l | `verdict`: "geçiyor" aralık yerine noktasal fark < 0 | `test_9a`, `test_9e`, `test_backtest_primary_cells_and_verdicts`, `test_metrics` | **KIRMIZI** 1/7 (`test_9e`) |
| m | `7cb49cf` kanıtının `created_at`'i iki alanda da 2026-08-01'e çekildi (iç tutarlı sahte) | `test_push_proof`, skor pini | `test_push_proof` 8/8 **yeşil**; skor pini **KIRMIZI** |
| n | `models/INDEX.json`'dan `v1_6_h99` girdisi silindi | `test_models`, kayıt tutarlılığı | **KIRMIZI** 8/32 |

Okuma: (a)–(h), (j)–(n) kodla yakalanıyor. (i) yalnız faz altın testleriyle yakalanıyor; `test_experiment_log` ve `test_b7` (5d84e88 sürümünün bayt öneki) sonradan eklenen bir satırın silinmesini görmez. (m) P2'nin (c) kalemidir. Klon her mutasyondan sonra `reset --hard` ile tabana döndü ve sonda temizdi.

Madde madde (zorlayan kod/test; mutasyonla gösterim):

| CLAUDE.md maddesi | Zorlayan kod / test | Mutasyon | Sonuç |
|---|---|---|---|
| 1 — kayıt TÜM modelleri ve hash'leri içerir | `freeze.build_record` (INDEX'in her modeli), `test_freeze_records::test_committed_record_consistency` (liste INDEX'in ön eki, sha'lar eşit), `test_record_contains_every_registered_model` | (a), (b), (n) | (a) `test_committed_record_consistency[CITAS]` + skor pini kırmızı; (b) `[NETGL]` + skor pini kırmızı; (n) INDEX'ten model silinmesi: `test_models` + 7 kayıt tutarlılık testi kırmızı |
| 1 — D_1'den önce commit + push | **Bekçi yok**; sınıflama LATE_RECORD yansıtır (`scoring.pair_class`) | — | zorlanmıyor (P2) |
| 1 — zaman kanıtı push | `push_proof.validate_proof`, `scoring.proof_time`; `test_push_proof`, `test_scoring::test_5d` | (c), (m) | (c) `live = True`: `test_5b_late_record`, `test_5e_inputs_not_pit_is_retro`, skor pini kırmızı; (m) sahte kanıt: yalnız skor pini kırmızı (bkz. P2) |
| 1 — kayıt silinmez / iptal kaydı | `freeze.cancel_record` (D_1'den sonra `FreezeError`), `_write_new('xb')`; `test_freeze_records::test_each_frozen_ipo_has_an_active_record…`, `scoring.sequence_violations` (kayıt commit'i yoksa ihlal) | (h) | (h) CITAS kaydı silinince `test_each_frozen_ipo_has_an_active_record…`, `test_sequence_rule_outcomes_follow_models_and_records` (kayıt commit'i yok → ihlal) ve skor pini kırmızı |
| 1 — POST_D1 / POST_BREAK cümleleri | `registry.t_open`, `class_post_d1`, `class_break_evidence`, bekçiler; `test_faz5_live`, `test_faz8_live` | — (sentetik testler mevcut) | kodda |
| 2 — payda | `registry.validate_ipos`, `test_registry_ipos::test_known_seven_present…`, `test_completeness_against_official_trading_start_notices` | (j) | (j) NETGL satırı silinince `test_known_seven_present…`, `test_completeness_against_official_trading_start_notices`, `test_7_denominator` kırmızı |
| 3 — teraziler toplanmaz | `scoring._one_scale`, `merge_scales`, `post_break.merge_cells`; `test_9d`, `test_13_13_scale_mix_is_refused`, `test_scale_mix_post_d1` | (d) | (d) `_one_scale` ölçek denetimi kaldırılınca üç test kırmızı (`DID NOT RAISE`) |
| 3 — prospektiflik tarihlerden | `pair_class` + `outcome_ingest_commit`; `test_5a–5j` | (c) | (c) `live = True`: `test_5b_late_record`, `test_5e_inputs_not_pit_is_retro`, skor pini kırmızı; (m) sahte kanıt: yalnız skor pini kırmızı (bkz. P2) |
| 4 — deney günlüğü append-only | `backtest.append_log` ('a' kipi); `test_experiment_log::test_official_log_contains_golden_runs`, `test_faz8_golden::test_b7` (git: yalnız ekleme) | (i) | (i) Faz 8 resmi satırı silinince `test_experiment_log` (4/4) ve `test_b7` **yeşil**; `test_faz8_golden::test_b1/b2/b6` kırmızı (ledger sha günlükte yok; sayaç; MODELS.md) |
| 5 — değişiklik = yeni model_id | `freeze.freeze` üzerine yazma reddi; INDEX sha pinleri: `test_models::test_index_lists_all_frozen_models_with_hashes`, `test_frozen_files_are_consistent…`, `test_faz1b_guardrails` | (e) | (e) `v1_5_h99.json` katsayısı +0.001: `test_index_lists_all_frozen_models_with_hashes`, `test_v1_5_h99_refit_reproduces_frozen_parameters`, `test_faz1a_model_files_and_index_entries_unchanged` kırmızı |
| 6 — sonuç yalnız resmi THB/THM | `outcomes.fetch` (sha ↔ MANIFEST), `test_faz5_live::test_l5_outcomes_regenerate_byte_equal`, `test_outcome_guard::test_outcome_rows_h_ge_2_follow_bulletin_commits` | (g), (g2) | (g) NETGL D5 kapanışı 27.52 → 27.50: `test_l5_outcomes_regenerate_byte_equal` ve skor pini kırmızı; (g2) satırın THB sha'sı bozulunca `test_l5` kırmızı (`test_outcome_rows_h_ge_2_follow_bulletin_commits` ve makine kaydı testi yeşil: onlar commit ve D_1..D_b sha'larına bakar) |
| 6 — tanımlar ilk skorlamadan önce kodda | git DAG: `e469a93` → `f1f9d44` [ÖLÇTÜM]; test yok (tarihsel olgu) | — | DAG ile sabit |
| 6 — eşleşik skor, aralık, "geçiyor" dili | `scoring.paired_metric`, `verdict`; `test_9a`, `test_9e`, `test_metrics` | (l) | (l) `verdict` noktasal farka çevrilince `test_9e_verdict_vocabulary` kırmızı (`test_9a` ve `test_metrics` yeşil: sentetik aralık 0'ı simetrik içeriyor; `test_backtest_primary_cells_and_verdicts` yeşil: birincil hücreler zaten geçiyor) |
| Sıra kuralı | `outcomes.sequence_guard` (indirme), `scoring.sequence_violations` (geçmiş); `test_outcome_guard` 10–10h; eski kohort: `outcomes_oot.download_gate`, G5′ | (k) | (k) `sequence_violations` boş liste: `test_10`, `10c`–`10h` kırmızı (7/8) |
| Yalnız resmi kaynak (girdiler) | `registry.inputs_pit_problems` (kaynak sha + yayın zamanı), `test_registry_inputs`, `test_source_documents_predate_first_trading_day` | — | kodda |
| push/tag/amend yalnız proje sahibi | **Kod yok** (hook yok) | — | zorlanmıyor (P2) |
| legacy/ değiştirilmez | `test_guardrails::test_legacy_files_match_provenance_hashes` | (f) | (f) legacy dosyasına bir bayt: `test_legacy_files_match_provenance_hashes` kırmızı |

## 5. Bağımsız yeniden hesaplananlar

| Sayı | Betik | Benim sonucum | Repodaki değer |
|---|---|---|---|
| Canlı sınıflar (27 × 7) | `s2_live_registry.py` | 111 LATE / 1 LIVE / 77 RETRO; `v1_5_h99` n_rows 7, n_scored 6, n_live 1, n_late 5, n_refused 1 | `scores.json` birebir (0 uyuşmazlık) |
| Kural 1 kapsaması | `s2` | 419 kaydın hepsi kendi commit'indeki INDEX'in bütün modellerini ve sha'larını taşır | — |
| Kesim hash'leri | `s3_cutoff_scan.py` | PLAN_V15 351/351 (9 ledger), PLAN_PB 345/345 (3), tavan PP 87/87 (12 ledger), post_d1 71/71 (16 NOT_APPLICABLE), v1 clip/real 87/87, pooled max tarih < T 97/97, yol hücreleri < D_1 87/87, kırılma F1 küme 82/82 | ledger sütunları |
| Skorlanabilir fold | `s3` | D1 89, D3 88, D5 87, D10 87 (PLAN_V15); PB 87/87/87/84; tavan 87; post_d1 70; kırılma 69 | `log.jsonl` `folds_scorable`, MODELS.md |
| `v1_5_h99` D5 MAE − medyan | `s4_bootstrap.py` | −0.08386585972 [−0.13431795513, −0.03211069342], n 87, 23 ay, 58/29/0 | `scores.json` bit-eşit |
| `v1_5_h99` D5 − her zaman tavan; D10 Brier − taban | `s4` | −0.11118 [−0.19083, −0.02782]; −0.03910 [−0.07562, +0.00234] | bit-eşit |
| `ceiling_hazard_v0` RPS − KM genişleyen / son-10 / @INF | `s4` | −0.05686 [−0.08326, −0.02865]; −0.04956 [−0.07515, −0.02186]; −0.05025 [−0.07238, −0.02632] | bit-eşit |
| `pb_ceiling_v0` RPS − KM genişleyen | `s4` | −0.03235 [−0.05444, −0.01136] | bit-eşit |
| `ceiling_path_v0` D5 MAE − medyan | `s4` | −0.11585 [−0.16114, −0.07382], n 85 | bit-eşit |
| `post_d1` RPS_1, Brier k = 2, k = 10 | `s4` | −0.010478 [−0.026400, +0.005814]; −0.051155 [−0.101027, −0.009717]; +0.009521 [−0.003366, +0.023329]; n 70, 22 ay | MODELS.md / kılavuz 4 ondalık aynı |
| `break_floor_v0` yakın dönem 6 hücre | `s4` | F1 − ürün −0.190384 [−0.252035, −0.124701]; F1 − @ZERO −0.028085 [−0.045282, −0.007396]; by_type +0.0106 [−0.0047, +0.0282]; F2 − ürün −0.0572 [−0.0847, −0.0239]; F2 − @ZERO −0.0001 [−0.0131, +0.0179]; bilgi +0.1623 [+0.1087, +0.2139] | `scores_break.json` `backtest_info` bit-eşit; MODELS.md aynı |
| v1 yakın dönem − v0 (clip / real / pooled) | `s4` | −0.00109 [−0.00663, +0.00490]; +0.01040 [+0.00276, +0.01830]; +0.02893 [+0.00886, +0.05183] | `scores.json near_era` bit-eşit |
| (C) pooled − h99 D10 Brier | `s4` | −0.00581 [−0.03401, +0.02195], n 75 | bit-eşit |
| `post_d1_hazard_v0` nihai fit | `s6b_post_d1_fit.py` | 81 arz, 409/67/342; p05/p95, μ/σ, iç CV 9 skor, λ = 30, δ = (−0.3278985872465678, +0.25106109793882575) | JSON bit-eşit (maks \|Δδ\| = 0) |
| NETGL D1 sonrası prova sayıları | `s6b` | h_2 0.1392 (ana 0.1373), S_cond 0.8608 … 0.0422, RPS_1 0.0576/0.0587; E[L] 3.2811, D1 %81.8, j = 3 ve 6'da %66.8, kalan 1.89, %44.6, %5.9 | kılavuz §5.2.5, §1.5/§8.14 (yuvarlamayla aynı) |
| 7 makine kaydı | `s6_machine_records.py` | b, D_b, b_floor, oran, ln, kırpma, z, p_F1, p_F2, min10, k_b, r_b, impossible, inputs_pit_ok, bant — maks \|Δp\| = 0; sınıf 7/7 RETRO, ingest commit'leri `f1f9d44` ×6, `c1eb7ae` ×1 | kayıtlar ve `scores_break.json` birebir |
| Eski kohort birincil hücreler | `s7_oot.py` | `v1_5_h99` açık −0.028153 [−0.080703, +0.022489] n 68; kasa −0.011866 [−0.070594, +0.041197] n 62; `ceiling_hazard_v0` açık +0.068627 [+0.001088, +0.131294]; kasa +0.072833 [−0.000814, +0.138804]; `pb_v0` açık −0.008214 [−0.054995, +0.035828]; kasa +0.030277 [−0.026276, +0.088253] | `scores_oot.json` bit-eşit |
| Eski kohort sıra | `s7` | 135/135 ilk kayıt commit'i ingest'in atası ve kanıtı önce; 8 yeni model: açıkta 0/71, kasada 64/64 kör | `scores_oot.json` n_oot_retro 71, kasa hücreleri var |
| Günlük | `s8_log_hashes.py` | 2 146 satır (2 054/72/19/1); 48 model_id; spec sha 2 116/2 116; her commit'li sürüm sonrakinin bayt öneki | — |
| Kanıt kapsaması | komut | 175 commit'in 162'si kapsanıyor | — |

## 6. Bakılmayanlar

- Tam `pytest` koşusu ve `app/scripts/test.sh` (görev kuralı; kolleksiyon 952 ile sınırlı).
- `docs/SCORES.md`, `SCORES_BREAK.md`, `SCORES_OOT.md`'nin yazılmış JSON'dan bayt-eşit render edildiği (testle pinli; yeniden koşulmadı).
- Düşen arz `pooled`/`addsale` fold'larının eğitim kümesi (v2 tablosu + J10 dışlaması) bağımsız kurulmadı; yalnız h99 kümesi ve ledger'ların iç tutarlılığı.
- `ceiling_hazard_v1_pooled` havuz PP kümesi bağımsız kurulmadı (yalnız `training_max_session_date < T` 97/97).
- Eski kohort ikincil ve keşif hücreleri, yıl/rejim kırılımları, `post_d1` eski kohort hücreleri (yalnız dosyadan okundu; Fable Faz 6/7 kör hesapları iddia olarak kabul edildi).
- Faz 4 tavan yolu hücre atomları ve ürün karşılaştırıcısının backtest değerleri (Fable Faz 8 denetiminin REPRO_OK'u iddia olarak kabul edildi; canlı ürün 7/7 NOT_AVAILABLE).
- `inputs_pit_problems`'ın belge yapısal denetimi (`validate_inputs`) yeniden yazılmadı; yalnız yayın zamanı ve sha eşitliği.
- Rust/uygulama tarafı (Denetim 4'ün işi).
- Kasa üyelerinin kodları yalnız bellekte tutuldu; hiçbir çıktıda yok.

## 7. Proje sahibine açık sorular

1. **P1:** `docs/checkup_20260921/` ve `docs/fable_audit_20260921/` repoya alınacak mı, yoksa CLAUDE.md ve kod yorumlarındaki atıflar mı düzeltilecek?
2. **P2 / B1:** Kural 3'ün lafzı ("sonuç repoya girmeden önce") yeterli mi? "Model push kanıtı D_1'den önce" eki istenirse tek LIVE satırı (NETGL × `v1_5_h99`) LATE'e düşer ve bu bir skor tanımı değişikliğidir (şartname değişikliği).
3. **P2 (c):** Push kanıtlarının GitHub'dan yeniden doğrulanması (status `id` ile GET) isteniyor mu? Çevrimdışı bekçi iç tutarlı sahte dosyayı ayıramıyor.

## 8. Koruma ve hijyen sayımları

- Koruma: dokuz ağaç sha'sı (`borsai data models registry scores app tests legacy CLAUDE.md`) başta (`ekler/3/koruma_once.txt`) ve sonda (`ekler/3/koruma_sonra.txt`) birebir aynı; korunan dizinlerde `git status --porcelain` iki ölçümde de boş. HEAD denetim sırasında `ee3796d`'den paralel denetimlerin commit'leriyle ilerledi; dokuz sha değişmedi.
- Hijyen (rapor + `ekler/3/` altındaki 42 dosya): `th[bm]` + 8 haneli tarih kalıbı **0**; kasa (SEALED) kodu **0** (kodlar yalnız bellekte küme olarak tutuldu; mutasyon çıktılarında bülten adı kalıbı kopyalama sırasında maskelendi: 1 geçiş).
- Geçici dizin `/tmp/borsai_kitap_audit_3/` (klon dahil) commit'ten sonra silindi.

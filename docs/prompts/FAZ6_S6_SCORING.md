# TASK_ID: BORSAI_FAZ6_S6_SCORING_20260925

Model: Opus 5.5 · yüksek. Klasör: ~/Desktop/BorsAi. **Ağ gerekmez ve KULLANILMAZ.** push/tag/amend yok.

## Bağlam
- Eski kohortun açık kümesi (71 arz) için sıra tamamlandı:
  - S2 kayıtları `1dcceff` (push kanıtı 2026-09-24T22:39:24Z);
  - S3a d1_rows `9e1e992` ve S3b post_d1 kayıtları `7ade6a8` (kanıtlar 2026-09-25T13:05:56Z / 13:05:58Z, kanıt commit'i `3c82378`);
  - S5 sonuç satırları `77b54f7` (kanıt commit'i `BORSAI_PUSH_PROOFS: Faz 6 S5 outcome rows (77b54f7)`).
  
  Raporlar: `docs/faz6/S2_RAPOR.md`, `docs/faz6/S3_S5_RAPOR.md`.
- Sonuç takvimi 2023-04-24'ü seans sayar (EK1, SPEC_DEVIATIONS I34–I38). Açık kümede 710 sonuç satırının hepsi `OK`, her üyede 10 seans var.
- Skor kodu var ve sentetik olarak testli (`1d4913e`): `scoring.build_oot_scores`, `write_oot_scores`, `class_oot`, `oot_post_d1_block`. `main()` bu dosyayı yazmıyor (SPEC_DEVIATIONS I1).
- Birincil hücreler değişmez (SPEC_OOT_PRE_H99_V0 §6, I11; kodda `OOT_PRIMARY_CELLS`, `OOT_POST_D1_PRIMARY`). Diğer hücreler "keşif"; yıl kırılımı "ikincil", rejim kırılımı "keşif".
- Önceden yazılmış beklenti SPEC_OOT_PRE_H99_V0 §8'dedir (sonuç görülmeden). **Beklentiden sapma modeli değiştirme gerekçesi değildir.**
- CLAUDE.md kural 3: üç terazi asla toplanmaz. Kural 6: "geçiyor" yalnız aralık 0'ı dışlıyorsa.
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.**
- **Bu göreve özel kural:** sonuçlar artık görünür. Skor tanımları (kayıp, eşleşme, sınıf, bootstrap, n kuralları) bu görevde DEĞİŞTİRİLMEZ. `build_oot_scores` ya da bağlı fonksiyonlarda hata bulursan düzeltme; DUR ve rapora yaz (düzeltmeyi bağımsız el yapar).
- Hijyen: hangi kodun SEALED olduğu yazılmaz. `docs/faz6/dogrulama/EXPOSURE.md` §3'ün ticker listesi okunmaz (T3).

## Paralel
Fable aynı anda `docs/prompts/FAZ6_FABLE_S6_RECOMPUTE.md`'yi koşuyor (kör bağımsız yeniden hesap). Onun dizinine (`docs/fable_faz6_s6/`) ve görev dosyasına dokunma. Commit'lerde yalnız kendi yollarını ver. `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.

## Orkestratörün ölçtükleri (S2 kayıtlarından ve S5 dosyalarından)
Açık küme 71 arz (2020: 4, 2021: 26, 2022: 20, 2023: 21). Sonuç satırları 710/710 `OK`, 71/71 üyede 10 seans. Kayıt durumları, açık küme:

| Model | PREDICTED | REFUSED (kod) | NOT_APPLICABLE_REGIME |
|---|---|---|---|
| v1_5_h99, v1_6_h99, v1_5_market20_v0, ceiling_hazard_v0 | 68 | 3 (F3_MISSING) | 0 |
| ceiling_path_v0 | 67 | 3 (F3_MISSING) | 1 (TICK_TABLE_MISMATCH) |
| pb_v0, pb_ceiling_v0 | 59 | 12 (PB_IDENTITY 6, PB_PRICE_RANGE 4, PB_FIELD_MISSING 2) | 0 |
| pb_ceiling_path_v0 | 58 | 12 (aynı) | 1 (TICK_TABLE_MISMATCH) |
| 7 kural, base_always_ceiling, üç @INF | 71 | 0 | 0 |

post_d1 kayıtları (açık küme 71): PREDICTED 59, REFUSED 3 (F3_MISSING), NOT_APPLICABLE 9 (D1_NOT_CEILING).

## Görev kararları (SPEC_DEVIATIONS bölüm I'ye sıradaki numaralarla)
- **T1:** `python -m borsai.scoring --oot` yalnız `scores/scores_oot.json` ve `docs/SCORES_OOT.md` yazar. Bayraksız `main()` değişmez: `scores.json`, `scores_post_d1.json` ve `docs/SCORES.md` bu görevde yazılmaz. Neden: `SCORES.md` = `render_doc(scores.json, post)` testle pinli ve bekçilerde salt okunur; ayrı dosya üç teraziyi ayrı tutar.
- **T2:** `render_oot_doc(scores_oot)` → `docs/SCORES_OOT.md`, yazılmış JSON'dan üretilir (SCORES.md kalıbı).
  - Başlık `OOT_TITLE` ve kohort sayaçları.
  - Model başına: birincil hücre (fark [%95 aralık], n, blok sayısı, hüküm) ve sayaçlar (n_scored, n_refused, n_not_applicable_regime, n_target_unavailable, n_oot_retro).
  - Birincil hücre için yıl (ikincil) ve rejim (keşif) kırılımları. Keşif hücreleri ayrı, "keşif" etiketli.
  - post_d1 ayrı başlıkla (`OOT_POST_D1_TITLE`, MACHINE_SEQUENCED).
  - Hüküm dili SCORES.md ile aynı: aralık 0'ı dışlıyor ve negatif → "geçiyor (zaman-dışı terazide)"; 0'ı dışlıyor ve pozitif → "geçemiyor"; aksi → "ayırt edilemiyor"; n < 10 → metrik yok; 10 ≤ n < 30 → "yetersiz örnek".
  - Hiçbir yerde backtest ya da canlı sayısı yok, toplam/ortalama yok. Üye başına değer tablosu yok (JSON'da var).
- **T3 (F5, KARARLAR D8-1):** `spk_corporate_action_members(path)` `EXPOSURE.md` §3'ü kodla okur ve kümeyi döner. Denetim: küme ⊆ kohort MEMBER'ları ve eleman sayısı = `registry.N_SPK_CORPORATE_ACTION_ROW_SEEN` (28); değilse hata. `--oot` bunu `build_oot_scores(spk_corporate_action_seen=…)`'a verir.
  - Küme hiçbir yere basılmaz, yazılmaz, loglanmaz.
  - §3'ün biçimine yalnız maskeli çıktıyla bakılır: 2–6 karakterli büyük harf/rakam kümeleri `▢` ile değiştirilir.
  - Test sentetik metinle.
- **T4: Önceden yazılmış akıl-sağlığı denetimleri.** Commit'ten önce; biri tutmazsa commit etme, DUR:
  - 19 modelin her birinde açık küme satırı 71; `n_skipped = 0`, `n_pending = 0`, `n_oot_retro = 0`, `n_target_unavailable = 0`.
  - REFUSED ve NOT_APPLICABLE_REGIME sayıları yukarıdaki tabloyla birebir; `n_scored` = PREDICTED sayısı.
  - `retro_info` boş. Her satırın `class_evidence`'ında `record_proof_before_ingest_proof = true` ve `cohort_gate_ok = true`.
  - post_d1: `n_oot_retro = 0`; satır sayısı ≤ 59; farkın nedeni sayılarla.
  - `code.borsai_dirty = false` (skor C commit'inden sonra üretilir).
  - `scores.json`, `scores_post_d1.json` ve `docs/SCORES.md` baytları önce ve sonra aynı.
- **T5: §8 karşılaştırması.** Raporda her birincil hücre için bir satır:
  - §8'deki yön ve aralık, aynen;
  - gözlenen fark [%95 aralık] ve n;
  - konum: "aralık içinde" / "altında: beklenenden iyi" / "üstünde: beklenenden kötü".
  
  Fark kayıp birimindedir (getiri için kesir). §8'deki "puan" ifadesi belirsizse bunu yaz ve iki okumayı da göster. Nokta tahmini §8 aralığının altındaysa "beklentiden çok iyi" diye işaretle; bağımsız doğrulama paralel Fable görevidir.
- **T6 (EK1/I38 bilgisi):** `v1_5_market20_v0` için f6 penceresi 2023-04-24'ü kesen açık üye sayısını (1) raporla. Birincil hücre o üye çıkarılınca da hesaplanır; etiket "keşif, duyarlılık"; kod yazılmaz.
- **T7:** Raporun başında proje sahibi için sade bir paragraf: hangi model zaman-dışı terazide ne durumda. Terazinin adı her cümlede açık olur; canlı ya da backtest sonucuyla birleştirilmez.

## İzinli izlenmeyen
`docs/prompts/FAZ6_S6_SCORING.md`, `docs/prompts/FAZ6_FABLE_S6_RECOMPUTE.md` ve (Fable koşuyorsa) `docs/fable_faz6_s6/` altındaki her şey. Başka bir şey varsa DUR.

ÖNCE OKU: CLAUDE.md; docs/specs_faz6/SPEC_OOT_PRE_H99_V0.md (§3, §6, §8); docs/specs_faz6/KARARLAR.md (D4, D5, D8); docs/SPEC_DEVIATIONS.md bölüm I; docs/specs/SPEC_SCORING.md (§7, §8); docs/faz6/S3_S5_RAPOR.md; borsai/scoring.py (eski kohort bölümü, `render_doc`, `main`); tests/test_faz6_oot.py (`scored_repo`, `test_build_oot_scores_synthetic`).

## Adımlar
0. **Taban.**
   - HEAD, S5 kanıt commit'inin ya da torununun üstünde. `git status --porcelain` yalnız izinli izlenmeyenleri gösterir.
   - `.venv/bin/python -c "from borsai import outcomes_oot as oo; print(oo.s2_gate_problems(), oo.s3_gate_problems())"` → `[] []`. `77b54f7`'nin push kanıtı `registry/push_proofs/`'ta var.
   - Tam `.venv/bin/pytest -q` ve `bash app/scripts/test.sh` yeşil. Sayılar `docs/faz6/ekler/s6_test_runs.txt`'ye.
1. **Kod (commit C).** T1, T2, T3 ve testleri (sentetik; `scored_repo` kalıbı):
   - `--oot`'un `scores.json`'a dokunmadığı;
   - `SCORES_OOT.md` = yazılmış JSON'un render'ı;
   - T3 ayrıştırıcısı (sentetik metin).
   
   SPEC_DEVIATIONS satırları. Tam pytest + test.sh yeşil → **commit C**.
2. **Skor:** `.venv/bin/python -m borsai.scoring --oot`. T4 denetimleri; tablo `docs/faz6/ekler/s6_denetim.txt`'ye (sayılar ve hücre değerleri; üye başına değer yok).
3. **Commit S6.** Yalnız bu yeni dosyalar yüzünden kırmızı olan temizlik bekçileri deselect edilir (ör. `test_scoring.py::test_faz4_scores_json_existing_blocks_unchanged`, `test_faz5_post_d1.py::test_14_models_goldens_and_read_only_paths_unchanged`). Deselect'li tam koşu yeşil → **commit S6** (yalnız `scores/scores_oot.json`, `docs/SCORES_OOT.md`) → deselect'siz tam pytest + test.sh yeşil. Başka bir kırmızı varsa DUR.
4. **Rapor** `docs/faz6/S6_RAPOR.md` (commit R):
   - C ve S6 hash'leri, T7 paragrafı;
   - T4 tablosu;
   - birincil hücreler tablosu (8 model + post_d1) ve diğer 11 modelin sayaçları;
   - T5 §8 karşılaştırması, T6;
   - yıl ve rejim kırılımları (etiketleriyle) ve keşif hücrelerinin kısa özeti;
   - `n_spk_corporate_action_seen` (yalnız sayı);
   - test sayıları;
   - model geliştirme için gözlemler ("keşif" etiketiyle).

## Kurallar
- Yazılabilir: `borsai/scoring.py` (yalnız T1–T3; skor tanımları değişmez), `tests/test_faz6_s6.py` (yeni) ya da `tests/test_faz6_oot.py`, `docs/SPEC_DEVIATIONS.md`, `scores/scores_oot.json` ve `docs/SCORES_OOT.md` (yalnız CLI ile), `docs/faz6/S6_RAPOR.md`, `docs/faz6/ekler/s6_*`, bu görev dosyası.
- Salt okunur: `models/`, `registry/`, `data/`, `scores/scores.json`, `scores/scores_post_d1.json`, `docs/SCORES.md`, `app/`, `docs/specs*`, `CLAUDE.md`, `legacy/`, diğer `borsai/` dosyaları, `tests/test_outcome_guard.py`, `docs/fable_faz6_s6/`.
- Skor dosyaları elle düzenlenmez.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- `git add -A` yok. Commit'ler (test dosyası adını kullandığınla değiştir):
  ```
  git add borsai/scoring.py tests/test_faz6_s6.py docs/SPEC_DEVIATIONS.md docs/prompts/FAZ6_S6_SCORING.md
  git commit -m "BORSAI_FAZ6_S6_CODE: scoring --oot writes scores_oot.json and SCORES_OOT.md; SPK exposure set read by code (F5)" -- borsai/scoring.py tests/test_faz6_s6.py docs/SPEC_DEVIATIONS.md docs/prompts/FAZ6_S6_SCORING.md
  git add scores/scores_oot.json docs/SCORES_OOT.md
  git commit -m "BORSAI_FAZ6_S6: out-of-time scores of the open set (third scale, never merged)" -- scores/scores_oot.json docs/SCORES_OOT.md
  git add docs/faz6/S6_RAPOR.md docs/faz6/ekler
  git commit -m "BORSAI_FAZ6_S6_REPORT: out-of-time primary cells, sanity checks, comparison with pre-registered expectation" -- docs/faz6/S6_RAPOR.md docs/faz6/ekler
  ```
- Rapor Türkçe.

## Kabul kapısı
- **K1** T1–T3 testli; C sonrası tam pytest + test.sh yeşil.
- **K2** T4 denetimlerinin hepsi tuttu: n_oot_retro 0, sayılar birebir, diğer skor dosyaları bayt-eşit.
- **K3** `scores_oot.json` ve `SCORES_OOT.md` commit'li; §8 karşılaştırması raporda.
- **K4** Sıra C → S6 → R; yalnız izinli yollar; push yok.

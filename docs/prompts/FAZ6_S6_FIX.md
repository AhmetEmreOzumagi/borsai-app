# TASK_ID: BORSAI_FAZ6_S6_FIX_20260925

Model: Opus 5.5 · yüksek (**yeni oturum**; S6'yı koşan oturum değil). Klasör: ~/Desktop/BorsAi. **Ağ gerekmez ve KULLANILMAZ.** push/tag/amend yok.

## Bağlam
- S6 oturumu (`docs/prompts/FAZ6_S6_SCORING.md`) adım 2'de doğru olarak DUR dedi. Kod commit'i `e79a4b7` (`--oot` CLI, render, F5; testli). Eski kohort skor kodunda üç hata bulundu ve kural gereği düzeltilmedi. Tanı dosyası: `docs/faz6/ekler/s6_denetim.txt` §3. İçinde hücre değeri yok; okuyabilirsin.
  - **B1 (KRİTİK):** `oot_post_d1_block`, D1'i tavan kapanmayan açık üyeleri de `post_d1_row`'a sokuyor. `_s_part(S, j = 1, L)` → `conditional_rps` L < j için `ValueError` veriyor ve komut çöküyor. Canlı `post_d1_block` bu arzları hiç satıra sokmuyor (`_d1_label` → `STAGE_NOT_APPLICABLE`, paydada sayılır).
  - **B2 (ÖNEMLİ, hijyen):** `build_oot_scores` üst düzey `retro_info`'yu kasadaki 64 üye × 19 model için dolduruyor. Kasadaki kodların tam listesi açık küme dosyasına yazılırdı. Etiket de yanlış: bu çiftlerin sonucu hiç girmedi.
  - **B3 (KÜÇÜK):** `oot_post_d1_block`, `post_d1_row`'a `path_params = None` veriyor. Canlı blok `ceiling_path_v0` JSON'unu (`params["path_secondary"]`) yüklüyor. Bu yüzden SPEC_POST_D1_V0 §4'ün path_conditional ikincil hücreleri eski kohortta hiç üretilmiyor.
- Listeleme öncesi 19 model etkilenmiyor. S6'nın T4 denetimleri o bloklarda tuttu: 19 × 71 satır OOT_BLIND, sayılar birebir.
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** Bu görev hiçbir modeli, kaydı, sonuç satırını ya da skor tanımını değiştirmez. Yalnız eski kohort post_d1 bloğunu canlı bloğun tanımına (SPEC_POST_D1_V0 §4, §7; SPEC_DEVIATIONS I11, I13, I23) uydurur ve kasa hijyenini düzeltir.

## Körlük (bu görev sonuçlara bakmaz)
- `scoring --oot`'u ya da `build_oot_scores`'u **gerçek repoda çalıştırma**. Bütün doğrulama sentetik depoyla yapılır (`tests/test_faz6_oot.py` `scored_repo` kalıbı).
- `data/outcomes_oot/`, `registry/oot/d1_rows/`, `registry/oot/post_d1/` ve `docs/fable_faz6_s6/` içeriklerini açma. Tam pytest'in kendi gerçek-repo testlerini koşması serbest.
- Hangi kodun SEALED olduğu yazılmaz.

## Kararlar
- **F1 (B1):** `oot_post_d1_block`, canlı `post_d1_block`'un D1 etiketi kapısını birebir uygular:
  - `_d1_label(realized)` = PENDING → `n_undetermined`; NA → `n_d1_label_na`; 0 → `n_not_applicable` (satır yok, paydada sayılır); yalnız 1 → `post_d1_row`.
  - Blok, canlı bloktaki gibi payda sayaçlarını taşır: `n_not_applicable`, `n_d1_label_na`, `n_undetermined`, `n_retro`, `n_no_record`.
  - Ek tutarlılık denetimi: kayıttaki hücre durumu NOT_APPLICABLE (`D1_NOT_CEILING`) ⇔ gerçekleşen D1 etiketi 0. Uyuşmazlık `ScoringError`.
- **F2 (B2):** `retro_info` yalnız açık küme çiftlerini taşır. `scores_oot.json` ve `SCORES_OOT.md`'nin hiçbir yerinde SEALED bir kod geçmez. Kasa bilgisi yalnız sayaçlarda (`n_sealed`) kalır.
- **F3 (B3):** `oot_post_d1_block`, `path_params`'ı canlı bloktaki gibi yükler (`params["path_secondary"]["model_id"]` → `models/INDEX.json` dosyası) ve `post_d1_row`'a verir.
- **F4 (tam karşılaştırma):** Canlı `post_d1_block` + `post_d1_row` + hücre üretimi ile `oot_post_d1_block`'u satır satır karşılaştır. Her farkı raporda bir tabloya yaz: fark, gerekçe (şartname ya da I-maddesi), karar.
  - Bilinen meşru farklar: sınıf `class_oot` (I13); T_open/PIT tabanlı kayıt seçimi yerine en erken etkin kayıt (I12, I23); `MACHINE_SEQUENCED` etiketi; ayrı ölçek; Faz 2C paritesi yok.
  - Başka bir fark şartnameye açıkça aykırıysa aynı ilkeyle düzelt ve testle.
  - Yorum gerektiren bir fark bulursan düzeltme; DUR ve raporla.

## Testler (önce kırmızı)
Yeni testler `e79a4b7` kodunda **kırmızı**, düzeltmeden sonra yeşil olmalı. Kırmızı çıktı rapora eklenir.
- **T-B1:** sentetik depoda iki açık üye: biri D1 tavan, biri D1 tavan değil (kaydı NOT_APPLICABLE). `build_oot_scores` çökmez. Post_d1 satırı 1, `n_not_applicable` 1. Ayrıca D1 etiketi NA olan bir üye `n_d1_label_na`'ya düşer.
- **T-B1b:** kayıt NOT_APPLICABLE ama gerçekleşen D1 etiketi 1 (ya da tersi) → `ScoringError`.
- **T-B2:** kasada bir üye varken serileştirilmiş `scores_oot.json` metninde ve render edilmiş `SCORES_OOT.md`'de o kod hiç geçmez. `retro_info`'da yalnız açık küme çiftleri var.
- **T-B3:** `ceiling_path_v0` hücresi PREDICTED olan bir arzda post_d1 satırının `ceiling_path_v0` karşılaştırıcısı `not_produced` değildir. path_conditional ikincil hücreleri n kuralına göre üretilir.
- **Gerçek repo bekçisi:** `tests/test_outcome_guard.py::test_sealed_codes_absent_from_every_extracted_file`'ın dosya listesine, varsa, `scores/scores_oot.json` ve `docs/SCORES_OOT.md` eklenir. Bugün bu dosyalar yok, test yine yeşil kalır.

## İzinli izlenmeyen
- `docs/faz6/ekler/s6_denetim.txt` ve `docs/faz6/ekler/s6_test_runs.txt` (S6 oturumunun dosyaları; **dokunma, commit etme**).
- Bu görev dosyası.
- Başka bir şey varsa DUR.

ÖNCE OKU: CLAUDE.md; docs/faz6/ekler/s6_denetim.txt; docs/specs_faz5/SPEC_POST_D1_V0.md (§4, §7); docs/specs_faz6/SPEC_OOT_PRE_H99_V0.md (§2, §6); docs/SPEC_DEVIATIONS.md (I10–I13, I23, I24); borsai/scoring.py (`post_d1_block`, `post_d1_row`, `_d1_label`, `post_d1_cell_specs`, `oot_post_d1_block`, `build_oot_scores`, `oot_model_block`); tests/test_faz6_oot.py (`scored_repo`, `test_oot_post_d1_block_machine_sequenced_rows`), tests/test_faz6_s6.py.

## Adımlar
0. **Taban.** HEAD `e79a4b7` ya da torunu (Fable'ın commit'leri olabilir). İzinli izlenmeyenler dışında temiz. Tam `.venv/bin/pytest -q` ve `bash app/scripts/test.sh` yeşil (beklenen 625).
1. **Testler önce:** yeni testleri yaz ve `e79a4b7` kodunda kırmızı olduklarını göster (T-B1, T-B1b, T-B2, T-B3).
2. **Düzeltmeler:** F1, F2, F3. F4 karşılaştırma tablosu.
3. SPEC_DEVIATIONS'a sıradaki numaralarla ekle (F1–F4; B1–B3'e atıf).
4. Tam pytest + test.sh yeşil → **commit**.
5. Rapor `docs/faz6/S6_FIX_RAPOR.md` (aynı commit'e): kırmızı → yeşil çıktıları, F4 tablosu, test sayıları, S6 oturumunun devamı için not.

## Kurallar
- Yazılabilir: `borsai/scoring.py` (yalnız `oot_post_d1_block`, `build_oot_scores` ve doğrudan yardımcıları), `tests/test_faz6_s6.py` ya da yeni `tests/test_faz6_s6_fix.py`, `tests/test_outcome_guard.py` (yalnız yukarıdaki bekçi genişlemesi), `docs/SPEC_DEVIATIONS.md`, `docs/faz6/S6_FIX_RAPOR.md`, bu görev dosyası.
- Salt okunur: geri kalan her şey. Canlı `post_d1_block` ve `scores.json` üreticileri DEĞİŞMEZ (canlı davranış aynı kalmalı; tam pytest bunu sınar).
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- `git add -A` yok. Commit (test dosyası adını kullandığınla değiştir):
  ```
  git add borsai/scoring.py tests/test_faz6_s6_fix.py tests/test_outcome_guard.py docs/SPEC_DEVIATIONS.md docs/faz6/S6_FIX_RAPOR.md docs/prompts/FAZ6_S6_FIX.md
  git commit -m "BORSAI_FAZ6_S6_FIX: out-of-time post_d1 block gated on D1 label like live (B1), open-set-only retro info (B2), path comparator loaded (B3)" -- borsai/scoring.py tests/test_faz6_s6_fix.py tests/test_outcome_guard.py docs/SPEC_DEVIATIONS.md docs/faz6/S6_FIX_RAPOR.md docs/prompts/FAZ6_S6_FIX.md
  ```
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Rapor Türkçe.

## Kabul kapısı
- **K1** T-B1, T-B1b, T-B2, T-B3 önce kırmızı, sonra yeşil. Gerçek repo bekçisi genişledi.
- **K2** F4 tablosu tam. Açıklanmamış fark yok ya da DUR ile raporlandı.
- **K3** Tam pytest + test.sh yeşil; canlı skor üreticileri değişmedi.
- **K4** `scoring --oot` gerçek repoda çalıştırılmadı; sonuç dosyaları açılmadı. Tek commit, yalnız izinli yollar, push yok.

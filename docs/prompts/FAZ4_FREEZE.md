# TASK_ID: BORSAI_FAZ4_FREEZE_20260922

Model: Opus 5 · yüksek. Klasör ~/Desktop/BorsAi. Ağ gerekmez. push/tag/amend yok.

## Bağlam
- Faz 4'ün üç modeli kodlandı ve backtest edildi (2d0c98e), ama dondurulmadı: §6'nın "beklentiden çok iyi" denetimi tetiklenmişti.
- Fable bağımsız yeniden üretimi ve denetimi yaptı: `docs/fable_faz4_audit/AUDIT.md`. Üç model için hüküm **FREEZE_OK**.
  - Yeniden üretim maks |Δ| = 0.0 (870 fold × ufuk hücresi).
  - §6'nın 36 satırı Δ = 0.
  - Sızıntı yok; sıra doğru; S_k yeniden fit edilmemiş.
  - Duyarlılık: N_MIN 5/20, tek grup ve havuzsuz varyantlarda birincil fark −0.112 … −0.122; hüküm değişmiyor.
- Bu görev yalnız dondurma ve denetimin bıraktığı küçük işler. Model tanımı, şartname ve ledger'lar DEĞİŞMEZ.

ÖNCE OKU:
- CLAUDE.md
- docs/specs_faz4/SPEC_CEILING_PATH_V0.md §1, §8 (son madde), §9
- docs/fable_faz4_audit/AUDIT.md §6 ve §7
- docs/SPEC_DEVIATIONS.md F bölümü
- borsai/ceiling_path.py, freeze.py, registry.py (`F3_MODELS`), specs.py

## Adımlar

**0.** `git log --oneline -3`, `git status --porcelain`. Çalışma ağacı temiz olmalı (`app/` dahil). Değilse DUR.
Tam test koşusu (`.venv/bin/pytest -q`): sayı ve süre.

**1. Altın ledger'ların kod damgası (AUDIT §6-1).**
- `tests/reference/macos_golden_faz4/MANIFEST.json` ve Faz 4 günlük satırları `borsai_source_sha256 = f96dbd02…`, `git_commit = 50c62da`, `borsai_dirty = true` diyor; HEAD'de kaynak sha `51a35452…`.
- Backtest'i HEAD'in temiz kodunda yeniden koş ve üç ledger'ın bayt-eşit çıktığını göster.
  - Bayt-eşitse: MANIFEST'in kod damgasını HEAD değerleriyle güncelle, ledger dosyalarına DOKUNMA, farkın neden doğduğunu (hangi dosyalar değişmiş) raporla.
  - Bayt-eşit DEĞİLSE: DUR ve raporla. Fable'ın denetlediği çıktı bu ledger'lardır.

**2. Dondurma** (şartname §8 son madde)
- Üç model: `ceiling_path_v0`, `ceiling_path_v0@INF`, `pb_ceiling_path_v0`.
- Hücreler 99 arzın tamamından, kesim 2026-08-19; seri modeli JSON'ları gömülü, sha'ları INDEX'le aynı.
- `models/INDEX.json`'a sona eklenir; ilk 16 kayıt değişmez.
- Dondurma temiz ağaçta yapılır; kayıtlarda `borsai_dirty` false olmalı.

**3. Denetimin bıraktığı işler**
- `registry.F3_MODELS`'e `ceiling_path_v0` eklenir (f3'süz reddediyor). `pb_ceiling_path_v0` ve `@INF` eklenmez.
- `docs/SPEC_DEVIATIONS.md`'ye üç satır:
  - f3 isteyen modeller listesinin tek kaynağı koddaki `F3_MODELS`; `ceiling_path_v0` dahil (SPEC_SCORING §6 metni dört modeli adıyla sayıyor).
  - D1 baz fiyat yuvarlaması HALF_UP: proje sahibi kararı, şartname §11 soru 1.
  - PB varyantında limit yolu planlanan fiyattan; model kartında böyle yazılacak (F4, AUDIT §6-5).
- `experiments/log.jsonl`'a Fable'ın 5 duyarlılık satırı eklenir (`docs/fable_faz4_audit/ekler/sensitivity_runs.jsonl`, `kind: sensitivity`, `is_model: false`). `tests/test_experiment_log.py` bu türü kabul edecek biçimde genişletilir; bu satırlar model değildir ve hiçbir tabloya girmez.
- `docs/MODELS.md` yeniden üretilir (dondurulmuş modeller artık INDEX'te). D10 satırlarına dipnot: kazanç L = 10 arzlarında yoğunlaşıyor (AUDIT §6-6). Faz 4 bölümünün sonuna bir cümle: bağımsız yeniden üretim 2026-09-22, maks |Δ| = 0, `docs/fable_faz4_audit/`.
- Ledger'lara yeni sütun EKLENMEZ (AUDIT §6-4 önerisi reddedildi: Fable'ın denetlediği dosyalar bayt olarak korunur). Gerekçeyi SPEC_DEVIATIONS'a yazma, rapora yaz.

**4. Skorlar**
- `python -m borsai.scoring` yeniden koşar; `scores/scores.json` ve `docs/SCORES.md` güncellenir.
- Üç yeni model 7 arz için RETRO'dur: `retro_info`'da görünür, canlı n'e girmez, hiçbir metrik üretmez.
- Mevcut 16 modelin blokları içerik olarak değişmemeli (üretim zamanı, kod sha'sı ve `n_variants_same_data` hariç; testle göster).
- `registry/` altına hiçbir şey yazılmaz.

**5. Testler:** tam koşu yeşil. Şartname §9'daki 13 kabul testi ve Faz 1/2 bekçileri dahil.

## Kurallar
- DEĞİŞMEZ: `docs/specs/`, `docs/specs_faz4/`, `docs/fable_faz4_audit/`, `tests/reference/macos_golden_faz4/` altındaki üç ledger dosyası (yalnız MANIFEST'in kod damgası), mevcut 16 model dosyası ve INDEX'teki ilk 16 kayıt, `legacy/`, `registry/`, `data/`, `app/`.
- Model davranışı şartnamedekidir. Dondurma sırasında bir uyuşmazlık bulursan o modeli dondurma, DUR ve raporla.
- `git add -A` YOK. Commit:
  ```
  git add <yollar>
  git commit -m "<mesaj>" -- <aynı yollar>
  ```
  Yollar: `models/`, `borsai/`, `tests/`, `experiments/log.jsonl`, `docs/MODELS.md`, `docs/SPEC_DEVIATIONS.md`, `docs/SCORES.md`, `scores/`, `docs/prompts/FAZ4_FREEZE.md`
- Mesaj: `BORSAI_FAZ4_FREEZE: ceiling path models frozen after independent reproduction (Fable FREEZE_OK, max |delta| 0)`
- Push yok.

## Teslim (rapor)
- Commit hash'i ve `git show --stat`.
- Ledger bayt-eşitlik sonucu ve kod damgası farkının nedeni.
- Üç modelin `model_id`, `sha256` ve eğitim n değerleri.
- INDEX'in yeni uzunluğu ve ilk 16 kaydın değişmediğinin kanıtı.
- `scores.json` değişmezlik testinin sonucu.
- Test sayısı ve süre.
- Sapmalar.

## Kabul kapısı
- K1 Üç model dondu; ledger'lar bayt-eşit; MANIFEST kod damgası HEAD ile tutarlı.
- K2 `F3_MODELS` güncel; SPEC_DEVIATIONS üç satır; duyarlılık satırları günlükte.
- K3 Mevcut 16 modelin dosyaları ve skor blokları değişmedi.
- K4 Tam test koşusu yeşil; push yok.

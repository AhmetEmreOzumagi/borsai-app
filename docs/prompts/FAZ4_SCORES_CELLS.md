# TASK_ID: BORSAI_FAZ4_SCORES_CELLS_20260923

Model: Opus 5 · yüksek. Klasör: ~/Desktop/BorsAi. Ağ gerekmez. push/tag/amend yok.

## Bağlam
- Faz 4'ün üç modeli dondu (a0df5b7). Backtest tabloları `docs/MODELS.md`'de var. Birincil hücre: `ceiling_path_v0` D5 MAE, `base_train_median`'a karşı: −0.1158 [−0.1611, −0.0738], n = 85.
- Ama `scores/scores.json`'da bu üç modelin `backtest.cells = []` ve `primary_cell = null`. Uygulamanın doğruluk paneli yalnız `scores.json`'u okur; yani bu sonuç orada görünmez.
- Nedeni: `borsai/scoring.py` içinde `backtest_cells` ve `PRIMARY_CELLS`'te `ceiling_path` dalı yok. Kaynak: Fable, `docs/app/SPEC_APP_EK2.md` §8, Ö1.
- İkinci eksik (Ö3): `comparators()` `ceiling_path` türü için `v1_5_h99`'u ve sıfır modeli içermiyor. SPEC_CEILING_PATH_V0 §5 ise ikisini de istiyor.
  - Bu modellerin canlı n'i bugün 0 (hepsi RETRO). Tanımı şimdi düzeltmek "tanımlar skorlamadan önce" kuralını korur.
- Paralel oturum: Opus, `docs/prompts/FAZ3_APP_P1.md` ile yalnız `app/` altında çalışıyor. `app/`'e dokunma, onun dosyalarını commit'ine alma.
- Yeni hesap yok. Hücreler, MODELS.md'yi üreten aynı ledger'lardan ve aynı eşleştirme fonksiyonlarından (`borsai/report_faz4.py`) gelir.

ÖNCE OKU:
- CLAUDE.md
- docs/specs_faz4/SPEC_CEILING_PATH_V0.md §5 (karşılaştırma tablosu ve TEK birincil hücre)
- docs/app/SPEC_APP_EK2.md §5 ve §8
- borsai/scoring.py (`PRIMARY_CELLS`, `backtest_cells`, `comparators`, `live_cell_specs`, `rule_values`, `build_scores`)
- borsai/report_faz4.py (`compare`, `comparator_rows`, `_comparison_table`), borsai/report_faz1b.py (`paired`)
- docs/MODELS.md Faz 4 bölümü, docs/SCORES.md

## Adımlar
0. `git log --oneline -3`, `git status --porcelain`. Çalışma ağacı temiz olmalı. İzinli istisnalar: bu görev dosyası, `docs/prompts/FAZ3_APP_P1.md` ve `app/` altındaki değişiklikler (paralel oturum, aşağıda). Başka değişiklik varsa DUR.
   - Tam test (`.venv/bin/pytest -q`): sayı ve süre.
   - `scores/scores.json`'un bir kopyasını `/tmp/scores_before.json`'a al.
1. **Backtest hücreleri (Ö1):** `backtest_cells` üç model için SPEC_CEILING_PATH_V0 §5 tablosundaki bütün karşılaştırmaları üretir.
   - Ufuklar D1, D3, D5, D10. Çıktılar `return` (MAE) ve `p_up` (Brier).
   - Karşılaştırılanlar §5'teki gibi. PB varyantı PB planı kurallarıyla ve `pb_v0` ile karşılaştırılır.
   - "Bilgi amaçlı" satırlar (PB ↔ ana model) hücre olarak eklenmez.
   - Aynı ledger'lar, aynı `paired`/`compare` fonksiyonları, aynı bootstrap. Hücre değerleri MODELS.md'deki Faz 4 tablolarıyla birebir aynı olmalı: fark, aralık, n, kazanç/kayıp/eşit. Bunu bir testle göster.
   - Hücre biçimi mevcut `_bt_cell`'inki. Yeni alan yok.
2. **Birincil hücre:** `PRIMARY_CELLS`'e YALNIZ `ceiling_path_v0` eklenir: `{"output": "return", "horizon_or_k": "D5", "metric": "MAE", "rule_ids": ["base_train_median"]}`.
   - `@INF` ve PB varyantına birincil hücre VERİLMEZ. Şartname tek birincil hücre ilan etti; diğerleri "keşif".
3. **Canlı karşılaştırmalar (Ö3):** `comparators()` ve gerekiyorsa `live_cell_specs` `ceiling_path` türü için §5'i izler.
   - `ceiling_path_v0`: kurallar + `v1_5_h99` + `ceiling_path_v0@INF`
   - `ceiling_path_v0@INF`: yalnız kurallar
   - `pb_ceiling_path_v0`: kurallar + `pb_v0`
   - Canlı tarafta PB planı kurallarının ayrı karşılığı yoksa mevcut canlı kural kimliklerini kullan. Bunu `docs/SPEC_DEVIATIONS.md`'ye tek satırla yaz.
   - Canlı n bugün 0. Hiçbir canlı hücre ya da metrik üretilmemeli (n < 10).
4. **Skorlar:** `python -m borsai.scoring`. `scores/scores.json` ve `docs/SCORES.md` güncellenir.
   - Mevcut 16 modelin blokları içerik olarak değişmemeli. Hariç: üretim zamanı, kod sha'sı, `n_variants_same_data`. Testle göster (FAZ4_FREEZE adım 4'teki kalıp).
   - `retro_info` 21 satır kalır.
   - `registry/` ve `data/` altına hiçbir şey yazılmaz.
5. **Testler:** hedefli testler, sonra tam koşu yeşil. Yeni testler:
   - (a) üç modelin hücreleri = MODELS.md / report_faz4 değerleri
   - (b) birincil hücre değerleri: −0.1158 [−0.1611, −0.0738], n = 85, hüküm "geçiyor", etiket "birincil"
   - (c) `PRIMARY_CELLS`'te yalnız `ceiling_path_v0` eklendi
   - (d) 16 eski blok değişmedi
   - (e) karşılaştırıcı listeleri §5 ile aynı

## Kurallar
- DEĞİŞMEZ: `models/`, `registry/`, `data/`, `app/`, `legacy/`, `docs/specs/`, `docs/specs_faz4/`, `docs/fable_faz4_audit/`, `docs/app/`, `tests/reference/`, bütün ledger'lar.
- Model tanımı ve dondurulmuş dosyalar değişmez. Değer uyuşmazlığı bulursan (scores.json hücresi ≠ MODELS.md) testi gevşetme. Kök nedeni bul, gerekirse DUR ve raporla.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- `git add -A` yok. Commit:
  ```
  git add borsai/scoring.py tests scores/scores.json docs/SCORES.md docs/SPEC_DEVIATIONS.md docs/prompts/FAZ4_SCORES_CELLS.md
  git commit -m "<mesaj>" -- borsai/scoring.py tests scores/scores.json docs/SCORES.md docs/SPEC_DEVIATIONS.md docs/prompts/FAZ4_SCORES_CELLS.md
  ```
  - Başka dosya değiştiyse (ör. `experiments/log.jsonl`) nedenini raporda yaz ve yollara ekle.
  - `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Mesaj: `BORSAI_FAZ4_SCORES: ceiling path backtest cells and primary cell in scores.json, live comparators per spec §5`
- Rapor Türkçe.

## Teslim (rapor)
- Commit hash'i ve `git show --stat`.
- Üç modelin hücre sayısı. Birincil hücrenin scores.json'daki tam değerleri.
- MODELS.md eşitlik testinin sonucu: kaç hücre karşılaştırıldı, maks |Δ|.
- 16 eski blok değişmezlik testinin sonucu.
- Karşılaştırıcı listeleri (üç model).
- Test sayısı ve süresi.
- Sapmalar.

## Kabul kapısı
- K1 Üç modelin backtest hücreleri scores.json'da ve MODELS.md ile birebir.
- K2 Birincil hücre yalnız `ceiling_path_v0` için ve değerleri doğru.
- K3 Canlı karşılaştırıcılar §5'le uyumlu; canlı metrik yok.
- K4 16 eski blok değişmedi; tam test yeşil; commit yalnız izinli yollar.

# TASK_ID: BORSAI_FAZ5_LIVE_B_APPFIX_20260924

Model: Sonnet 5 · yüksek. Klasör: ~/Desktop/BorsAi. Ağ gerekmez. push/tag/amend yok.

## Bağlam
- Canlı POST_D1 akışı commit A'sı `660cec1` (`docs/faz5/LIVE_RAPOR.md`). Commit B ATILMADI: `bash app/scripts/test.sh` kırmızıydı.
- Kök neden (Opus ölçtü, orkestratör rapordan doğruladı): `borsai/predict_hazard.py` Faz 5 A'da (`7ce0593`, SPEC_DEVIATIONS H1) davranış değiştirmeden yeniden düzenlendi. Uygulamanın altın MANIFEST'i (`app/parity/golden/MANIFEST.json`) bu dosyanın eski sha'sını pinliyor: `predict_sources_sha256["borsai/predict_hazard.py"]` 8099ead3… → bugün a1523ac8…. `gen_golden.py --check` 25 dosyadan YALNIZ MANIFEST'i farklı buluyor; 24 altın vektör dosyası bugünkü kodla birebir.
- Çalışma ağacında B çıktıları hazır duruyor (HEAD 660cec1'de üretildi): `scores/scores.json` (M), `scores/scores_post_d1.json` (??), `docs/SCORES.md` (M), `docs/faz5/LIVE_RAPOR.md` (M; B bölümü).

## İzinli izlenmeyen / değişmiş (adım 0'da bunlar dışında bir şey varsa DUR)
`scores/scores.json`, `scores/scores_post_d1.json`, `docs/SCORES.md`, `docs/faz5/LIVE_RAPOR.md`, `docs/prompts/FAZ5_LIVE_B_APPFIX.md`, `docs/prompts/FAZ6_*.md`, `docs/specs_faz6/KARARLAR.md`.

### Paralel
Bir Opus oturumu `docs/prompts/FAZ6_VERIFY_CODEX_INPUTS.md`'yi koşuyor. Yalnız repo DIŞINA (`~/Desktop/BorsAi_codex/verified/`) yazar; repoya yazmaz, commit atmaz.

ÖNCE OKU: CLAUDE.md; docs/faz5/LIVE_RAPOR.md (B bölümü); app/parity/gen_golden.py (başlık); app/parity/test_gen_golden.py; app/scripts/test.sh.

## Adımlar
0. `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -3` (HEAD `660cec1`), `git status --porcelain` (yukarıdaki liste).
1. **Altın MANIFEST.**
   - `.venv/bin/python app/parity/gen_golden.py --check`: yalnız `golden/MANIFEST.json`'ın farklı olduğunu göster.
   - Sonra `.venv/bin/python app/parity/gen_golden.py`.
   - `git status --porcelain -- app/`: YALNIZ `app/parity/golden/MANIFEST.json` değişmiş olmalı. MANIFEST farkı yalnız `predict_hazard.py` sha'sı (ve varsa üretim zamanı/kod damgası) olmalı. Başka bir altın dosya değiştiyse DUR, geri alma, raporla.
   - `bash app/scripts/test.sh` YEŞİL. Kırmızıysa DUR ve raporla.
   - **Commit C1** (yalnız MANIFEST).
2. **Skorlar (B).**
   - `.venv/bin/python -m borsai.scoring` yeniden koş (outcomes güncellemesi YAPMA).
   - Çıkan `scores/scores.json` ve `scores/scores_post_d1.json`, çalışma ağacındaki önceki hâllerinden yalnız `generated_at_utc` ve `code.git_head` gibi kod/zaman damgalarında farklı olabilir. Başka alan farkı varsa DUR. (Önceki hâlleri adımdan önce `/tmp/`'ye kopyala ve karşılaştır.)
   - `scores.json`'un HEAD'e göre farkı YALNIZ `generated_at_utc`, `code` ve 19 kartta `n_variants_same_data` 19 → 20 olmalı.
   - `docs/faz5/LIVE_RAPOR.md` B bölümünün sonuna "B'nin tamamlanması" alt bölümü ekle: C1 hash'i, MANIFEST farkı, test.sh sonucu, yeniden üretilmiş skorların sha256'ları.
   - Tam `.venv/bin/pytest -q` YEŞİL ve `bash app/scripts/test.sh` YEŞİL.
   - **Commit B.**
3. **Uygulama derlemesi:** `source app/scripts/env.sh && cd app && npm run tauri build -- --bundles app`. `/Applications`'a kopyalama. Yeni `src-tauri/target/release/bundle/macos/BorsAi.app/Contents/MacOS/borsai-app` sha256'sını rapora yaz.
4. Rapor.

## Kurallar
- Yalnız şu dosyalar değişir: `app/parity/golden/MANIFEST.json`, `scores/scores.json`, `scores/scores_post_d1.json`, `docs/SCORES.md`, `docs/faz5/LIVE_RAPOR.md`. `borsai/`, `tests/`, `models/`, `registry/`, `data/`, diğer `app/` dosyaları değişmez.
- Testi gevşetme; kök nedeni bul; gerekirse DUR.
- `git add -A` yok. Commit'ler:
  ```
  git add app/parity/golden/MANIFEST.json docs/prompts/FAZ5_LIVE_B_APPFIX.md
  git commit -m "BORSAI_APP_GOLDEN_MANIFEST: repin predict_hazard.py source sha after behavior-preserving Faz 5 refactor (vectors unchanged)" -- app/parity/golden/MANIFEST.json docs/prompts/FAZ5_LIVE_B_APPFIX.md
  git add scores docs/SCORES.md docs/faz5/LIVE_RAPOR.md
  git commit -m "BORSAI_FAZ5_LIVE_B: scores regenerated (variant counter 20, separate scores_post_d1.json with retro_info only)" -- scores docs/SCORES.md docs/faz5/LIVE_RAPOR.md
  ```
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Rapor Türkçe.

## Teslim (rapor)
C1 ve B hash'leri; MANIFEST farkı (satır düzeyinde); `gen_golden --check` önce/sonra; test.sh ve pytest sayıları; skor farkı özeti; yeni `borsai-app` sha256'sı.

## Kabul kapısı
- K1 Altın vektör dosyaları bayt-eşit; yalnız MANIFEST değişti; test.sh yeşil.
- K2 `scores.json` farkı yalnız izinli alanlar; `scores_post_d1.json` commit'li; tam pytest yeşil.
- K3 `.app` derlendi; commit'ler yalnız izinli yollarda; push yok.

# TASK_ID: BORSAI_FAZ2C_CONDITIONAL_SCORING_20260924

Model: Opus (arayüzdeki en yeni) · Extra. Klasör: ~/Desktop/BorsAi. Ağ gerekmez. push/tag/amend yok.

## Bağlam
- Koşullu güncelleme ("seri j gün sürdüyse") üründe var: uygulama P(L ≥ k | L ≥ j) ve tavan-yolu koşullu getirisini dondurulmuş kayıttan gösteriyor. Bu tahminlerin CANLI isabetini ölçen kod yok.
- Tanım yazılı ve push kanıtlı: `docs/specs_faz4/SPEC_CEILING_PATH_V0.md` §7 "Canlı skorlama tanımı" (`52e1567`, kanıt `9b50c90`).
- `scores.json` okuyucu sözleşmesi sabit: `docs/app/SPEC_APP_EK2.md` §5 (`borsai.scores_conditional/1`, `models[].conditional.by_j[]`). Uygulama okuyucusu ve bütünlük denetimi hazır: `app/src-tauri/src/commands/scores.rs::check_conditional`, `app/src/render/accuracy.ts::conditional`.
- H99 keşif tarafı ZATEN var (`borsai/ceiling_path.py` §7 bölümü, `borsai/predict_path.py` `conditional_rps`/`conditional_brier`, `experiments/log.jsonl` `conditional_eval` 1 satır, `docs/MODELS.md` "Koşullu güncelleme (keşif)"). Bu görev yalnız CANLI tarafıdır. Metrik fonksiyonları o ortak fonksiyonlardan gelir; ikinci bir tanım yazılmaz.
- **Neden şimdi:** CLAUDE.md kural 6 "tanımlar ilk skorlamadan önce kodda". NETGL'in D4–D10'u (D10 = 2026-09-30) ve ilk yeni arz henüz repoya girmedi; kod şimdi girerse sonuç verisi commit'lerinin atası olur.
- Bugünkü veri [orkestratör ölçtü]:
  - `scores/scores.json` `as_of_session` 2026-09-21; 7 arz × 16 model kayıt (`7cb49cf`); Faz 4 modellerinin kaydı yok (RETRO).
  - Gerçekleşen L: CITAS 5, TKNKA 7, VEYAS 0, KPEKS 5, INTET 4, BKRGY 0, NETGL ≥ 3 (h = 4..10 PENDING).
  - Beklenen: her j'de n < 10 → **hiçbir koşullu hücre ya da hüküm yok**; yalnız satır tabloları. j = 1'de 4 skorlanan arz (CITAS, TKNKA, KPEKS, INTET) + NETGL hedef eksik. Bu beklentiyi kendin ölç; tutmazsa nedenini yaz.

### Paralel oturum
Fable, `docs/prompts/FAZ5_FABLE_POST_D1_SPEC.md` görevini koşuyor; YALNIZ `docs/specs_faz5/` altına ve kendi görev dosyasına yazıyor. Ona dokunma, commit'lerine alma.

ÖNCE OKU:
- CLAUDE.md
- docs/specs_faz4/SPEC_CEILING_PATH_V0.md §5, §7
- docs/specs/SPEC_SCORING.md §3, §5–§8
- docs/app/SPEC_APP_EK2.md §5
- docs/SPEC_DEVIATIONS.md (C7 ve F bölümü)
- borsai/scoring.py (özellikle `live_block`, `_row`, `live_cells`, `paired_metric`, `verdict`, `block_bootstrap_ci`, `merge_scales`/`ScaleMixError`, `build_scores`, `render_doc`)
- borsai/predict_path.py koşullu fonksiyonları; borsai/ceiling_path.py §7 keşif bölümü
- tests/test_scoring.py
- app/src-tauri/src/commands/scores.rs `check_conditional`; app/tests/fixtures/scores/conditional.json (okuyucunun beklediği satır alanları)

## Adımlar
0. Taban:
   - `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -3`, `git status --porcelain`
   - İzinli izlenmeyenler: `docs/prompts/FAZ2C_CONDITIONAL_SCORING.md`, `docs/prompts/FAZ5_FABLE_POST_D1_SPEC.md`, `docs/specs_faz5/**`. Başka bir şey varsa DUR.
   - Taban: `.venv/bin/pytest -q` (sayı ve süre).
1. **Tanım eşlemesi (kod yazmadan önce):** §7'nin her cümlesini koddaki karşılığına eşleyen tablo rapora. Şartnamede boşluk ya da iki okumalı yer varsa kararını ve gerekçesini `docs/SPEC_DEVIATIONS.md`'ye yeni bir "G. Faz 2C" bölümü olarak yaz. Bilinen iki nokta:
   - §7 madde 3 "yalnız S kısmı" listesinde `pb_ceiling_v0@INF` açıkça yok: kaydında S vektörü olan her tavan modeli koşullu S skorunu alır mı?
   - Koşullu skor hangi modellere, hangi karşılaştırıcılarla (koşullu KM iki kural, koşullu `@INF`, koşullu her-zaman-tavan) uygulanır?
   Karar ölçütü: şartnamenin lafzı; sonuç verisine bakarak seçim yapma.
2. **Commit A — kod ve testler (sonuç verisi yok).** `scores/scores.json`'a dokunmadan:
   - `models[].conditional` bloğunu üreten kod: EK2 §5 şeması; j = 1..9; satır alanları en az `ticker, class, record_id, L, S_cond, rps_cond, brier_next, brier_10, status`; j başına `n_scored/n_refused/n_skipped/n_target_unavailable/n_live/n_late`. Sınıf kayıttan miras (§7). n < 10 → `cells = []`; 10 ≤ n < 30 → "yetersiz örnek"; aralık SPEC_SCORING §8.
   - Kaydında S olmayan modeller (Faz 4, kayıt yok) için blok ya hiç yok ya da boş `by_j` satırları. Kararını yaz; uygulama ikisini de okur ("henüz koşullu skor yok").
   - Tavan-yolu ikincilleri (koşullu p_up Brier, koşullu medyan MAE; h ∈ {3, 5, 10}, h > j) yalnız kaydında tavan-yolu çıktısı olan modellere. Bugün hiçbir kayıtta yok; kod ve test sentetik kayıtla.
   - Birleştirme yasağı: farklı j'ler ve koşulsuz tablolar hiçbir yerde toplanmaz. `ScaleMixError` mantığı `live_conditional` ölçeğini de kapsar.
   - Testler (`tests/test_scoring_conditional.py`, yeni):
     - (t1) sentetik 12 arzlık fixture'da j = 1 n = 12 → hücreler var ve "yetersiz örnek"; j = 3 n = 4 → `cells = []`
     - (t2) elle hesaplanmış koşullu RPS ve Brier değerleri birebir (en az 3 arz × 2 j)
     - (t3) j başına sınıf mirası: LIVE kayıt → LIVE satır, LATE → LATE
     - (t4) D_{j+1}..D_10'dan biri PENDING → o (a, j) `TARGET_UNAVAILABLE`/PENDING, bütün modellerde aynı anda
     - (t5) L < j olan arz o j'nin paydasında yok
     - (t6) koşullu ile koşulsuz hücreyi birleştiren çağrı `ScaleMixError` verir
     - (t7) üretilen blok EK2 §5 şemasıyla birebir; uygulamanın fixture'ı `app/tests/fixtures/scores/conditional.json` ile aynı alan adları
     - (t8) koşullu metrik fonksiyonları `predict_path`'teki ortak fonksiyonlardır (ikinci tanım yok)
   - Tam pytest yeşil. Commit A.
3. **Commit B — `scores.json` yeniden üretimi.**
   - `python -m borsai.scoring` (outcomes güncellemesi YAPMA; veri `as_of_session` 2026-09-21'de kalır).
   - Fark yalnız `models[].conditional` blokları, üst bilgi (`generated_at_utc`, `code`) ve `docs/SCORES.md`'nin koşullu bölümü olmalı. Başka bir alan değiştiyse DUR ve nedenini bul.
   - `docs/SCORES.md`'ye koşullu bölüm (j başına satır tablosu, "n < 10: metrik hesaplanmaz").
   - Tam pytest yeşil.
   - Uygulama testleri gerçek `scores.json`'u okur: `bash app/scripts/test.sh` koş. Kırmızıysa `app/`'e DOKUNMA: kök nedeni raporla. Uygulama yanlış okuyorsa ya da test fazla sıkıysa, B'yi commit etme, A'yı bırak, DUR.
   - Yeşilse commit B, sonra uygulamayı yeniden derle (gömülü `scores.json` güncellensin): `source app/scripts/env.sh && cd app && npm run tauri build -- --bundles app`. `/Applications`'a kopyalama.
4. Rapor.

Tek oturumda bitmezse: A yeşil ve commit'liyse orada dur, B'yi raporda bırak.

## Kurallar
- Yazılabilir: `borsai/`, `tests/`, `scores/`, `docs/SCORES.md`, `docs/SPEC_DEVIATIONS.md`.
- Salt okunur: `docs/specs/`, `docs/specs_faz4/`, `docs/specs_faz5/`, `docs/app/`, `app/`, `models/`, `registry/`, `data/`, `legacy/`, `experiments/`.
- Hiçbir modelin, kaydın ya da sonuç dosyasının içeriği değişmez. Yeni model yok.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma (`tests/test_outcome_guard.py`).
- `git add -A` yok. Commit'ler:
  ```
  git add borsai tests docs/SPEC_DEVIATIONS.md docs/prompts/FAZ2C_CONDITIONAL_SCORING.md
  git commit -m "BORSAI_FAZ2C_A: live conditional scoring definitions in code (SPEC_CEILING_PATH_V0 §7), no score data" -- borsai tests docs/SPEC_DEVIATIONS.md docs/prompts/FAZ2C_CONDITIONAL_SCORING.md
  git add scores docs/SCORES.md
  git commit -m "BORSAI_FAZ2C_B: conditional blocks in scores.json (row tables only, n < 10)" -- scores docs/SCORES.md
  ```
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Rapor Türkçe.

## Teslim (rapor)
- İki commit hash'i ve `git show --stat`; A'nın B'nin atası olduğu.
- Tanım eşleme tablosu ve SPEC_DEVIATIONS G kararları.
- j başına tablo: model · n_scored · n_live · n_late · n_target_unavailable · satır sayısı. Beklenti (j = 1'de 4 skorlanan) tuttu mu?
- `scores.json` farkının özeti (hangi anahtarlar değişti).
- Test sayıları: pytest önce/sonra; `app/scripts/test.sh` sonucu; derleme sonucu.
- Sapmalar ve kalan işler.

## Kabul kapısı
- K1 Metrikler `predict_path`'in ortak fonksiyonlarından; t1–t8 yeşil; tam pytest yeşil.
- K2 Bugünkü veriyle hiçbir j'de koşullu hücre ya da hüküm yok (n < 10); satır tabloları var.
- K3 `scores.json` farkı yalnız koşullu bloklar ve üst bilgi; uygulama testleri yeşil.
- K4 A, B'nin atası. Commit'ler yalnız izinli yollar.

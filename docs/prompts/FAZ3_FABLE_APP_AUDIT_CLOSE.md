# TASK_ID: BORSAI_FAZ3_FABLE_APP_AUDIT_CLOSE_20260924

Model: Fable · yüksek. Klasör: ~/Desktop/BorsAi. Ağ gerekmez (indirme gerekirse DUR).
- Git: yalnız okuma komutları ve her zaman `GIT_OPTIONAL_LOCKS=0` öneki. Sonda tek commit, yalnız kendi yollarınla.
- Yazma: YALNIZ `docs/fable_app_audit/KAPANIS.md` ve `docs/fable_app_audit/ekler/kapanis/`. Geçici işler `/tmp/borsai_app_audit_close/` altında.
- `app/` altında hiçbir dosyayı değiştirme.

## Bağlam
- Senin denetimin: `70e1c52`, `docs/fable_app_audit/AUDIT.md`. Hüküm DÜZELTMEYLE UYGUN; B1 (KRİTİK), B2, B3 (ÖNEMLİ) ve küçükler.
- Opus düzeltmesi: `db8e239` (`docs/prompts/FAZ3_APP_AUDIT_FIX.md`). Kapsam B1–B8, B10, B12. B9 kabul; B11 Python görevi, sonra.
- Orkestratör diffi okudu. Tariflerin koda girdiğini gördü ama hiçbir testi koşamadı.
  - B1: `commands/config.rs` `resolve_path` bileşen bileşen bağ izliyor; `scenario.rs` `check_export_target` hedef bağsa reddediyor; `write_export` `create_new` ya da geçici dosya + `rename`.
  - B3: `commands/freeze.rs` `freeze_in` başında `preflight_in`; `render/freeze.ts` `ready` preflight ister.
  - B2: `tests/screens_invoke.test.ts`, `tests/decl_flow.ts`.
  - B5: ortam isteyen 8 test `#[ignore]` + `expect`; `test.sh` `--include-ignored`.
  - B10: `app/parity/bit_equal_floor.json`; toplam 7671, `target/parity_report.json` ile model başına eşit.
- Bu, kapanış denetimidir; tam denetimi tekrarlama. Soru tek: "Düzeltmeler gerçekten kapandı mı, yeni açık açıldı mı?"

ÖNCE OKU:
- docs/fable_app_audit/AUDIT.md (bulgu tablosu, adım 3, adım 5)
- docs/fable_app_audit/ekler/: `mutate.sh`, `audit_probe.rs`, `mutasyon_ciktilari.txt`, `yol_bekcisi_sonda.txt`
- docs/prompts/FAZ3_APP_AUDIT_FIX.md
- `GIT_OPTIONAL_LOCKS=0 git --no-pager diff 70e1c52..db8e239 -- app`

## Adımlar
0. Taban:
   - `git log --oneline -3`, `git status --porcelain`
   - İzinli izlenmeyen dosya yalnız bu görev dosyası. Başka bir şey varsa DUR.
1. **Tarif tablosu.** B1–B8, B10, B12 için tek satır: tarif · koda girdi mi (dosya:satır) · testi hangi test ve assert · hüküm KAPANDI / KISMEN / AÇIK.
2. **Yol bekçisi sondası (B1).** `audit_probe.rs`'i klonda yeniden koş; `symlink_file` artık `Err` olmalı. Ayrıca `resolve_path`'in uç hâlleri:
   - göreli hedefli bağ; iki halkalı zincir (dış → dış → repo); döngü (a → b → a, `MAX_LINKS`)
   - `/tmp` → `/private/tmp`; büyük/küçük harf
   - bağdan sonra `..` (fiziksel üst mü, sözcüksel mi); var olmayan ara dizinli `..`
   - dizin bağının içindeki askıda bağ
   - kaydetme yolunda `scenarios/` dizininin kendisinin bağ olması

   Her biri: bekçi sonucu ve repo altında dosya oluştu mu. Repo dışını gösteren bağlar hâlâ kabul edilmeli; aşırı ret de bulgudur (KÜÇÜK).
3. **Mutasyon yeniden koşusu.** Klon + ayrı `CARGO_TARGET_DIR`, `mutate.sh` kalıbı. Her mutasyon: uygula → test → kırmızı mı → geri al.
   - Denetimin 11 mutasyonu. (a) ve (e2) artık KIRMIZI olmalı; öteki 9'u hâlâ kırmızı.
   - Yeni:
     - (j) `check_export_target`'taki bağ reddi ve `resolve_path` eski `canonicalize` davranışına döndürülür → B1 testleri kırmızı
     - (k) `freeze_in`'deki preflight denetimi kaldırılır → `freeze_refuses_when_preflight_blocked` kırmızı
     - (l) `render/freeze.ts` `ready`'den `preflight?.ok` kaldırılır → `freeze.test.ts` kırmızı
     - (m) `path.rs` OUTPUT kaynağında `None` → gömülü sha geri → B8 testi kırmızı
     - (n) `bit_equal_floor.json`'dan bir model silinir → `golden_parity` kırmızı
     - (o) `test.sh`'tan `--include-ignored` kaldırılır → env isteyen testler koşmaz. Bunu hangi kontrol yakalıyor? Hiçbiri yakalamıyorsa KÜÇÜK bulgu yaz.
4. **Tam koşu (ölç).** `ekler/kapanis/test_runs.txt`'ye:
   - `bash app/scripts/test.sh`, iki e2e betiği, `.venv/bin/pytest -q`: sayılar ve süreler; `AUDIT.md`'deki sayılarla fark ve nedeni.
   - `app/src-tauri` içinde env'siz yalın `cargo test --workspace`: hiçbir test "ok" diye env'siz geçmiyor; ignored listesi.
   - Asıl repoda `git status` ile `registry/`, `data/`, `scores/` sha listeleri koşu öncesi ve sonrası aynı.
5. **KAPANIS.md** ve commit.

## Hüküm biçimi
KAPANIS.md'nin başında:
- Genel hüküm, üç seçenekten biri:
  - **UYGUN**: gerçek arz dondurmasında uygulama kullanılabilir.
  - **DÜZELTMEYLE UYGUN**: kalan liste.
  - **UYGUN DEĞİL**
- 5 satırlık özet.
- Yeni bulgular: yalnız varsa, AUDIT.md'deki tablo biçiminde, `C1…` diye numaralı.

Ölçtüğünü **[ÖLÇTÜM]**, çıkarımını **[ÇIKARIM]** diye işaretle.

## Kurallar
- `app/`, `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `tests/` ve `docs/` (kendi iki yolun hariç) salt okunur.
- Kişinin gerçek uygulama verisine yazma, oradaki dosyaları açma.
- Dondur akışını ya da `borsai.freeze`'i asıl repoda ÇALIŞTIRMA; yalnız klonda.
- `npm run tauri dev` ve `app/scripts/screens.sh` çalıştırma.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- `git add -A` yok. Commit:
  ```
  git add docs/fable_app_audit/KAPANIS.md docs/fable_app_audit/ekler/kapanis docs/prompts/FAZ3_FABLE_APP_AUDIT_CLOSE.md
  git commit -m "<mesaj>" -- docs/fable_app_audit/KAPANIS.md docs/fable_app_audit/ekler/kapanis docs/prompts/FAZ3_FABLE_APP_AUDIT_CLOSE.md
  ```
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Mesaj: `BORSAI_FAZ3_FABLE_APP_AUDIT_CLOSE: closure check of audit fixes (B1-B8, B10, B12), mutation rerun and full test run`
- Rapor Türkçe.

## Teslim (rapor)
- Commit hash'i.
- Genel hüküm; varsa yeni bulgular (tek satır).
- Mutasyon tablosu: 11 + 6 satır; mutasyon · test · kırmızı mı.
- Test sayıları, önce (AUDIT) / sonra.

## Kabul kapısı
- K1 Tarif tablosunda 10 satır, her biri kanıtlı.
- K2 17 mutasyonun hepsi koşuldu; sonuçlar komut çıktısıyla.
- K3 Tam koşu ölçülmüş; asıl repoda `registry/`, `data/`, `scores/` değişmemiş.
- K4 Commit yalnız kendi üç yolun.

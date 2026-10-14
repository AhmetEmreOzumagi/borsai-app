# TASK_ID: BORSAI_FAZ7_APP_P1_20260930

Model: Opus 5.5 · Extra. Klasör: ~/Desktop/BorsAi. Ağ gerekmez. push/tag/amend yok.

## Rol
Uygulama EK3'ün ilk aşaması **P1**. Şartname `docs/app/SPEC_APP_EK3.md` (Fable, `7be8394`); bu görev onu uygular:
- **A:** `ceiling_hazard_v1` ailesinin (clip, real, pooled, pooled@INF) Rust portu ve TÜFE tablosu (EK3 §2–§4).
- **D:** Sonuç sayfasının başına **"Tavan serisi — kaç gün tavan?"** özet kartı (EK3 §5). Proje sahibinin asıl isteği budur: "kaç gün tavan" tahmini ilk bakışta görünsün.
- Sonunda uygulama derlenir; proje sahibi kurup ekranda görür.

Bu işten sonra dondur akışı yeniden çalışır. Kurulu derleme 19 modelli INDEX'i gömdüğü için bugün `INDEX_SHA` ön koşulunda duruyor.

## Bağlam: EK3 yazıldığından beri değişenler (orkestratör ölçtü, 2026-09-30)
EK3 2026-09-27'de, 23 modelli INDEX ve kapalı kasayla yazıldı. O günden sonra:
1. **INDEX 27 giriş:** 19 eski + 4 v1 + 4 düşen arz (`fall_d10_v0_h99`, `_pooled`, `_addsale`, `_pooled@ZERO`; dondurma `ce569a8`). Düşen arz modelleri P4'tür. P1'de `PINNED_MODEL_IDS` 19 → 23 olur ve **`ignored_model_ids` tam bu dört (C) kimliğidir.** EK3 U58'deki `ignored_model_ids == []` beklentisi P1'de "== dört (C) kimliği" olarak okunur (J31 kalıbı; `tests/build_embed.rs` bugün (C) kimliklerini zaten bekliyor). Yeni kayıtlar 27 model taşır: kayıt paritesi 23/23 + `unsupported` 4 (C).
2. **Ö1 ve Ö2 yapıldı:** `scores/scores.json` 27 model ve `models[].backtest.near_era` bloklarını taşıyor (EK3 §5.5 şeması; `docs/faz7_oot/RAPOR.md` §5). Etiketler: clip "tolerans içinde", real "bozuyor", pooled "bozuyor", pooled@INF "bozuyor" (kural satırı).
3. **Ö4 yapıldı, kasa açıldı:** `scores/scores_oot.json` şu anahtarları taşıyor: `oot_pre_h99` (27 model; açık küme), `oot_pre_h99_sealed` (27 model; kasa), `oot_pre_h99_all` (19 model), `post_d1`, `post_d1_sealed`, `post_d1_all`. Kasa bağımsız yeniden hesapla doğrulandı (Fable `VAULT_SCORE_OK`, `docs/fable_faz7_vault/AUDIT.md`). Rapor `docs/faz7_vault/SKOR_RAPOR.md`.
   - Kasa satırlarında `open: false`, `vault: "SEALED"`.
4. **Öne çıkarma kuralının kasa sonucu** (SPEC_HAZARD_V1 §5.5, yalnız dosyadaki sayılardan):

   | Aday | k1 kasa birincil | k2 kasada RPS − v0 üst uç < 0 | k3 yakın dönem | Uygun |
   |---|---|---|---|---|
   | clip | ayırt edilemiyor | evet | tolerans içinde | hayır (k1) |
   | real | ayırt edilemiyor | evet | bozuyor | hayır |
   | pooled | **geçiyor** | evet | **bozuyor** | hayır (k3) |

   **Öne çıkan: `ceiling_hazard_v0`, neden `RULE_5_5_NONE_ELIGIBLE_V0`.** Kart bunu dosyadan kendisi bulmalı; elle yazılmaz.
5. **`KIND_TEXT['fall']`** eklendi (`05d0960`).
6. **Test altyapısı:** paralel pytest var (`docs/ENV.md`). Ara koşular `.venv/bin/pytest -q -n 6 --dist loadgroup`; her commit'ten önceki son kabul koşusu sıralı `.venv/bin/pytest -q`.
   - Taban (a9ffa4a): pytest 864 geçti; `test.sh` yeşil (cargo 94, vitest 222/222, parity 4, golden_unchanged); `gen_golden --check` 25/0.

## Proje sahibi ve orkestratör kararları (bağlayıcı)
- **K-P1-1 (EK3 §13 cevapları, orkestratör kabul etti):**
  1. Öne çıkarma veri-güdümlüdür (`featured_ceiling`; elle dosya yok).
  2. Yakın dönem etiketi `scores.json` `near_era` bloğundan okunur.
  3. TÜFE: bağımsız modda gömülü tablo, repo modunda repo dosyası.
- **K-P1-2 (proje sahibi, 2026-09-29): "eski arzları katmayalım, bize bugün lazım."**
  - Öne çıkan tavan modeli `ceiling_hazard_v0`.
  - `real` ve `pooled` listeden kalkmaz (KARARLAR K4); ikincil satırda "bozuyor" etiketiyle görünür.
  - Kartta öne çıkan satırın açıklama metni: "öne çıkan: ceiling_hazard_v0 (kasa sonrası kural: uygun v1 adayı yok)".
- **K-P1-3: zaman-dışı okuyucu P1'e alınır.** Kasa açık olduğu için kartın "zaman-dışı (kasa)" sütunu ve `featured_ceiling` P1'de gerçek dosyayı okumalı.
  - P1'e taşınan EK3 §7.1 parçaları: `commands/scores_oot.rs` (okuma, kaynak seçimi REPO/EMBEDDED, `build.rs` anlık kopya gömme) ve bütünlük denetimi.
  - Panel arayüzü (`render/accuracy_oot.ts`, Doğruluk sekmesi bölümü) **P3'te kalır**.
  - **Bütünlük kuralında değişiklik:** `OOT_ROW_NOT_OPEN` yalnız `oot_pre_h99` (açık küme) bloğunun satırlarına uygulanır. `oot_pre_h99_sealed` ve `oot_pre_h99_all` bloklarında `vault == "SEALED"` satırları meşrudur (kasa açıldı).
  - P1 hiçbir satır çizmez; yalnız hücreleri okur.
- **K-P1-4: kartın terazi sütunları.**
  - **Zaman-dışı:** öne çıkan ve üç aday için `oot_pre_h99_sealed` bloğundaki `label == "birincil"` hücrenin `verdict`'i + " (zaman-dışı terazide)". Birincil hücresi olmayan kural satırları için "—".
  - **Yakın dönem:** `near_era.label`; v0 ve KM kuralları için "—".
  - **Canlı:** `scores.json`'dan (n < 10 → "n = {n}: hüküm yok").
  - Hiçbir terazi değeri toplanmaz, ortalanmaz.
- **K-P1-5: Windows uyumu** (proje sahibi, 2026-09-29: uygulama hem Mac hem Windows için geliştiriliyor).
  - Yeni kodda sabit Mac yolu (`.venv/bin/python` gibi) ya da zsh'e özel komut yok.
  - Dosya yolları `PathBuf`/`Path.join` ile kurulur; satır sonları LF.
  - Platform farkı gerekiyorsa tek bir fonksiyonda toplanır.
  - Mevcut Mac'e özel kodu bu görev düzeltmez; yeni kod eklemez.
- **K-P1-6: Önceden onaylı pin güncellemeleri (J31 kalıbı).**
  - `app/` altında model sayısı, `ignored_model_ids`, altın MANIFEST sha'ları ya da skor dosyası içeriğini sayan test/fikstür satırları asgari yeniden pinlenebilir.
  - `tests/` (Python) altında bir test `app/` dosyasının sha'sını ya da model sayısını pinliyorsa ve kırılırsa, yalnız o pin satırı güncellenebilir. Ayrı commit APPPIN.
  - Mantık değişmesi gerekiyorsa DUR ve raporla.
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** Parite tutmuyorsa Rust düzeltilir; Python'a dokunulmaz; tolerans gevşetilmez.
- **Soru sorman gerekirse** seçenekleri açık yaz. Proje sahibi orkestratöre danışarak cevaplayacak.

## İzinli izlenmeyen
Bu görev dosyası ve `docs/prompts/LIVE_NETGL_D10.md` (sonraki bir görevin dosyası; dokunma, commit'leme). Başka bir şey varsa DUR.

## Paralel
Bu görev koşarken başka oturum yok. Proje sahibi bu sırada git komutu çalıştırmaz.

## ÖNCE OKU
- CLAUDE.md
- `docs/app/SPEC_APP_EK3.md` (tamamı; özellikle §0–§5, §10.1, §11, §12)
- `docs/app/SPEC_APP.md` §2.3, §3b, §3g, §4, §5.3; `docs/app/SPEC_APP_EK2.md` §3–§4 (parite ve altın vektör kalıbı)
- `docs/specs_faz7/SPEC_HAZARD_V1.md` §3, §5.5, §8, §12; `docs/specs_faz7/KARARLAR.md`
- `docs/faz7/FREEZE_RAPOR.md` (§4 kayıt biçimi, §9 MANIFEST tuzağı); `docs/faz7_oot/RAPOR.md` §5–§6; `docs/faz7_vault/SKOR_RAPOR.md` (T6 seçim kuralı)
- `docs/ENV.md` (test komutları)
- `borsai/predict_hazard.py` (v1 dalı), `borsai/tufe.py`, `borsai/specs.py` (`TUFE_PIN`)
- `app/src-tauri/build_embed.rs`, `app/src-tauri/crates/borsai_predict/src/*`, `app/src-tauri/src/commands/{ceiling,scores,freeze,predict,parity,models,config}.rs`, `app/src/render/{results,ceiling,card}.ts`, `app/src/i18n/tr.ts`, `app/parity/gen_golden.py`, `app/scripts/{test.sh,screens.sh,env.sh}`

## Adımlar
Her adım kendi commit'iyle biter ve tek başına yeşildir (`bash app/scripts/test.sh`).

0. **Taban.**
   - `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -1` = `origin/main`; ağaçta yalnız izinli iki izlenmeyen dosya.
   - `bash app/scripts/test.sh`, `.venv/bin/python app/parity/gen_golden.py --check`, paralel pytest. Sayılar `docs/app/p1/test_runs.txt`'ye.
1. **A1: crate portu (commit A1).**
   - EK3 §2 (`V1Params`, `hazard::linear`, v1 dalı, çıktı alanları, ret ve uyarı kodları, `Warning.bool_fields`).
   - EK3 §3.2 (`tufe.rs`: `month_for`, `index_for`, önek pini, `parse`).
   - `dec_cases.json` `real_size` bölümü ve `tufe_cases.json` (U56).
   - Crate birim testleri yeşil.
2. **A2: altın vektörler ve parite (commit A2).**
   - EK3 §4: `gen_golden.py` 23 model; 4 yeni `.jsonl` (≥ 600 satır/model); `_patched_params.jsonl` +12; MANIFEST; `bit_equal_floor.json` 23.
   - Açık küme girdileri `vault != SEALED` süzgeciyle ve kodsuz `case_id` ile girer (EK3 §4; kasa açılmış olsa da bu kural aynen kalır).
   - U53 (parite 23/23), U54 (kapsama), U55 (`golden_unchanged.sh`: eski 19 dosya bayt-eşit).
3. **A3: gömme, komutlar, TÜFE kaynağı (commit A3).**
   - `build_embed.rs` PINNED 23 + TÜFE CSV gömme; `commands/{models,predict,parity,freeze,config}.rs`.
   - TÜFE kaynağı (repo modunda repo dosyası her tahminde yeniden okunur; bağımsız modda gömülü). Dondur sihirbazında `TUFE_MONTH` engeli.
   - U57, U58 (K-P1 bağlam 1'e göre), U59 (geçici klonda `freeze` → 27 modelli kayıt; Rust parite 23/23 + unsupported 4).
   - Dondur ön koşulu `INDEX_SHA` artık gerçek INDEX'le eşleşmeli (gömülü INDEX = repodaki 27 girişli INDEX).
4. **D: Tavan serisi kartı (commit D).**
   - EK3 §5 (içerik §5.2, kural §5.3, tel kafes §5.4, near_era okuyucu §5.5) + K-P1-3 + K-P1-4.
   - `commands/scores_oot.rs` (okuyucu + bütünlük), `featured_ceiling`, `ceiling_summary`; `render/summary.ts`; Grup B `<details>` altında katlanır.
   - Testler:
     - U60–U63;
     - EK3'ün sentetik "kasa kapalı" fikstürüne ek olarak **gerçek `scores/scores_oot.json` + gerçek `scores/scores.json` ile render testi**: öne çıkan `ceiling_hazard_v0`, neden `RULE_5_5_NONE_ELIGIBLE_V0`; kasa sütunu v0/clip/real "ayırt edilemiyor (zaman-dışı terazide)", pooled "geçiyor (zaman-dışı terazide)"; yakın dönem clip "tolerans içinde", real/pooled "bozuyor";
     - U61 birim testlerine bu gerçek dosya durumunu da ekle;
     - bütünlük: kasa bloklarındaki `open: false` satırlar hata vermez; açık küme bloğunda `open: false` → `OOT_ROW_NOT_OPEN` (sentetik).
   - Ön uçta hesap yok (`no_frontend_math` taraması genişler).
5. **Ekran görüntüleri:** `app/scripts/screens.sh` (ya da mevcut `snapshot` yolu) ile sonuç ekranı.
   - İki senaryo: NETGL girdileri (j = 0 ve j = 3) ve VEYAS girdileri (f3 boş: v1 satırları RET).
   - `docs/app/p1/ekran/*.png`'ye kaydet; rapora ekle. Görüntüde kart, adaylar tablosu, üç terazi sütunu ve katlanmış Grup B görünmeli.
6. **Derleme** (commit yok):
   ```
   source app/scripts/env.sh
   cd app
   npm run tauri build -- --bundles app
   ```
   `/Applications`'a kopyalama. Yeni `BorsAi.app/Contents/MacOS/borsai-app` sha256'sını rapora yaz.
7. **Son kabul:** sıralı `.venv/bin/pytest -q`, `bash app/scripts/test.sh`, `gen_golden --check`. Gerekirse önceden onaylı APPPIN commit'i.
8. **Rapor** `docs/app/p1/RAPOR.md` (commit R). İçerik:
   - hash'ler;
   - U53–U63 sonuçları (tablo), EK3 §11 beklentisiyle karşılaştırma;
   - K-P1-3 okuyucusunun kapsamı;
   - gerçek dosyalarla kart çıktısı (metin olarak): öne çıkan, neden, adaylar tablosunun satırları;
   - ekran görüntüleri; test sayıları; `.app` sha'sı;
   - proje sahibi için kurulum komutları (aşağıdaki blok);
   - P2/P3/P4 için notlar.

## Proje sahibi için kurulum bloğu (rapora aynen koy)
Önce çalışan uygulamayı kapat (Cmd+Q), sonra:
```
cd ~/Desktop/BorsAi
ditto app/src-tauri/target/release/bundle/macos/BorsAi.app /Applications/BorsAi.app
open /Applications/BorsAi.app
```

## Tek oturumda bitmezse
- Her adım commit'le biter. Yeniden başlarken `git log`'dan son commit'i bul ve sonraki adımdan devam et. Yarım adımın commit'lenmemiş değişiklikleri ağaçta kalır: önce ölç, sonra sürdür.
- Bağlam dolarsa bir adım sonunda dur ve rapora "kalan adımlar" yaz. Proje sahibi aynı cümleyle yeni oturum açar.

## Kurallar
- **Yazılabilir:** `app/` (EK3 §1 P1 satırındaki dosyalar ve K-P1-3'ün `commands/scores_oot.rs`'i), `docs/app/p1/`, bu görev dosyası. K-P1-6 kapsamında `tests/` pin satırları (ayrı commit).
- **Salt okunur:** `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `docs/specs*`, `docs/app/SPEC_APP*.md`, `CLAUDE.md`, `legacy/`.
- Python'da eksik bulunursa Ö-görevi olarak raporla; düzeltme.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- `git add -A` yok. Her commit yalnız kendi yollarıyla:
  ```
  git add <yollar>
  git commit -m "BORSAI_APP_P1_<A1|A2|A3|D|APPPIN|REPORT>: <özet>" -- <yollar>
  ```
  İlk commit (A1) bu görev dosyasını da içerir. `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Push yok. Rapor Türkçe.

## Kabul kapısı
- **K1** Parite 23/23 (maks |Δ| ≤ 1e-9); eski 19 altın dosya bayt-eşit; `ignored_model_ids` = dört (C) kimliği.
- **K2** TÜFE kaynağı ve `TUFE_MONTH` engeli testli. Dondur ön koşulu gerçek INDEX'le geçiyor. Kayıt paritesi 23/23 + unsupported 4.
- **K3** Kart gerçek dosyalarla doğru: öne çıkan v0, neden `RULE_5_5_NONE_ELIGIBLE_V0`, terazi sütunları dosyadan, ön uçta hesap yok, Grup B katlanır. Ekran görüntüleri raporda.
- **K4** Son kabul: sıralı pytest + test.sh + `gen_golden --check` yeşil; `.app` derlendi. Commit'ler yalnız izinli yollarda; push yok.

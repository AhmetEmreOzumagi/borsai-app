# TASK_ID: BORSAI_FAZ7_APP_P3P4_20261001

Model: Opus 5.5 · Extra. Klasör: ~/Desktop/BorsAi. Ağ gerekmez. push/tag/amend yok.

## Rol
Uygulama EK3'ün son iki aşaması. Şartname `docs/app/SPEC_APP_EK3.md` (Fable, `7be8394`):
- **Bölüm 1 — P4:** `fall_d10_v0` ailesinin Rust portu ve Sonuç sayfasında **"Düşüş (D10) — arz fiyatının altına düşme olasılığı"** kartı (EK3 §8, §9 P4 satırları, §10.4, §11). Proje sahibinin "düşer mi" sorusu budur.
- **Bölüm 2 — P3:** Doğruluk sekmesinde **"Zaman-dışı test (eski kohort)"** paneli (EK3 §7, §10.3, §11).

Sıra P4 → P3. Her bölüm kendi commit'leriyle biter ve tek başına yeşildir. Sonunda uygulama bir kez derlenir.

## Bağlam: EK3 yazıldığından beri değişenler (orkestratör ölçtü, 2026-10-01)
0. **Taban:** `origin/main` = `572ac1f` (P2 bitti, push'lu; ağaç temiz).
1. **P1 ve P2 bitti:**
   - `PINNED_MODEL_IDS` 23; `ignored_model_ids` = dört (C) kimliği.
   - İkinci dizin (`INDEX_POST_D1`) gömülü.
   - `commands/scores_oot.rs` (P1) dosyayı satırsız önbellekte tutuyor; `OOT_ROW_NOT_OPEN` yalnız `oot_pre_h99` bloğunda (K-P1-3).
   - Raporlar: `docs/app/p1/RAPOR.md`, `docs/app/p2/RAPOR.md` (§11 notları).
2. **(C) dondurulmuş, Python referansı var.** EK3 §8'in "referans yok" notu artık geçersiz.
   - Model kimlikleri: `fall_d10_v0_h99`, `_pooled`, `_addsale`, `_pooled@ZERO` (INDEX 27 giriş, sha256 `7e636e8bf64b…`, dondurma `ce569a8`).
   - Referans `borsai/predict_fall.py`:
     - `FAMILY_FALL = "fall_d10_v0"`, `FALL_ALGORITHM = "l2_logit_v1_6_grid"`;
     - `ADDITIONAL_SALE_MISSING`, `additional_sale_flag`, `predict`, `fall_probability`;
     - `freeze.model_kind` → `"fall"`.
   - P4 adım 0 "referans kilidi" yine yapılır (çıktı anahtarları, ret sırası, kırpma uyarı kodu, `@ZERO` biçimi). Çelişkide **Python kazanır**.
3. **(C) kasa sonucu** (`docs/faz7_vault/SKOR_RAPOR.md`; D10 Brier, karşılaştırıcı `base_rate`, n 60–62):

   | Aday | k1 | k2 | k3 | Uygun |
   |---|---|---|---|---|
   | `pooled` | **geçiyor** (−0.045 [−0.092, −0.002]) | hayır: `v1_5_h99`'dan ayırt edilemiyor | — | hayır |
   | `h99` | hayır: ayırt edilemiyor (−0.040 [−0.088, +0.004]) | hayır | — | hayır |
   | `addsale` | hayır: ayırt edilemiyor (−0.006) | hayır | — | hayır |

   k1–k3 SPEC_C_V0 §5.5'teki kart seçim koşullarıdır. **Beklenen `featured_fall` sonucu: öne çıkan yok.** Kart bunu dosyadan kendisi bulmalı; elle yazılmaz.
4. **`scores.json` `near_era` (C) blokları:**
   - `h99`: "tolerans içinde" (karşılaştırıcı `base_rate`, −0.043 [−0.077, −0.005]);
   - `pooled`: "belirsiz" (karşılaştırıcı `fall_d10_v0_h99`);
   - `addsale`: "belirsiz" (`base_rate`);
   - `pooled@ZERO`: "tolerans içinde" (`base_rate`).
5. **Kayıtlar:**
   - Canlı 7 kayıt 16 modelli; P4'ten sonra kayıt paritesi "16/16 + kayıtta yok".
   - Yeni dondurulan kayıtlar 27 modelli; geçici klonda yazılan kayıtta parite 27/27, `unsupported` boş.
   - Eski kohortun açık küme üyelerinin (`vault != SEALED`, 71 arz) `registry/oot/records/<T>/` altında ikişer kaydı var; ikinci kayıt (C) modellerini taşır. **Ölçülen (C) hücreleri (toplam 284):**

     | Model | PREDICTED | `ADDITIONAL_SALE_MISSING` | `F3_MISSING` |
     |---|---|---|---|
     | `addsale` | 70 | 1 | — |
     | `h99` | 67 | 1 | 3 |
     | `pooled` | 67 | 1 | 3 |
     | `@ZERO` | 71 | — | — |
6. **`scores/scores_oot.json` bugün** (EK3 §11'deki "19 blok" beklentisi eski):

   | Blok | Model | Birincil hücre | Satırlar |
   |---|---|---|---|
   | `oot_pre_h99` | 27 | 8 | 1 349 (hepsi `open: true`) |
   | `oot_pre_h99_sealed` | 27 | 14 (2 geçiyor, 11 ayırt edilemiyor, 1 geçemiyor) | 1 728 (hepsi `open: false`) |
   | `oot_pre_h99_all` | 19 | 8 | 2 565 (1 349 açık + 1 216 değil) |
   | `post_d1`, `post_d1_sealed`, `post_d1_all` | 1'er | 1'er | `open` alanı yok |

   `retro_info` 568. Dosya 41 MB. `docs/SCORES_OOT.md` bölümleri: açık küme §2, kasa §8.1, toplam §9.1, D1 sonrası §6 / §10 / §11.
7. **Test komutları** (`docs/ENV.md`):
   - ara koşular `.venv/bin/pytest -q -n 6 --dist loadgroup`;
   - her commit'ten önceki son kabul koşusu sıralı `.venv/bin/pytest -q`.

   Taban sayıları adım 0'da ölçülür.

## Proje sahibi ve orkestratör kararları (bağlayıcı)
- **K-P4-1: düşüş kartında öne çıkarma.**
  - `featured_fall` SPEC_C_V0 §5.5 k1–k3'ü yalnız dosyalardaki `verdict`, `ci95` ve `near_era`'dan uygular; skor hesaplamaz.
  - Uygun aday yokken kartın satırı: **"öne çıkan yok — kasa sonrası kural (§5.5): uygun aday yok"**. SPEC_C §9'daki "kasada geçen aday yok" metni kullanılmaz: `pooled` kasada k1'i geçti, o metin yanıltır. Sapma rapora yazılır.
  - Her aday satırında, ilk sağlanmayan koşul düz metinle gösterilir (`tr.ts` eşlemesi):
    - k1 → "kasada taban orandan ayırt edilemiyor";
    - k2 → "kasada V1.5'ten ayırt edilemiyor";
    - k3 → "yakın dönemde taban orandan kötü / bozuyor".
  - Beklenen: `pooled` k2; `h99` ve `addsale` k1.
  - V1.5'in p_up sütunu olduğu gibi kalır. Hiçbir model listeden kalkmaz.
- **K-P4-2: düşüş kartının terazi sütunları** (K-P1-4 kalıbı).
  - **Zaman-dışı:** `oot_pre_h99_sealed` bloğunun birincil hücresinin `verdict`'i + " (zaman-dışı terazide)", karşılaştırıcısıyla.
  - **Yakın dönem:** `near_era.label` + karşılaştırıcı, dört model için de dosyadan.
  - **Canlı:** `scores.json` (n < 10 → "n = {n}: hüküm yok").
  - Değerler toplanmaz.
- **K-P4-3: gerçek kayıt paritesi (EK3'e ek; K-P2-4 kalıbı).**
  - Rust `predict_fall`, eski kohortun açık küme kayıtlarıyla koşulur. Süzgeç `registry/oot/cohort_pre_h99.csv` `vault != SEALED`; SEALED dizinleri **açılmaz**.
  - Girdiler kaydın `model_inputs`'undan alınır (`tufe_index` dahil).
  - Beklenti (önceden yazılı): **284 hücre, parite 284/284**, durum dağılımı bağlam 5'teki tabloyla birebir.
  - Çıktıda yalnız sayılar yer alır.
- **K-P3-1: zaman-dışı panelde kod görünürlüğü.**
  - Satır tablosu **yalnız `oot_pre_h99` (açık küme) bloğunda** ve yalnız `open == true` satırlarla çizilir.
  - `oot_pre_h99_sealed`, `oot_pre_h99_all` ve üç `post_d1*` bloğunda yalnız hücreler, kırılımlar (`by_year`, `by_regime`) ve sayaçlar gösterilir. Satır tablosu ve arz kodu yoktur.
  - `retro_info` yalnız açık satırlarda geçen kodlarla çizilir (EK3 §7.1).
  - Amaç: kasa kodları uygulama ekranında, fikstürlerde, ekran görüntülerinde ve raporlarda hiç görünmez.
- **K-P3-2: bütünlük.**
  - `OOT_ROW_NOT_OPEN` yalnız `oot_pre_h99` bloğunda uygulanır (K-P1-3 aynen).
  - `post_d1*` satırlarında `open` alanı yoktur; bu denetim onlara uygulanmaz.
  - EK3 §7.1'in diğer kuralları (`OOT_CELLS_BELOW_MIN_N`, `VERDICT_WITHOUT_INTERVAL`, `OOT_LIVE_COUNTS_NONZERO`, sürüm) altı bloğun hepsinde geçerlidir.
- **K-P3-3: U75 beklentisi güncel dosyaya göre:**
  - açık küme 27 blok / 8 birincil (`SCORES_OOT.md` §2);
  - kasa 27 / 14 (§8.1);
  - toplam 19 / 8 (§9.1);
  - D1 sonrası üç alt bölüm (§6, §10, §11);
  - kasa satırı "kasa: açıldı — {generated_at_utc}".

  Değer metinleri `SCORES_OOT.md` ile aynıdır (biçim farkı hariç).
- **K-P34-4: Windows uyumu** (K-P1-5 aynen).
  - Yeni kodda sabit Mac yolu ya da kabuğa özel sözdizimi yok.
  - Yollar `PathBuf`/`Path.join` ile kurulur.
  - Platform farkı tek fonksiyonda toplanır.
- **K-P34-5: önceden onaylı pin güncellemeleri** (K-P1-6 aynen).
  - `app/` altında model sayısı, `ignored_model_ids` (→ `[]`), MANIFEST sha'ları, altın dosya sayısı ve fikstür sayan satırlar asgari yeniden pinlenebilir.
  - `tests/` (Python) altında yalnız `app/` dosyasını ya da `gen_golden --check` dosya sayısını pinleyen satırlar değişebilir. Bunlar ayrı commit APPPIN olur.
  - Bekçi (sıra, kasa, hijyen, temizlik) testine dokunmak gerekirse **DUR**.
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** Parite tutmuyorsa Rust düzeltilir; Python'a dokunulmaz; tolerans gevşetilmez.
- **Soru sorman gerekirse** seçenekleri açık yaz. Proje sahibi orkestratöre danışarak cevaplayacak.

## İzinli izlenmeyen
Yalnız bu görev dosyası. Başka bir şey varsa DUR.

## Paralel
Bu görev koşarken başka oturum yok. Proje sahibi bu sırada git komutu çalıştırmaz.

## ÖNCE OKU
- CLAUDE.md
- `docs/app/SPEC_APP_EK3.md`: §0, §1, §4.1, §7, §8, §9 (P3/P4 satırları), §10.3, §10.4, §11, §12
- `docs/app/p1/RAPOR.md` §3, §11 ve `docs/app/p2/RAPOR.md` §7, §11
- `docs/specs_faz7_c/SPEC_C_V0.md` (§2.3, §3, §5.5, §8, §9) ve `KARARLAR_C.md`
- `docs/faz7_vault/SKOR_RAPOR.md` ((C) satırları ve §5.5 sonucu)
- `docs/SCORES_OOT.md` (§1, §2, §6, §8.1, §9.1, §10, §11)
- `docs/ENV.md`
- `borsai/predict_fall.py`, `borsai/freeze.py` (`model_kind`), `borsai/predict.py` (V1.5 `predict_core`)
- `app/src-tauri/build_embed.rs`, `crates/borsai_predict/src/*`, `src/commands/{scores,scores_oot,predict,parity,models,ceiling}.rs`, `src/render/{summary,accuracy,results}.ts`, `src/screens/accuracy.ts`, `src/i18n/tr.ts`, `app/parity/gen_golden.py`, `app/scripts/{test.sh,screens.sh,env.sh}`

## Adımlar
0. **Taban.**
   - `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -1` = `origin/main`; ağaçta yalnız bu görev dosyası.
   - `bash app/scripts/test.sh`, `.venv/bin/python app/parity/gen_golden.py --check`, paralel pytest. Sayılar `docs/app/p34/test_runs.txt`'ye.

### Bölüm 1 — P4 (düşüş kartı)
1. **C0: referans kilidi** (commit yok). EK3 §8 ile `predict_fall.py` arasındaki farkları ölç ve listele (U76); rapora girer, kod Python'u izler.
2. **C1: crate (commit C1; bu görev dosyası da girer).** `Kind::Fall`, `parse_fall`, `fall::predict_fall` (§8.1–§8.2, referans kilidine göre), ret ve uyarı kodları, `tr.ts` `CODE_TEXT`/`KIND_TEXT`. Birim testleri.
3. **C2: altın vektörler (commit C2).**
   - §8.3: `gen_golden.py` 27 model, `FALL_IDS`; dört `.jsonl` (≥ 560 satır/model); `_patched_params.jsonl` +10; MANIFEST; `bit_equal_floor.json` 27.
   - Girdi tabanlarında kasa süzgeci P1'deki gibi.
   - U77, U78. `golden_unchanged.sh`: mevcut bütün altın `.jsonl` dosyaları (23 model + 3 koşullu + post_d1) ve `_patched_params.jsonl`'un mevcut 51 satırı bayt-eşit (U80; taban P2 commit'i).
4. **C3: gömme ve komutlar (commit C3).**
   - `build_embed.rs` `PINNED_MODEL_IDS` 27, `ignored_model_ids == []`; bütünlük 27.
   - `predict_all` 27 sütun; kayıt paritesi; K-P4-3 gerçek kayıt paritesi (284/284).
5. **C4: düşüş kartı (commit C4).**
   - §8.4 + K-P4-1 + K-P4-2; `featured_fall` (`scores::featured_ceiling` kalıbı); `render/summary.ts`.
   - U79 ve ek olarak **gerçek `scores.json` + gerçek `scores_oot.json` ile render testi:** "öne çıkan yok — kasa sonrası kural (§5.5): uygun aday yok"; `pooled` satırında "kasada V1.5'ten ayırt edilemiyor"; `h99`/`addsale` satırlarında "kasada taban orandan ayırt edilemiyor"; kasa sütunu `pooled` "geçiyor (zaman-dışı terazide)", `h99`/`addsale` "ayırt edilemiyor (zaman-dışı terazide)"; yakın dönem etiketleri bağlam 4'teki gibi.
   - Ön uçta hesap yok (`no_frontend_math` genişler). Sözcük listesi SPEC_APP §4.

### Bölüm 2 — P3 (zaman-dışı panel)
6. **E1: okuyucu ve bütünlük (commit E1).**
   - `commands/scores_oot.rs` genişler: repo modunda yalnız `oot_pre_h99` açık satırları süzgeçli okunur (K-P3-1); altı bloğun hücre ve kırılımları; K-P3-2.
   - U73 (fail-closed), U74 (kasa alt bölümleri).
7. **E2: panel (commit E2).**
   - EK3 §7.2 yerleşimi: `render/accuracy_oot.ts`, `.panel-oot`, `scalesNote` üç terazi; açık küme / kasa / toplam / D1 sonrası (üç alt bölüm) / OOT_RETRO.
   - U71, U72, U75 (K-P3-3 beklentisiyle).
   - Kasa kodu taraması: DOM'da `cohort_pre_h99.csv`'deki SEALED kodlarından hiçbiri yok. Test kodu yalnız sayı basar.

### Kapanış
8. **Ekran görüntüleri** (`docs/app/p34/ekran/*.png`):
   - NETGL girdileriyle düşüş kartı;
   - VEYAS girdileriyle düşüş kartı (h99/pooled RET, addsale tahmin);
   - zaman-dışı panelin açık küme, kasa, toplam ve D1 sonrası bölümleri.

   Görüntülerde kasa kodu görünmez.
9. **Derleme** (commit yok):
   ```
   source app/scripts/env.sh
   cd app
   npm run tauri build -- --bundles app
   ```
   `/Applications`'a kopyalama. `.app` sha256'sı rapora.
10. **Son kabul:** sıralı `.venv/bin/pytest -q`, `bash app/scripts/test.sh`, `gen_golden --check`. Gerekirse önceden onaylı APPPIN commit'i.
11. **Rapor** `docs/app/p34/RAPOR.md` (commit R). İçerik:
    - hash'ler;
    - referans kilidi farkları;
    - U71–U80 + K-P4-3 sonuçları (tablo), EK3 §11 ve bu dosyanın beklentileriyle karşılaştırma;
    - gerçek dosyalarla düşüş kartı ve zaman-dışı panel çıktısı (metin olarak);
    - ekran görüntüleri; test sayıları; `.app` sha;
    - kurulum bloğu (aşağıda);
    - Windows derlemesi için notlar (Mac'e özel kalan yerlerin listesi: ör. `config.rs: default_python`, `borsai/tufe.py` `APPEND_COMMAND`).

## Proje sahibi için kurulum bloğu (rapora aynen koy)
Önce çalışan uygulamayı kapat (Cmd+Q), sonra:
```
cd ~/Desktop/BorsAi
ditto app/src-tauri/target/release/bundle/macos/BorsAi.app /Applications/BorsAi.app
open /Applications/BorsAi.app
```

## Tek oturumda bitmezse
- Her adım commit'le biter. Yeniden başlarken `git log`'dan son commit'i bul ve sonraki adımdan devam et. Yarım adımın commit'lenmemiş değişiklikleri ağaçta kalır: önce ölç, sonra sürdür.
- Bağlam dolarsa bir adım sonunda dur ve `docs/app/p34/test_runs.txt`'ye "kalan adımlar" yaz. Proje sahibi aynı cümleyle yeni oturum açar.

## Kurallar
- **Yazılabilir:**
  - `app/` (EK3 §1 P3 ve P4 satırlarındaki dosyalar);
  - `docs/app/p34/`, bu görev dosyası;
  - K-P34-5 kapsamında `tests/` pin satırları (ayrı commit).
- **Salt okunur:** `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `docs/specs*`, `docs/app/SPEC_APP*.md`, `CLAUDE.md`, `legacy/`.
- Python'da eksik bulunursa Ö-görevi olarak raporla; düzeltme.
- Kasa (SEALED) üyelerinin kodları `app/` ve `docs/app/p34/` altındaki hiçbir dosyaya, fikstüre, rapora, ekran görüntüsüne ya da test çıktısına girmez.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- `git add -A` yok. Her commit yalnız kendi yollarıyla:
  ```
  git add <yollar>
  git commit -m "BORSAI_APP_P34_<C1|C2|C3|C4|E1|E2|APPPIN|REPORT>: <özet>" -- <yollar>
  ```
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Push yok. Rapor Türkçe.

## Kabul kapısı
- **K1** Parite 27/27 (U77; `p_up` ≤ 1e-9); mevcut altın dosyalar bayt-eşit; `ignored_model_ids == []`; gerçek kayıt paritesi 284/284 ve durum dağılımı birebir.
- **K2** Düşüş kartı gerçek dosyalarla K-P4-1/K-P4-2'ye uygun: öne çıkan yok, neden metinleri, terazi sütunları dosyadan; ön uçta hesap yok.
- **K3** Zaman-dışı panel üç terazi ayrı; altı blok K-P3-3 sayılarıyla; satır tablosu yalnız açık kümede; DOM'da, fikstürlerde ve ekran görüntülerinde kasa kodu yok.
- **K4** Son kabul: sıralı pytest + test.sh + `gen_golden --check` yeşil; `.app` derlendi. Commit'ler yalnız izinli yollarda; push yok.

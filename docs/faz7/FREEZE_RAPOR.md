# BORSAI_FAZ7_FREEZE_20260927 — `ceiling_hazard_v1` ailesinin dondurulması: rapor

Görev `docs/prompts/FAZ7_FREEZE.md` (Opus 5.5, bağımsız el: sonuçları gören uygulayıcıdan ayrı oturum). Ağ yok; push, tag,
amend yok. Bağlayıcı metinler `docs/specs_faz7/SPEC_HAZARD_V1.md` (sha256 `25229cea8f6f235db6562f3dee4992e6b8e22e0cbc23b44b25eeb6d2704d0944`),
`docs/specs_faz7/KARARLAR.md`; denetim `docs/fable_faz7_audit/AUDIT.md` (`eda9732`: dört kimlik FREEZE_OK). **Model davranışı
değişmedi**: bütün düzeltmeler "kodu şartnameye uydurmak = aynı model_id" sınıfındadır; şartname değişmedi.

## 0. Kısa sonuç

- Dört kimlik donduruldu: `ceiling_hazard_v1_clip`, `ceiling_hazard_v1_real`, `ceiling_hazard_v1_pooled`,
  `ceiling_hazard_v1_pooled@INF` (§6.4: etiketi "bozuyor" olan real ve pooled da; §5.5 k3 gereği uygulama birincili olamazlar).
- Donmuş JSON'lar nihai fit önizlemeleriyle `created_at`, `code_version`, `runtime` dışında `==` (gerçekte yalnız `created_at` ve
  `code_version` farklı); dondurma temiz ağaçta (`borsai_dirty` false), kod commit'i K'nın koduyla.
- `models/INDEX.json` 19 → 23 giriş; ilk 19 giriş metin olarak aynı; 19 eski model dosyası, `post_d1_hazard_v0.json` ve
  `INDEX_POST_D1.json` bayt-eşit.
- Denetim bulguları kapandı: B1 (yalnız `test_clipped` değişti; 35 / 36 / 23), B2 ve B3 (mutasyon c2 ve j artık kırmızı),
  B4–B6, B8–B9 belgelendi, B7 bekçisi kodda; duyarlılık satırları günlükte.
- İki karar proje sahibine soruldu (bu görevde): F1'in kırdığı uygulama pinleri için **asgari yeniden pin** (ayrı commit APPPIN,
  J31) ve dondurma sonrası skor karşılaştırmalarında **J30 istisnası**. İkisi de onaylandı.
- Tam test her aşamada yeşil (F1 sonrası 729 passed); `test.sh` ve `gen_golden --check` yeniden pinden sonra yeşil.

## 1. Commit'ler (sıra K → F1 → APPPIN → F2)

| Commit | Hash | Üst | İçerik |
|---|---|---|---|
| K | `d903ab1496b1105297319d56b3605c3fde9bc835` | `4fe4e51` | `borsai/` (freeze, hazard, registry, report_faz7, tufe), `data/raw/tuik/build_tufe_csv.py`, testler, Faz 7 altın dizini (B1), `experiments/log.jsonl` (+8), MODELS.md, SPEC_DEVIATIONS J (J10/J16 ekleri, J23–J31), PROVENANCE §11a, `docs/faz7/ekler/` (4 dosya), görev dosyası — 35 dosya, +1406 / −168 |
| F1 | `66adbca9d73f1699fea6b44586b3efa50aded486` | `d903ab1` | yalnız `models/ceiling_hazard_v1_{clip,real,pooled,pooled@INF}.json` ve `models/INDEX.json` — 5 dosya, +2047 |
| APPPIN | `7133991b8ba14a219b059f1be6125fc8d743b931` | `66adbca` | `app/parity/golden/MANIFEST.json` (1 satır), `app/tests/fixtures/ui/preflight_{ok,blocked}.json` (INDEX sha), `app/src-tauri/tests/build_embed.rs` (beklenen yok sayılan liste) — 4 dosya, +10 / −5 |
| F2 | (bu raporu içeren commit) | `7133991` | `tests/test_faz7_frozen.py` (yeni), `tests/test_faz7_golden.py` (1 satır), `borsai/report_faz7.py` (dondurma notu), `docs/MODELS.md`, `docs/faz7/` |

`4fe4e51` paralel Fable oturumunun commit'idir (BORSAI_FAZ7_C_SPEC; yalnız `docs/specs_faz7_c/` ve kendi görev dosyası): K'dan önce
geldi, `borsai/`, `models/`, `data/`, `tests/` yollarına dokunmadı. B1 koşusu (17:06) ondan önceydi (17:12); koşunun HEAD'i `eda9732`.

## 2. K1 · B1 (`clipped` = herhangi bir sütun, §3.1)

`hazard.TrainingResult.predict`: `clipped = bool(clipped_features)` (önce `bool(t["f3_winsorized"])`). v0/PB tariflerinde kırpılan tek
sütun f3 olduğundan bayrak orada aynıdır (Faz 1B/4 altınları bayt-eşit, tam testte). Yeniden üretim `docs/faz7/ekler/k1_b1_regen.py`
(çıktı `k1_b1_regen.txt`), resmi günlüğe `context = faz7_golden_b1` ile dört satır.

| Ledger | Sütun × satır | Değişen | Eski sha256 → yeni sha256 |
|---|---|---|---|
| `ceiling_hazard_v1_clip` | 74 × 87 | yalnız `test_clipped`, 15 satır FALSE → TRUE | `ca711a6c029c…` → `22057c06f683871ea1fd7cb8c98d46a36f60135b5f7d173fd8e71b7987865141` |
| `ceiling_hazard_v1_real` | 76 × 87 | yalnız `test_clipped`, 16 satır FALSE → TRUE | `026598438264…` → `e97a67f4246e5f706250ae74585e2aa0e29e3204dfa7a5ed221ad5e66610e955` |
| `ceiling_hazard_v1_pooled` | 81 × 97 | yalnız `test_clipped`, 16 satır FALSE → TRUE | `45a3e2dfe5f5…` → `e165cafe26ee7150b66eb3b31e8e0d83e351983a889be6974e68f5c0f6f1010c` |
| `ceiling_hazard_v1_pooled@INF` | — | bayt-eşit | `08cec307684d4da7aaa863fc5d3e22827a6032834a34c1d52914cfb5475a4128` |
| `base_km_expanding__pooled`, `base_km_last10__pooled` | — | bayt-eşit | `cd77d9fec3d6…`, `e93ffc42a75e…` |

- Herhangi-sütun sayıları **35 / 36 / 23** (yalnız f3: 20 / 20 / 7); @INF 0. Fable'ın bağımsız ledger'larıyla
  (`docs/fable_faz7_audit/ekler/repro_ledgers/`, `test_clipped_any`, `test_clipped_features`) 87/87, 87/87, 97/97 aynı.
- Dört nihai fit önizlemesi yeniden kuruldu ve eskileriyle (üç alan dışında) aynı; dosyaları bayt olarak korundu.
- MANIFEST `934811c7876ab91a68b1d80078b2ad5e4f373348c76bd02236101ab87b2a3f01`, SHA256SUMS `bca5f194bd8648f078b32057cd51e3c1272a8a7e3cd7c40c4e6b00b90321dfdf`.
  MANIFEST ve dört günlük satırı `borsai_dirty = true`, `git_commit = eda9732`: kod düzeltmesi ile altın dosyalar aynı commit'te (K)
  olduğundan kaçınılmaz (Faz 1A/1B/4 altın satırları da böyleydi). `borsai_source_sha256 = 0d374dd8ae9a…` K'nın `borsai/` ağacıdır;
  test bunu satırı getiren commit'in ağacıyla sınar (`faz7_support.code_sha_matches_introducing_commit`).
- Günlükte eski satırlar değişmedi; model başına ikinci satır. Metrikler, yakın dönem hücresi, özetler eski satırla aynı;
  `faz7_variants` 2 / 2 (değişmedi). MODELS.md fold özeti: "test arzı kırpılan fold (herhangi bir özellik, §3.1): 35 (f3 kırpılan: 20)" vb.

## 3. K2 / K3 · mutasyonların kırmızı gösterimi (`docs/faz7/ekler/k2_k3_mutasyon.txt`)

| Mutasyon | Denetimde | Şimdi |
|---|---|---|
| c2: `tufe.index_for` bekçisi `release_date ≤ T`'yi kabul eder | 10 passed (yeşil) | `test_release_on_T_itself_is_not_pit` KIRMIZI (1 failed, 16 passed) |
| j: `NEAR_ERA_TOLERANCE = 0.015` | 12 passed (yeşil) | `test_near_era_tolerance_constant_and_rule_text`, `test_models_md_faz7_section_only_with_golden_and_before_faz5`, `test_report.py::test_models_md_is_up_to_date` KIRMIZI (3 failed) |

Her ikisi geri alındı (dosyalar bayt-eşit; `borsai/` ağacı önce/sonra `0d374dd8…`); mutasyonsuz aynı seçimler yeşil.
`OPERATIONAL_RULES_FAZ7`'deki eşik artık `f"{bt.NEAR_ERA_TOLERANCE:+.3f}"`; render edilen MODELS.md kural metni bayt-eşit.

## 4. K4 / K5 · dondurma ve kayıt kodu, TÜFE aylık ekleme

**Dondurma yolu (J25):** `freeze.freeze` FAZ7 kimliklerini `freeze.fit_v1` → `backtest.final_fit_v1`'e yönlendirir (fit.fit v1'i
bilmez); CLI `--models` bu kimlikleri tanır; INDEX girişi sona.

**Kayıt girdileri (J26), ortak yol `freeze.v1_record_inputs`** (canlı `build_record` ve eski kohort `build_oot_record`):
- INDEX'te deflatörlü model varsa `tufe` bloğu {series, rule `T_MONTH_MINUS_2`, file, file_sha256, pins, month, index, release_date,
  bulletin_id, refusal, reason} ve `model_inputs["tufe_index"]` / `["tufe_refusal"]` (`tufe.index_for(T)`, `release_date < T` bekçisi
  ve modellerin önek pini).
- **Yeni ön koşul:** T'nin ayı − 2 dosyada yoksa `freeze.TufeMissing`, kayıt **yazılmaz**; ileti eksik ayı ve komutu verir. Önek pini
  tutmazsa `TUFE_FILE_MISMATCH`, yayım T'den önce değilse `TUFE_NOT_PIT`: deflatörlü hücreler RET, kayıt yazılır. T bilinmiyorsa
  `TUFE_MISSING` reddi.
- Canlı kayıtta `alloc_regime` yok (r = 0); eski kohort kaydında rejimli model varsa `alloc_regime` = kohort satırının ALLOC_REGIME
  etiketi. **B7 bekçisi** (`regime_input_problems`): rejimli model varken anahtarsız eski kohort kaydı ve anahtarlı canlı kayıt kurulmaz.
  Görev bekçiyi `build_record`'da anıyordu; eski kohort kayıtlarını `build_oot_record` kurduğu için bekçi ikisinin ortak yolunda
  (aksi halde B7'nin riski o yolda kalırdı). INDEX'te bu modeller yokken kayıt biçimi aynen (S2 kayıtları, 7 canlı kayıt).
- `registry.F3_MODELS` üç adayı içerir (J24; @INF hariç).

**Aylık TÜFE ekleme (J27, PROVENANCE §11a).** Komut (tek metin `borsai/tufe.py: APPEND_COMMAND`):

```
.venv/bin/python data/raw/tuik/build_tufe_csv.py --append-month <YYYY-MM> --bulletin-id <bülten sayısı> --release <YYYY-MM-DDT10:00:00+03:00> --xls <indirilen tablo .xls> --download-url '<indirme bağlantısı>' --sha256 <indirilen tablonun sha256'sı>
```

Ay m kendi bülteninin tablosundan gelir (tablo m'de biter, [2025=100], her eski ayı aynen verir; aksi halde durur: yeni veri sürümü);
yayım m + 1'in ≥ 3'ü 10:00 iş günü; sha verilenle aynı; yeni satır tabloyu adlandırır; eski satırlar bayt-eşit, `TUFE_PIN` tutar;
tam derleme yeni dosyayı üretmezse yazılanlar geri alınır; `--check` bütün dosyayı yeniden üretir. **Gerçek ay eklenmedi** (ağ yok);
sentetik testler `tests/test_faz7_tufe.py::test_monthly_append_*`. İlk gerçek ekleme **Eylül 2026** (bülten 2026-10-05 beklenir;
Kasım 2026 arzlarının kaydı için gerekli; Ekim arzları 2026-08'i kullanır, dosyada).

Testler: `tests/test_faz7_freeze.py` (7), `tests/test_faz7_tufe.py` (+8), `tests/test_faz7_backtest.py` (+1).

## 5. K6 / K7 · belgeler ve günlük

SPEC_DEVIATIONS: J10'a B4 eki (mod salınımı 2023-09 … 2025-01, dışlamalı 44 fold / 25'i yakın dönemde, nihai fit'te dışlama yok,
+0.0289 → +0.0279, "kural değişmez"); J16'ya B6 eki (beşinci test); J23 (B1), J24 (F3_MODELS), J25 (dondurma yolu), J26 (kayıt
girdileri, B7), J27 (aylık ekleme), J28 (B5), J29 (B8, B9), J30 (dondurma sonrası skor karşılaştırma istisnası), J31 (uygulama
yeniden pini). Günlük 71 → 79 satır (yalnız ekleme): 4 B1 koşusu + Fable'ın 4 duyarlılık satırı (`kind: sensitivity`,
`context: fable_faz7_audit_sensitivity`, denetimin dosyasıyla aynen).

## 6. F1 · dondurma

`.venv/bin/python -m borsai.freeze --models ceiling_hazard_v1_clip ceiling_hazard_v1_real ceiling_hazard_v1_pooled ceiling_hazard_v1_pooled@INF`
(HEAD `d903ab1`, ağaç temiz, `borsai_dirty` false). Dosya adları beklenen adlar.

| model_id | sha256 | Eğitim | Veri sürümü | spec_sha256 |
|---|---|---|---|---|
| `ceiling_hazard_v1_clip` | `f3a147535242f8bde381ea68113f295f0a7dcdb5dd8a1046a3c1a55b0308241d` | 97 (kesim 2026-08-19) | `a0c7d082…` (H99) | `6103d3c9189c…` |
| `ceiling_hazard_v1_real` | `d81dad3d60c18ba23298d0ca4c4e315b60cc665d34781ca52f06d001d21ba09d` | 97 | `a0c7d082…` | `fea051b61752…` |
| `ceiling_hazard_v1_pooled` | `e03e71e0bb6e7c65ceb9cdf0ee95b25334749362549428077ab670dd3f261402` | 165 | `2ee8d51b…` (v2) | `2a088b0d86d7…` |
| `ceiling_hazard_v1_pooled@INF` | `7d7c9d1ee5a6a0c255fcf98103f872239439436a9e2da478601837d5eaf3f361` | 165 | `2ee8d51b…` | `f53ad4cf1ba9…` |

INDEX'e eklenen dört giriş `freeze.index_entry` alanlarıyla (algorithm, file, sha256, schema_version, spec_sha256, training_n,
training_cutoff_date, training_tickers_sha256, data_version_sha256, frozen_at 2026-09-27T17:38:13/15+03:00, frozen_at_basis, status FROZEN);
yeni INDEX sha256 `53265dd5d324b30eeca8a4211c17d3314815900ea9159dd63a34fcf23ab037a7`. Her JSON'da `spec.spec_document.sha256` =
`25229cea…0944` = şartname dosyasının sha'sı.

**Önizleme ↔ donmuş JSON:** dördünde de yalnız `created_at` ve `code_version` farklı (`code_version` = {git_commit `d903ab1…`,
borsai_dirty false, borsai_source_sha256 `0d374dd8…`}); `runtime` dahil öteki bütün alanlar `==`. Uyuşmazlık yok. Commit öncesi hızlı
kontrol (`test_faz7_golden.py`, `test_faz7_model.py`): 36 passed, 1 failed — yalnız `test_models_dir_unchanged`'in "`models/` commit'li"
satırı (dosyalar henüz commit'lenmemişti); F1'den sonra yeşil.

## 7. Bayt-eşitlikler

- `models/INDEX.json`'un ilk 19 girişi metin olarak aynı (yeni dosya eski metnin son girişe kadarki önekiyle başlar); 19 eski model
  dosyası, `post_d1_hazard_v0.json`, `INDEX_POST_D1.json`: 21/21 bayt-eşit (`tests/test_faz7_frozen.py` ayrıca `eda9732`'yle sınar).
- `data/` altında yalnız `build_tufe_csv.py` değişti; TÜFE CSV'si ve xls bayt-eşit (`--check` identical).
- `tests/reference/` altında Faz 7 dışı dosyalar değişmedi; Faz 7 altın dizininde yalnız 3 ledger, MANIFEST, SHA256SUMS.
- `scores/`, `docs/SCORES.md`, `registry/`, `docs/specs*`, `docs/fable_faz7_audit/`, `legacy/`, `CLAUDE.md` değişmedi.

## 8. Test sayıları (ayrıntı `docs/faz7/ekler/freeze_test_runs.txt`)

| Aşama | pytest | test.sh | gen_golden --check |
|---|---|---|---|
| Taban (eda9732) | 712 passed, 450.7 s | yeşil (cargo 94, npm 222, parity 4, U46) | 25/0 |
| K öncesi (commit'siz) | 726 passed, 3 failed, 677.9 s — üçü temizlik bekçisi (commit'lenmemiş `data/raw/tuik/build_tufe_csv.py`) | yeşil | 25/0 |
| K sonrası | 729 passed, 516.2 s | — | — |
| F1 sonrası (MODELS.md çalışma ağacında) | 729 passed, 504.9 s | yeniden pin öncesi kırmızı (§9); sonrası yeşil | önce MANIFEST farklı; sonra 25/0 |
| F2 öncesi | 741 passed, 502.8 s (+12: `tests/test_faz7_frozen.py`) | yeşil (cargo 94, npm 222, parity 4, U46; 55 s) | 25/0 |

## 9. Uygulama etkisi (EK3 girdisi; kaynakta ve prova klonunda ölçüldü)

- **Yeniden derlenmeden (bugünkü ikili, gömülü INDEX 19 giriş, sha `1bc33791…`):** `freeze.rs: preflight_in` repo INDEX'inin sha'sını
  (`53265dd5…`) gömülüyle karşılaştırır → `INDEX_SHA` engeli; `freeze_in` Python'u çağırmadan `FREEZE_PREFLIGHT_BLOCKED` döner; ayarlar
  ekranındaki `INDEX_SHA` denetimi kırmızı. Uygulama yeniden derlenene kadar "dondur" akışı kapalıdır (doğru davranış).
- **Yeniden derlenince:** `build_embed` sabit 19 kaydı gömer, dört v1 kaydı `ignored_model_ids`'e (Hakkında ekranında görünür);
  `INDEX_JSON` 23 girişli; `models::verify` 19 dosyayı INDEX'in ilk 19 girişiyle denetler (geçer).
- **`compare_record` v1'li bir kaydı:** 23 hücrenin 19'u Rust'ta yeniden çalıştırılır; dört v1 hücresi `unsupported` listesine düşer
  (uyuşmazlık değil; `ParityReport::ok()` yalnız `mismatches`'a bakar) → parite ok, `n_record_models = 23`. Kaydın `model_inputs`'undaki
  yeni anahtarlar (`tufe_index`, `tufe_refusal`) Rust tahmininde yok sayılır (girdiler anahtarla okunur). Sicil ekranı v1 hücrelerini
  `unsupported_models` olarak listeler. Var olan 7 kayıt (19 hücre) için değişiklik yok.
- **Pinler:** F1 dört yeri kırdı (§8); proje sahibi kararıyla APPPIN'de yalnız INDEX sha'ları ve beklenen yok sayılan liste güncellendi
  (J31). `app/src-tauri/build_embed.rs`'nin başındaki "`ignored_model_ids` … bugün boştur" yorumu artık eskidir (değiştirilmedi).
- **EK3'ün işi:** Rust v1 desteği (f1r Decimal 60, genel kırpma bayrağı ve `clipped_features`, rejim bloğu, TÜFE retleri, yeni çıktı
  alanları), `PINNED_MODEL_IDS` 19 → 23, altın vektörler (16 eski dosya bayt-eşit), "Tavan serisi" kartı, uygulamanın TÜFE'yi nereden
  alacağı (IMPL_RAPOR §14), UI fikstürleri.

## 10. Sapmalar ve kararlar

1. **Ek commit APPPIN (J31)** — görev `app/`'i salt okunur sayıyor, kabul kapısı ise F1 sonrası `test.sh` ve `gen_golden --check` yeşil
   istiyordu; F1 dört pini kırdı (geçici klonda önceden ölçüldü). Proje sahibine soruldu: "asgari yeniden pin" (Rust mantığı yok).
2. **J30 test istisnası** — "skorlar yeniden üretilmez" kararıyla commit'li `scores.json`/`scores_post_d1.json` eski kaldı; yeniden
   hesaptan yalnız dondurulmuş Faz 7 kimliklerinin izleri (4 kart, 28 retro_info satırı, INDEX sha'sı) çıkarılıyor. Proje sahibi onayladı.
3. **Dondurma sonrası durumu tanıyan test uyarlamaları K'da** — "19 model" varsayan testler (J30 listesi) iki durumda da doğru olacak
   biçimde K'ya girdi; böylece F1 sonrası tam test ek değişiklik gerektirmedi (MODELS.md dışında). Geçici klon provası: uyarlamasız
   22 kırmızı, uyarlamalı 2 (MODELS.md, F2'nin işi).
4. **B7 bekçisinin yeri ve eski kohort girdileri** — bekçi hem canlı hem eski kohort kayıt yolunda; eski kohort yolu (INDEX'te v1 varken)
   `tufe` bloğu ve kohort etiketinden `alloc_regime` yazar. `--only-missing-models`, model başına kapı ve `oot_pre_h99_sealed/_all`
   yapılmadı (sıradaki görev).
5. **`registry.F3_MODELS`** üç adayla genişletildi (J24); görev listesinde adıyla yoktu, F13 kuralının gereği.
6. **B1 satırları `borsai_dirty = true`** (J23) — tek K commit'i şartı yüzünden; kod sha'sı K'ya bağlandı ve testli.
7. MODELS.md'de Faz 7 dışı tek değişiklik "Kayıtlı modeller" tablosuna INDEX'ten gelen dört satır (render); öteki bölümler aynen.
   `docs/faz7/IMPL_RAPOR.md`'deki "20 / 20 / 7" yalnız f3 sayısıdır; rapor değiştirilmedi (düzeltme J23'te ve MODELS.md'de).
8. Hijyen: yeni metinlerde bülten adı kalıbı ve kasa kodu yok (bekçi testleri yeşil); duyarlılık satırları denetimin dosyasıyla aynen.

Push yok. Zaman kanıtı için proje sahibi F1'i (ve onu içeren dalı) push etmeli; ardından `python -m borsai.push_proof 66adbca`.

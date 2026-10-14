# BORSAI_FAZ7_OOT_RECORDS_20260928 — eski kohort ek kayıtları, model başına kapı ve kasa skorlama kodu: rapor

Görev `docs/prompts/FAZ7_OOT_RECORDS.md` (Opus 5.5). Ağ yok; push, tag, amend yok. Bağlayıcı metinler: SPEC_HAZARD_V1 §7.1 adım
3–5, §7.2, §7.3, §11-10/11/12; SPEC_C_V0 §5.2, §7, §11-10; KARARLAR, KARARLAR_C; SPEC_OOT_PRE_H99_V0 §2, §6 ve KARARLAR D6;
SPEC_APP_EK3 §5.5 (Ö1) ve §12 (Ö2). **Hiçbir model davranışı değişmedi** (model dosyaları, `predict*.py`, `features.py`,
`models/INDEX.json` aynen; INDEX sha256 `7e636e8b…`). Yorumlar `docs/SPEC_DEVIATIONS.md` bölüm L (L1–L12). **Gerçek veriyle kasa
skoru üretilmedi; `scores/scores_oot.json` ve `docs/SCORES_OOT.md` değişmedi.** Bu raporda hiçbir kasa kodu yoktur.

## 0. Kısa sonuç

- **Model başına kohort kapısı** kodda (SPEC_HAZARD_V1 §7.3): indirme kapısı (`outcomes_oot.s2_gate_problems` / `download_gate`;
  `open_vault` de çağırır) ve skor kapısı (`scoring.cohort_gate_ok(ctx, ingest, model_id)`; ata **ve** kanıt sırası) aynı kayıt
  seçimini (`freeze.oot_primary_of`: modeli içeren en erken etkin kayıt) kullanır. Sentetik depoda: bir üyenin ikinci kaydı eksikken
  kırmızı, kanıt sonrayken kırmızı, hepsi tamamken yeşil.
- **Kasa skorlama kodu**: `scoring --oot` kasa açılınca `oot_pre_h99_sealed` (INDEX'in 27 modeli) ve `oot_pre_h99_all` (yalnız açık
  kümede OOT_BLIND olan modeller; yeni 8 model formülle dışarıda) yazar. Birincil hücreler v1 §5.2 (RPS − `base_km_expanding`), (C)
  §5.2 (D10 Brier − `base_rate`); ilan edilmiş ikinciller "ikincil" etiketli. Sentetik kasa senaryosunda yeni modellerin kasa satırları
  OOT_BLIND; açık küme satırları formülle OOT_RETRO. Gerçek depoda bellekte yeniden hesap: yeni 8 modelin her birinde
  `n_oot_retro = 71`; 19 eski modelin açık küme blokları commit'li `scores_oot.json` ile aynı; kasa anahtarı üretilmedi (kasa kapalı).
- **135 ek kayıt** (R1): her biri tam 8 model (4 v1 + 4 (C)), girdiler ve `model_inputs` ilk kayıtla bayt-eşit (+ `tufe_index`,
  `tufe_refusal`, `alloc_regime`), sonuç alanı yok, kasa alanı (`vault`) yok; 1 080 hücre: 1 045 tahmin, 34 ret, 1 rejimle
  uygulanamaz; bütün hücreler `model_inputs`'tan yeniden hesapla bit-eşit. İlk 135 kayıt bayt-eşit.
- **Skorlar 27 modelle** (S): 19 eski kartta yalnız `n_variants_same_data` 20 → 23 ve `inputs.models_index_sha256` değişti; 8 yeni
  kart, 56 yeni RETRO çifti (7 canlı arz × 8 model), sekiz `backtest.near_era` bloğu (EK3 §5.5 şeması aynen), dört (C) kartında
  `n_exploration_family = 2054`. J16/J30/K10/K19 istisnaları koşullarıyla kendiliğinden düştü.
- **Uygulama**: gerçek skor dosyasının içeriğini sayan dört test (Rust 1, vitest 3) önceden onaylı asgari yeniden pinle güncellendi
  (APPPIN_S); Rust mantığı değişmedi, yeni skor dosyası ayrıştırılıyor ve bütünlük denetiminden geçiyor (cargo 94/94). **Açık kalan tek
  kırmızı** vitest `stage5.test.ts` A5-4: yeni `fall` türünün `KIND_TEXT`'te Türkçe karşılığı yok (pin değil, uygulama metni; EK3 §9'da
  önceden tanımlı, P4 işi). Görev kuralı gereği `app/`'e dokunulmadı; test.sh bu testte kırmızı (§6, §10).
- **Hijyen olayı (düzeltildi, commit'ten önce):** ilk R1 yazımı ek kayıtlara ilk kayıttan `vault` alanını kopyalamıştı; 135 dosya
  commit'lenmeden silindi, kod C2'de düzeltildi, kayıtlar yeniden yazıldı (§8).

## 1. Commit'ler

| Sıra | Commit | Üst | İçerik |
|---|---|---|---|
| C | `4c184c4402588a34011d9ca68cb45c5c18e3475a` | `696a04d` | `borsai/` (freeze, outcomes_oot, registry, report, report_faz7, report_faz7c, scoring), testler (yeni `tests/test_faz7_oot.py`; 7 dosyada uyarlama), SPEC_DEVIATIONS L, `docs/faz7_oot/ekler/` (denetim ve fark betikleri, test sayıları), görev dosyası — 19 dosya, +1754 / −143 |
| C2 | `f0588ef2434ccfec86353a3655f4c60118a96fef` | `4c184c4` | ek kaydın `vault` alanını ve kohort satırının `vault` sütununu yazmaması (hijyen), denetim + testler, SPEC_DEVIATIONS L3 eki — 4 dosya |
| R1 | `28aaa3bd5ddae7ddde52e207558ddc984c9aedf6` | `f0588ef` | yalnız `registry/oot/records/<T>/…json` 135 yeni dosya (+83 284 satır); başka yol yok |
| S | `cd222225de0d7dc34843a9e867d9ccf0a5101abb` | `28aaa3b` | `scores/scores.json`, `scores/scores_post_d1.json`, `docs/SCORES.md`, `docs/MODELS.md` |
| APPPIN_S | `1246b15a12a4965f3345a2b73070e7eec443793f` | `cd22222` | `app/src-tauri/tests/stage4.rs` (gerçek skor dosyasının model sayısı 19 → 27) ve `app/tests/accuracy.test.ts` (27 blok, 11 RETRO grubu, gizlemeden sonra 26 blok); yalnız sayı pinleri |
| R | bu raporu ekleyen commit | `1246b15` | `docs/faz7_oot/RAPOR.md`, `docs/faz7_oot/ekler/` (R1 denetimi, skor farkı, test sayıları) |

C'nin görev metnindeki mesajı aynen; C2 ve APPPIN_S görev metninde yoktu (§10).

## 2. Kod ve testleri (C, C2)

### 2.1 Model başına kapı (SPEC_HAZARD_V1 §7.3; L1)

- **Kayıt seçimi (tek tanım):** `freeze.oot_primary_of(recs, m)` / `oot_primary_record(T, m)` = (model, üye) için modeli içeren en
  erken etkin kayıt. Eski 19 model için S2 kaydı (I12 ile aynı), yeni 8 model için ek kayıt.
- **İndirme kapısı:** INDEX'in her modeli × her MEMBER için birincil kayıt var, commit'li, değişmemiş, push kanıtlı; değilse
  `GateError` ve hiçbir zip indirilmez. `open_vault` artık indirmeden önce `download_gate`'i çağırır.
- **Skor kapısı:** her MEMBER için modeli içeren birincil kayıt ingest commit'inin atası ve kaydın push kanıtı ingest kanıtından önce
  (D6-5 ve §7.3'ün ikinci terimi; Faz 6 kodu yalnız ata terimine bakıyordu). `class_oot` model başına kapıyı çağırır; POST_D1 modeli
  için taban kaydın modeli (`ceiling_hazard_v0`). Gerçek açık küme için sonuç değişmez (S2 kanıtı 2026-09-24T22:39:24Z < S5 kanıtı
  2026-09-25T13:45:54Z; 19 eski modelin blokları bellekte yeniden hesapta aynı).

### 2.2 `freeze --oot <kohort> --only-missing-models` (L3)

Üye başına yalnız etkin kayıtlarında bulunmayan INDEX modelleri; üretici ilk kayıtla aynı (`build_oot_record`). Ek alanlar
`record_scope = ONLY_MISSING_MODELS`, `delta_of` (ilk kaydın dosya adı), `delta_of_sha256`; `models_index.sha256` yeni INDEX,
`model_ids` INDEX'in tamamı; `comparators` boş (kural değerleri ilk kayıtta). `oot_delta_problems` girdileri ilk kayıtla karşılaştırır
(bayt-eşit değilse hiçbir kayıt yazılmaz); ek kayıt `vault` taşımaz (C2). Tam üyede kayıt yazılmaz (yeniden koşu güvenli); etkin kaydı
olmayan üye `NO_BASE_RECORD`. CLI yalnız sayı basar. `registry.MARGIN_MODELS` += `ceiling_hazard_v1_pooled@INF` (L4: "`@INF`
kuralları" lafzı).

### 2.3 Kasa skorlama kodu (L2, L5–L7)

- Satırlar (model, üye) birincil kaydından; karşılaştırılanlar kendi birincil kayıtlarından (v1 satırında `ceiling_hazard_v0` ve
  `base_km_expanding` S2 kaydından, merdiven karşılaştırılanları ek kayıttan).
- Kaydı olup modeli içeren kaydı olmayan üye: model sonuçtan sonra dondurulduysa OOT_RETRO bilgi satırı (kayıt kimliği yok), değilse
  SKIPPED (`NO_RECORD_FOR_MODEL`).
- `oot_pre_h99_sealed` / `oot_pre_h99_all` yalnız kasa açılınca (bir SEALED üyenin sonuç dosyası repoda); açılmadan hiçbir kasa satırı
  ya da kodu çıktıda yok. `all`'a giriş formülle (`all_eligible`: açık kümede ≥ 1 OOT_BLIND ve 0 OOT_RETRO); dışarıda kalanlar
  `excluded_models`'ta. `docs/SCORES_OOT.md` §8 (kasa) ve §9 (toplam) yalnız anahtarlar varken.
- Hücre tanımları: `FAZ7_*`/`FAZ7C_*` sözlükleri (pinli `PRIMARY_CELLS`/`OOT_PRIMARY_CELLS` aynen), karşılaştırılanlar
  `NEW_MODEL_COMPARATORS`; (C) kasa bloklarında kalibrasyon bilgi satırı; `fall` türünün canlı yolları D1 varsaymaz (L8).

### 2.4 `scores.json` ekleri (L9, L10)

`models[].backtest.near_era` (EK3 §5.5, 12 alan aynen; yalnız dondurulmuş Faz 7/7C kimliklerinde) ve dört (C) kartında
`n_exploration_family` + `exploration_family_source {path, sha256, kind}`. SCORES.md §5.1–§5.2 bunları yazar; MODELS.md Faz 7/7C kart
tablolarındaki sayaç sütunları aynı sayıyı `scores/scores.json`'un kartından okur (skorlar yeniden üretilmeden belge değişmez).

### 2.5 Testler

Yeni `tests/test_faz7_oot.py` (19 test; sentetik zaman çizelgesi: 19 model → S1 → S2 → açık küme sonuçları → 8 model → ek kayıtlar →
kasa açılışı; 12 açık + 15 kasa üyesi, kodlar SYN*/SYK*):

| Test | Ne gösterir |
|---|---|
| `test_delta_records_hold_only_missing_models_and_byte_equal_inputs` | ek kayıt tam 8 model; bağlam ve girdiler bayt-eşit; yeni anahtarlar yalnız üçü; `vault` yok; f3 boş, ek satış boş ve marj %20 üyesinde model başına "ret + neden" / NA |
| `test_delta_writer_is_idempotent_and_all_or_nothing` | commit'siz ve commit'li yeniden koşu yazmaz; ilk kayıttan sonra değişen girdi → DUR, hiçbir dosya; kirli ağaç → ön koşul |
| `test_delta_problems_detects_every_changed_block` | her bayt-eşitlik bloğu ve `vault` denetimi |
| `test_delta_cli_prints_numbers_only`, `test_delta_skips_member_without_first_record` | CLI yalnız sayı; ilk kaydı olmayan üye |
| `test_download_gate_is_per_model_and_blocks_downloads` | ek kayıtlar yokken kırmızı; **bir kasa üyesinin ikinci kaydı eksikken kırmızı** (yalnız o üye); `open_vault` hiçbir zip indirmez; commit'siz / kanıtsız kırmızı; hepsi tamam yeşil |
| `test_scoring_gate_red_when_a_second_record_is_missing` | skor kapısı yeni 8 modelde kırmızı, eski modelde yeşil |
| `test_scoring_gate_red_when_second_record_proof_is_not_before_ingest` | **kanıt kasa kanıtıyla eşit ya da sonra → kırmızı; önce → yeşil (OOT_BLIND)** |
| `test_open_set_rows_of_new_models_are_oot_retro_by_formula` | açık küme satırları ek kayıtlardan önce ve sonra OOT_RETRO (`n_oot_retro` = açık küme); eski modellerin açık tablosu değişmez; kasa kapalıyken anahtar yok |
| `test_sealed_rows_are_blind_with_earliest_record_rule` | kasa satırları OOT_BLIND; kayıt = ek kayıt, karşılaştırılan kendi birincil kaydından; marj üyesinde @INF NA |
| `test_sealed_primary_and_declared_secondary_cells` | birincil hücreler (n ≥ 10, ≥ 6 blok, aralık var) ve "ikincil" etiketleri §5.2 listesiyle aynı; (C) kalibrasyon satırı |
| `test_all_key_never_merges_new_models` | **`oot_pre_h99_all` yeni 8 modeli birleştirmez**; eski model = açık + kasa |
| `test_vault_doc_sections_without_member_codes`, `test_committed_oot_doc_unchanged_by_new_renderer` | §8–§9 bölümleri, kod yok; commit'li belge aynen |
| `test_new_model_comparators_and_labels_follow_spec`, `test_fall_rows_render_and_descriptive_without_d1` | hücre tanımları ve etiketler; (C) canlı satırı D1 varsaymaz |
| `test_near_era_blocks_equal_golden_ledgers_and_log` | sekiz blok altın ledger'lardan, günlük satırlarıyla float eşit |
| `test_family_exploration_counter_is_log_exploration_count` | 2 054 = günlük = kaynak sha |
| `test_real_second_records_hold_the_eight_models_with_byte_equal_inputs` | gerçek depoda (commit'li ek kayıtlar ya da C durumunda bellekte kuru koşu) 135 × 8, girdiler bayt-eşit, sonuç ve `vault` alanı yok (yalnız sayı) |

Uyarlanan testler (L11, L12): `test_faz6_oot.py` (iki kapı senaryosuna kanıt/ayrı commit eklendi; iddia aynen), `test_outcome_guard.py`
(G2 ek kaydı tanır; G5′ model başına ve sonuç commit'indeki INDEX'le; iletiler kod taşımaz), `test_scoring.py` (iki test),
`test_faz4_ceiling_path.py`, `test_faz5_live.py`, `test_faz7c_backtest.py` (yeniden üretimden önce ve sonra geçer).

## 3. 135 ek kayıt (R1) — sayılar

Komut (temiz ağaç, HEAD `f0588ef`): `.venv/bin/python -m borsai.freeze --oot registry/oot/cohort_pre_h99.csv --only-missing-models` →
`{"written": 135, "complete": 0, "skipped": 0}`; `cohort_file_sha256 = 7d05b334…60a7`. Denetim `docs/faz7_oot/ekler/r1_denetim.txt`
(betik `r1_denetim.py`; yalnız sayı).

- Üye 135 (açık 71, kasa 64); her üyede 2 etkin kayıt; ek kayıt 135; her denetim 135/135: 8 model doğru sırada, girdiler bayt-eşit,
  `delta_of` ilk kayıt, ilk kayıt 19 model, INDEX sha güncel, sonuç alanı yok, `record_stage = OOT_PRE_LISTING`, karşılaştırılan boş,
  TÜFE ayı T − 2 (ret yok), `alloc_regime` = kohort etiketi; `code.git_head = f0588ef`, `borsai_dirty = false`.
- Bit-eşitlik: 1 080/1 080 hücre kaydın `model_inputs`'u ile doğrudan tahmin çağrısına kanonik JSON olarak eşit.
- `vault` anahtarı ya da kasa değeri metni taşıyan ek kayıt: 0. İzlenen 135 ilk kayıt bayt-eşit (`git diff` boş).

| Model | tahmin / ret / rejimle uygulanamaz (135) | ret: açık küme | ret: kasa | ret kodları (açık; kasa) |
|---|---|---|---|---|
| `ceiling_hazard_v1_clip` | 130 / 5 / 0 | 3 | 2 | F3_MISSING 3; F3_MISSING 2 |
| `ceiling_hazard_v1_real` | 130 / 5 / 0 | 3 | 2 | F3_MISSING 3; F3_MISSING 2 |
| `ceiling_hazard_v1_pooled` | 130 / 5 / 0 | 3 | 2 | F3_MISSING 3; F3_MISSING 2 |
| `ceiling_hazard_v1_pooled@INF` | 134 / 0 / 1 | 0 | 0 | — (NA: MARGIN_NOT_10PCT 1, toplam) |
| `fall_d10_v0_h99` | 127 / 8 / 0 | 4 | 4 | F3_MISSING 3, ADDITIONAL_SALE_MISSING 1; F3_MISSING 2, ADDITIONAL_SALE_MISSING 2 |
| `fall_d10_v0_pooled` | 127 / 8 / 0 | 4 | 4 | aynı |
| `fall_d10_v0_addsale` | 132 / 3 / 0 | 1 | 2 | ADDITIONAL_SALE_MISSING 1; 2 |
| `fall_d10_v0_pooled@ZERO` | 135 / 0 / 0 | 0 | 0 | — |
| **Toplam** | **1 045 / 34 / 1** (1 080) | | | |

Sayılar önceden yazılı kapsama sayımlarıyla tutarlı (f3 boş 5 = açık 3 + kasa 2; ek satış boş 3 = açık 1 + kasa 2, KARARLAR_C C4).
Rejimle uygulanamaz hücrenin açık/kasa ayrımı bilerek basılmadı (§8).

## 4. Skorların yeniden üretimi (S) — fark

`.venv/bin/python -m borsai.scoring` (27 model) ve `.venv/bin/python -m borsai.report`. Fark `docs/faz7_oot/ekler/skor_farki.txt`
(betik `skor_farki.py`, R1'e karşı):

- `scores.json`: 19 eski modelde değişen tek yol `card/n_variants_same_data` (20 → 23: H99 sürümünde v1_clip, v1_real ve
  fall_d10_v0_h99 backtest varyantları). Üst düzeyde yalnız `code`, `generated_at_utc`, `inputs.models_index_sha256` (`1bc33791…` →
  `7e636e8b…`) ve yeni `faz7c_near_era` bloğu. `retro_info` 21 → 77 (eski 21 çift aynen; yeni 56 = 7 canlı arz × 8 yeni model,
  formülle RETRO). Eski kartların hücreleri, satırları ve sınıfları aynen.
- 8 yeni kart: v1 adayları `primary_cell` RPS − `base_km_expanding` (SPEC_HAZARD_V1 §5.3), (C) adayları D10 Brier − `base_rate`
  (SPEC_C_V0 §5.3); kural satırlarında yok; `live.rows` boş (7 arz RETRO); `backtest.cells` boş, `backtest.near_era` dolu; varyant
  sayacı H99 sürümündeki kartlarda 23, v2 sürümündekilerde 2 059; (C) kartlarında `n_exploration_family` 2 054.
- `scores_post_d1.json`: yalnız `code`, `generated_at_utc`, `inputs.models_index_sha256` ve kartın `n_variants_same_data` (20 → 23).
- `SCORES.md`: sınıf tablosunda 8 satır, RETRO satırı, §5'e (C) paneli satırı + §5.1 yakın dönem blokları + §5.2 (C) kart sayaçları, §6
  koşullu bloklarında v1 modelleri (satırsız). `MODELS.md`: yalnız Faz 7 ve 7C kart tabloları (sayaç sütunları) ve 7C kartının altına
  bir açıklama satırı; başka satır değişmedi.
- `scores/scores_oot.json` ve `docs/SCORES_OOT.md` değişmedi.

## 5. Yakın dönem blokları (`models[].backtest.near_era`; EK3 §5.5)

Hepsi `schema_version = borsai.near_era/1`, `scale = backtest_near_era`, `subset = first_trading_date >= 2024-01-01`; değerler altın
ledger'lardan, günlükteki satırlarla float eşit (test).

| Model | Karşılaştırılan | Metrik | n (ay) | fark | %95 aralık | tolerans | Etiket |
|---|---|---|---|---|---|---|---|
| `ceiling_hazard_v1_clip` | `ceiling_hazard_v0` | RPS | 78 (22) | −0.0011 | [−0.0066, +0.0049] | 0.010 | tolerans içinde |
| `ceiling_hazard_v1_real` | `ceiling_hazard_v0` | RPS | 78 (22) | +0.0104 | [+0.0028, +0.0183] | 0.010 | bozuyor |
| `ceiling_hazard_v1_pooled` | `ceiling_hazard_v0` | RPS | 78 (22) | +0.0289 | [+0.0089, +0.0518] | 0.010 | bozuyor |
| `ceiling_hazard_v1_pooled@INF` | `ceiling_hazard_v0` | RPS | 78 (22) | +0.0547 | [+0.0287, +0.0806] | 0.010 | bozuyor (kural satırı) |
| `fall_d10_v0_h99` | `base_rate` | D10 Brier | 75 (22) | −0.0434 | [−0.0773, −0.0048] | 0.008 | tolerans içinde |
| `fall_d10_v0_pooled` | `fall_d10_v0_h99` | D10 Brier | 75 (22) | −0.0058 | [−0.0340, +0.0219] | 0.008 | belirsiz |
| `fall_d10_v0_addsale` | `base_rate` | D10 Brier | 76 (22) | −0.0065 | [−0.0301, +0.0161] | 0.008 | belirsiz |
| `fall_d10_v0_pooled@ZERO` | `base_rate` | D10 Brier | 75 (22) | −0.0043 | [−0.0162, +0.0080] | 0.008 | tolerans içinde (kural satırı) |

(C)'de birincil hücreyi yalnız `fall_d10_v0_pooled` taşır; h99, addsale ve @ZERO satırları §5.5 k3'ün "yakın dönem − `base_rate`"
hücresidir, etiket aynı kuralla (alt > 0 → "bozuyor" = k3'ün "tamamen 0'ın üstünde"). k3 okuması: v1_real ve v1_pooled uygulama
birincili olamaz (bilinen; MODELS.md); (C) adaylarının hiçbiri k3'e takılmaz.

## 6. Uygulama etkisi

- S'den sonra `bash app/scripts/test.sh` kırmızıydı. Pin olanlar (skor dosyasının içeriğini sayan testler; önceden onaylı, APPPIN_S):
  `app/src-tauri/tests/stage4.rs::real_scores_file_passes_integrity` (`models.len()` 19 → 27; `--no-fail-fast` ile öteki bütün cargo
  testleri yeşildi) ve `app/tests/accuracy.test.ts`'in "gerçek scores/scores.json ile render" bloğundaki üç test (model bloğu 19 → 27,
  RETRO grubu 3 → 11 — üç Faz 4 + sekiz yeni model, her biri 7 çift —, bir model gizlenince 18 → 26). Rust mantığı, UI mantığı,
  fikstürler ve altın vektörler değişmedi.
- **Açık kalan (pin değil): `app/tests/stage5.test.ts` A5-4** — Doğruluk panelindeki her model bloğu özetinin `model_id · KIND_TEXT[kind]
  · canlı n` olmasını ister; `app/src/i18n/tr.ts` `KIND_TEXT`'te `fall` yok, render ham `fall` yazar (`KIND_TEXT[m.kind] ?? m.kind`).
  Metin EK3 §9'da önceden tanımlı: `fall: "düşen arz (D5/D10 arz altı kapanış olasılığı)"` (P4). Görev kuralı `app/`'te yalnız pin
  satırlarına izin verdiği ve bu bir uygulama metni/mantık açığı olduğu için dokunulmadı; test.sh bu testte kırmızıdır (vitest 221/222).
  Seçenekler §10'da.
- Aynı `stage4` testinin öteki iddiaları yeni dosyada geçti: bütünlük denetimi temiz (hiçbir canlı hücre n < 10 kuralını çiğnemiyor;
  yeni kartlarda canlı ve koşullu hücre yok), `ceiling_path_v0` birincil hücresi aynen.
- Uygulama `scores.json`'u `serde_json::Value` olarak okur; yeni alanlar (`backtest.near_era`, `n_exploration_family`,
  `exploration_family_source`, üst düzey `faz7c_near_era`) ayrıştırmayı bozmaz. EK3 §12 Ö1 (yakın dönem bloğu) ve Ö2 (27 modelli
  `scores.json`) artık karşılanıyor. Not: EK3 §8.4 k3 h99/addsale'in "yakın dönem − `base_rate`" hücresini `backtest.cells`'ten okumayı
  öngörüyordu; orkestratör kararıyla bu hücre `backtest.near_era` bloğundadır (`comparator: "base_rate"`), EK3 P4 okuyucusu buna uymalı.
- `gen_golden --check` her aşamada 25/0 (pinli tahmin kaynakları değişmedi); parity 4 passed; golden_unchanged YEŞİL. Gömülü skor
  anlık görüntüsü (`score_hints.json`) yalnız varlık denetimli.

## 7. Test sayıları (ayrıntı `docs/faz7_oot/ekler/test_runs.txt`)

| Aşama | pytest | test.sh | gen_golden --check |
|---|---|---|---|
| Taban (`696a04d`) | 829 passed, 651.1 s | yeşil (cargo 94, npm 222, parity 4, U46) | 25/0 |
| C öncesi, ilk koşu | 847 passed, 1 failed, 836.5 s (`test_backtest_primary_cells_and_verdicts`; uyarlandı) | — | 25/0 |
| Geçici klon provası (C + R1 + S commit'li) | 846 passed, 2 failed, 933.0 s (iki test; uyarlandı, klonda 11 passed) | — | — |
| C öncesi, son koşu (`4c184c4`'ün içeriği) | 848 passed, 751.1 s | — | 25/0 |
| C2 öncesi | 848 passed, 759.8 s | — | — |
| R1 commit'lenmeden (5 temizlik bekçisi dışarıda) | 843 passed, 5 deselected, 751.7 s; commit'ten sonra 5 passed | — | — |
| S commit'lenmeden (2 `scores/` bekçisi dışarıda) | 846 passed, 2 deselected, 758.9 s; commit'ten sonra 2 passed | exit 101: cargo 93 / 1 kırmızı (pin) | 25/0 |
| Son (`1246b15`, deselect yok) | **848 passed, 698.4 s** | exit 1: cargo 94/0, vitest 221/222 (A5-4, §6), parity 4, U46 yeşil | 25/0 |

848 = 829 + 19 (`tests/test_faz7_oot.py`). Ayrıntı `docs/faz7_oot/ekler/test_runs.txt`.

## 8. Hijyen ve maruziyet

- Kasa üyeleri için yalnız listeleme öncesi girdiler okundu (`registry/oot/inputs/<T>.json`, kohort satırı, ilk kayıtlar); sonuç,
  karantina, ağ yok. `EXPOSURE.md` dosyaları ve Codex `exposure_log`'ları okunmadı. Kohort dosyası yalnız betikle okundu; satırı basılmadı.
- Yeni metinlerde (rapor, ekler, SPEC_DEVIATIONS L, testler) kohort kodu, kasa kodu ve bülten adı kalıbı yok (betikle sayıldı: 0);
  testlerdeki kodlar sentetik. Yeniden üretilen `scores.json` ve `SCORES.md`'de bir kasa koduyla aynı dizge tek satırda geçer; bu
  eşleşme yeniden üretimden önce de aynı satırda vardı (SPEC_DEVIATIONS J18/J29 B9'da beyan edilen, kohort penceresi dışı satır), yeni
  eşleşme yok; `scores_post_d1.json` ve `MODELS.md`'de 0. Ek kayıtlar kaçınılmaz olarak kendi üyelerinin kodunu taşır (dosya yolu ve `ticker`), ama **hangi kodun kasada olduğunu
  taşımaz** (C2).
- **Olay 1 (düzeltildi):** commit C'nin yazıcısı ek kayda ilk kaydın `vault` alanını ve kohort satırının `vault` sütununu kopyalıyordu
  (ilk S2 kayıtları ve kohort dosyası bu alanı zaten taşır; ek kayıtta yeni bilgi değildir ama görev kuralı "hiçbir dosyaya yazılmaz"
  der). İlk yazımdan sonra, commit'ten önce fark edildi; 135 izlenmeyen dosya silindi (hiçbiri commit'lenmedi ya da push edilmedi),
  düzeltme C2, kayıtlar temiz ağaçta yeniden yazıldı. Denetim: `vault` taşıyan ek kayıt 0.
- **Olay 2 (beyan):** geçici klondaki ilk denetim betiği ret/NA sayılarını açık/kasa ayrımıyla bastı; rejimle uygulanamaz (MARGIN) hücre
  kohortta tek üyeye aittir ve o üyenin adı Faz 6 belgelerinde geçer, bu yüzden ayrımlı sayı o üyenin kasa durumunu çıkarsanabilir kıldı.
  Bu çıkarım hiçbir dosyaya yazılmadı; betik düzeltildi (NA yalnız toplam), bu rapor da NA'yı yalnız toplam verir. Hiçbir sonuç ya da
  kasa verisi görülmedi; oturumun hiçbir kararı bu bilgiye dayanmaz.

## 9. Kasa açılışı görevi için ön koşullar

1. **R1'in push kanıtı (proje sahibi):**
   ```
   git push origin main
   .venv/bin/python -m borsai.push_proof 28aaa3b
   git add registry/push_proofs
   git commit -m "BORSAI_PUSH_PROOFS: Faz 7 eski kohort ek kayıtları (28aaa3b)" -- registry/push_proofs
   git push origin main
   ```
2. **Kapının gerçek depoda bu kanıtla yeşile döndüğünü doğrulayan komut** (yalnız sayı basar; bugün 135, hepsi "push kanıtı yok"):
   ```
   .venv/bin/python -c "from borsai import outcomes_oot as oo; p = oo.s2_gate_problems(); print(len(p))"
   ```
   Beklenen `0`. Ardından `.venv/bin/python -c "from borsai import outcomes_oot as oo; oo.download_gate(); print('kapı açık')"`.
3. **SPEC_HAZARD_V1 §7.1-5 ve SPEC_C_V0 §7.1-5 (tek seferde, ayrı görev):**
   - Ön koşullar (§7.4 / §7.3): v1 kayıtları ve (C) kayıtları push kanıtlı (madde 1; R1 ikisini birlikte taşır); (C) şartnamesi push
     kanıtlı (`4fe4e51`, kanıt repoda); `oot_pre_h99_sealed`/`_all` kodu sentetik testte yeşil (C, C2); model başına kapı yeşil (madde 2).
   - `outcomes_oot.open_vault(feature_spec="docs/specs_faz7_c/SPEC_C_V0.md")`: model başına kapı, MANIFEST_OOT'taki her zip'in pinli
     sha256 ile yeniden indirilmesi; dönen SEALED kümesiyle `resolve_member(..., unsealed=…)` üzerinden SEALED satırlarının ayıklanması
     (`data/outcomes_oot/<T>.csv`, ham kopyalar, MANIFEST_OOT; D6-4). Bu ayıklama sürücüsü henüz yok (`extract_open_members` yalnız açık
     küme); kasa görevi `extract_open_members` kalıbıyla yazmalı ve kasa kodlarını hiçbir çıktıya basmamalı. Tek commit; push; kanıt.
   - `.venv/bin/python -m borsai.scoring --oot`: `oot_pre_h99_sealed` (27 model) ve `oot_pre_h99_all` (19 eski model; 8 yeni model
     `excluded_models`'ta) kendiliğinden yazılır; `docs/SCORES_OOT.md` §8–§9. Kasa ingest commit'inin kanıtı R1'in kanıtından sonra
     olmalıdır (aksi halde yeni modellerin kasa satırları formülle OOT_RETRO).
   - Seçim kuralları: SPEC_HAZARD_V1 §5.5 (k1–k3; k3 yukarıdaki yakın dönem etiketleri) ve SPEC_C_V0 §5.5; MODELS.md ve uygulama
     (EK3 Ö4–Ö5) güncellenir. §6.4 (e) "beklentiden çok iyi" durumunda bağımsız yeniden hesap (Fable `recompute.py` kalıbı) zorunlu.
   - Not: yeniden üretilen `scores_oot.json`'da açık küme anahtarına 8 yeni modelin OOT_RETRO blokları (her biri 71 çift, 568 çift) ve
     `definitions`'a Faz 7/7C hücre tanımları girer; 19 eski modelin açık küme blokları bugünkü dosyayla aynıdır (bellekte ölçüldü).

## 10. Sapmalar ve kararlar (proje sahibinin gözden geçirmesi için)

Ayrıntı SPEC_DEVIATIONS L1–L12. Proje sahibine soru sorulmadı; aşağıdakiler şartname lafzıyla verilen yorum kararlarıdır:

1. **Kanıt sırası kapıda** (L1): skor kapısı ata terimine ek olarak kaydın push kanıtının ingest kanıtından önce olmasını ister (§7.3,
   D6-5 metni). İki Faz 6 testinin yapay senaryosu buna göre uyarlandı (L11); gerçek açık küme sonucu değişmedi.
2. **`ceiling_hazard_v1_pooled@INF` marj kuralında "`@INF` kuralı"** (L4): tek üyede NA; kural satırıdır, aday değildir.
3. **`fall_d10_v0_pooled@ZERO`'nun yakın dönem bloğu** (L9): görevin "dört (C)" bloğu için `base_rate` karşılaştırıcısıyla bilgi bloğu.
4. **MODELS.md kart sayaçları `scores.json`'dan** (L10): "aynı sayı" yapısal; sonuç olarak skorlar yeniden üretilince MODELS.md de
   yeniden üretilmelidir.
5. **Kasa anahtarları yalnız kasa açılınca** (L6) ve `all`'a giriş formülle.
6. **Ek commit'ler**: C2 (hijyen düzeltmesi, §8 olay 1) ve APPPIN_S (önceden onaylı kalıp). Push yok.
7. **Açık karar (proje sahibi / orkestratör): `KIND_TEXT['fall']`** (§6). Seçenekler: (a) EK3 §9'daki tek satırı
   `app/src/i18n/tr.ts`'e aynen eklemek (ayrı küçük commit; test aynen katı kalır, test.sh yeşile döner; öneri); (b) A5-4 beklentisini
   render gibi `KIND_TEXT[kind] ?? kind` yapmak (yalnız test; panel P4'e kadar ham `fall` yazar); (c) EK3 P4'e bırakmak (test.sh o
   zamana kadar bu testte kırmızı). Bu oturumda soru soruldu, cevap gelmeden devam istendi; görev kuralı gereği (a)/(b) yapılmadı.

## 11. Kabul kapısı

- **K1** ✓ Kapı ve kasa skorlama kodu sentetik testlerde doğru (`tests/test_faz7_oot.py`, 19 test); `oot_pre_h99_all` yeni modelleri
  birleştirmiyor (`test_all_key_never_merges_new_models`).
- **K2** ✓ 135 ek kayıt, her biri 8 model; girdiler ilk kayıtla bayt-eşit; sonuç alanı yok; kasa alanı yok; kasa kodu hiçbir yeni metinde
  yok (ek kayıtlar yalnız kendi üyelerinin kodunu taşır).
- **K3** ✓ 27 modelli skorlar üretildi; 19 eski modelde yalnız varyant sayacı ve INDEX sha değişti; near_era blokları altın ledger'lar ve
  günlükle eşit; aile keşif sayacı (C) kartlarında (2 054), MODELS.md ve SCORES.md aynı sayıyı yazar.
- **K4** kısmen: tam pytest yeşil (§7); `gen_golden --check` yeşil; `test.sh` cargo, parity ve golden_unchanged yeşil, **vitest'te 1 test
  kırmızı** (`KIND_TEXT['fall']`, §6, §10-7). Commit'ler yalnız izinli yollarda (C/C2: borsai, tests, SPEC_DEVIATIONS, docs/faz7_oot,
  görev dosyası; R1: yalnız registry/oot/records; S: dört skor/belge dosyası; APPPIN_S: iki app test dosyası; R: docs/faz7_oot); push yok.

## Ek (APPPIN_S2): `KIND_TEXT['fall']` ve son test sayıları

- Proje sahibi §10-7'de seçenek (a)'yı onayladı; metni kendisi verdi. `app/src/i18n/tr.ts` `KIND_TEXT`'e tek satır eklendi:
  `fall: "düşen arz (D10'da arz fiyatı altında kapanma olasılığı)"`. Başka hiçbir dosya ya da satır değişmedi (Rust, test ve render
  mantığı aynen). Metni EK3 P4 kesinleştirir. Doğruluk panelindeki (C) model bloklarının özeti artık ham `fall` yerine bu metni yazar.
- Son test sayıları (HEAD `02b91fd` + bu satır, commit'ten önce):
  - `bash app/scripts/test.sh`: **exit 0**, 32.1 s; cargo 94 passed / 0 failed, vitest 16 dosya / **222/222** passed (A5-4 dahil),
    parity 4 passed, golden_unchanged YEŞİL (U46).
  - `.venv/bin/python app/parity/gen_golden.py --check`: {"checked": 25, "different": []}.
  - `.venv/bin/pytest -q -p no:cacheprovider`: **848 passed** in 702.99 s (0:11:42).
- §0, §6 ve §11'deki "vitest'te 1 test kırmızı" ifadeleri bu ekten önceki durumu anlatır. Bu ekle **K4 tam karşılandı**: tam pytest,
  test.sh ve `gen_golden --check` yeşil; commit'ler yalnız izinli yollarda; push yok.

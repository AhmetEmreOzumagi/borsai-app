# Kopya kaynakları (PROVENANCE)

## Genel

- **Kaynak:** eski repo `~/Desktop/Halka_Arz_Modeli` (arşiv, salt okunur). Kopyalama anında HEAD `604e2187f8a1f4a452bf0434ad5d1454bbbf4d21`, yani adım 1'in commit'i. Kopya tarihi 2026-09-21.
- **Eski commit:** dosyaya en son dokunan commit (`git log -1 -- <yol>`).
- **Çalışma kopyası:** kopyalanan 87 dosyanın hepsinde eski repodaki çalışma kopyası HEAD blob'uyla bayt bayt aynıydı (`git show HEAD:<yol>` ile karşılaştırıldı).
- **sha256:** dosya baytlarının ham sha256'sı. Eski sha256 eski repodaki baytlara, yeni sha256 bu repodaki baytlara aittir.
- **Dönüşüm türleri:**
  - "yok": bayt bayt aynı, eski ve yeni sha256 eşit.
  - "CRLF→LF": yalnız satır sonları değişti. Yeni dosyada her `\n`'i `\r\n` yapınca eski baytlar birebir geri gelir. Kaynaklarda tek başına CR yoktu (denetlendi). UTF-8 BOM'lar korundu.
  - "türetilmiş": yalnız XU100 dosyası (§1).
- **Sayılar:**
  - 87 kopya: data/raw 11, legacy 21 + 13 ek yardımcı modül, registry/legacy_frozen 29, tests/reference 13.
  - Dönüşüme göre: 77 bayt bayt aynı, 9 CRLF→LF, 1 türetilmiş.
  - 16 dosya kopyalanmadı ("Faz 2'de alınacak", §5).
- **Kopyalama betiği** (repo dışında çalıştı):
  - Hedefte var olan dosyanın üzerine yazmayı reddetti.
  - Eski repoya hiçbir şey yazmadı. Kopyadan sonra eski repoda `git status --porcelain` boş.

## 1. data/raw/

Kural: 2026-08-19 sonrası seans verisi taşıyan satır içeren dosya kopyalanmadı.

İstisna, pinli XU100 JSON'u. Dosyanın 9684 kaydından ikisi 2026-08-19 sonrasına aitti (2026-08-20, 2026-08-21). f6_market20 Faz 1'de bu veriye ihtiyaç duyacağı için dosya olduğu gibi kopyalanmadı. Onun yerine bu iki kaydın çıkarıldığı bir türev konuldu: 9682 kayıt, son `hisTs` = 2026-08-19. Bu, proje sahibinin onayına açık bir karardır. İstenmezse `git rm` ile kaldırılabilir; o durumda f6 verisi Faz 2'de alınır.

"En son tarih" sütunu, dosyadaki bütün tarih biçimleri (YYYY-MM-DD, YYYYMMDD, GG.AA.YYYY) tarandıktan sonra bulunan en büyük değerdir; hangi sütunda geçtiği parantez içinde yazılı.

| # | Eski yol | Eski sha256 | Eski commit | Yeni yol | Yeni sha256 | Dönüşüm | En son tarih |
|---|---|---|---|---|---|---|---|
| 1 | `artifacts/ipo_master/historical99/HISTORICAL99_FROZEN_COHORT_V1/canonical/HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv` | `573f4c77c5ac9f9d3aaf7715a5b054ff412991120c73f2c03065521c7fc9173b` | `d0a2435b0782fe82af427e58590dc2d9d4719c82` | `data/raw/HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv` | `6011917a549a4ac638ef4a70948ea8904be1244f9b894b10b370ae8a691b6d0a` | CRLF→LF (100 satır sonu); başka bayt değişmedi | 2026-08-06 (first_trading_date) |
| 2 | `artifacts/ipo_master/historical99/HISTORICAL99_FROZEN_COHORT_V1/canonical/HISTORICAL99_FROZEN_COHORT_V1_canonical_feature_readiness.csv` | `630044a5d576113c8668b41b91acd0ad1e3d1d195660463d1e57932e203b7623` | `d0a2435b0782fe82af427e58590dc2d9d4719c82` | `data/raw/HISTORICAL99_FROZEN_COHORT_V1_canonical_feature_readiness.csv` | `73fbaefe6539d7f3ada1da015d5007e68d98baa686783b407516d737f1bd1d17` | CRLF→LF (100 satır sonu); başka bayt değişmedi | 2026-08-06 (first_trading_date) |
| 3 | `artifacts/ipo_master/historical99/HISTORICAL99_FROZEN_COHORT_V1/canonical/HISTORICAL99_FROZEN_COHORT_V1_canonical_provenance.csv` | `c54aee2c392a0113e6ad66df28baa441f336fabab5b65b9a127a49197f5e3123` | `d0a2435b0782fe82af427e58590dc2d9d4719c82` | `data/raw/HISTORICAL99_FROZEN_COHORT_V1_canonical_provenance.csv` | `5d2f55466af25325d24e062a1fdd4bf05e03a46ff0ba588584eb76dc6faeecc1` | CRLF→LF (100 satır sonu); başka bayt değişmedi | 2026-08-21 (source_evidence_path); yalnız kanıt dosyası adında (`…EXACT100_EVIDENCE_FINAL_20260821.txt`). Veri değeri olan en son tarih 2025-02-13 (notes) |
| 4 | `artifacts/ipo_master/historical99/HISTORICAL99_FROZEN_COHORT_V1/canonical/HISTORICAL99_FROZEN_COHORT_V1_canonical_membership.csv` | `b15c2e2c9e1a6ad9f702a469e6ba7c03eeef4828fd29afb59dbe780d8a2a1801` | `d0a2435b0782fe82af427e58590dc2d9d4719c82` | `data/raw/HISTORICAL99_FROZEN_COHORT_V1_canonical_membership.csv` | `ed3ad538751d394a2711264dbb5772e9fe4152fcc8c8ed17535a36442e7c6a8a` | CRLF→LF (100 satır sonu); başka bayt değişmedi | 2026-08-06 (first_trading_date, historical_anchor_date) |
| 5 | `artifacts/outcomes/historical99/HISTORICAL99_FROZEN_COHORT_V1/OFFICIAL_BIST_OUTCOME_V1/canonical/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_field_provenance.csv` | `4ebbd4d47c5b5baab0f05bb0d1ee546794feaa93eb06403c3a7bc6bc32f414de` | `d0a2435b0782fe82af427e58590dc2d9d4719c82` | `data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_field_provenance.csv` | `550cbff299386759f28ec9771d24e28cb6a42dc70e082650638f6768b3566706` | CRLF→LF (11881 satır sonu); başka bayt değişmedi | 2026-08-19 (local_path, target_session_date); seans verisinin son günü |
| 6 | `artifacts/outcomes/historical99/HISTORICAL99_FROZEN_COHORT_V1/OFFICIAL_BIST_OUTCOME_V1/canonical/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_d1_d3_d5_d10_targets.csv` | `64dce0bb3b2aff28f5dfd5f335da8f423a5cf0839430cac1df200bfed4417f9c` | `d0a2435b0782fe82af427e58590dc2d9d4719c82` | `data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_d1_d3_d5_d10_targets.csv` | `bdad71422d67424a29dfc9284013c91354bc36acad9ff9ed6aa06f641ca4c050` | CRLF→LF (397 satır sonu); başka bayt değişmedi | 2026-08-19 (target_session_date, thb_local_path); seans verisinin son günü |
| 7 | `artifacts/outcomes/historical99/HISTORICAL99_FROZEN_COHORT_V1/OFFICIAL_BIST_OUTCOME_V1/canonical/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv` | `aacf5990e764550c539f8cc37a5534d5315e272fa22b8f470ac8d63bc210caca` | `d0a2435b0782fe82af427e58590dc2d9d4719c82` | `data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv` | `eca620d3a5e8fed0b118bab556da5ce519257a4b2e14efcd22065f5bcdc93da9` | CRLF→LF (991 satır sonu); başka bayt değişmedi | 2026-08-19 (target_session_date, thb_local_path, thm_local_path); seans verisinin son günü |
| 8 | `artifacts/outcomes/historical99/HISTORICAL99_FROZEN_COHORT_V1/OFFICIAL_BIST_OUTCOME_V1/canonical/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_pay_session_calendar.csv` | `402a5ea6ed0565e666999111fceac40ee178f7049f2ef57391effa36bf7d9a2d` | `d0a2435b0782fe82af427e58590dc2d9d4719c82` | `data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_pay_session_calendar.csv` | `15d4d975db53a42006c1e57bab7b5f11eab52f281069cc90f0c38361770bf9cb` | CRLF→LF (1064 satır sonu); başka bayt değişmedi | 2026-08-19 (calendar_date) |
| 9 | `artifacts/data/prebookbuild_point_in_time_canonical/BORSAI_PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_20260825/PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv` | `5e52d4d23b4f196ef0fd44fb6d4f4edab0ea326241288b036952c30c5e24a613` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `data/raw/PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv` | `5e52d4d23b4f196ef0fd44fb6d4f4edab0ea326241288b036952c30c5e24a613` | yok (bayt bayt aynı) | 2026-08-25 (evidence_file); yalnız kanıt dosyası adında (`…_VERIFIED_20260825.txt`). Veri değeri olan en son tarih 2026-08-06 (canonical_first_trading_date) |
| 10 | `artifacts/modeling/v2_market_regime_preregistration_candidate/BORSAI_V2_MARKET20_PREREG_CANDIDATE_20260824_R4/v2_market20_official_pay_calendar_evidence_r4.csv` | `49b58029715881a7f1a304afb7e41fcff3d5c1c7a8896de3ed9bb555fb02d159` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `data/raw/v2_market20_official_pay_calendar_evidence_r4.csv` | `49b58029715881a7f1a304afb7e41fcff3d5c1c7a8896de3ed9bb555fb02d159` | yok (bayt bayt aynı) | 2026-08-19 (calendar_date) |
| 11 | `artifacts/modeling/historical99_market_sector_microstructure_stage_a/HISTORICAL99_MARKET_SECTOR_MICROSTRUCTURE_STAGE_A_V1/raw/official_bist_xu100_graphic_pinned.json` | `13db0171345a917d53ae99308e68694b54b56090df3b8612f6686444e99236b0` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `data/raw/official_bist_xu100_graphic_pinned_through_20260819.json` | `34859d7eefdb552a31f6476e2230a07a825ada3ee769a2a7646f12399c303fdf` | TÜRETİLMİŞ: hisTs = 2026-08-20 ve 2026-08-21 olan iki kayıt (dosyanın ilk iki kaydı) tek bir bayt aralığı olarak çıkarıldı; diğer her bayt aynı. Çıkarılan değerler bilerek hiçbir yere yazılmadı | 2026-08-19 (data[].hisTs) |

Notlar:
- **H99 membership:** 100'lük hedef evrenin 99 üyesini listeler. `known_membership_gap_count` = 1, `membership_gap_status` = `DEFERRED_RECONCILIATION`.
- **Oturum takvimi:**
  - Yarım günler `session_status` = `OPEN_HALF_DAY` olarak kayıtlı: 6 gün, 3'ü H99 seanslarında.
  - Tam kapanışlar `OFFICIAL_FULL_CLOSURE` olarak kayıtlı.
  - İşlem durdurma bilgisi takvimde değil, seans dosyasında (`bist_session_outcomes.security_trading_status`). 990 seansın hepsi `ACTIVE_NOT_SUSPENDED`.
- **f6_market20 takvimi:** Takvim B = `v2_market20_official_pay_calendar_evidence_r4.csv`: 910 resmi seans, 2023-01-02…2026-08-19. `v2_market20_repair_01_core.py` ise H99 oturum takvimini okur; wiring r7 Takvim B'ye bağlıdır (CHECKUP `detay/A2:248, 369`). İkisi de alındı.

## 2. legacy/

Eski repo yolları `legacy/` altında aynen korunur; örneğin `scripts/modeling/x.py` → `legacy/scripts/modeling/x.py`. Tüm dosyalar bayt bayt aynıdır.

Bu kod bu haliyle çalıştırılmak için değil, port için referans olarak durur. Arşivdeki `artifacts/…`, `config/…` yollarını ve hash pinlerini okur.

### 2a. İstenen modüller

| # | Eski yol | Eski sha256 | Eski commit | Yeni yol | Yeni sha256 | Dönüşüm |
|---|---|---|---|---|---|---|
| 1 | `scripts/modeling/candidate_models.py` | `f49df50989d345a900830f5f663303a6aa4d095fe819174fc1c0d9207cfb5565` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/scripts/modeling/candidate_models.py` | `f49df50989d345a900830f5f663303a6aa4d095fe819174fc1c0d9207cfb5565` | yok (bayt bayt aynı) |
| 2 | `scripts/modeling/preprocessing.py` | `777920e4ba0982b522d26e1cfdd079ca3bac3f5fed82be25e20c8af1005f8e44` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/scripts/modeling/preprocessing.py` | `777920e4ba0982b522d26e1cfdd079ca3bac3f5fed82be25e20c8af1005f8e44` | yok (bayt bayt aynı) |
| 3 | `scripts/modeling/logistic_policy.py` | `08527ede03f3cb95ff46c180cae126a0831f1fe102425374e5534f4259c7e1fd` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/scripts/modeling/logistic_policy.py` | `08527ede03f3cb95ff46c180cae126a0831f1fe102425374e5534f4259c7e1fd` | yok (bayt bayt aynı) |
| 4 | `scripts/modeling/metrics.py` | `809116038ac614c92105cf7b20556113f3401c46e07b8c5ac246b5cc9e5c83d6` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/scripts/modeling/metrics.py` | `809116038ac614c92105cf7b20556113f3401c46e07b8c5ac246b5cc9e5c83d6` | yok (bayt bayt aynı) |
| 5 | `scripts/modeling/baselines.py` | `045271871419c4eca2cf0f9f3082019eaa2bb33b06d86bac03d08999daf73ebc` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/scripts/modeling/baselines.py` | `045271871419c4eca2cf0f9f3082019eaa2bb33b06d86bac03d08999daf73ebc` | yok (bayt bayt aynı) |
| 6 | `scripts/modeling/fold_engine.py` | `d5fd48a893512b47f8b720ae6371cc261b66fb1aa950f68945ce32a2b9f097d9` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/scripts/modeling/fold_engine.py` | `d5fd48a893512b47f8b720ae6371cc261b66fb1aa950f68945ce32a2b9f097d9` | yok (bayt bayt aynı) |
| 7 | `scripts/modeling/target_extraction.py` | `252c480c165c7685f47fbe3dc5983b1410c8216d59369ba81301b02037f3690e` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/scripts/modeling/target_extraction.py` | `252c480c165c7685f47fbe3dc5983b1410c8216d59369ba81301b02037f3690e` | yok (bayt bayt aynı) |
| 8 | `scripts/modeling/feature_assembly.py` | `1f3fc2e845573719582601a22308ce8f1dc3b4f66d3a91c49fb02d71a73d1362` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/scripts/modeling/feature_assembly.py` | `1f3fc2e845573719582601a22308ce8f1dc3b4f66d3a91c49fb02d71a73d1362` | yok (bayt bayt aynı) |
| 9 | `scripts/modeling/common.py` | `a6f1d5a02f48745642803cf24151bb547e0d39812346b636eb4fbbcbc8c5ff6b` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/scripts/modeling/common.py` | `a6f1d5a02f48745642803cf24151bb547e0d39812346b636eb4fbbcbc8c5ff6b` | yok (bayt bayt aynı) |
| 10 | `scripts/modeling/compute_true_live_v1_5_prediction_contract.py` | `d940aeef87778710d31b44babb7a9e0f034ca5be133a98f7034e41aa01d1da30` | `10262e0640ff18847c6c1e92b0b95e950cf1933f` | `legacy/scripts/modeling/compute_true_live_v1_5_prediction_contract.py` | `d940aeef87778710d31b44babb7a9e0f034ca5be133a98f7034e41aa01d1da30` | yok (bayt bayt aynı) |
| 11 | `scripts/modeling/run_post_bookbuild_pre_listing_v1_5_prospective_freeze.py` | `eb648553fd3d1bce7bd4d6653203a6a1b37db4fca4cc6a34a6852530981fcea2` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/scripts/modeling/run_post_bookbuild_pre_listing_v1_5_prospective_freeze.py` | `eb648553fd3d1bce7bd4d6653203a6a1b37db4fca4cc6a34a6852530981fcea2` | yok (bayt bayt aynı) |
| 12 | `scripts/modeling/run_historical99_frozen_v1_5_benchmark.py` | `43d4e0f152f357e554555c3ae91a277ce7760805799309318e488bc99864314f` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/scripts/modeling/run_historical99_frozen_v1_5_benchmark.py` | `43d4e0f152f357e554555c3ae91a277ce7760805799309318e488bc99864314f` | yok (bayt bayt aynı) |
| 13 | `scripts/collect_historical99_bist_raw_v1.py` | `9c4a49fa6496b219de34c87cc5d60847c58b31723d1a7909f8ccbaefb0b238d6` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/scripts/collect_historical99_bist_raw_v1.py` | `9c4a49fa6496b219de34c87cc5d60847c58b31723d1a7909f8ccbaefb0b238d6` | yok (bayt bayt aynı) |
| 14 | `src/halka_arz_audit/true_live_freeze.py` | `d720d9ac46e82c4d9672a03afd8823049d063a9d3d921f5ed9a51f48209d455c` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/src/halka_arz_audit/true_live_freeze.py` | `d720d9ac46e82c4d9672a03afd8823049d063a9d3d921f5ed9a51f48209d455c` | yok (bayt bayt aynı) |
| 15 | `scripts/modeling/prebookbuild_v1_r6/pb_core4.py` | `c0f29ebdd32f00235a701441efaa3acf5d1f41b750acb847474564226a8e0304` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/scripts/modeling/prebookbuild_v1_r6/pb_core4.py` | `c0f29ebdd32f00235a701441efaa3acf5d1f41b750acb847474564226a8e0304` | yok (bayt bayt aynı) |
| 16 | `scripts/modeling/prebookbuild_v1_r6/chronology.py` | `38966efde38b829f811622df9b65bf092979bfd0a1b2f125e1a9284d1f5b865f` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/scripts/modeling/prebookbuild_v1_r6/chronology.py` | `38966efde38b829f811622df9b65bf092979bfd0a1b2f125e1a9284d1f5b865f` | yok (bayt bayt aynı) |
| 17 | `scripts/modeling/v2_market20_repair_01_core.py` | `a17e6e7d79f5eb068cf681c9ae4334c0d2ff14a4c0d1f70ab5c57020750da712` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/scripts/modeling/v2_market20_repair_01_core.py` | `a17e6e7d79f5eb068cf681c9ae4334c0d2ff14a4c0d1f70ab5c57020750da712` | yok (bayt bayt aynı) |
| 18 | `config/model_v1_5_spec.json` | `1245bf0f96c63cabdbd740cf043e9f3c58f8fc50af48472933c29e05dce211b1` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/config/model_v1_5_spec.json` | `1245bf0f96c63cabdbd740cf043e9f3c58f8fc50af48472933c29e05dce211b1` | yok (bayt bayt aynı) |
| 19 | `scripts/validation/validate_batch.py` | `bd13fbaaefa1630e0027f38d86a24b1736dfd570490e1bba584bb4c498b61563` | `ea278b1fae7db390ebecfdf791a33e3e968f3551` | `legacy/scripts/validation/validate_batch.py` | `bd13fbaaefa1630e0027f38d86a24b1736dfd570490e1bba584bb4c498b61563` | yok (bayt bayt aynı) |
| 20 | `artifacts/governance/BORSAI_PRETRADE_EXTENSION_COLLECTION_SPEC_20260912_R6/PRETRADE_EXTENSION_COLLECTION_SPEC.md` | `7de82fc9a9392ca3ecfe5f9b4ab5e9e03c78f8fc4d111ad71ca3e6daacb8eb39` | `50b0c001999d1a97c7b1230e783348ab1f97b70c` | `legacy/artifacts/governance/BORSAI_PRETRADE_EXTENSION_COLLECTION_SPEC_20260912_R6/PRETRADE_EXTENSION_COLLECTION_SPEC.md` | `7de82fc9a9392ca3ecfe5f9b4ab5e9e03c78f8fc4d111ad71ca3e6daacb8eb39` | yok (bayt bayt aynı) |
| 21 | `artifacts/governance/BORSAI_PRETRADE_EXTENSION_COLLECTION_SPEC_20260912_R6/PRETRADE_EXTENSION_COLLECTION_SPEC.json` | `8ea2b66300b67cb7bfe28f8e97db168394b0e4fea2c012922c725cd037d12f96` | `50b0c001999d1a97c7b1230e783348ab1f97b70c` | `legacy/artifacts/governance/BORSAI_PRETRADE_EXTENSION_COLLECTION_SPEC_20260912_R6/PRETRADE_EXTENSION_COLLECTION_SPEC.json` | `8ea2b66300b67cb7bfe28f8e97db168394b0e4fea2c012922c725cd037d12f96` | yok (bayt bayt aynı) |

### 2b. Import kapanışından gelen ek yardımcı modüller

İstenen modüllerin AST ile çıkarılan import kapanışında (fonksiyon içi importlar ve paket `__init__.py` dosyaları dahil) listede olmayanlar şunlar:

| Modül | Neden gerekli |
|---|---|
| `scripts/__init__.py`, `scripts/modeling/__init__.py` | `scripts.modeling.*` paket importları ve göreli importlar (`from . import …`) |
| `scripts/modeling/prebookbuild_v1_r6/__init__.py` | PB r6 paket başlatıcısı |
| `scripts/modeling/prebookbuild_v1_r6/identity_gate.py` | `chronology.py` buradan `MIN_TRAIN_N`, `NO_CONFLICT`, `OFFICIAL_VERIFIED` alır |
| `scripts/modeling/prebookbuild_v1_r6/targets.py` | `chronology.py` buradan `OutcomeRow` alır |
| `src/halka_arz_audit/__init__.py` | Paket başlatıcısı; import anında `inventory`, `evaluation`, `frozen_predictions`, `guards` modüllerini yükler |
| `src/halka_arz_audit/guards.py` | `true_live_freeze.py` (`PolicyViolation`) ve diğer modüller |
| `src/halka_arz_audit/live_forecast.py` | `true_live_freeze.py` (`load_config`) |
| `src/halka_arz_audit/live_forecast_freeze.py` | `true_live_freeze.py` |
| `src/halka_arz_audit/evaluation.py`, `inventory.py`, `frozen_predictions.py` | `halka_arz_audit/__init__.py` |
| `src/halka_arz_audit/ooxml_reader.py` | `frozen_predictions.py` |

Tek dinamik import `candidate_models.py:168`'deki `__import__('sys')`'tür (stdlib). Üçüncü taraf importları numpy, scipy, sklearn, joblib ve threadpoolctl'dir; hepsi `pyproject.toml`'da.

| # | Eski yol | Eski sha256 | Eski commit | Yeni yol | Yeni sha256 | Dönüşüm |
|---|---|---|---|---|---|---|
| 1 | `scripts/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/scripts/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | yok (bayt bayt aynı) |
| 2 | `scripts/modeling/__init__.py` | `a43d5f67aee581a255a0abac33bacbb9f3f3e1b98e450b9d4c4c5c594e559d4f` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/scripts/modeling/__init__.py` | `a43d5f67aee581a255a0abac33bacbb9f3f3e1b98e450b9d4c4c5c594e559d4f` | yok (bayt bayt aynı) |
| 3 | `scripts/modeling/prebookbuild_v1_r6/__init__.py` | `f6dd2979ef8f890d858a426dfcb6db02b3dd70bba7e51617a761734b915154d1` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/scripts/modeling/prebookbuild_v1_r6/__init__.py` | `f6dd2979ef8f890d858a426dfcb6db02b3dd70bba7e51617a761734b915154d1` | yok (bayt bayt aynı) |
| 4 | `scripts/modeling/prebookbuild_v1_r6/identity_gate.py` | `6a1c4d5939439c630b71837cef778258b0ddb5f7801b9c2796354d5133ca0dc0` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/scripts/modeling/prebookbuild_v1_r6/identity_gate.py` | `6a1c4d5939439c630b71837cef778258b0ddb5f7801b9c2796354d5133ca0dc0` | yok (bayt bayt aynı) |
| 5 | `scripts/modeling/prebookbuild_v1_r6/targets.py` | `6b5ee7e1385fe07e8b636e46671eed35239303dbfc4c66328dc2d6805feaf166` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/scripts/modeling/prebookbuild_v1_r6/targets.py` | `6b5ee7e1385fe07e8b636e46671eed35239303dbfc4c66328dc2d6805feaf166` | yok (bayt bayt aynı) |
| 6 | `src/halka_arz_audit/__init__.py` | `98edfa7bef3f8435a46edd79bc0e147b4d8c89909b051dfdc8acb572b451df0f` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/src/halka_arz_audit/__init__.py` | `98edfa7bef3f8435a46edd79bc0e147b4d8c89909b051dfdc8acb572b451df0f` | yok (bayt bayt aynı) |
| 7 | `src/halka_arz_audit/guards.py` | `ac0b1fd73feec705884a75693341a096cbbe68d7e3bb2707057be8b3625e5da4` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/src/halka_arz_audit/guards.py` | `ac0b1fd73feec705884a75693341a096cbbe68d7e3bb2707057be8b3625e5da4` | yok (bayt bayt aynı) |
| 8 | `src/halka_arz_audit/live_forecast.py` | `ab907cccb7eda442839e461ee8eb2740cc7371453f90f7591292c01a36664bfd` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/src/halka_arz_audit/live_forecast.py` | `ab907cccb7eda442839e461ee8eb2740cc7371453f90f7591292c01a36664bfd` | yok (bayt bayt aynı) |
| 9 | `src/halka_arz_audit/live_forecast_freeze.py` | `0c382bc289436868b9f91693353b5a5d69f55a4ff6ac4e4e7800292df31523e3` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/src/halka_arz_audit/live_forecast_freeze.py` | `0c382bc289436868b9f91693353b5a5d69f55a4ff6ac4e4e7800292df31523e3` | yok (bayt bayt aynı) |
| 10 | `src/halka_arz_audit/evaluation.py` | `e6eb8be8eec64c979ccfadf0f9af88c3ffeb7fd6a6c6abad5eb84d1ec278ce4e` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/src/halka_arz_audit/evaluation.py` | `e6eb8be8eec64c979ccfadf0f9af88c3ffeb7fd6a6c6abad5eb84d1ec278ce4e` | yok (bayt bayt aynı) |
| 11 | `src/halka_arz_audit/frozen_predictions.py` | `b3297f3066b712d96aa1c15a26e35c4b8b535c3762f24e4695e6a4af0d8dcf37` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/src/halka_arz_audit/frozen_predictions.py` | `b3297f3066b712d96aa1c15a26e35c4b8b535c3762f24e4695e6a4af0d8dcf37` | yok (bayt bayt aynı) |
| 12 | `src/halka_arz_audit/inventory.py` | `86d5c6e8d5bba047572ab3400dbace247684e47b447ba55dc620720492c74284` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/src/halka_arz_audit/inventory.py` | `86d5c6e8d5bba047572ab3400dbace247684e47b447ba55dc620720492c74284` | yok (bayt bayt aynı) |
| 13 | `src/halka_arz_audit/ooxml_reader.py` | `e96b3b7d1716f9a8819203e64e5f7cd4cb532f4fd26b90a3d1de18879a206363` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `legacy/src/halka_arz_audit/ooxml_reader.py` | `e96b3b7d1716f9a8819203e64e5f7cd4cb532f4fd26b90a3d1de18879a206363` | yok (bayt bayt aynı) |

## 3. registry/legacy_frozen/

Gerçekleşen sonuç değeri içeren hiçbir dosya kopyalanmadı. Aşağıdaki dosyaların hepsi okunarak denetlendi: yalnız tahmin, girdi, eğitim kümesi özeti ve zaman kanıtı içeriyorlar. Beş BKRGY/INTET dondurması `…_FROZEN_AWAITING_REALIZATION` durumunda.

### 3a. Kayıt başına bilgiler

Model kimliği adlandırması AUDIT §3'e göre yapıldı: `v1_5_h99` = V1.5, Historical99 ile eğitilmiş (her ufukta n = 99); `v1_5_full20` = V1.5, FULL20 ile eğitilmiş (n = 20/20/20/19).

| Kayıt | Arz | Tahmin zamanı (kaydın kendi beyanı) | Sınıf | f3 | Model | Zaman kanıtı | Rol |
|---|---|---|---|---|---|---|---|
| `NETGL_20260916_V1_5/`, `true_live_v1_5_registry.csv`, `NETGL_20260916_V1_5/netgl_input_contract.json` | NETGL | 2026-09-16T13:45:51+03:00; ilk işlem 2026-09-17 | POST_BOOKBUILD_PRE_LISTING_PROSPECTIVE | 2.84 | v1_5_h99 | **git+push**: eski repoda commit `5f70acedcd1e31cc9045ad073a0b317a5691b44e` (2026-09-16 14:09:46 +03:00); GitHub status `created_at` 2026-09-16T11:32:27Z (`push_proof.json`) | birincil |
| `BKRGY_20260825_V1_5/` (R1) | BKRGY | 2026-08-25 | DURING_BOOKBUILD_PRE_RESULT_PROSPECTIVE | yok (`DATA_NOT_FOUND`, f5 = 1) | v1_5_h99 | self-reported (git'e ilk giriş `d7e8453`, 2026-09-06) | geçersiz kullanım, yalnız bilgi |
| `BKRGY_20260825_V1_5_R2/` | BKRGY | 2026-08-25 (manifestte `…T00:00:00+03:00`) | DURING_BOOKBUILD_PRE_RESULT_PROSPECTIVE | yok (`DATA_NOT_FOUND`, f5 = 1) | v1_5_h99 | self-reported (`d7e8453`, 2026-09-06) | geçersiz kullanım, yalnız bilgi |
| `BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING/` | BKRGY | 2026-08-27T16:34:21+03:00 | POST_BOOKBUILD_PRE_LISTING_PROSPECTIVE | 1.77 | v1_5_h99 | self-reported (`d7e8453`, 2026-09-06) | birincil |
| `INTET_20260825_V1_5/` (PRE) | INTET | 2026-08-25T10:51:58+03:00 | PRE_BOOKBUILD_PROSPECTIVE | yok (`DATA_NOT_FOUND`, f5 = 1) | v1_5_h99 | self-reported (`d7e8453`, 2026-09-06) | geçersiz kullanım, yalnız bilgi |
| `INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING/` | INTET | 2026-08-31T10:52:15+03:00 | POST_BOOKBUILD_PRE_LISTING_PROSPECTIVE | 1.7 | v1_5_h99 | self-reported (`d7e8453`, 2026-09-06) | birincil |
| `TKNKA_20260819_V1_5_FULL20/TKNKA_TRUE_LIVE_V1_5_FREEZE_20260819.md` | TKNKA | 2026-08-19T14:48:53+03:00; ilk işlem 2026-08-20 | TRUE_LIVE, talep toplama sonrası (f3 sonuç bildiriminden) | 6.45 | **v1_5_full20** | self-reported (git'e ilk giriş `c2a56fb`, 2026-09-06) | birincil (v1_5_full20 için) |

Notlar:
- BKRGY ve INTET'in ilk işlem tarihi dondurma kayıtlarında yok; Faz 2'de resmi kaynaktan alınacak.
- TKNKA belgesinin sonunda, sonradan eklenmiş bir "PROVENANCE ADDENDUM" var. Yalnız KAP yayın zamanlarını düzeltiyor, tahmine dokunmuyor.
- V2-INTET shadow kaydı kopyalanmadı (§5). Oluşturulma tarihi 2026-09-04, yani listelemeden sonra, ve 2026-08-19 sonrasına ait bir XU100 kapanışı içeriyor.

### 3b. Dosyalar

| # | Eski yol | Eski sha256 | Eski commit | Yeni yol | Yeni sha256 | Dönüşüm |
|---|---|---|---|---|---|---|
| 1 | `artifacts/live_forecast/true_live_v1_5_registry.csv` | `94eddeab41597816206a2392bbd9accc11498008a87d99d4a32374417dd44793` | `5f70acedcd1e31cc9045ad073a0b317a5691b44e` | `registry/legacy_frozen/true_live_v1_5_registry.csv` | `ab28ab44217e58355b7b8e93ad9ced88aea3fd5261cb10ef369f5636c83d0fe9` | CRLF→LF (5 satır sonu); başka bayt değişmedi |
| 2 | `artifacts/derived/netgl_true_live_v1_5_20260916/netgl_input_contract.json` | `59f6285b5ed47b5b7590518e289bb58c887dd7b038e10e205fc2a634a7452a97` | `7a27033d670eb5472aed53a0e6be2c08eb7df754` | `registry/legacy_frozen/NETGL_20260916_V1_5/netgl_input_contract.json` | `59f6285b5ed47b5b7590518e289bb58c887dd7b038e10e205fc2a634a7452a97` | yok (bayt bayt aynı) |
| 3 | `artifacts/predictions/prospective/NETGL_20260916_V1_5/NETGL_20260916_V1_5_frozen_prediction_ledger.csv` | `920284024211cbdefee4b3337d16f64cad1e56a72191eb7fb8d92145bdf57007` | `5f70acedcd1e31cc9045ad073a0b317a5691b44e` | `registry/legacy_frozen/NETGL_20260916_V1_5/NETGL_20260916_V1_5_frozen_prediction_ledger.csv` | `920284024211cbdefee4b3337d16f64cad1e56a72191eb7fb8d92145bdf57007` | yok (bayt bayt aynı) |
| 4 | `artifacts/predictions/prospective/NETGL_20260916_V1_5/NETGL_20260916_V1_5_prediction_freeze_manifest.json` | `7187a40bb1199d5ea8ef1aaa0f58d8985ae466ea8030c0c553fd51d7cbafbee9` | `5f70acedcd1e31cc9045ad073a0b317a5691b44e` | `registry/legacy_frozen/NETGL_20260916_V1_5/NETGL_20260916_V1_5_prediction_freeze_manifest.json` | `7187a40bb1199d5ea8ef1aaa0f58d8985ae466ea8030c0c553fd51d7cbafbee9` | yok (bayt bayt aynı) |
| 5 | `artifacts/predictions/prospective/NETGL_20260916_V1_5/NETGL_20260916_V1_5_pretrade_evidence_packet.csv` | `fd1d21d7c5bd90e0838d70e231adb6bbdb35a9762a0b8d995bec689dcd0dafe6` | `5f70acedcd1e31cc9045ad073a0b317a5691b44e` | `registry/legacy_frozen/NETGL_20260916_V1_5/NETGL_20260916_V1_5_pretrade_evidence_packet.csv` | `fd1d21d7c5bd90e0838d70e231adb6bbdb35a9762a0b8d995bec689dcd0dafe6` | yok (bayt bayt aynı) |
| 6 | `artifacts/predictions/prospective/NETGL_20260916_V1_5/NETGL_20260916_V1_5_push_proof_manifest.json` | `6be331dcf48ae2206e3c390340c74e9d13da3e2566c5fc436d7f57525f849a13` | `1d11a6191600f6f148229ce3eea521418a3bec69` | `registry/legacy_frozen/NETGL_20260916_V1_5/NETGL_20260916_V1_5_push_proof_manifest.json` | `6be331dcf48ae2206e3c390340c74e9d13da3e2566c5fc436d7f57525f849a13` | yok (bayt bayt aynı) |
| 7 | `artifacts/predictions/prospective/NETGL_20260916_V1_5/NETGL_20260916_V1_5_training_eligibility_summary.csv` | `b27e5cf841278629aa43ae77b06913dd11736e08a173390ff9b62270bd78465f` | `5f70acedcd1e31cc9045ad073a0b317a5691b44e` | `registry/legacy_frozen/NETGL_20260916_V1_5/NETGL_20260916_V1_5_training_eligibility_summary.csv` | `b27e5cf841278629aa43ae77b06913dd11736e08a173390ff9b62270bd78465f` | yok (bayt bayt aynı) |
| 8 | `artifacts/predictions/prospective/NETGL_20260916_V1_5/push_proof.json` | `276851c15083e8d18e8b5469bf6ca885d353f46bdb1805406ab40364194f4a07` | `1d11a6191600f6f148229ce3eea521418a3bec69` | `registry/legacy_frozen/NETGL_20260916_V1_5/push_proof.json` | `276851c15083e8d18e8b5469bf6ca885d353f46bdb1805406ab40364194f4a07` | yok (bayt bayt aynı) |
| 9 | `artifacts/predictions/prospective/BKRGY_20260825_V1_5/BKRGY_20260825_V1_5_frozen_prediction_ledger.csv` | `be99d022c9984e173ab7b291fbba07bd55f8e171c6bff24ff5e3a1bab965d951` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `registry/legacy_frozen/BKRGY_20260825_V1_5/BKRGY_20260825_V1_5_frozen_prediction_ledger.csv` | `be99d022c9984e173ab7b291fbba07bd55f8e171c6bff24ff5e3a1bab965d951` | yok (bayt bayt aynı) |
| 10 | `artifacts/predictions/prospective/BKRGY_20260825_V1_5/BKRGY_20260825_V1_5_prediction_freeze_manifest.json` | `511c45bb99f8a9799340dbaa3da33286d56567ea7ecf393cedfe253535b0534a` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `registry/legacy_frozen/BKRGY_20260825_V1_5/BKRGY_20260825_V1_5_prediction_freeze_manifest.json` | `511c45bb99f8a9799340dbaa3da33286d56567ea7ecf393cedfe253535b0534a` | yok (bayt bayt aynı) |
| 11 | `artifacts/predictions/prospective/BKRGY_20260825_V1_5/BKRGY_20260825_V1_5_pretrade_evidence_packet.csv` | `eeeb3acd3f8cefead337dc47bc3fc2cbb28c21cd6fc140bbe94ed80f8930dc3b` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `registry/legacy_frozen/BKRGY_20260825_V1_5/BKRGY_20260825_V1_5_pretrade_evidence_packet.csv` | `eeeb3acd3f8cefead337dc47bc3fc2cbb28c21cd6fc140bbe94ed80f8930dc3b` | yok (bayt bayt aynı) |
| 12 | `artifacts/predictions/prospective/BKRGY_20260825_V1_5/BKRGY_20260825_V1_5_training_eligibility_summary.csv` | `c60b5b7344c4cd5de5858fad17c4ed3de6407ddb1e360c2e93dca18f7857bf0c` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `registry/legacy_frozen/BKRGY_20260825_V1_5/BKRGY_20260825_V1_5_training_eligibility_summary.csv` | `c60b5b7344c4cd5de5858fad17c4ed3de6407ddb1e360c2e93dca18f7857bf0c` | yok (bayt bayt aynı) |
| 13 | `artifacts/predictions/prospective/BKRGY_20260825_V1_5_R2/BKRGY_20260825_V1_5_R2_frozen_prediction_ledger.csv` | `be99d022c9984e173ab7b291fbba07bd55f8e171c6bff24ff5e3a1bab965d951` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `registry/legacy_frozen/BKRGY_20260825_V1_5_R2/BKRGY_20260825_V1_5_R2_frozen_prediction_ledger.csv` | `be99d022c9984e173ab7b291fbba07bd55f8e171c6bff24ff5e3a1bab965d951` | yok (bayt bayt aynı) |
| 14 | `artifacts/predictions/prospective/BKRGY_20260825_V1_5_R2/BKRGY_20260825_V1_5_R2_prediction_freeze_manifest.json` | `b9472d63bf41528090819c1f99b3e860fa129ec2c5b3c75dff67465315e36c76` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `registry/legacy_frozen/BKRGY_20260825_V1_5_R2/BKRGY_20260825_V1_5_R2_prediction_freeze_manifest.json` | `b9472d63bf41528090819c1f99b3e860fa129ec2c5b3c75dff67465315e36c76` | yok (bayt bayt aynı) |
| 15 | `artifacts/predictions/prospective/BKRGY_20260825_V1_5_R2/BKRGY_20260825_V1_5_R2_pretrade_evidence_packet.csv` | `eeeb3acd3f8cefead337dc47bc3fc2cbb28c21cd6fc140bbe94ed80f8930dc3b` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `registry/legacy_frozen/BKRGY_20260825_V1_5_R2/BKRGY_20260825_V1_5_R2_pretrade_evidence_packet.csv` | `eeeb3acd3f8cefead337dc47bc3fc2cbb28c21cd6fc140bbe94ed80f8930dc3b` | yok (bayt bayt aynı) |
| 16 | `artifacts/predictions/prospective/BKRGY_20260825_V1_5_R2/BKRGY_20260825_V1_5_R2_training_eligibility_summary.csv` | `c60b5b7344c4cd5de5858fad17c4ed3de6407ddb1e360c2e93dca18f7857bf0c` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `registry/legacy_frozen/BKRGY_20260825_V1_5_R2/BKRGY_20260825_V1_5_R2_training_eligibility_summary.csv` | `c60b5b7344c4cd5de5858fad17c4ed3de6407ddb1e360c2e93dca18f7857bf0c` | yok (bayt bayt aynı) |
| 17 | `artifacts/predictions/prospective/BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING/BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING_frozen_prediction_ledger.csv` | `af0f02fd7aa42b93c9ef850d7b2876f609e04d8bb407b39c1d2d478c4cc3c706` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `registry/legacy_frozen/BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING/BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING_frozen_prediction_ledger.csv` | `af0f02fd7aa42b93c9ef850d7b2876f609e04d8bb407b39c1d2d478c4cc3c706` | yok (bayt bayt aynı) |
| 18 | `artifacts/predictions/prospective/BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING/BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING_prediction_freeze_manifest.json` | `b5ef1ef603631aa8351589573bcd7ce1b775e76a8695f581b5c08e29a4ab0035` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `registry/legacy_frozen/BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING/BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING_prediction_freeze_manifest.json` | `b5ef1ef603631aa8351589573bcd7ce1b775e76a8695f581b5c08e29a4ab0035` | yok (bayt bayt aynı) |
| 19 | `artifacts/predictions/prospective/BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING/BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING_pretrade_evidence_packet.csv` | `1e72653af9e3c44c2e8755908ac7574f5d36ce8a39697bd12767f854bf4f71c6` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `registry/legacy_frozen/BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING/BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING_pretrade_evidence_packet.csv` | `1e72653af9e3c44c2e8755908ac7574f5d36ce8a39697bd12767f854bf4f71c6` | yok (bayt bayt aynı) |
| 20 | `artifacts/predictions/prospective/BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING/BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING_training_eligibility_summary.csv` | `fbf26b359a5993bfe9cfe456c79e81ca88f30e536f53b7a7fa4c670911dfa776` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `registry/legacy_frozen/BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING/BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING_training_eligibility_summary.csv` | `fbf26b359a5993bfe9cfe456c79e81ca88f30e536f53b7a7fa4c670911dfa776` | yok (bayt bayt aynı) |
| 21 | `artifacts/predictions/prospective/INTET_20260825_V1_5/INTET_20260825_V1_5_frozen_prediction_ledger.csv` | `486a1b07d59599b801fd32bd268f8cd165433d4e1e40759a9f596097355d6df2` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `registry/legacy_frozen/INTET_20260825_V1_5/INTET_20260825_V1_5_frozen_prediction_ledger.csv` | `486a1b07d59599b801fd32bd268f8cd165433d4e1e40759a9f596097355d6df2` | yok (bayt bayt aynı) |
| 22 | `artifacts/predictions/prospective/INTET_20260825_V1_5/INTET_20260825_V1_5_prediction_freeze_manifest.json` | `c74ce7ed675ec9d4a42edd164ab37ae7d3c71835897341096613778339cb48c2` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `registry/legacy_frozen/INTET_20260825_V1_5/INTET_20260825_V1_5_prediction_freeze_manifest.json` | `c74ce7ed675ec9d4a42edd164ab37ae7d3c71835897341096613778339cb48c2` | yok (bayt bayt aynı) |
| 23 | `artifacts/predictions/prospective/INTET_20260825_V1_5/INTET_20260825_V1_5_pretrade_evidence_packet.csv` | `4c0b99148a1fb9bc6e21bdf5eb9bd53d2ba0f746275f238778412211b341685c` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `registry/legacy_frozen/INTET_20260825_V1_5/INTET_20260825_V1_5_pretrade_evidence_packet.csv` | `4c0b99148a1fb9bc6e21bdf5eb9bd53d2ba0f746275f238778412211b341685c` | yok (bayt bayt aynı) |
| 24 | `artifacts/predictions/prospective/INTET_20260825_V1_5/INTET_20260825_V1_5_training_eligibility_summary.csv` | `02fdcbeb4d2635fba82d2aa56254144451e7d6529ae3a548d813bab0e3cd2a91` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `registry/legacy_frozen/INTET_20260825_V1_5/INTET_20260825_V1_5_training_eligibility_summary.csv` | `02fdcbeb4d2635fba82d2aa56254144451e7d6529ae3a548d813bab0e3cd2a91` | yok (bayt bayt aynı) |
| 25 | `artifacts/predictions/prospective/INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING/INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING_frozen_prediction_ledger.csv` | `3d5ca35e92ef2a4598d549f796741759b77f06e0fa2c77390a45b7ce3cbd9e58` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `registry/legacy_frozen/INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING/INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING_frozen_prediction_ledger.csv` | `3d5ca35e92ef2a4598d549f796741759b77f06e0fa2c77390a45b7ce3cbd9e58` | yok (bayt bayt aynı) |
| 26 | `artifacts/predictions/prospective/INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING/INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING_prediction_freeze_manifest.json` | `62689de2bf50c6d0904d1c7c4883a3528c7dbb35fd23be9351af71de0bf67566` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `registry/legacy_frozen/INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING/INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING_prediction_freeze_manifest.json` | `62689de2bf50c6d0904d1c7c4883a3528c7dbb35fd23be9351af71de0bf67566` | yok (bayt bayt aynı) |
| 27 | `artifacts/predictions/prospective/INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING/INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING_pretrade_evidence_packet.csv` | `7d1f290806debcf0289a812695b14925bdda9b8b5999432f8878afb1b47502e7` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `registry/legacy_frozen/INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING/INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING_pretrade_evidence_packet.csv` | `7d1f290806debcf0289a812695b14925bdda9b8b5999432f8878afb1b47502e7` | yok (bayt bayt aynı) |
| 28 | `artifacts/predictions/prospective/INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING/INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING_training_eligibility_summary.csv` | `caa0d1b610edc6546290180237534f8f62e25e7088bf9d3c2b0440a1657f82a1` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `registry/legacy_frozen/INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING/INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING_training_eligibility_summary.csv` | `caa0d1b610edc6546290180237534f8f62e25e7088bf9d3c2b0440a1657f82a1` | yok (bayt bayt aynı) |
| 29 | `BorsAi_External_Archive/SPECS/TKNKA_TRUE_LIVE_V1_5_FREEZE_20260819.md` | `9688b29824958a85bb6dff9730023b5a35332621ebeabb20c93c2e7d6afa3813` | `c2a56fbc83936b27989953e3ab9c9ed84edada3c` | `registry/legacy_frozen/TKNKA_20260819_V1_5_FULL20/TKNKA_TRUE_LIVE_V1_5_FREEZE_20260819.md` | `9688b29824958a85bb6dff9730023b5a35332621ebeabb20c93c2e7d6afa3813` | yok (bayt bayt aynı) |

## 4. tests/reference/

Ne işe yaradıkları:
- `v1_5_benchmark/` ve `baseline_benchmark/`: Faz 1 port kabul testinin referansları (V15B ve BLB).
- `netgl_input_contract.json` ve `A_v1_5_probe_cikti.json`: `predict` paritesi.
- `v1_5_macos_runtime_replay_20260911/` ve `q3a_macos_yeniden_kosu_cikti.json`: tolerans gerekçesi (AUDIT §1.2-b, §3a).

`netgl_input_contract.json` hem burada hem `registry/legacy_frozen/NETGL_20260916_V1_5/` altında durur; aynı kaynaktan iki kopya.

| # | Eski yol | Eski sha256 | Eski commit | Yeni yol | Yeni sha256 | Dönüşüm |
|---|---|---|---|---|---|---|
| 1 | `artifacts/modeling/historical99_v1_5_benchmark/HISTORICAL99_FROZEN_V1_5_BENCHMARK_V1/HISTORICAL99_V1_5_outer_fold_prediction_ledger.csv` | `f78d58ef3b0b3088afd7e69d894ace4b9016e8fddd72f3a849ea1b91dff00060` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `tests/reference/v1_5_benchmark/HISTORICAL99_V1_5_outer_fold_prediction_ledger.csv` | `f78d58ef3b0b3088afd7e69d894ace4b9016e8fddd72f3a849ea1b91dff00060` | yok (bayt bayt aynı) |
| 2 | `artifacts/modeling/historical99_v1_5_benchmark/HISTORICAL99_FROZEN_V1_5_BENCHMARK_V1/HISTORICAL99_V1_5_horizon_metric_summary.csv` | `97cea81ac1bfe781b2bf914110d63180fbcd8cedad648959d1bc442c38a872e3` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `tests/reference/v1_5_benchmark/HISTORICAL99_V1_5_horizon_metric_summary.csv` | `97cea81ac1bfe781b2bf914110d63180fbcd8cedad648959d1bc442c38a872e3` | yok (bayt bayt aynı) |
| 3 | `artifacts/modeling/historical99_v1_5_benchmark/HISTORICAL99_FROZEN_V1_5_BENCHMARK_V1/HISTORICAL99_V1_5_selected_hyperparameter_distribution.csv` | `c4469556f72ea4c5f7001ef72b0a2f3cd50eb53e5ea8a7301c0b074aa057a8c1` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `tests/reference/v1_5_benchmark/HISTORICAL99_V1_5_selected_hyperparameter_distribution.csv` | `c4469556f72ea4c5f7001ef72b0a2f3cd50eb53e5ea8a7301c0b074aa057a8c1` | yok (bayt bayt aynı) |
| 4 | `artifacts/modeling/historical99_predefined_baseline_benchmark/HISTORICAL99_PREDEFINED_BASELINE_BENCHMARK_V1/HISTORICAL99_predefined_baseline_metric_summary.csv` | `655d763b8a6ceb2a5721b98385bb4311bde9a11663dc0480a09c492031ea0113` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `tests/reference/baseline_benchmark/HISTORICAL99_predefined_baseline_metric_summary.csv` | `655d763b8a6ceb2a5721b98385bb4311bde9a11663dc0480a09c492031ea0113` | yok (bayt bayt aynı) |
| 5 | `artifacts/modeling/historical99_predefined_baseline_benchmark/HISTORICAL99_PREDEFINED_BASELINE_BENCHMARK_V1/HISTORICAL99_predefined_baseline_fold_ledger.csv` | `f3867d6bb49035d5d0dd1c92f055c103348c48b3da5d10cedfff9aa85354e201` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | `tests/reference/baseline_benchmark/HISTORICAL99_predefined_baseline_fold_ledger.csv` | `f3867d6bb49035d5d0dd1c92f055c103348c48b3da5d10cedfff9aa85354e201` | yok (bayt bayt aynı) |
| 6 | `artifacts/derived/netgl_true_live_v1_5_20260916/netgl_input_contract.json` | `59f6285b5ed47b5b7590518e289bb58c887dd7b038e10e205fc2a634a7452a97` | `7a27033d670eb5472aed53a0e6be2c08eb7df754` | `tests/reference/netgl_input_contract.json` | `59f6285b5ed47b5b7590518e289bb58c887dd7b038e10e205fc2a634a7452a97` | yok (bayt bayt aynı) |
| 7 | `docs/checkup_20260921/A_v1_5_probe_cikti.json` | `ca0593ac060344ad781e9fea6eea8d2aed21f68c5814295aab06ee8220b7ba0a` | `604e2187f8a1f4a452bf0434ad5d1454bbbf4d21` | `tests/reference/A_v1_5_probe_cikti.json` | `ca0593ac060344ad781e9fea6eea8d2aed21f68c5814295aab06ee8220b7ba0a` | yok (bayt bayt aynı) |
| 8 | `artifacts/derived/v1_5_macos_runtime_replay_20260911/REPLAY_REPORT.md` | `5bf0532e30832d451320e0e9aa6125485d25e5a5a823ac5e18233c6da1093981` | `95127cd0a594a714ccbe23bd0c58e2fec3d7ced3` | `tests/reference/v1_5_macos_runtime_replay_20260911/REPLAY_REPORT.md` | `5bf0532e30832d451320e0e9aa6125485d25e5a5a823ac5e18233c6da1093981` | yok (bayt bayt aynı) |
| 9 | `artifacts/derived/v1_5_macos_runtime_replay_20260911/replay_comparison.csv` | `4d79407f10f71daabbe0a2c2e0c42e131a5be060bc891024e1f0ad402efbbd6f` | `95127cd0a594a714ccbe23bd0c58e2fec3d7ced3` | `tests/reference/v1_5_macos_runtime_replay_20260911/replay_comparison.csv` | `4d79407f10f71daabbe0a2c2e0c42e131a5be060bc891024e1f0ad402efbbd6f` | yok (bayt bayt aynı) |
| 10 | `artifacts/derived/v1_5_macos_runtime_replay_20260911/replay_stdout.json` | `1409eaa17b7fe8e20421852feb001f5b7918613865a5f834c8f1e0f583cca2c9` | `95127cd0a594a714ccbe23bd0c58e2fec3d7ced3` | `tests/reference/v1_5_macos_runtime_replay_20260911/replay_stdout.json` | `1409eaa17b7fe8e20421852feb001f5b7918613865a5f834c8f1e0f583cca2c9` | yok (bayt bayt aynı) |
| 11 | `artifacts/derived/v1_5_macos_runtime_replay_20260911/replay_summary.json` | `1409eaa17b7fe8e20421852feb001f5b7918613865a5f834c8f1e0f583cca2c9` | `95127cd0a594a714ccbe23bd0c58e2fec3d7ced3` | `tests/reference/v1_5_macos_runtime_replay_20260911/replay_summary.json` | `1409eaa17b7fe8e20421852feb001f5b7918613865a5f834c8f1e0f583cca2c9` | yok (bayt bayt aynı) |
| 12 | `artifacts/derived/v1_5_macos_runtime_replay_20260911/v1_5_macos_replay_harness.py` | `99db576376cf5690f5f40a6b8b566167f76ffd553e4e1a040cfd668673092aa7` | `95127cd0a594a714ccbe23bd0c58e2fec3d7ced3` | `tests/reference/v1_5_macos_runtime_replay_20260911/v1_5_macos_replay_harness.py` | `99db576376cf5690f5f40a6b8b566167f76ffd553e4e1a040cfd668673092aa7` | yok (bayt bayt aynı) |
| 13 | `docs/fable_audit_20260921/ekler/q3a_macos_yeniden_kosu_cikti.json` | `4e3617a3d1a09f33f5fe3e08af9d50bce1791de1d729f76462524d094cdf4c1f` | `604e2187f8a1f4a452bf0434ad5d1454bbbf4d21` | `tests/reference/q3a_macos_yeniden_kosu_cikti.json` | `4e3617a3d1a09f33f5fe3e08af9d50bce1791de1d729f76462524d094cdf4c1f` | yok (bayt bayt aynı) |

## 5. Kopyalanmadı: Faz 2'de alınacak

Aşağıdaki dosyalar sıra kuralı gereği alınmadı. Ya 2026-08-06 sonrası listelenen arzların gerçekleşen sonuç değerlerini taşıyorlar (ya da o sonuçlar görüldükten sonra üretilmiş replay kayıtları), ya da 2026-08-19 sonrası seans verisi içeriyorlar. Faz 1 model JSON'ları dondurulduktan sonra, Faz 2'de alınacaklar.

| # | Eski yol | Eski sha256 | Eski commit | Neden |
|---|---|---|---|---|
| 1 | `artifacts/predictions/retrospective_oos/CITAS_20260818_V1_5/CITAS_20260818_V1_5_pretrade_replay_packet.csv` | `ccdc9e03410224efc2950c384371649030c4cce3d90969f4a08adf4ff19e623c` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | CITAS/VEYAS/KPEKS replay kaydı: gerçekleşen sonuç değeri ya da sonuç görüldükten sonra üretilmiş replay |
| 2 | `artifacts/predictions/retrospective_oos/CITAS_VEYAS_FROZEN_V1_5_RETROSPECTIVE_OOS_REPLAY_01/CITAS_VEYAS_V1_5_frozen_prediction_ledger.csv` | `371f167e53472edf9a9ba5a8d12b09ee66d73226e23d0a19f48a2e8f68a3b9b6` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | CITAS/VEYAS/KPEKS replay kaydı: gerçekleşen sonuç değeri ya da sonuç görüldükten sonra üretilmiş replay |
| 3 | `artifacts/predictions/retrospective_oos/CITAS_VEYAS_FROZEN_V1_5_RETROSPECTIVE_OOS_REPLAY_01/CITAS_VEYAS_V1_5_prediction_freeze_manifest.json` | `ed94419e6911d508319e42f18e2fe89f43bb2c0b06225d0ccf55d194b9c3cdac` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | CITAS/VEYAS/KPEKS replay kaydı: gerçekleşen sonuç değeri ya da sonuç görüldükten sonra üretilmiş replay |
| 4 | `artifacts/predictions/retrospective_oos/CITAS_VEYAS_FROZEN_V1_5_RETROSPECTIVE_OOS_REPLAY_01/CITAS_VEYAS_V1_5_realization_ledger.csv` | `0617cb7044ec392a9c9db638c24b01bac1027180caf7048573aa7aef3e28c218` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | CITAS/VEYAS/KPEKS replay kaydı: gerçekleşen sonuç değeri ya da sonuç görüldükten sonra üretilmiş replay |
| 5 | `artifacts/predictions/retrospective_oos/CITAS_VEYAS_FROZEN_V1_5_RETROSPECTIVE_OOS_REPLAY_01/CITAS_VEYAS_V1_5_replay_evaluation_summary.csv` | `f5aba8c5b36d9def3d4e1ad04b1054e6ab68230e846b24f47cb5c4b085710e21` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | CITAS/VEYAS/KPEKS replay kaydı: gerçekleşen sonuç değeri ya da sonuç görüldükten sonra üretilmiş replay |
| 6 | `artifacts/predictions/retrospective_oos/CITAS_VEYAS_FROZEN_V1_5_RETROSPECTIVE_OOS_REPLAY_01/CITAS_VEYAS_V1_5_training_eligibility_summary.csv` | `c8ac4cd7190d8f4708e331062eacfd7e37fb6ca78c90c8be09104f7955a7aab6` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | CITAS/VEYAS/KPEKS replay kaydı: gerçekleşen sonuç değeri ya da sonuç görüldükten sonra üretilmiş replay |
| 7 | `artifacts/predictions/retrospective_oos/KPEKS_20260817_V1_5/KPEKS_20260817_V1_5_retrospective_oos_replay.json` | `7dcdc84d8754006613c037f86ad48840999f2b4ccfb8d270bdb466c892d5f924` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | CITAS/VEYAS/KPEKS replay kaydı: gerçekleşen sonuç değeri ya da sonuç görüldükten sonra üretilmiş replay |
| 8 | `artifacts/predictions/retrospective_oos/VEYAS_20260820_V1_5/VEYAS_20260820_V1_5_pretrade_replay_packet.csv` | `674afa5cb4cb04970cb9a022208e2aa7e469bee57125d3bf11943731230d4dc1` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | CITAS/VEYAS/KPEKS replay kaydı: gerçekleşen sonuç değeri ya da sonuç görüldükten sonra üretilmiş replay |
| 9 | `artifacts/modeling/v2_market20_r3_case_studies/BORSAI_V2_MARKET20_R3_INTET_SHADOW_RESEARCH_20260904_R1/INTET_V2_SHADOW_RESEARCH_REPORT.md` | `43a0e2d0ad283593e49c3cc8d4485bb187ca6a47729fa9bacb1919bc048a893c` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | V2-INTET shadow: 2026-08-19 sonrası XU100 seans kapanışı içeriyor (S0 = 2026-08-27); listelemeden sonra üretilmiş (2026-09-04) |
| 10 | `artifacts/modeling/v2_market20_r3_case_studies/BORSAI_V2_MARKET20_R3_INTET_SHADOW_RESEARCH_20260904_R1/evidence_inventory.csv` | `5fdd8a957cbea8d335ad0fd9efaef3386c9fd64fc4baf37da202dca13cd3ac73` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | V2-INTET shadow: 2026-08-19 sonrası XU100 seans kapanışı içeriyor (S0 = 2026-08-27); listelemeden sonra üretilmiş (2026-09-04) |
| 11 | `artifacts/modeling/v2_market20_r3_case_studies/BORSAI_V2_MARKET20_R3_INTET_SHADOW_RESEARCH_20260904_R1/intet_shadow_research_input.json` | `82a31ad679d40e702cff7e61dd388e5ab65ba69616778e6cc524d83bd3bd90f0` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | V2-INTET shadow: 2026-08-19 sonrası XU100 seans kapanışı içeriyor (S0 = 2026-08-27); listelemeden sonra üretilmiş (2026-09-04) |
| 12 | `artifacts/modeling/v2_market20_r3_case_studies/BORSAI_V2_MARKET20_R3_INTET_SHADOW_RESEARCH_20260904_R1/intet_v2_shadow_prediction_freeze.json` | `1d9482255793cdba83ba91b5160151727a5ce27dd63181b10f1b333219a4a7d4` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | V2-INTET shadow: 2026-08-19 sonrası XU100 seans kapanışı içeriyor (S0 = 2026-08-27); listelemeden sonra üretilmiş (2026-09-04) |
| 13 | `artifacts/modeling/v2_market20_r3_case_studies/BORSAI_V2_MARKET20_R3_INTET_SHADOW_RESEARCH_20260904_R1/manifest.json` | `8fa3109f3461651eac426a5a9c54989e897b8661ad000724d0ad87134c5f8c4c` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | V2-INTET shadow: 2026-08-19 sonrası XU100 seans kapanışı içeriyor (S0 = 2026-08-27); listelemeden sonra üretilmiş (2026-09-04) |
| 14 | `artifacts/modeling/v2_market20_r3_case_studies/BORSAI_V2_MARKET20_R3_INTET_NUMERICAL_SHADOW_AFTER_GOVERNANCE_20260904_R1/intet_numerical_shadow_research_input.json` | `421f3ca9361577ac4df5d0b001e0ed437f4d67801beb87509a305259c1da23c9` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | V2-INTET shadow: 2026-08-19 sonrası XU100 seans kapanışı içeriyor (S0 = 2026-08-27); listelemeden sonra üretilmiş (2026-09-04) |
| 15 | `artifacts/modeling/v2_market20_r3_case_studies/BORSAI_V2_MARKET20_R3_INTET_NUMERICAL_SHADOW_AFTER_GOVERNANCE_20260904_R1/intet_v2_numerical_shadow_prediction_freeze.json` | `754fdb38849fcd362a49397dc441274dc695838e00ea71d606640d7d047a835a` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | V2-INTET shadow: 2026-08-19 sonrası XU100 seans kapanışı içeriyor (S0 = 2026-08-27); listelemeden sonra üretilmiş (2026-09-04) |
| 16 | `artifacts/modeling/v2_market20_r3_case_studies/BORSAI_V2_MARKET20_R3_INTET_NUMERICAL_SHADOW_AFTER_GOVERNANCE_20260904_R1/manifest.json` | `5d41fe6d7f0079775204df18dc800417ff9adcd0db24fb7091828569c1398ac2` | `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` | V2-INTET shadow: 2026-08-19 sonrası XU100 seans kapanışı içeriyor (S0 = 2026-08-27); listelemeden sonra üretilmiş (2026-09-04) |

Pinli XU100 JSON'unun özgün hali de (`artifacts/modeling/historical99_market_sector_microstructure_stage_a/HISTORICAL99_MARKET_SECTOR_MICROSTRUCTURE_STAGE_A_V1/raw/official_bist_xu100_graphic_pinned.json`, sha256 `13db0171345a917d53ae99308e68694b54b56090df3b8612f6686444e99236b0`) bu repoda yok. Yalnız §1'deki türevi var.

## 6. K2 tarih taraması

Tarama, commit öncesinde repodaki bütün izlenecek dosyalar üzerinde koştu (`.git` ve `.venv` hariç). Aradıkları:
- 2026-08-19 sonrası tarihler, üç biçimde: YYYY-MM-DD, YYYYMMDD, GG.AA.YYYY.
- CITAS, VEYAS, TKNKA, KPEKS, INTET, BKRGY, NETGL adları.

Her eşleşme bağlamıyla (CSV sütunu, JSON anahtarı ya da metin satırı) listelendi.

**Seans tarihi sütunları:** Aşağıdaki sütunların hepsinde en büyük değer ≤ 2026-08-19:
- `target_session_date`, `calendar_date`, `hisTs`: data/raw ve tests/reference;
- `maximum_target_session_date`: registry eğitim özetleri.

**2026-08-19 sonrası tarihler.** Hepsi seans verisi dışı şu türlere giriyor:
- Tahmin, dondurma, kalıcılaştırma ve push kanıtı zaman damgaları (registry).
- Önceden ilan edilmiş ilk işlem günleri: NETGL 2026-09-17, TKNKA 2026-08-20.
- Talep toplama pencereleri (BKRGY 08-24…26, INTET 08-26…27, NETGL bitiş 09-11).
- KAP/SPK belge yayın zamanları.
- Görev ve kimlik adlarındaki tarihler: `…_20260912_V1`, `…_R6_20260826`, spec R6 geçmişi.
- Kanıt dosyası adları: `…_20260821.txt`, `…_20260825.txt`.
- `collect_historical99_bist_raw_v1.py`'deki tatil sabitleri: 2026-10-28 yarım gün, 2026-10-29 kapanış.
- Bu repodaki belgelerin kendi tarihleri (2026-09-21).

**7 arzın adları** yalnız şu yerlerde geçiyor:
- registry'deki tahmin kayıtları (girdi, tahmin, eğitim özeti);
- legacy kod yorumları;
- BKRGY/INTET tahmin replay karşılaştırması (`replay_comparison.csv`: dondurulmuş ve yeniden hesaplanan tahmin değerleri);
- belgeler.

Bu arzların satırlarında sonuç sütunu (`close`, `official_close`, `target_return`, `above_ipo_flag`, `upper_limit`, `realized_*`) taşıyan değer sayısı: **0**.

## 7. Faz 2A: 2026-08-19 sonrası XU100 ve takvim uzatması (SPEC_MARKET20_V0 §4)

Görev `BORSAI_FAZ2A_REGISTRY_INPUTS_20260922`. XU100 bir arz sonucu değildir; sıra kuralının kapsamında değildir. THB/THM ve pay fiyatı indirilmedi.

| # | Yeni yol | sha256 | Kaynak | Alınma | İçerik |
|---|---|---|---|---|---|
| 1 | `data/raw/xu100/xu100_graphic_20260922.json` | `04637c911f912e007522790520191ae99ad5cf47f8d38a4360698ea3038397fe` | `https://www.borsaistanbul.com/graphic.php?veriTuru=endeks-graphic&indexCode=XU100` (eski pinli dosyayla aynı uç nokta; kaynak etiketi `BORSA_ISTANBUL_OFFICIAL`) | 2026-09-22T14:43:04+03:00 (HTTP `date: Tue, 22 Sep 2026 11:43:04 GMT`); ham yanıt değiştirilmeden, 579614 bayt | 9705 kayıt, yalnız `indexName = XU100`, 1986-01-31…2026-09-21; gün içi (2026-09-22) kayıt yok |
| 2 | `data/raw/pay_calendar_b_extension_20260820_20261231.csv` | `273ca0e7f815c7bb1a0ce562ba7060d2dc806603f2112cdde460195cbebc6432` | BIST Pay Piyasası 2026 tatil tablosu (EK-3): eski repo `inputs/ohlcv/bist_official/reference/pay-piyasasi-2026-yili-tatil-tablosu_RAW.pdf`, sha256 `e45fa97e2f67d85b3571ce9e6c4758292a57379c2216fc88183f32504584e680`, eski commit `d7e8453402e0d8873bfb6dc52cb3a37bb95f467f` (Takvim B'nin 2026 satırlarıyla aynı belge; kopyalanmadı, yalnız o dosya okundu) | 2026-09-22 | Takvim B şeması; 2026-08-20…2026-12-31, 134 gün, 95 seans. Tam kapanış 2026-08-30 (Pazar) ve 2026-10-29; yarım gün 2026-10-28 (seans sayılır) |

Denetimler:
- **Revizyon (§4-2):** eski pinli dosyanın 9682 kaydının hepsi yeni dosyada Decimal-eşit (`market20.check_revision`). Eski repodaki özgün 9684 kayıtlık dosya (`13db0171…`, 2026-08-20 ve 2026-08-21 dahil) da birebir örtüşüyor. Yeni: 23 kayıt, 2026-08-20…2026-09-21.
- **Çapraz denetim (§4-5):** 2026-08-20…2026-09-21 aralığında takvim seans günleri kümesi = XU100 kayıt günleri kümesi (23 = 23). Bu satırların `verification_status` değeri `FAZ2A_TRANSCRIBED_SESSION_SET_EQUALS_XU100_DATES_THROUGH_20260921`; sonraki satırlar `FAZ2A_TRANSCRIBED_NOT_YET_CROSS_CHECKED_AGAINST_XU100`.
- **Kullanım:** eski dosyalar yerinde kalır; H99 (backtest/fit) yolları değişmedi. Canlı/geç kayıt f6'sı `market20.load_live_sources()` ile en yeni pinli XU100'ü ve Takvim B + uzatmayı okur; kayda dosya sha'larını yazar.
- **Karar (proje sahibinin onayına açık):** takvim uzatması görev metnindeki izinli yollar arasında adıyla geçmiyor (`data/raw/ (XU100)`). SPEC_MARKET20_V0 §4-4 uzatmayı XU100 güncellemesinin parçası saydığı ve uzatma olmadan ilk işlem günü 2026-08-21 ve sonrası olan 4 arzda (KPEKS, INTET, BKRGY, NETGL) f6 `CALENDAR_NOT_COVERING` ile RET vereceği için eklendi.

## 8. Faz 2A: listeleme öncesi kaynak belgeler (`registry/source_docs/`)

Ağ yalnız `kap.org.tr` ve `spk.gov.tr`. Her belge ilgili arzın ilk işlem gününden önce yayımlandı. Yayın zamanı: KAP'ta bildirim PDF'inin başlığındaki 'KAP'ta yayınlanma tarihi ve saati' (Europe/Istanbul; KAP liste API'sindeki zaman 1–4 saniye sonra, `kap_api_publish_date`); SPK bülteninde URL'deki 24 haneli kimliğin sunucu oluşturma zamanı (HTTP Last-Modified ve bülten üzerindeki tarihle tutarlı).

KAP ek dosyaları (`api/file/download/<id>`) Java `ObjectOutputStream(byte[])` sarmalıyla gelir. Saklanan dosya PDF'in kendisidir; `download_sha256` sarmallı ham yanıttır. Eski repodaki kayıtlarda geçen ek sha'ları (CITAS `5dd4c70a…`, `c4b7b1d1…`; VEYAS `f51d39f1…`, `77627321…`; TKNKA `b733ad79…`, `c21cb0bf…`) bu ham yanıtlarla birebir aynı; bildirim PDF'leri de eski repodaki kopyalarla aynı (NETGL `43398d23…`, `87985416…`). Yani KAP belgeleri değişmemiş.

| Arz | Kaynak kimliği | Tür | Yayın zamanı | Dosya | sha256 | Ham indirme sha256 |
|---|---|---|---|---|---|---|
| BKRGY | `KAP_1655263` | KAP_NOTIFICATION_PDF | 2026-08-27T09:35:29+03:00 | `registry/source_docs/BKRGY/KAP_1655263_bildirim.pdf` | `91c0f676762e140d2a98e78a288e106441e4b6082afcaacda1e9fd1a0014ae61` | — |
| BKRGY | `KAP_1655263_EK1` | KAP_ATTACHMENT_PDF | 2026-08-27T09:35:29+03:00 | `registry/source_docs/BKRGY/KAP_1655263_ek1.pdf` | `fdbe76a51bf032193e33a99057a5bcb1458ec6415c21cf4a786bd7d4e026da10` | `ee8a4c8ff47e4130700f15b6aacb805f96d2eaefa843f6b3a9bc0e8e29f35435` |
| BKRGY | `KAP_1655292` | KAP_NOTIFICATION_PDF | 2026-08-27T11:34:59+03:00 | `registry/source_docs/BKRGY/KAP_1655292_bildirim.pdf` | `43a07a80cd945fe9cc9138d9a296c76878d57e0a3460c474e8d750389471545d` | — |
| BKRGY | `KAP_1655292_EK1` | KAP_ATTACHMENT_PDF | 2026-08-27T11:34:59+03:00 | `registry/source_docs/BKRGY/KAP_1655292_ek1.pdf` | `4f766ab307b12ec8966d291761b292e52ad3b4b907f7564d6c88eed30c700c78` | `11395212a60124a71145dce2252ed6c10cc8fd7f4e5b95b41a6462e5bbdc2db2` |
| BKRGY | `KAP_1655891` | KAP_NOTIFICATION_PDF | 2026-08-28T18:11:04+03:00 | `registry/source_docs/BKRGY/KAP_1655891_bildirim.pdf` | `4fd3d93128c6cc83bb34ba36275f8f7e673094d896aaff99ad39221d312a3b36` | — |
| BKRGY | `SPK_BULTEN_2026_52` | SPK_BULLETIN | 2026-08-20T20:44:05+03:00 | `registry/source_docs/BKRGY/SPK_BULTEN_2026-52.pdf` | `a1940a9dbe874ffdea4c9c1ad697ed52359b0494f102b56b971b8790c61450a0` | — |
| CITAS | `KAP_1649026` | KAP_NOTIFICATION_PDF | 2026-08-13T13:12:37+03:00 | `registry/source_docs/CITAS/KAP_1649026_bildirim.pdf` | `e8481bbc10c40a284db6e70a97598d678ff5000d0f3f191c4ba78da05c38dd21` | — |
| CITAS | `KAP_1649026_EK1` | KAP_ATTACHMENT_PDF | 2026-08-13T13:12:37+03:00 | `registry/source_docs/CITAS/KAP_1649026_ek1.pdf` | `f88675a19cc4f3e5907259038d1e5113737d82319f28928dc1c5f3382970d02a` | `5dd4c70ae709f513d692090a2153ae82e7bfe463398b199ca81ad3bd6e662389` |
| CITAS | `KAP_1649391` | KAP_NOTIFICATION_PDF | 2026-08-13T18:10:49+03:00 | `registry/source_docs/CITAS/KAP_1649391_bildirim.pdf` | `cb64822ec9d33d44373f746b55b68dea379f2106f6d6b268f6b2afc0106c47fa` | — |
| CITAS | `SPK_BULTEN_2026_49` | SPK_BULLETIN | 2026-08-05T22:56:18+03:00 | `registry/source_docs/CITAS/SPK_BULTEN_2026-49.pdf` | `04cf2aaceba9cb032739edfc1c226198e8369f196ed6bc2e46c810b28011eb7b` | — |
| INTET | `KAP_1654174` | KAP_NOTIFICATION_PDF | 2026-08-21T18:10:16+03:00 | `registry/source_docs/INTET/KAP_1654174_bildirim.pdf` | `816c75fdd3968f2d0cebeb3dc1ba43c35420515a7719bde0a90de4299d1c3942` | — |
| INTET | `KAP_1655573` | KAP_NOTIFICATION_PDF | 2026-08-28T11:39:53+03:00 | `registry/source_docs/INTET/KAP_1655573_bildirim.pdf` | `56a29c1453a4fa911f487759962c832b748a9bd402d400a60f211e8a567f1087` | — |
| INTET | `KAP_1655573_EK1` | KAP_ATTACHMENT_PDF | 2026-08-28T11:39:53+03:00 | `registry/source_docs/INTET/KAP_1655573_ek1.pdf` | `6df48115631e0ffe7426520b658cd00e254541cf0bac5d1282a1bc200c1a1f08` | `749cfca878e84df9325757da362c857b1ba0fcaee400e041a6c4438c349febf8` |
| INTET | `KAP_1655890` | KAP_NOTIFICATION_PDF | 2026-08-28T18:10:50+03:00 | `registry/source_docs/INTET/KAP_1655890_bildirim.pdf` | `c7752145551b5a7e1001ca47c84c22162086a50a4b04060b830e263960108509` | — |
| INTET | `SPK_BULTEN_2026_52` | SPK_BULLETIN | 2026-08-20T20:44:05+03:00 | `registry/source_docs/INTET/SPK_BULTEN_2026-52.pdf` | `a1940a9dbe874ffdea4c9c1ad697ed52359b0494f102b56b971b8790c61450a0` | — |
| KPEKS | `KAP_1650970` | KAP_NOTIFICATION_PDF | 2026-08-17T08:54:17+03:00 | `registry/source_docs/KPEKS/KAP_1650970_bildirim.pdf` | `1c1cc0a0c68f40021df7e5a2c26ed5cff46ae4bc00c09d25a2d45fc330923d55` | — |
| KPEKS | `KAP_1650970_EK1` | KAP_ATTACHMENT_PDF | 2026-08-17T08:54:17+03:00 | `registry/source_docs/KPEKS/KAP_1650970_ek1.pdf` | `272e168f12cefee429f0113ed63f4e99c5f144c99c5caf3751fd0f6454b70c4f` | `fa6e25f798b76a3a44a113fc61b7af2459c8a5a6de9d66146761d8271945562b` |
| KPEKS | `KAP_1652131` | KAP_NOTIFICATION_PDF | 2026-08-18T18:11:03+03:00 | `registry/source_docs/KPEKS/KAP_1652131_bildirim.pdf` | `8cc6c77bb209e013369e5d50c29185d0b4915e67b1550358a774173945e98686` | — |
| KPEKS | `SPK_BULTEN_2026_49` | SPK_BULLETIN | 2026-08-05T22:56:18+03:00 | `registry/source_docs/KPEKS/SPK_BULTEN_2026-49.pdf` | `04cf2aaceba9cb032739edfc1c226198e8369f196ed6bc2e46c810b28011eb7b` | — |
| NETGL | `KAP_1662138` | KAP_NOTIFICATION_PDF | 2026-09-13T17:30:28+03:00 | `registry/source_docs/NETGL/KAP_1662138_bildirim.pdf` | `87985416ec82db60dcda5679de400fc149ff963fac5105142fa9751f01e95592` | — |
| NETGL | `KAP_1662138_EK1` | KAP_ATTACHMENT_PDF | 2026-09-13T17:30:28+03:00 | `registry/source_docs/NETGL/KAP_1662138_ek1.pdf` | `bdf25f373877c85c794667b66c03d05aed9a48aab84ebd4709323151c57a4bfb` | `46533bb8479304789244f638136c709ef689f116fbe280218e7008e726e30ac1` |
| NETGL | `KAP_1663155` | KAP_NOTIFICATION_PDF | 2026-09-15T18:10:17+03:00 | `registry/source_docs/NETGL/KAP_1663155_bildirim.pdf` | `43398d23da6c8c96d10f71e2db131680b3fa08d4836c3f4ffa51d0e49785acb1` | — |
| NETGL | `SPK_BULTEN_2026_56` | SPK_BULLETIN | 2026-09-03T20:18:20+03:00 | `registry/source_docs/NETGL/SPK_BULTEN_2026-56.pdf` | `319f08488ae0d0e2c4d92703d19d5d7f51d55c66feb3525f19e295de66d024dc` | — |
| TKNKA | `KAP_1651025` | KAP_NOTIFICATION_PDF | 2026-08-17T10:53:26+03:00 | `registry/source_docs/TKNKA/KAP_1651025_bildirim.pdf` | `dd4f530855bccb87c235242a21fb62d4c940a409cb6916ba2469801d892ed79a` | — |
| TKNKA | `KAP_1651025_EK1` | KAP_ATTACHMENT_PDF | 2026-08-17T10:53:26+03:00 | `registry/source_docs/TKNKA/KAP_1651025_ek1.pdf` | `42b9a7e68bc683a0df5861c47f6984eebbcd7bf9137c4220b2ee846bb724a3b8` | `c21cb0bf845e7e0fa001ed73a0831553cf9df66c16e2a555c48cf7c00646e09e` |
| TKNKA | `KAP_1652127` | KAP_NOTIFICATION_PDF | 2026-08-18T18:10:48+03:00 | `registry/source_docs/TKNKA/KAP_1652127_bildirim.pdf` | `6d893b120f4dcddc076c776ae3ec932f098d6a8d5f232bd0287b7511af04f19d` | — |
| TKNKA | `SPK_BULTEN_2026_49` | SPK_BULLETIN | 2026-08-05T22:56:18+03:00 | `registry/source_docs/TKNKA/SPK_BULTEN_2026-49.pdf` | `04cf2aaceba9cb032739edfc1c226198e8369f196ed6bc2e46c810b28011eb7b` | — |
| VEYAS | `KAP_1650990` | KAP_NOTIFICATION_PDF | 2026-08-17T09:38:51+03:00 | `registry/source_docs/VEYAS/KAP_1650990_bildirim.pdf` | `47c2bff0bab035f7908a126086c478a67305018fc2017a9c0d7dfc382b00579b` | — |
| VEYAS | `KAP_1650990_EK1` | KAP_ATTACHMENT_PDF | 2026-08-17T09:38:51+03:00 | `registry/source_docs/VEYAS/KAP_1650990_ek1.pdf` | `98791c4dfff7f79d544e3f3c21987e4f1fc872ac38a810acfb3267223a2d7fa8` | `f51d39f177d9985510b2a3108b68703022d9f2c7561324d51890be7f88290cf3` |
| VEYAS | `KAP_1652124` | KAP_NOTIFICATION_PDF | 2026-08-18T18:10:26+03:00 | `registry/source_docs/VEYAS/KAP_1652124_bildirim.pdf` | `16fe84a311394f5859f84cd79586c6b24c78848079d7cac30e9440ead9a31b55` | — |
| VEYAS | `SPK_BULTEN_2026_49` | SPK_BULLETIN | 2026-08-05T22:56:18+03:00 | `registry/source_docs/VEYAS/SPK_BULTEN_2026-49.pdf` | `04cf2aaceba9cb032739edfc1c226198e8369f196ed6bc2e46c810b28011eb7b` | — |

Payda taraması kanıtı (`registry/source_docs/_ENUMERATION/`):

- `kap_byCriteria_subject_paylarin_islem_gormeye_baslamasi_20260801_20260922.json` (sha256 `5bedac31427fd796412fdb4eccf89cb5e2cdf040ab528bd2ae33986c2579c80a`): KAP `byCriteria` ham yanıtı, konu 'Payların İşlem Görmeye Başlaması', 8 kayıt (QUICK + 7 arz).
- `KAP_1641554_bildirim.pdf` (sha256 `3f67be8e41f74d540401648cbcb042a70a71edcec4837eecba1e8d009ad47bac`): Bewen Enerji halka arzının ertelenmesi (2026-07-31).
- `ENUMERATION.json`: sorgular, BIST bildirim konu sayıları, listeleme benzeri bildirimler ve kararlar, SPK 2026/44–61 'İlk Halka Arzlar' onayları.

Eski repodan okunanlar (kopyalanmadı): `inputs/prospective/_window_enumeration/*` (KAP API biçimi), `scripts/modeling/emit_true_live_push_proof.py` (push kanıtı yöntemi, `borsai/push_proof.py`'ye taşındı), CITAS/VEYAS/KPEKS replay dosyalarının yalnız GİRDİ alanları (§5 satır 1, 7, 8; yalnız karşılaştırma için; gerçekleşen alan içeren dosyalar — realization ledger, evaluation summary — açılmadı) ve split_prevalence S1 belge kopyaları (sha karşılaştırması). Girdi değerlerinin hepsi yukarıdaki resmi belgelerden bağımsız alındı; eski değerlerle birebir aynı.

## 9. Faz 2A: sicil dosyaları

- `registry/inputs/<TICKER>.json` (şema `borsai.inputs/1`): alan başına değer, kaynak kimliği, yayın zamanı, belge sha256'sı, belge yolu ve belgedeki alıntı (PDFKit metin çıkarımında aranarak doğrulandı).
- `registry/records/<TICKER>/<UTC>_<sha12>.json` (şema `borsai.record/1`): `python -m borsai.freeze registry/inputs/<TICKER>.json` çıktısı; 16 kayıtlı modelin hepsi.
- `registry/ipos.csv`: payda (SPEC_SCORING §4).
- `registry/legacy_roles.json`: `registry/legacy_frozen/` kayıtlarının SPEC_SCORING §6 rolleri ve dosya sha256'ları (içerikleri değişmedi).

## 10. Faz 2B: resmi BIST THB/THM bültenleri (`data/raw/bist/`)

Görev `BORSAI_FAZ2B_OUTCOMES_SCORING_20260922`. Kaynak kalıbı SPEC_SCORING §1 ve legacy `collect_historical99_bist_raw_v1.py` `source_url`: `https://www.borsaistanbul.com/data/{thb,thm}/YYYY/MM/{kind}YYYYMMDD1.zip`. İndirici `borsai/outcomes.py` (`python -m borsai.outcomes fetch|update|completeness`); ağ yalnız `www.borsaistanbul.com`. Ham zip baytları değiştirilmeden `data/raw/bist/<kind>/YYYY/` altına yazılır; her dosya `data/raw/bist/MANIFEST.csv`'de (tarih, tür, URL, sha256, bayt, iç dosya adı, indirme zamanı — yerel saat, kanıt değil — ve sunucunun `Last-Modified` başlığı). H99 SESSIONS dosyasında sha256'sı pinli bülten (2026-08-06…2026-08-19) başka baytlarla gelirse indirici durur.

**Commit A (tanımlar, sonuç verisi yok):** yalnız kaynak sınaması için 2026-08-17 bültenleri. 2026-08-17'de işlem gören post-08-06 arz yok (CITAS'ın D_1'i 2026-08-18).

| Yol | sha256 | Bayt | URL | HTTP Last-Modified | H99 SESSIONS ile |
|---|---|---|---|---|---|
| `data/raw/bist/thb/2026/thb202608171.zip` | `5637f92b31550e31cd0d59f9024d8904f956473c5cfea3e3cfeff1da3541d380` | 285384 | `https://www.borsaistanbul.com/data/thb/2026/08/thb202608171.zip` | Mon, 17 Aug 2026 15:28:08 GMT | `thb_sha256` birebir aynı (QUICK D8) |
| `data/raw/bist/thm/2026/thm202608171.zip` | `c156c6f30f4edffabb880df116fa62f4549542b9221906e2649e80e0edcaf262` | 94291 | `https://www.borsaistanbul.com/data/thm/2026/08/thm202608171.zip` | Mon, 17 Aug 2026 05:02:07 GMT | `thm_sha256` birebir aynı |

Ayrıştırılan QUICK satırı (kapanış, sözleşme sayısı, referans, üst/alt limit) SESSIONS'taki `thb_raw_*` / `thm_raw_*` metinleriyle aynı (`tests/test_outcomes.py`). Takvim: H99 Pay Piyasası takvimi (`CALENDAR_A_SHA256`) ∪ Faz 2A uzatması (`CALENDAR_B_EXT_SHA256`); ilan dışı kapanış olursa `data/raw/bist/UNANNOUNCED_CLOSURES.csv`.

**Commit B (sonuç verisi):** `python -m borsai.outcomes update` (2026-09-22T17:52+03:00; 2026-09-22 bülteni henüz yayımlanmamıştı, 2026-09-21'de durdu) ve `python -m borsai.outcomes completeness`.

| Tür | Dosya | Tarih aralığı | Toplam bayt | Not |
|---|---|---|---|---|
| THB | 33 | 2026-08-06…2026-09-21 | 9836091 | 2026-08-06…2026-08-14 (7 seans) yalnız tamlık denetimi için; 2026-08-17 commit A'da |
| THM | 26 | 2026-08-17…2026-09-21 | 2720952 | 2026-08-17 commit A'da |

- Bu commit'te yeni: 57 dosya, 12177368 bayt (MANIFEST.csv'de her birinin URL'si, sha256'sı, sunucu `Last-Modified`'ı).
- H99 SESSIONS'ta sha256'sı pinli bültenler (THB 2026-08-06…2026-08-14, 2026-08-18, 2026-08-19; THM 2026-08-18, 2026-08-19) birebir aynı geldi (aksi halde indirici durur).
- Takvim uyuşmazlığı yok: 2026-08-18…2026-09-21 arasındaki 25 resmi seansın hepsinin THB ve THM'si yayımlanmış; `UNANNOUNCED_CLOSURES.csv` oluşmadı. 2026-08-30 (Pazar, tam kapanış) takvimde seans değil.
- Sonuç dosyaları `data/outcomes/<T>.csv` (7 arz) yalnız bu bültenlerden ve `registry/inputs/<T>.json` arz fiyatından; ağsız yeniden üretim testi `tests/test_outcomes.py::test_committed_outcomes_rebuild_from_raw_bulletins`.
- Tamlık denetimi `data/outcomes/COMPLETENESS.csv`: pencere 2026-08-07…2026-09-21, taban 2026-08-06; 5579 yeni kod: 5566 pay dışı araç (3174 alım varantı, 2384 satım varantı, 4 BYF, 1 fon, 3 grup `NSE`), 11 `ipos.csv` satırı (7 arzın `.E` kodu, INTET.HE birincil piyasa kodu, SEKFK/KRTEK/CVKMD `.BE` bedelli kalan pay kodları), 1 kod değişikliği (MARKA.E -> USHOL.E), 1 temerrüt pazarı kodu (OYAKC.TE); açıklanamayan yeni pay 0, `ipos.csv`'de olup görünmeyen arz 0. Yeni halka arz yok.
- EK 1 (`docs/prompts/FAZ2B_EK1_OYAKC.md`): ilk koşuda OYAKC.TE (2026-09-21 THB: `YAPISAL BAZDA PIYASA ALT BOLUMU` = `BUYIN`, `ENSTRUMAN TIPI` = `BUYINEQT`, 3 sözleşme; aynı gün OYAKC.E normal pay) açıklanamadığı için denetim durdu; genel temerrüt pazarı kuralı eklendi (SPEC_DEVIATIONS E20) ve sırayla tamlık denetimi, `update` (2026-09-22T18:14+03:00; 2026-09-22 bülteni yayımlanmamıştı, yeni dosya yok, sonuç dosyaları değişmedi) ve `python -m borsai.scoring` yeniden koşuldu.

## 11. Faz 7: TÜİK TÜFE (`data/raw/tuik/`) ve eğitim tablosu v2

Görev `BORSAI_FAZ7_HAZARD_V1_IMPL_20260925`; şartname `docs/specs_faz7/SPEC_HAZARD_V1.md` §3.2, §3.4 ve `docs/specs_faz7/KARARLAR.md` K3 (deflatör TÜİK TÜFE genel endeksi, 2025=100, ay kuralı T − 2). Ağ yalnız TÜİK veri portalı (`veriportali.tuik.gov.tr`).

| Yol | sha256 | Bayt | Kaynak |
|---|---|---|---|
| `data/raw/tuik/tufe_degisim_oranlari_bulten_58290.xls` | `6f7ee8e4ce7e8a7ac79a332db375c4a3179d02162a5d72f684d352aa6c70ff86` | 58368 | TÜİK "Tüketici Fiyat Endeksi, Ağustos 2026" bülteni (sayı 58290, yayım 2026-09-03 10:00), "Tablolar → Tüketici fiyat endeksi ve değişim oranları" [2025=100]; indirme 2026-09-25T18:22:51Z, bağlantı ve HTTP başlıkları `…58290.source.json`'da. Komut satırı istemcisi sunucuda 403 aldığı için dosya bülten sayfasının kendi oturumunda (yerleşik tarayıcı) okundu; baytlar değiştirilmedi. |
| `data/raw/tuik/tufe_bultenleri.csv` | (içerik) | — | 2019-11…2026-08'in her ayı için o ayın kendi TÜFE bülteni: sayı, dönem, "Yayım Tarihi" (Europe/Istanbul, hepsi 10:00), sayfa adresi `https://veriportali.tuik.gov.tr/tr/press/<sayı>`; bülten sayfaları 2026-09-25'te tek tek okundu (82 sayfa). 78 ay "ayın 3'ü ya da sonraki ilk iş günü" kuralına uyuyor; 4 ay bayram nedeniyle daha geç (2020-07 → 2020-08-04, 2022-04 → 2022-05-05, 2023-06 → 2023-07-05, 2026-05 → 2026-06-05). |
| `data/raw/tuik/tufe_genel_2025_100.csv` | `3d61cbcfca2453cfce476d4cfaae38a3c77c68a4d168641162d1627e731a567b` | — | `data/raw/tuik/build_tufe_csv.py` (stdlib; OLE2/BIFF8 okuyucu dahil) iki kaynaktan üretir; `--check` bayt-eşitliği sınar. Sütunlar `month, index, release_date, bulletin_id, source_url, source_sha256`; 82 ay (2019-11…2026-08); `index` tablonun binary64 değerinin en kısa metni (≤ 6 ondalık, denetli); 2025 ortalaması 100.00. |

- 2025 ve öncesi ayların değerleri TÜİK'in 2026'da 2025=100'e zincirlediği (yeniden ölçeklediği) seridir; o aylar yayımlandıklarında 2003=100 temelindeydi. `release_date` ayın kendi bülteninin yayım günüdür. Yeniden ölçekleme yayımlanmış aylık değişim oranlarını korur (tablonun kendi aylık oranları düzeylerden hesaplananla 259/259 ayda ±0.0051 içinde; derleyici denetler); f1r = büyüklük / (endeks / 100) bu yüzden T anında yayımlı bilgiyle aynı sırayı ve oranları verir (SPEC_DEVIATIONS J).
- Ay eklemek veri sürümünü değiştirmez: yeni ay yeni indirilen tablonun url/sha'sıyla dosyanın sonuna bir satırdır; eski satırlar bayt-eşit kalır (`borsai.tufe.prefix_sha256`, pin `borsai/specs.py: TUFE_PIN`). Temel yıl, zincirleme ya da eski bir satırın değişmesi yeni veri sürümü = yeni model_id'dir.
- `data/training_table_v2.csv` ve `data/data_version_v2.json`: `data/build_training_table_v2.py` (mantık `borsai/data.py`). H99'un 99 satırı `data/training_table.csv`'nin 31 sütununu hücre hücre taşır; eski kohortun açık kümesinin 71 üyesi `registry/oot/inputs/` (girdi; `registry.inputs_pit_problems` temiz) ve `data/outcomes_oot/` (sonuç) dosyalarından. Kasa üyelerinin hiçbir dosyası okunmadı; açık üyelerin dosyaları `data_version_v2.json`'da birleşik sha256 ile pinlidir (kod adı yazılmaz). `data/training_table.csv`, `data/data_version.json` ve `data/build_training_table.py` değişmedi.

### 11a. Aylık TÜFE ekleme (dondurma görevi `BORSAI_FAZ7_FREEZE_20260927`)

Deflatörlü modeller (`ceiling_hazard_v1_real`, `_pooled`) dondurulduktan sonra her canlı kayıt T'nin ayı − 2'nin TÜFE'sini ister; o ay dosyada yoksa kayıt **yazılmaz** (`borsai.freeze.TufeMissing`, ileti eksik ayı ve aşağıdaki komutu söyler; SPEC_HAZARD_V1 §9). Ay m'nin bülteni m + 1'in 3'ünde (hafta sonu/bayramda sonraki iş günü) 10:00'da yayımlanır; ekleme o günden sonra yapılır. Komut (tek metin: `borsai/tufe.py: APPEND_COMMAND`):

```
.venv/bin/python data/raw/tuik/build_tufe_csv.py --append-month <YYYY-MM> --bulletin-id <bülten sayısı> --release <YYYY-MM-DDT10:00:00+03:00> --xls <indirilen tablo .xls> --download-url '<indirme bağlantısı>' --sha256 <indirilen tablonun sha256'sı>
```

1. Bülten sayfası `https://veriportali.tuik.gov.tr/tr/press/<bülten sayısı>` tarayıcıda açılır (komut satırı istemcisi 403 alır); "Tablolar → Tüketici fiyat endeksi ve değişim oranları" [2025=100] indirilir; dosyanın sha256'sı ve indirme bağlantısı not edilir (`shasum -a 256 <dosya>`). Sayfadaki "Yayım Tarihi" `--release`'e yazılır.
2. Komut (`data/raw/tuik/build_tufe_csv.py --append-month`) önce bellekte doğrular: ay dosyanın son ayından hemen sonraki ay; indirilen dosyanın sha256'sı verilenle aynı; bağlantı TÜİK veri portalında; yayım m + 1'in ≥ 3'ü, 10:00 (+03:00), iş günü; tablo [2025=100] temelinde, **m'de biter** ve dosyadaki her eski ayın değerini **aynen** verir (revizyon, temel yıl ya da zincirleme değişimi varsa durur: bu yeni veri sürümüdür = yeni model_id, CLAUDE.md kural 5); m'nin düzeyi tablonun kendi aylık oranıyla tutarlı.
3. Sonra yazar: tablo `data/raw/tuik/tufe_degisim_oranlari_bulten_<sayı>.xls` (+ `.source.json`: sha256, bayt, bülten, bağlantı, indirme zamanı), `tufe_bultenleri.csv`'ye bir satır, `tufe_genel_2025_100.csv`'nin sonuna bir satır (`source_url`/`source_sha256` o ayın tablosu). Eski satırlar bayt-eşit kalır; pin `TUFE_PIN` (2026-08'e kadarki önek) tutar. Tam derleme yeni dosyayı bayt bayt yeniden üretmezse bütün yazılanlar geri alınır. Ardından `--check` bütün dosyayı pinli tablolardan yeniden üretir.
4. Commit (yalnız `data/raw/tuik/`), push (proje sahibi). Kayıt bu commit'ten sonra yazılır.

Bu görevde gerçek ay **eklenmedi** (ağ yok); yol sentetik testle gösterildi (`tests/test_faz7_tufe.py`: `test_monthly_append_*`, `test_append_command_documented_in_provenance`). İlk gerçek ekleme **Eylül 2026** TÜFE'si olacak (bülten 2026-10-05'te beklenir): Kasım 2026'da ilk işlem görecek arzların kaydı (T − 2 = 2026-09) için gerekli; Ekim 2026 arzları 2026-08'i kullanır (dosyada).

## 12. Faz 7: izahname alanları (135 eski kohort üyesi)

Görev `BORSAI_FAZ7_PROSPECTUS_INTAKE_20260926` (alım, 2026-09-26; `docs/prompts/FAZ7_PROSPECTUS_INTAKE.md`). Kaynak dizin `~/Desktop/BorsAi_codex/verified_faz7/` (salt okunur). Doğrulayıcı görev `BORSAI_FAZ7_VERIFY_PROSPECTUS_20260925` (Claude Code, Opus 5.5; 2026-09-25 21:05 – 2026-09-26 07:05 İstanbul; `docs/prompts/FAZ7_VERIFY_PROSPECTUS.md`); ilk çıkarım Codex + GPT-6 Astra (`docs/prompts/FAZ7_CODEX_PROSPECTUS_B1..B4.md`). Kapsam: 7 listeleme öncesi alan (`distribution_method`, `price_stability_planned`, `price_stability_days`, `issuer_lockup_days`, `shareholder_lockup_days`, `sector`, `participation_index_eligible`) × 135 üye = 945 hücre; 841 dolu, 104 boş (yalnız `participation_index_eligible`; nedenleri `docs/faz7/prospectus/REPORT.md` §4). Alım görevi hiçbir değeri değiştirmedi; tanımlar ve eşleme kuralları REPORT §3'te.

| Yol | Dosya | Bayt | Not |
|---|---|---|---|
| `registry/oot/candidate_features_faz7/<T>.json` | 135 | 2122442 | kaynakla bayt-eşit |
| `registry/oot/source_docs_faz7/<T>/MANIFEST.json` | 135 | 1329784 | kaynakla bayt-eşit; toplam 1284 belgenin URL'si, KAP bildirimi, yayın zamanı, sha256'sı, baytı, sayfası, metin katmanı |
| `docs/faz7/prospectus/` | 40 | 971515 | doğrulayıcı teslimatından 37 dosya (`REPORT.md`, `coverage.csv`, `verification_log.jsonl`, `EXPOSURE.md`, `scripts/` 27, `logs/` 6) + `README.md`, `intake_mutation.txt`, `intake_test_runs.txt` |
| `registry/oot/candidate_features_faz7/SHA256SUMS` | 1 | 29333 | 310 satır: 135 özellik + 135 MANIFEST + `docs/faz7/prospectus/` altındaki 40 dosya (sha256sum biçimi, yollar dosyanın dizinine göreli) |

- `SHA256SUMS` sha256: `601bf5aca94bc3792d147d391013e0949d209b1d224e648cf6ae4da84adca785`. Bekçi `tests/test_faz7_prospectus.py` (dosya kümeleri = evren listesindeki 135 MEMBER = `registry/oot/inputs/`; 7 alan ve durum kümesi; alan başına durum sayıları REPORT §1 ile birebir; her dolu alanın kaynağı MANIFEST'te, sha256'sı eşit, yayın zamanı ilk işlem gününden önce; pinsiz dosya yok; sonuç alanı yok). Mutasyon gösterimi `docs/faz7/prospectus/intake_mutation.txt`, test koşuları `intake_test_runs.txt`.
- Satır sonu: `docs/faz7/prospectus/coverage.csv` kaynakta CRLF'ydi (8885 bayt, sha256 `47fc7b6b9889d2a3f3604fe513a5cfb0d4299c28ecde727d8c9f83532bdd8831`). `.gitattributes` (`* text=auto eol=lf`) commit'te LF'ye çevireceği için pin taze klonda tutsun diye dosya baştan LF'ye çevrildi (8749 bayt, sha256 `94cccfd34c8133c5ee84e1fbaf04338f84b68b57eb69963eeaa8722825a38661`; yalnız satır sonu). Başka hiçbir dosya değişmedi.
- PDF'ler repoda değil: 1284 PDF (3,19 GB) `~/Desktop/BorsAi_codex/verified_faz7/source_docs/<T>/` altında kaldı; her birinin resmi URL'si ve sha256'sı MANIFEST'te, yeniden indirilip eşlenebilir. Özellik dosyalarındaki `source_file` yolları o ağaca görelidir. `_tools/`'tan yalnız `scripts/*.py`, `scripts/*.md` ve altı kayıt dosyası (`verifier_interventions.jsonl`, `sha_compare.json`, `sample10.txt`, `recheck_log.jsonl`, `audit_result.json`, `tables.md`) alındı; önbellek, dossier, karar dosyaları, ham günlükler, `ocr_vision` ikilisi, `ocr_vision.m`, `text_loop.sh` ve `wait_ready.sh` alınmadı.
- `EXPOSURE.md` bayt-eşit kopyadır; alım görevinde okunmadı, yalnız sha'landı.
- Açık tanım noktası (REPORT §8): `shareholder_lockup_days` toplama kuralı (§3). Değer, herhangi bir ortağın borsada satış kısıtının ilk gevşediği gündür: bileşenlerin en kısası; aynı ortağın daha uzun ve en az o kadar sıkı bir kısıtı tarafından kapsanan bileşen hesaba girmez; mevzuat kısıtları (Pay Tebliği 8/1, 9/3 ve 20/412 ilke kararı) dahildir. Her taahhüt alanın `components` listesindedir (kim, gün, tür, dayanak, başlangıç); başka bir kural (ör. ortak başına en uzun süre ya da yalnız MUTLAK) `components`'ten yeniden hesaplanabilir. Kuralı sahibin kararı belirler; alım görevi kuralı değiştirmedi.

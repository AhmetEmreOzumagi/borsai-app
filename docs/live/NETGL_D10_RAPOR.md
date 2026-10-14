# NETGL D4–D10: resmi sonuçlar, canlı skorlar ve dondurulmuş tahminler

TASK_ID: BORSAI_LIVE_NETGL_D10_20260930. Terazi: **canlı (prospektif)**. n = 7 arz (< 10): hiçbir canlı metrik, ortalama ya da "geçiyor" hükmü yok; aşağıdaki karşılaştırmalar n = 1 betimlemesidir. NETGL'nin ilk işlem günü 2026-09-17, D10 = 2026-09-30 (takvimden).

## 1. Özet

- D10 bülteni yayımlanmıştı (HEAD 200). NETGL h = 4…10 resmi THB/THM'den dolduruldu, hepsi `OK`, `PENDING` 0. Seri uzunluğu **L = 3** (D4'te tavan bozuldu).
- D4…D10'un yedi kapanışının hepsi resmi THM alt limitine (taban) tam eşit. D6'dan itibaren kapanış arz fiyatının altında; **D10 getirisi −%36.17, Y₁₀ = 0**.
- Payda denetimi temiz: yeni halka arz yok. Skorlar yeniden üretildi (`as_of_session` = 2026-09-30); `scores_oot.json` ve `SCORES_OOT.md` bayt-eşit.
- Görev sırasında üç bekçi, canlı sonuç ilerlemesi ya da yeni görünen mevcut pay kodları yüzünden kırmızı çıktı; üçü de proje sahibinin yazılı onayıyla ve dondurulmuş içerik gevşetilmeden güncellendi (§7).

## 2. Hash'ler

| Adım | Commit | Mesaj (kısaltılmış) |
|---|---|---|
| Taban | `b29486e` | BORSAI_APP_P1_REPORT |
| T | `3b4d785` | BORSAI_LIVE_GUARD: COMPLETENESS kasa-kodu istisnası iki kipli (M23) |
| **O** | `c1eb7ae` | BORSAI_LIVE_OUTCOMES: NETGL D4-D10 resmi THB/THM sonuçları |
| M24 | `cf5019c` | BORSAI_LIVE_GUARD2: f1f9d44 skor pini sonuç ilerlemesine izin verir |
| S | `87434ff` | BORSAI_LIVE_SCORES: canlı skorlar D10'a kadar yeniden üretildi |
| M24 devamı | `f61eb18` | BORSAI_LIVE_GUARD3: a0df5b7 skor pini aynı kuralı kullanır |
| M24 notu | `fd22be3` | BORSAI_LIVE_DEVIATIONS_FIX: M24 metnindeki yanlış sınıflandırma cümlesi düzeltildi (yalnız belge) |
| R | bu raporu ekleyen commit | BORSAI_LIVE_NETGL_REPORT |

Dosya sha256'ları (önce → sonra):

| Dosya | Önce | Sonra |
|---|---|---|
| `data/outcomes/NETGL.csv` | `bccc3803bb88…` | `89aac762f635…` |
| `data/outcomes/COMPLETENESS.csv` | `83bc13ba114c…` | `93f992992f42…` (yalnız ekleme, +834 satır) |
| `data/raw/bist/MANIFEST.csv` | `02472ab4cbb9…` | `19e0e62ea34d…` (yalnız ekleme, +14 satır) |
| `scores/scores.json` | `022a2f9904ba…` | `48f59c927851…` |
| `scores/scores_post_d1.json` | `a27515108764…` | `fea3e6f9632f…` |
| `docs/SCORES.md` | `5747dde1e238…` | `c432f35189e3…` |
| `scores/scores_oot.json` | `12852121309c…` | `12852121309c…` (bayt-eşit) |
| `docs/SCORES_OOT.md` | `ab50ccd42e32…` | `ab50ccd42e32…` (bayt-eşit) |

Diğer altı canlı arzın sonuç dosyaları (CITAS, TKNKA, VEYAS, KPEKS, INTET, BKRGY) bayt-eşit; NETGL'nin h = 1…3 satırları bayt-eşit.

Yeni resmi bültenler (14 dosya; her sha256 dosyayla eşit ve MANIFEST'e eklendi):

| Seans | Tür | sha256 | Bayt |
|---|---|---|---|
| 2026-09-22 | THB | `afd2f9f1b10dd4ed4ee82eed35f08ff559b358dc89309917ebb595d043579673` | 298445 |
| 2026-09-22 | THM | `10747676a807996b4159f75578a300f87266b065d76f93d4e0262bde4f76ce6a` | 108183 |
| 2026-09-23 | THB | `a4789c9bb6ff0b8331a597a335bde77e7a4e38e7145d53799a7e534b88a5d4a9` | 297620 |
| 2026-09-23 | THM | `40e6cd6bd80d01f17a15c800d36a10f7126f89acca42976a4bc5c6a216c63a09` | 106667 |
| 2026-09-24 | THB | `c7fa6d13c1d1d6ec1af1d065298c6e133b8df7c08d568901d23b98e3370235bb` | 300374 |
| 2026-09-24 | THM | `4d162e09ca40d1a6d768f8c655e4e555865d91800ff0a2e32799be8bc38b7368` | 106625 |
| 2026-09-25 | THB | `cd5a365205582b32afc7b2942748708b0bc7b4becc67773f6a6e575f87a73e57` | 293251 |
| 2026-09-25 | THM | `ef0b7e828d649a332c7b7e391c181a25c62af4b584726409b09465953281a48b` | 107149 |
| 2026-09-28 | THB | `cb856e8e15d9e9a10f82c88e9752811d285dac0aa8d38b91a624adf63c057494` | 296173 |
| 2026-09-28 | THM | `56372cf7e4591990181df6b730e44a5fd35cfb883465a3c563b132091c7e7bc7` | 104008 |
| 2026-09-29 | THB | `a95bf6218f3774f5ea85b498645e8c1b7558e34615e883979f44118ed9fc31f4` | 310152 |
| 2026-09-29 | THM | `968330a02cd946c595926694a61295386c4c02099010bfd7f124ec7498528075` | 108864 |
| 2026-09-30 | THB | `a736e64415bf29dd4c6ad16b360bb587dfcd1a8d0a3a196e6f3c980db9a5ccd6` | 308760 |
| 2026-09-30 | THM | `dd1bfc471052980c9efe401cc0fd9a5f2dbc0745d48929b7c2aa1a8d6a0ed5fa` | 110770 |

Ağ yalnız `www.borsaistanbul.com` bülten adresleridir: D10 THB için bir HEAD (200, `application/zip`, 308760 bayt), sonra 14 zip indirmesi. Başka ağ işi yok.

## 3. NETGL gerçekleşen yol (resmi THB/THM)

Arz fiyatı 25.52. Tavan etiketi = `Decimal(kapanış) == Decimal(üst limit)` (SPEC_SCORING §3).

| h | Seans | Kapanış | Üst limit | Alt limit | Tavan etiketi | Arz fiyatına göre |
|---|---|---|---|---|---|---|
| D1 | 2026-09-17 | 28.06 | 28.06 | 22.98 | 1 | +9.95% |
| D2 | 2026-09-18 | 30.86 | 30.86 | 25.26 | 1 | +20.92% |
| D3 | 2026-09-21 | 33.94 | 33.94 | 27.78 | 1 | +32.99% |
| D4 | 2026-09-22 | 30.56 | 37.32 | 30.56 | 0 | +19.75% |
| D5 | 2026-09-23 | 27.52 | 33.60 | 27.52 | 0 | +7.84% |
| D6 | 2026-09-24 | 24.78 | 30.26 | 24.78 | 0 | −2.90% |
| D7 | 2026-09-25 | 22.32 | 27.24 | 22.32 | 0 | −12.54% |
| D8 | 2026-09-28 | 20.10 | 24.54 | 20.10 | 0 | −21.24% |
| D9 | 2026-09-29 | 18.09 | 22.10 | 18.09 | 0 | −29.11% |
| D10 | 2026-09-30 | 16.29 | 19.89 | 16.29 | 0 | −36.17% |

- **L = 3** (D1, D2, D3 tavan; D4'te kapanış tavanın altında). Yarım gün, durdurma ve kayma yok; yedi yeni seansın hepsi `OK`.
- D4…D10 kapanışlarının hepsi o seansın THM alt limitine eşit (yedi ardışık taban kapanışı). Bu bir gözlemdir; SPEC_SCORING'de tanımlı bir hedef değildir ve hiçbir skora girmez.
- **Getiriler:** R₁ = +0.0995, R₃ = +0.3299, **R₅ = +0.0784**, **R₁₀ = −0.3617** (Decimal, ham metinden; `NETGL.csv`'de tam değerler).
- **y4 (D10 kapanışı arz fiyatının altında mı): evet.** 16.29 < 25.52; Y₁ = Y₃ = Y₅ = 1, **Y₁₀ = 0**. Kapanış ilk kez D6'da (24.78) arz fiyatının altına indi.

## 4. Dondurulmuş `ceiling_hazard_v0` tahmini ve gerçekleşen

**Kayıt zamanı:** NETGL için `ceiling_hazard_v0` kaydı (`20260922T121936Z_65a39d7392dd.json`) listeleme öncesi girdilerle üretildi (`inputs_pit_ok` = doğru) **ama D1'den sonra kaydedildi**: push kanıtı 2026-09-22T14:06:05Z, D1 = 2026-09-17. Bu yüzden sınıfı `LATE_RECORD`'dur; `n_live`'a girmez, canlı terazide `n_late` içindedir (SPEC_SCORING §5). Listeleme öncesi push'lu tek kayıt `v1_5_h99`'un eski kaydıdır (§5).

S_k = P(L ≥ k) (dondurulmuş), 1[L ≥ k] gerçekleşen, P_k = P(D_k tavan kapanışı):

| k | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| S_k | 0.818 | 0.705 | 0.608 | 0.406 | 0.271 | 0.181 | 0.121 | 0.081 | 0.054 | 0.036 |
| 1[L ≥ k] | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P_k | 0.818 | 0.710 | 0.614 | 0.415 | 0.375 | 0.298 | 0.247 | 0.212 | 0.189 | 0.174 |
| D_k tavan kapanışı | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

| Model (hepsi `LATE_RECORD`) | Medyan L | P(L ≥ 3) | P(L ≥ 5) | E[L] | Gerçekleşen L |
|---|---|---|---|---|---|
| `ceiling_hazard_v0` | **3** | **0.608** | **0.271** | 3.28 | 3 |
| `ceiling_hazard_v0@INF` | 4 | 0.671 | 0.426 | 4.35 | 3 |
| `pb_ceiling_v0` | 3 | 0.631 | 0.349 | 3.75 | 3 |
| `pb_ceiling_v0@INF` | 4 | 0.657 | 0.418 | 4.26 | 3 |

Medyan L = P(L ≤ l) ≥ 0.5 olan en küçük l (uygulamadaki tanım; P(L ≤ l) = 1 − S_{l+1}). E[L] = Σ S_k. `ceiling_hazard_v0@INF`, `pb_ceiling_v0` ve `pb_ceiling_v0@INF` kayıtlarında `pb_after_bookbuild_start` işareti 1'dir (PB girdileri planlanan yapıdır). Betimleme: gerçekleşen L = 3, `ceiling_hazard_v0`'ın medyanıyla aynı; P(L ≥ 3) olayı gerçekleşti, P(L ≥ 5) olayı gerçekleşmedi. n = 1; hüküm yok.

## 5. V1.5 getiri tahmini ve gerçekleşen

Kayıt: `NETGL_20260916_V1_5` (eski depo, git + push; push kanıtı 2026-09-16T11:32:27Z < D1; f3 = 2.84). Sınıf `LIVE` (`n_live` = 1). Çıktı: modelin getiri tahmini (`return`, Ridge) ve P(kapanış > arz). Görev metni "medyan getiri" diyordu; modelin çıktısı budur, skorlamada MAE ile ölçülür.

| Ufuk | V1.5 getiri tahmini | Gerçekleşen | \|hata\| | `base_train_median` (\|hata\|) | `base_zero` \|hata\| | V1.5 P(kapanış > arz) | Y | `base_rate` |
|---|---|---|---|---|---|---|---|---|
| D1 | +0.0770 | +0.0995 | 0.0226 | +0.1000 (0.0005) | 0.0995 | 0.913 | 1 | 0.899 |
| D3 | +0.1847 | +0.3299 | 0.1453 | +0.3297 (0.0003) | 0.3299 | 0.857 | 1 | 0.808 |
| **D5** | **+0.2552** | **+0.0784** | 0.1768 | +0.3738 (0.2955) | 0.0784 | 0.797 | 1 | 0.778 |
| **D10** | **+0.2583** | **−0.3617** | 0.6200 | +0.2471 (0.6088) | 0.3617 | 0.602 | 0 | 0.707 |

Betimleme: D5'te V1.5 getiriyi fazla, ama `base_train_median`'dan daha az fazla tahmin etti; D10'da üç referansın hepsi (V1.5, `base_train_median`, `base_zero`) yanlış işaretliydi ve V1.5 hatası `base_train_median`'dan hafifçe büyük. D10 için V1.5 P(kapanış > arz) = 0.602, gerçekleşen Y₁₀ = 0. Tek arz; sıralama ya da üstünlük iddiası yok.

## 6. Canlı sicilin yeni sayaçları

`scores/scores.json`, `as_of_session` = 2026-09-30. Terazi: **canlı (prospektif) = LIVE ∪ LATE_RECORD**; backtest terazisi bu görevde değişmedi (backtest blokları ve kartlar bayt-eşit); iki terazi toplanmaz. Her satırda n_rows = 7.

| Model | n_live | n_late | n_scored | n_refused | n_pending | n_partial_pending |
|---|---|---|---|---|---|---|
| `v1_5_h99` | 1 | 5 | 6 | 1 | 0 | 1 → 0 |
| `v1_6_h99`, `v1_5_market20_v0`, `ceiling_hazard_v0` | 0 | 6 | 6 | 1 | 0 | 1 → 0 |
| `base_*` (8 kural), `pb_v0`, `ceiling_hazard_v0@INF`, `pb_ceiling_v0`, `pb_ceiling_v0@INF` | 0 | 7 | 7 | 0 | 0 | 1 → 0 |

- Başka hiçbir sayaç değişmedi (sınıf ve satır sayıları aynı; `n_variants_same_data` aynı). `v1_5_h99` için `n_self_reported_scored` = 2 aynı.
- n = 7 < 10: `live.cells` boş, hiçbir canlı hücre/hüküm yok.
- NETGL için 11 model (v1 dört model, tavan yolu üç model, düşen arz dört model) `retro_info`'dadır (RETRO; kayıt dondurmadan sonra); canlı n'e girmezler. `post_d1_hazard_v0` de NETGL için RETRO'dur (`scores_post_d1.json`: yalnız `retro_info`; farkı yalnız `as_of_session`, girdi sha'sı ve kod/zaman damgası).
- `scores.json` farkı (848 yaprak): NETGL satırlarının `realized` ve `targets` alanları, `n_partial_pending`, NETGL'den türeyen `conditional.by_j` hücreleri, `outcomes` NETGL bloğu, `as_of_session`, `inputs.outcomes_sha256`, kod/zaman damgaları. `prediction`, `class`, `record_id`, `rules`, `backtest`, `card`, `definitions`, `retro_info`, `skipped` değişmedi (M24 kuralı testle zorlar).

## 7. Denetimler, testler ve sapmalar

**Ağ ve veri (adım 1–3):** D10 THB HEAD 200. `update --through 2026-09-30`: 14 zip, ilan dışı kapanış yok. Payda denetimi: `ok: true`, açıklanamayan yeni pay 0, `listed_not_seen` boş, yeni halka arz yok; `COMPLETENESS.csv` yalnız ekleme (+834 satır: 800 varant, 1 ETF, 33 temerrüt pazarı kodu; silinen satır yok).

**Kasa bekçisi (karar, M23):** yeni 33 temerrüt kodundan üçü (2026-09-24 ×1, 2026-09-25 ×2) mevcut payların temerrüt kodudur ve kasa üyesi kodlarıyla eşleşir; halka arz değildir. Görev "kasa bekçisi kırmızıysa DUR" diyordu; durdum. Orkestratör kararı ve proje sahibinin yazılı onayıyla T (`3b4d785`): COMPLETENESS istisnası iki kipli. Kapalı kipte pin 1 ve `OUT_OF_SCOPE` aynen; açık kipte (bugün) eşleşen her satır `first_seen` ≥ 2026-08-07 ve `ipos.csv`'de halka arz olarak geçmemeli, sayı pini yok. **Açık kipte eşleşen satır sayısı: 4** (HEAD'deki 1 + 3 temerrüt). Yazıcı değişmedi. Mutasyonlar kırmızı: `first_seen` < 2026-08-07, `ipos.csv`'de geçen kod, kapalı kipte yeni satır.

**İki içerik pini (karar, M24):** skorlar yeniden üretilince iki test, sonucu ilerleyen canlı terazi yüzünden kırmızı çıktı: `test_faz4_ceiling_path::test_scores_json_faz1_blocks_unchanged_since_f1f9d44` (f1f9d44 pini) ve `test_scoring::test_faz4_scores_json_existing_blocks_unchanged` (a0df5b7 pini). **Benim hatam:** ikincisi S öncesi koşuda da kırmızıydı, ama onu çalışma ağacı temizliği testi sandım (çıktıdaki "16 eksik model" ifadesini yanlış okudum) ve proje sahibinden onayı yalnız f1f9d44 pini için istedim; S sonrası temiz ağaçtaki koşuda yeniden kırmızı çıkınca fark ettim ve ikinci onayı ayrıca istedim. Bu yüzden GUARD3 ve düzeltme commit'i (`fd22be3`) ayrı. İkisi de proje sahibinin ayrı, yazılı onayıyla ortak bir genel kurala bağlandı (`faz1_progress_problems`, `cf5019c` ve `f61eb18`): model listesi, `prediction`/`class`/`record_id`/`rules`, backtest, kart, `separate_models`/`skipped`/`definitions`/`schema_version`, `records_sha256`, `outcomes`'ta aynı arzlar aynı sırada ve f1f9d44'te PENDING olmayan her ufuk aynen; yalnız PENDING → dolu, türev sayaçlar, `as_of_session` (geri gidemez) ve `outcomes_sha256` serbest. Yeni ticker kırmızı kalır. Mutasyon testi (`test_faz1_progress_rule_mutations`): bir `prediction` değeri, dolu bir ufuk (satır, `outcomes`, başka arz), `records_sha256`, eklenmiş ticker, geriye giden `as_of_session`, sabit sayaç, `definitions` → kırmızı; değişmemiş kopya ve serbest alanlar yeşil.

**Test sonuçları:**

| Koşu | Sonuç |
|---|---|
| Başlangıç, ara paralel (O yok, COMPLETENESS değişmiş) | 857 geçti, 7 kırmızı: 4 temizlik, 2 skor yeniden hesap, 1 kasa bekçisi (DUR nedeni) |
| O öncesi sıralı, 6 test adıyla deselect (4 temizlik + 2 skor yeniden hesap) | 859 geçti, 6 deselect, 0 kırmızı (16 dk 22 sn) |
| O sonrası paralel, deselect'siz | 863 geçti, tam olarak beklenen 2 skor testi kırmızı (11 dk 28 sn) |
| S öncesi sıralı, deselect'siz (skorlar commit'siz) | 861 geçti, 4 kırmızı: 2 temizlik (`test_faz7c_golden`, `test_faz7c_model`) + 2 içerik pini (f1f9d44 ve a0df5b7). İkincisi o sırada yanlışlıkla temizlik sayıldı (aşağıda); f1f9d44 pini M24'e yol açtı |
| S sonrası sıralı, deselect'siz | 865 geçti, 1 kırmızı: a0df5b7 pini (GUARD3'e yol açtı) (26 dk 51 sn) |
| S sonrası `bash app/scripts/test.sh` | yeşil: vitest 243, Rust tümü ok, parite pytest 6, `golden_unchanged` yeşil |
| S sonrası `gen_golden --check` | 30 dosya, fark yok |
| GUARD3 sonrası sıralı modül koşusu (`test_scoring`, `test_faz4_ceiling_path`, `test_outcome_guard`, `test_faz7_vault`, `test_guardrails`, `test_faz1b_guardrails`, `test_faz7c_model`, `test_faz7c_golden`, `test_faz5_post_d1`, `test_faz5_live`) | 244 geçti, 0 kırmızı (9 dk 58 sn) |

**Açık not (kapsam):** proje sahibinin kararıyla GUARD3 sonrasında tam pytest yeniden koşulmadı. Son tam sıralı koşu S sonrasıdır (865 geçti, 1 kırmızı); o kırmızı test ve yukarıdaki dokuz bekçi/hijyen/skor modülü GUARD3 sonrası yeşildir. GUARD3 yalnız `tests/test_scoring.py` ve `docs/SPEC_DEVIATIONS.md`'ye dokundu; uygulama tarafı (`test.sh`, `gen_golden`) S sonrası koşuldu ve bu iki dosyadan etkilenmez.

**Uygulama pini:** `test.sh` ve `gen_golden --check` yeşil olduğu için APPPIN commit'i gerekmedi.

**Sapmalar ve belirsizlikler:**
1. Görev adım 4'teki "O sonrası deselect'siz sıralı koşu yeşil" şartı O ile S arasında sağlanamaz (skor yeniden hesap testleri S'ye kadar kırmızıdır); orkestratör düzeltmesiyle sıra T → O → S → R oldu ve deselect'siz koşu S sonrasına alındı.
2. Görev metni adım 6'da "listeleme öncesi `ceiling_hazard_v0` tahmini" diyordu; kayıt D1'den sonra yazıldığı için `LATE_RECORD`'dur (§4).
3. V1.5 çıktısı "medyan" değil Ridge getiri tahminidir (§5).
4. a0df5b7 pini yanlış sınıflandırıldı (yukarıda): bu yüzden M24 onayı iki aşamada alındı ve `docs/SPEC_DEVIATIONS.md`'deki o cümle ayrı bir belge commit'iyle düzeltildi (`fd22be3`).
5. `tests/` ve `docs/SPEC_DEVIATIONS.md` bu görevde üç ayrı yazılı onayla değişti (T, M24, M24 devamı); `borsai/`, `models/`, `registry/`, `legacy/`, `docs/specs*`, `scores/scores_oot.json` ve `docs/SCORES_OOT.md` değişmedi. Hiçbir model, kod ya da şartname değişmedi.

## 8. Push bloğu

Sonuç satırları sıra iddiası taşır; kanıt gerekir. Yerelde `origin/main`'in önünde 7 commit var (T, O, M24, S, GUARD3, M24 notu, R). Sıra kuralının zaman kanıtı O'nundur:

```
cd ~/Desktop/BorsAi
git push origin main
.venv/bin/python -m borsai.push_proof c1eb7ae
git add registry/push_proofs
git commit -m "BORSAI_PUSH_PROOFS: NETGL D4-D10 outcomes (c1eb7ae)" -- registry/push_proofs
git push origin main
git --no-pager log --oneline -3 origin/main
```

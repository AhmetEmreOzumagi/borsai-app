# POST_D1 akışı: D1 akşamı → D2 09:40 (canlı `post_d1_hazard_v0`)

Tanım: `docs/specs_faz5/SPEC_POST_D1_V0.md` §7; kararlar `docs/SPEC_DEVIATIONS.md` H28–H47; CLAUDE.md kural 1 (POST_D1
cümlesi). Bu belge bir sonraki arzın görevine kopyalanmak üzere yazıldı (orkestratör). Komutlar repo kökünde, `.venv` ile.

## 0. Ön koşullar (arzdan önce, bir kez)

| Ne | Denetim | Kimde |
|---|---|---|
| `post_d1_hazard_v0` dondurulmuş ve push kanıtlı | `models/INDEX_POST_D1.json` listeler; `registry/push_proofs/7c18c0f58ed1b686d3580165eef70b0e71640e26.json` var (2026-09-24T14:13:55Z) | tamam |
| Arz `registry/ipos.csv`'de `FROZEN` ve listeleme öncesi kaydı var | `registry/records/<T>/…json`; kayıtta resmi f3 (`total_demand_multiple`) dolu olmalı (yoksa POST_D1 yok, aşağıda E) | Claude, listeleme öncesi akış |
| Listeleme öncesi kayıt D_1'den önce push kanıtlı | `registry/push_proofs/` kaydı kapsıyor (base_record LIVE ve `inputs_pit_ok` için) | proje sahibi |
| D_1 takvim içinde ve D_1'den sonra resmi seans var | takvim 2026-12-31'de biter: D_1 = 2026-12-31 ya da sonrası → `CALENDAR_NOT_AVAILABLE` (aşağıda G) | Claude |
| Çalışma ağacında `models/`, `registry/records/`, `registry/post_d1/` temiz ve commit'li | `git status --porcelain -- models registry/records registry/post_d1` boş (yoksa `outcomes update` `SequenceRuleError` verir) | Claude |

## 1. Zaman çizelgesi (D_1 = ilk işlem günü; T_open = D_1'i izleyen ilk resmi seans 09:40:00 Europe/Istanbul)

| Adım | Ne zaman | Kim | Komut | Beklenen çıktı / denetim |
|---|---|---|---|---|
| 1 | D_1 akşamı, THB yayımından sonra (ölçülen 18:25–18:40; D_1 THM'si aynı sabah ~08:00) | Claude | `.venv/bin/python -m borsai.outcomes update --through <D_1>` | `through_session` = D_1; `data/outcomes/<T>.csv` h = 1 `OK` (ya da `NA_LIMIT`), h ≥ 2 `PENDING`; yalnız D_1 (ve eksik önceki) bültenler iner |
| 2 | hemen | Claude | `git add data/raw/bist data/outcomes` sonra `git commit -m "BORSAI_OUTCOMES: <T> D_1 bülteni (<D_1>)" -- data/raw/bist data/outcomes` | D_1 bülteni ve h = 1 sonucu commit'li (listeleme öncesi modellerin sonuç girişi budur) |
| 3 | hemen | Claude | `.venv/bin/python -m borsai.freeze --post-d1 <T>` | JSON: `path` (`registry/post_d1/<T>/<UTC>_<sha>.json`), `d1`, `ceiling_close_D1`, `summary`, `T_open`, `note` ("T_open'dan ÖNCE …"). `ceiling_close_D1 = 1` ve `summary.n_predicted = 1` beklenir |
| 4 | hemen | Claude | `git add registry/post_d1/<T>` sonra `git commit -m "BORSAI_POST_D1_RECORD: <T> (D_1 <D_1>, T_open <T_open>)" -- registry/post_d1/<T>` | kayıt commit'li; `git status --porcelain -- registry/post_d1` boş |
| 5 | **T_open'dan önce** (hedef: D_1 akşamı) | **proje sahibi** | `git push` sonra `.venv/bin/python -m borsai.push_proof <adım 4 commit'i>` | `registry/push_proofs/<sha>.json`, `created_at` < T_open (UTC; T_open 06:40:00Z). Kanıtın ZAMANI POST anıdır: `push_proof` 09:40'tan önce koşmalı; kanıt dosyasının commit'i sonra olabilir |
| 6 | adım 5'ten sonra | proje sahibi (ya da Claude, commit) | `git add registry/push_proofs` sonra `git commit -m "BORSAI_PUSH_PROOFS: POST_D1 <T>" -- registry/push_proofs`; `git push` | kanıt repoda |
| 7 | D2 akşamı ve sonraki seanslar | Claude | `.venv/bin/python -m borsai.outcomes update` → commit (adım 2 gibi) | h = 2.. satırları dolar; `registry/post_d1/` commit'li olmadan indirme durur (L7) |
| 8 | sonuç girdikçe (D_10'a kadar, en çok 15 seans) | Claude | `.venv/bin/python -m borsai.scoring` → `git commit … -- scores docs/SCORES.md` | `scores/scores_post_d1.json`: arz `denominator` satırı `RECORD`, satır `class` = LIVE (kanıt < T_open) ya da LATE_RECORD; D2..D10 hepsi girince `status = SCORED`. n < 10: metrik yok, yalnız satır |

Denetim komutları (adım 5'ten sonra, isteğe bağlı): `.venv/bin/pytest -q tests/test_outcome_guard.py tests/test_faz5_live.py`.
Sınıfın ölçütü yalnız git DAG'ı ve push kanıtıdır; kaydın içindeki `recorded_at_*` yerel saattir, kanıt değildir.

## 2. Başarısızlık hâlleri

| # | Durum | Nasıl görünür | Ne olur / ne yapılır |
|---|---|---|---|
| A | **D1 tavan kapatmadı** (`ceiling_close_D1 = 0`) | adım 3 çıktısı `ceiling_close_D1: 0`, `summary.n_not_applicable = 1` | Model kapsam dışı (§1.2). Kayıt isteğe bağlıdır: yazılırsa hücre `NOT_APPLICABLE` (ret değil). Payda satırı kayıttan bağımsız `NOT_APPLICABLE`; hiçbir n'e girmez. Push gerekmez; yazıldıysa commit'li kalmalı (L7). |
| B | **D1 işlem görmedi** (tam gün durdurma; THB'de satır yok ya da sözleşme 0) | adım 1'de h = 1 `PENDING`; adım 3 `D1NotAvailable: D1_NOT_TRADED` | Kayıt YAZILMAZ. D_1 kayar (SPEC_SCORING §2): payın işlem gördüğü ilk seansın akşamı adım 1'den tekrar; T_open o gerçek D_1'e göre hesaplanır. |
| C | **Üst limit yok** (D_1 THM satırı yok ya da limit boş/≤ 0) | h = 1 `NA_LIMIT`; adım 3 `ceiling_close_D1: null`, hücre `REFUSED` (`D1_LIMIT_NA`) | Kayıt yazılabilir (ret görünür); payda `NOT_SCORABLE_D1_LABEL_NA`. THM'yi elle inceleyin (tahmin edilmez). |
| D | **Hacim/fiyat alanı tutarsız** | hücre `REFUSED` `D1_VOLUME_INVALID` / `D1_FIELD_INVALID` | Kayıt yazılır (ret nedeni kayıtta); bülten satırı elle incelenir; model düzeyi ret atlama değildir (`n_refused`). |
| E | **`base_record` yok** (listeleme öncesi `ceiling_hazard_v0` kaydı yok ya da resmi f3 yok, ör. VEYAS gibi) | adım 3 `NoBaseRecord: SKIPPED_POST_D1: NO_PRE_LISTING_RECORD` | Kayıt YAZILMAZ; payda satırı `SKIPPED_POST_D1: NO_PRE_LISTING_RECORD`. PB tabanlı varyant ayrı model_id'dir (§13 açık soru 2, henüz yok). |
| F | **T_open geçti** (push ya da `push_proof` 09:40'tan sonra) | adım 3 `note`: "T_open GEÇTİ"; kanıt `created_at` ≥ T_open | Kayıt yine yazılır ve push edilir: model prospektif ve `inputs_pit_ok_post_d1` ise `LATE_RECORD` (canlı teraziye `n_late` olarak girer), değilse RETRO. D2 bülteni kayıttan önce commit edilmemeli (bekçi zaten engeller). |
| G | **Takvim sonu** (D_1 ≥ 2026-12-31) | adım 3 `CalendarNotAvailable: CALENDAR_NOT_AVAILABLE` | Kayıt YAZILMAZ; önce resmi takvim uzatması (Faz 2A kalıbı, ayrı görev); payda `CALENDAR_NOT_AVAILABLE`. |
| H | **D2_cal ilan dışı kapanış** (D_1'i izleyen hafta içi gün bülten yayımlanmadı) | `outcomes update` `unannounced_closures` listesi | Sınır aynı kural (H32): T_open, kapanış düşülmüş takvimde bir sonraki resmi seansın 09:40'ı. Yine de hedef ilk 09:40'tır. |
| I | **Hatalı kayıt** (yanlış bülten, yeniden indirme) | — | T_open'dan ÖNCE: `.venv/bin/python -m borsai.freeze --cancel registry/post_d1/<T>/<dosya> --reason "<neden>"` (aynı dizine iptal kaydı), sonra yeni kayıt, ikisi de commit + push. T_open'dan itibaren iptal yapılamaz (hata). Aynı base_record + aynı iki bülten + aynı model dizini ikinci kez → `DUPLICATE_RECORD`. |
| J | **`SequenceRuleError`** (adım 1 ya da 7) | "model/kayıt dosyaları commit edilmemiş" | `git status -- models registry/records registry/post_d1`: commit'lenmemiş kayıt varsa önce commit (adım 4), sonra tekrar. |
| K | **Push kanıtı üretilemiyor** (`SKIPPED_NO_AUTH`) | `push_proof` çıkış 2 | Yalnız proje sahibi üretebilir (gh / GH_TOKEN); 09:40'tan önce üretilemezse F. |

## 3. Ne olmaz

- D2'nin THM'si (D1 kapanışından deterministik) kayda alınmaz; kayıt yalnız D_1 tarihli THB+THM taşır (bekçi: `registry.post_d1_record_problems`).
- POST_Dj (j ≥ 2) kaydı yok (karar 1-4: canlı n ≥ 10 olmadan açılmaz).
- Uygulama (`app/`) bu akışta değişmez; POST_D1 kaydını EK 3'te okuyacak.
- `scores/scores.json` yapısı değişmez; POST_D1 skorları `scores/scores_post_d1.json` ve `docs/SCORES.md` §7.

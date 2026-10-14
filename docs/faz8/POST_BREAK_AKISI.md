# POST_BREAK akışı: kırılma akşamı (canlı `break_floor_v0`, makine sıralı)

Tanım: `docs/specs_faz8/SPEC_BREAK_V0.md` §9; kararlar `docs/SPEC_DEVIATIONS.md` N26–N33; CLAUDE.md kural 1 (POST_BREAK cümlesi).
Komutlar repo kökünde, `.venv` ile. Bu aşamada **akşam iş yükü yoktur**: kayıt insan tarafından yazılmaz, push kanıtı gerekmez.

## 0. Ön koşullar (bir kez; bugün tamam)

| Ne | Denetim |
|---|---|
| `break_floor_v0` ve `break_floor_v0@ZERO` donmuş ve push kanıtlı | `models/INDEX_POST_BREAK.json`; `registry/push_proofs/4d3c9a26be65ee4b3b8f204945f36cdae7eedd5a.json` (2026-10-02T14:45:08Z) |
| Arz `registry/ipos.csv`'de `FROZEN` ve `registry/inputs/<T>.json` var | `shares_offered` kaynağı D_1'den önce yayımlanmış (değilse satır RETRO) |
| Takvim D_b'den sonra en az bir resmi seans içeriyor | takvim 2026-12-31'de biter (D_b = 2026-12-31 → `CALENDAR_NOT_AVAILABLE`) |

## 1. Ne zaman, hangi komut, ne commit'lenir

| Adım | Ne zaman | Kim | Komut | Commit |
|---|---|---|---|---|
| 1 | Her seans akşamı sonuçlar güncellenirken (listeleme öncesi akışın parçası) | Claude | `.venv/bin/python -m borsai.outcomes update` | `data/raw/bist`, `data/outcomes` (bugünkü sonuç commit'i) |
| 2 | `outcomes update` commit'inden sonra, istenen zamanda (kırılma akşamı ya da sonrası; acele yok) | Claude | `.venv/bin/python -m borsai.scoring --break` | `git add registry/post_break scores/scores_break.json docs/SCORES_BREAK.md` sonra `git commit -m "BORSAI_POST_BREAK: <T> makine kaydı ve skor (D_b <tarih>)" -- registry/post_break scores/scores_break.json docs/SCORES_BREAK.md` |
| 3 | sonraki push'la birlikte | proje sahibi | `git push` | push kanıtı **gerekmez** (makine kaydının sınıfı yazılma zamanına bağlı değildir; K-LB-10) |

`--break` sırayla: (i) ipos.csv'de `FROZEN` olup kırılma akşamı (b ∈ 1..9) oluşmuş, D_1..D_b bültenleri pinli, girdisi ve takvimi olan
her arz için eksik makine kaydını `registry/post_break/<T>/machine_<UTC>_<kısa-sha>.json` olarak yazar (aynı model dizini + aynı
bültenler + aynı girdi dosyasıyla kayıt varsa yazmaz); (ii) `scores/scores_break.json`; (iii) yazılmış JSON'dan `docs/SCORES_BREAK.md`.
İkinci kez koşmak güvenlidir (0 yeni kayıt; JSON'da yalnız `generated_at_utc` değişir).

Sınıf tarihlerden hesaplanır: model JSON'u (commit `4d3c9a2`), D_b'den sonraki ilk bülteni ya da h ≥ b + 1 sonucunu repoya sokan
commit'in atası ve push kanıtlı ise satır `MACHINE_SEQUENCED`'dir (ölçek `live_break`; LIVE ile toplanmaz). Bu yüzden 1. adımın sonuç
commit'i, modelin push'undan sonra gelen her yeni arzda kendiliğinden prospektiftir.

## 2. Skor dosyasında ne görülür

| Arzın durumu | `denominator` | n |
|---|---|---|
| Seri sürüyor (D_{L+1} henüz yok) | `STREAK_PENDING` | yok |
| L = 10 (seri hiç bozulmadı) / b = 10 | `NOT_APPLICABLE_NO_BREAK` / `NOT_APPLICABLE_B10` | yok |
| Seride üst limit NA | `NOT_SCORABLE_STREAK_NA` | yok |
| D_1..D_b bülteni pinli değil / girdi yok / takvim yok | `BULLETIN_NOT_PINNED` / `INPUTS_NOT_AVAILABLE` / `CALENDAR_NOT_AVAILABLE` (kayıt yazılmaz; `outcomes update` ya da ön koşul sonra tekrar) | yok |
| Kırılma akşamı oldu, D_{b+1} bekleniyor | `RECORD`, satır `PENDING` | yok |
| D_{b+1} geldi | `RECORD`, satır `SCORED` (F2 için D_{b+2}; b = 9'da F2 yok) | `n_scored` (`n_machine`) |
| Model prospektif değil (sonuç modelden önce) | `RETRO` (yalnız `retro_info`) | yok |

Dil: n_scored < 10 yalnız satır tablosu; 10 ≤ n < 30 "yetersiz örnek"; "geçiyor" yalnız n ≥ 30 ve aralık 0'ın altında (birincil
ürün hücresi ve `@ZERO` hücresi birlikte). Kartın öne çıkan durumu n < 30 iken "ön eleme (yakın dönem backtest'i, tasarıma maruz);
canlı n = k".

## 3. Ne olmaz

- İnsan kaydı (gece kaydı, LIVE yolu) v0'da yok; ileride aynı model_id ile eklenebilir (§9.1 b).
- Makine kaydı iptal edilmez, yeniden yazılmaz (append-only); kod değişirse yeni kayıt yazılmaz, skorlama tahmini bellekte yeniden
  üretip kayıtla karşılaştırır (|Δ| > 1e-12 → hata).
- Bugünkü 7 arzın (CITAS, TKNKA, VEYAS, KPEKS, INTET, BKRGY, NETGL) hepsi RETRO'dur; kayıtları bilgi satırı içindir.
- `PRODUCT_BREAK_FLOOR` yalnız listeleme öncesi kaydı `ceiling_path_v0` (ya da `@INF`) taşıyan arzlarda vardır (yeni arzların kaydı 27
  modeli taşır); bugünkü 7 kayıtta yok (`NOT_AVAILABLE`).
- `app/` bu akışta değişmez; `scores_break.json`'ı EK 5 okuyacak.

# Sentetik `scores.json` fixture'ları (SPEC_APP §5.3, EK 2 §5)

Kaynak: `docs/app/ekler/scores_n7_sentetik.json`, `scores_n12_sentetik.json`,
`scores_n35_sentetik.json`. Buradaki kopyalarda **alan adları gerçek şemaya uyarlandı**
(`borsai.scores/1` + `docs/SPEC_DEVIATIONS.md` satır 83'ün eklediği alanlar); **kurallar, sayılar ve
hüküm metinleri değişmedi**. Uyarlamalar:

- `primary_cell.rule_id` → `primary_cell.rule_ids[]`
- hücrelere `scale`, `label` ("birincil"/"keşif"), `n_blocks`, backtest'te `bootstrap`
- satırlarda `realized.{R,Y,L,L_status}` (gerçek dosyadaki biçim), `rules[<id>].values`,
  `class_evidence` (zaman kanıtı sütunu buradan okunur), `d1_basis`, `record_source`,
  `selection_rule`, `targets`, `inputs_pit_problems`
- canlı blokta `n_rows`, `n_partial_pending`, `scale`, `descriptive`, `n_self_reported_scored`,
  `self_reported_cells`, `invalid_use_rows`, `cancelled_records`

SNTxx / LGCxx / CNDxx arzları **gerçek değildir**; dosyalar `synthetic: true` taşır.

| Dosya | Ne için |
|---|---|
| `n7.json` | n < 10 (yalnız satır tablosu; U16). Ek alanlar: `invalid_use_rows` (1), `cancelled_records` (1), bir `REFUSED` satır |
| `n7_accuracy_rule_null.json` | U20: `metric = accuracy` hücresinin `rule_value`'su null → satır gizlenir |
| `n12.json` | 10 ≤ n < 30 ("yetersiz örnek"; U17). Ek: `self_reported_rows` (2), `retro_info` (3), `separate_models` (1) — U26 |
| `n35.json` | n ≥ 30 (hüküm ve renk; U18). Ek: `live.descriptive` (2; SPEC_DEVIATIONS E13) |
| `conditional.json` | EK 2 §5 `models[].conditional`: j = 1 (n = 4, satır tablosu), j = 3 (n = 12, "yetersiz örnek") — U51 |
| `conditional_bad_version.json` | Koşullu blok sürümü desteklenmiyor → blok gösterilmez, mesaj yazılır (U51) |
| `bad_schema_version.json` | §2.5: `borsai.scores/2` → panel kapalı, kısmi gösterim yok (U35) |
| `bad_live_cells.json` | §2.3 ihlali (n_scored = 7 iken canlı hücre): panel yerine kural metni (U24, ekran görüntüsü 30) |
| `post_d1_n12.json` | EK 3 §6.5 / U70: `borsai.scores_post_d1/1`, `conditional_j1` n = 12 ("yetersiz örnek", renk yok); SNTPxx kurgusal |
| `post_d1_n35.json` | U70: n = 35 (n_live 30, n_late 5): birincil "geçiyor", kural "geçemiyor" / "ayırt edilemiyor" (renk yalnız ilk ikisinde) |
| `post_d1_bad_cells.json` | U70 fail-closed: n = 8 iken hücre → `CONDITIONAL_CELLS_BELOW_MIN_N`, bölüm kapalı |

`post_d1_*` dosyaları gerçek `scores/scores_post_d1.json`'ın yapısından (kart, tanımlar, girdi sha'ları) kopyalanıp sayaçları,
hücreleri, satırları ve paydası kurgusal SNTPxx arzlarıyla değiştirildi; `retro_info` boş, `synthetic: true`. Görünümler
`app/src-tauri/tests/stage4.rs: scores_post_d1_reader` ile `app/tests/fixtures/ui/scores_post_d1_views.json`'a yazılır.

Öteki bütünlük ihlalleri için diskte dosya yoktur: `app/src-tauri/tests/stage4.rs` bu dosyaların
kopyalarını bellekte bozar ve görünümleri `app/tests/fixtures/ui/scores_views.json`'a yazar
(`doc_file: null`, çünkü fail-closed davranışta belge gösterilmez).

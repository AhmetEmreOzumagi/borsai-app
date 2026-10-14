# TASK_ID: BORSAI_FAZ4_CEILING_PATH_IMPL_20260922

Model: Opus 5 · Extra. Çalışma klasörü ~/Desktop/BorsAi; ek dizin gerekmez. Ağ gerekmez. push/tag/amend yok.

## Bağlam

- Fable'ın tavan yolu şartnamesi `docs/specs_faz4/SPEC_CEILING_PATH_V0.md` (ekleri: `docs/specs_faz4/ekler/`). Uygulamadan önce commit edilip push edildi. Beklentileri §6'da, sonuç görülmeden yazıldı.
- Kurulacak üç yeni model:
  - `ceiling_path_v0`: ana model
  - `ceiling_path_v0@INF`: sıfır model, MECHANICS_BASE
  - `pb_ceiling_path_v0`: PB varyantı
- Seri bileşeni dondurulmuş tavan modellerinden aynen alınır. Yeni hazard fit edilmez.
- Faz 2B bitti (e469a93 tanımlar, f1f9d44 sonuçlar). 2026-08-06 sonrası 7 arzın sonucu repoda. Yeni modeller bu 7 arz için RETRO'dur, bu normal. Amaç, bir sonraki arzı canlı yakalamak için hızla ve doğru dondurmak.
- Proje sahibinin açık sorulara kararları (şartname §11): beş öneri de KABUL.
  1. D1 baz fiyat yuvarlaması HALF_UP.
  2. Marj sabiti 0.10; rejim değişirse yeni model_id.
  3. Hücre evreni 99 arz.
  4. Birincil hücre: D5 MAE, `base_train_median`'a karşı.
  5. Kırılma sonrası izleme v0'da yok.
- Paralel oturum: masaüstü uygulaması aşama 0–1 (`docs/prompts/FAZ3_APP_STAGE01.md`). Yalnız `app/` altına yazıyor ve kendi commit'ini atıyor. Sen `app/`'e dokunma.

ÖNCE OKU:
- CLAUDE.md
- docs/specs_faz4/SPEC_CEILING_PATH_V0.md (tamamı, bağlayıcı) ve `ekler/`
- docs/specs/SPEC_CEILING_V0.md, SPEC_SCORING.md, SPEC_PB_V0.md
- docs/SPEC_DEVIATIONS.md
- docs/prompts/FAZ1B_NEW_MODELS.md: aynı iş akışı, kalıp olarak.
- borsai/: predict_hazard.py, survival.py, freeze.py, backtest.py, report_faz1b.py, specs.py, scoring.py (`prediction_of_cell`)
- tests/reference/macos_golden_faz1b/

## Adımlar

**0. Başlangıç**
- `git log --oneline -3` ve `git status --porcelain` çıktısını al.
- `.venv/bin/pytest -q` tam koşusunu yap; test sayısını ve süreyi yaz. Kırmızı test varsa DUR.

**1. Tarama bekçisi**
- Paralel uygulama oturumu `app/node_modules`, `app/src-tauri/target` ve `app/dist` üretecek. Bu dizinler `app/.gitignore`'da olacak, repo içeriği değiller.
- `tests/test_outcome_guard.py`'deki tam repo taramasının `SKIP_DIRS` kümesine `node_modules`, `target` ve `dist` ekle. Bu testte başka değişiklik yok.
- Aynı tür bir tam repo taraması başka bir testte de varsa aynısını yap ve raporla.

**2. Uygulama.** Şartnameyi DEĞİŞTİRME.
- `borsai/predict_path.py`: yalnız stdlib + `predict_hazard`/`features`/`survival`.
- `model_kind`'a `ceiling_path` türünü ekle.
- Limit yolu, hücreler, havuzlama merdiveni, karışım, medyan/p_up/kuantiller: şartname §2–§4 ve §12.
- Koşullu güncelleme fonksiyonları (§7, durum 1 ve 2): saf ve test edilmiş. Uygulama da bunları kullanacak.

**3. Backtest** (§8)
- S_k tavan ledger'larından yeniden kullanılır; yeniden fit yok.
- Hücreler her fold'da walk-forward kurulur.
- Deney günlüğüne yazılır.
- Altın ledger'lar `tests/reference/macos_golden_faz4/` altına.

**4. `docs/MODELS.md`'ye Faz 4 bölümü** (üretilmiş rapor; mevcut bölümlere dokunma)
- Şartname §5'teki bütün hücreler: fark, %95 aralık ve n.
- Birincil hücre ayrıca vurgulanır.
- §6 beklenti tablosu ile gerçekleşen, satır satır yan yana: "tuttu" / "tutmadı" / "daha iyi" / "daha kötü".
- Başarısızlık tanımları (a)–(d) tek tek.
- §7'nin H99 koşullu (keşif) tablosu.

**5. "Beklentiden çok iyi" denetimi** (§6 tanımı)
- Tetiklenirse DONDURMA. Raporda açıkça yaz; proje sahibi Fable'la sıfırdan yeniden üretim başlatacak.
- Tetiklenmezse devam et.

**6. Dondurma** (§8 son madde)
- Hücreler 99 arzın tamamından kurulur, kesim 2026-08-19.
- Seri modeli JSON'ları gömülü.
- `models/INDEX.json`'a sona eklenir.
- Davranış değiştiren bir sapma gerekirse o modeli dondurma; `docs/SPEC_DEVIATIONS.md`'ye yaz ve raporla.

**7. Kayıt ve skor uyumu** (§9-13)
- `freeze.build_record` yeni modeller için hücre üretir. Bir sonraki arzın kaydı 19 modelin hepsini içerecek.
- `scoring`'de yalnız yeni türün okunması eklenir.
- `python -m borsai.scoring` yeniden koşar. Ardından `scores/scores.json` ve `docs/SCORES.md` güncellenir.
- Mevcut 16 modelin blokları f1f9d44'teki hâliyle aynı kalmalı. Üretim zamanı ve kod sha'sı gibi alanlar hariç; bunu bir test sınar.
- Yeni modeller bu 7 arz için RETRO'dur: `retro_info`'da görünürler, canlı n'e girmezler.
- `registry/` altına hiçbir şey yazılmaz. Bu 7 arz için yeni model kaydı YAZILMAZ.

**8. Testler:** şartname §9'daki 13 kabul testinin hepsi. Faz 1A/1B bekçileri ve Faz 2B testleri yeşil kalmalı.

## Kurallar
- DEĞİŞMEZ: `docs/specs/`, `docs/specs_faz4/`, `models/` altındaki mevcut 16 model dosyası ve INDEX'in ilk 16 kaydı, `tests/reference/` altındaki mevcut dosyalar, `legacy/`, `registry/`, `data/`.
- Faz 2B tanımları değişmez: `borsai/outcomes.py`, ve `borsai/scoring.py`'deki mevcut metrik/sınıf/birincil kayıt kodu. `scoring`'e yalnız yeni türün okunması eklenir.
- `app/`'e dokunma.
- Testi gevşetme. Kök nedeni bul; gerekirse DUR.
- Rapor Türkçe.

## Commit
- Tek commit. Mesaj: `BORSAI_FAZ4: ceiling path models (main, MECHANICS_BASE, PB) implemented per Fable spec, backtested and frozen`
- Paralel oturum yüzünden commit YALNIZ kendi yollarınla atılır:
  ```
  git add <yollar>
  git commit -m "<mesaj>" -- <aynı yollar>
  ```
  Yollar:
  - `borsai/`
  - `tests/`
  - `models/`
  - `experiments/log.jsonl`
  - `docs/MODELS.md`
  - `docs/SPEC_DEVIATIONS.md`
  - `scores/`
  - `docs/SCORES.md`
  - `docs/prompts/FAZ4_CEILING_PATH_IMPL.md`
- `git add -A` YOK.
- `index.lock` hatası alırsan 10 saniye bekle ve yeniden dene. Kilit dosyasını SİLME.
- Push yok.

## Teslim (rapor)
- Commit hash'i ve `git show --stat`.
- Başlangıç ve son tam test koşusu: sayı ve süre.
- §9'daki 13 testin sonuçları.
- MODELS.md Faz 4 tablosu: birincil hücre ve §6 beklenti karşılaştırması.
- "Beklentiden çok iyi" denetiminin sonucu.
- Başarısızlık tanımları (a)–(d).
- Dondurulan modellerin sha'ları.
- `scores.json` değişmezlik testi.
- Sapmalar ve kararlar.

## Kabul kapısı
- K1 13 kabul testi yeşil; eski testler yeşil.
- K2 Mevcut 16 modelin dosyaları, altın ledger'ları ve `scores.json` blokları değişmedi.
- K3 Beklenti karşılaştırması satır satır yazılı; "çok iyi" tetiklendiyse dondurma yok.
- K4 Commit yalnız izinli yollarda; push yok.

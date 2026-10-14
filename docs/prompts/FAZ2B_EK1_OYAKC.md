# EK 1: BORSAI_FAZ2B_OUTCOMES_SCORING_20260922. Tamlık durağı kararı (orkestratör + proje sahibi, 2026-09-22)

## Durum
Tamlık denetimi `OYAKC.TE` (ilk görülme 2026-09-21) için `ACIKLANAMAYAN_YENI_PAY` verdi ve görev kuralı gereği durdu. Doğru davranış.

## Karar: halka arz DEĞİL
2026-09-21 THB'sinde:
- `OYAKC.TE` satırı: PAZAR = `BUYIN`, ENSTRUMAN TIPI = `BUYINEQT`, adı "OYAK CIMENTO -TEMERR".
- Aynı gün `OYAKC.E` normal pay olarak işlem görüyor (MSPOT, BIST 100 üyesi).

Yani bu satır var olan bir payın temerrüt (buy-in) işlem kodu. `registry/ipos.csv`'ye satır eklenmez; `registry/` değişmez.

## Yapılacak
1. `borsai/outcomes.py` tamlık sınıflandırıcısına GENEL bir kural ekle; yalnız OYAKC'ye özel olmasın. Koşul: PAZAR `BUYIN` ya da enstrüman tipi `BUYIN` ile başlıyor. Sonuç: sınıf `TEMERRUT_PAZARI`, neden "var olan payın temerrüt işlem kodu; halka arz değil".
   - Başka hiçbir fonksiyona dokunma. `resolve_sessions`, `ceiling_label`, sonuç dosyası üretimi ve `borsai/scoring.py` e469a93'teki hâliyle kalır.
2. Kuralı sentetik bir satırla test et (`tests/test_outcomes.py`). `docs/SPEC_DEVIATIONS.md`'ye bir satır ekle.
3. Sırayla çalıştır: tamlık denetimi, `python -m borsai.outcomes update`, `python -m borsai.scoring`, tam test koşusu.
4. Görev dosyasındaki COMMIT B'yi at. Mesaj değişmez. Yollar:
   - görevdeki yollar
   - `borsai/outcomes.py`
   - `tests/test_outcomes.py`
   - `docs/SPEC_DEVIATIONS.md`
   - `docs/prompts/FAZ2B_EK1_OYAKC.md`

   Başka bir oturumun dosyalarını commit'e EKLEME: `docs/app/`, `docs/specs_faz4/`, `docs/prompts/FAZ3_*`, `docs/prompts/FAZ4_*`.

## Raporda
- `git diff e469a93 HEAD -- borsai/`: değişiklik yalnız sınıflandırıcıda olmalı.
- `scores/scores.json` ve `docs/SCORES.md` durak öncesi üretimle karşılaştırılır. Tamlık bölümü dışında değişen alan varsa listele.
- Tamlık denetiminde `ACIKLANAMAYAN_YENI_PAY` sayısı 0 olmalı.
- Test sayısı ve süre.

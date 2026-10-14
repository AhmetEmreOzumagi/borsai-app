# TASK_ID: BORSAI_FAZ1B_NEW_MODELS_20260921

Model: Opus 5, akıl yürütme yüksek/Extra. Çalışma klasörü ~/Desktop/BorsAi (ek dizin ~/Desktop/Halka_Arz_Modeli arşivi, salt okunur). Ağ yok. push/tag/amend yok.

## Bağlam

Faz 1A tamam (commit 5fa849d): çekirdek paket, V1.5 portu, toleranslı kabul testleri, dondurulmuş `v1_5_h99` ve basit kurallar.
Fable yeni modellerin şartnamelerini yazdı: docs/specs/ (commit edilmiş hâlde). Bu task o şartnameleri koda döker, her modeli backtest'ten geçirir ve dondurur.

**Neden şimdi:** CLAUDE.md sıra kuralı. Bu modellerin JSON'ları, 2026-08-19 sonrası THB/THM verisi repoya girmeden ÖNCE dondurulup push edilecek. Böylece 2026-08-06 sonrası listelenen 7 arz bu modeller için gerçek prospektif örneklem olur.

ÖNCE OKU: CLAUDE.md; docs/specs/SPEC_CEILING_V0.md, SPEC_PB_V0.md, SPEC_MARKET20_V0.md, SPEC_V1_6.md (tamamı); SPEC_SCORING.md (yalnız tanımlar için; skorlama kodu bu task'ta YOK); docs/MODELS.md; borsai/ paketinin mevcut hali.

## İş

Şartnamelerdeki modelleri AYNEN uygula:

| model_id | Şartname |
|---|---|
| `ceiling_hazard_v0` | SPEC_CEILING_V0 |
| `pb_v0`, `pb_ceiling_v0` | SPEC_PB_V0 |
| `v1_5_market20_v0` | SPEC_MARKET20_V0 |
| `v1_6_h99` | SPEC_V1_6 |

Her model için:
1. `fit` (sklearn kullanabilir) ve `predict` (yalnız Python stdlib; mevcut `borsai/predict.py` deseniyle). Şartnamedeki ret ve uyarı kuralları `predict`'e girer.
2. Şartnamedeki walk-forward planıyla backtest. Her koşu `experiments/log.jsonl`'a otomatik yazılır.
3. Şartnamedeki basit kurallar (tavan için son-10 ve genişleyen Kaplan–Meier taban oranları dahil) aynı fold'larda, aynı şemada kayıtlı modeller olarak eklenir.
4. Şartnamedeki kabul testlerinin HEPSİ `tests/` altına yazılır ve yeşil olur.
5. Model, 99 arzın hepsiyle (şartnamede başka kesim yazıyorsa o) fit edilip `models/<model_id>.json` olarak dondurulur. `models/INDEX.json` güncellenir.

`docs/MODELS.md` `python -m borsai.report` ile yeniden üretilir:
- Yeni modellerin eşleşik fark tabloları (fark + blok bootstrap %95 aralığı + n).
- Tavan modeli için şartnamenin birincil metriği (RPS) ve kuralları.
- Her modelin "sonuç görülmeden yazılan beklentisi" şartnameden aynen alınıp gerçekleşen backtest sonucunun yanına konur (beklenti tuttu mu, tutmadı mı; şartnamede ne yazıyorsa o).

## Şartnameden sapma

Şartnameyi DEĞİŞTİRME (docs/specs/ salt okunur). Şartname belirsizse ya da uygulanamıyorsa:
- Küçük belirsizlikte en makul yorumu seç ve `docs/SPEC_DEVIATIONS.md`'ye yaz: şartname dosyası:bölüm, belirsizlik, seçtiğin yorum, gerekçe.
- Bir modelin davranışını ya da parametre sayısını değiştiren bir sapma gerekiyorsa o modeli DONDURMA; kodunu ve testini bırak, raporda "şartname kararı gerekiyor" diye işaretle. Diğer modeller devam eder.

## Kurallar

- `v1_5_h99` ve basit kural JSON'ları ile `tests/reference/macos_golden/` DEĞİŞMEZ. Mevcut testler yeşil kalır.
- legacy/ ve docs/specs/ değişmez.
- Veri indirme yok. 2026-08-19 sonrası hiçbir veri repoya girmez. XU100 yalnız mevcut pinli dosyadan.
- Skorlama ve sicil kodu bu task'ta YOK (Faz 1C).
- Commit'e yalnız adı geçen yollar: borsai/, tests/, models/, experiments/, docs/MODELS.md, docs/SPEC_DEVIATIONS.md, docs/prompts/FAZ1B_NEW_MODELS.md. `git add -A` / `git add .` YOK.

## Commit

Tek commit. Mesaj: "BORSAI_FAZ1B: ceiling hazard, PB, market20 and V1.6 models implemented per Fable specs, backtested and frozen". Push yok.

## Teslim (rapor)

- Commit hash'i, `git show --stat` özeti.
- Test sayısı ve sonucu (eski ve yeni testler ayrı).
- Dondurulan modeller: model_id, dosya sha256, eğitim n'i, parametre sayısı; dondurulmayan varsa nedeni.
- Her modelin backtest özeti: şartnamedeki beklenti ile gerçekleşen sonucun yan yana tablosu.
- SPEC_DEVIATIONS.md'deki maddelerin listesi.
- `predict.py` ve yeni predict modüllerinin import listesi (stdlib kanıtı).

## Kabul kapısı

- K1 Beş yeni model şartnameye uygun uygulandı; her şartnamenin kabul testleri yeşil. Dondurulmayan model varsa gerekçesi yazılı.
- K2 Eski testler ve altın ledger'lar değişmedi, yeşil.
- K3 predict yolları yalnız stdlib.
- K4 INDEX.json ve MODELS.md güncel; her backtest koşusu log.jsonl'da.
- K5 legacy/, docs/specs/ değişmedi; 2026-08-19 sonrası veri yok.
- K6 Push, tag, amend yok.

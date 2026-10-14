# FAZ9_UI_FIX — Sade görünüm düzeltmeleri (sunum öncesi)

**Model: Claude Code / Opus 5.5 · Extra**

- **TASK_ID:** `BORSAI_FAZ9_UI_FIX_20261004`
- **Klasör:** repo kökü `~/Desktop/BorsAi`
- **Ağ:** yok.
- **Commit konusu öneki:** `BORSAI_FAZ9_UI_FIX_` (A, C, R; aşağıda).

## Rol

Uygulamanın ana mühendisisin. Proje sahibi yeni sade görünümü kullandı ve altı sorun buldu. Bu hafta hocalarına uygulamayı gösterecek. Görev yalnız bu altı maddedir; başka iyileştirme yapma, bulduğunu rapora yaz.

## Proje sahibinin bulduğu sorunlar ve orkestratörün ölçtüğü nedenler (2026-10-04, HEAD = origin/main = `b045e71`, ağaç temiz)

1. **Analiz'de bir arz seçilince arz listesine dönülemiyor.** `app/src/sade/screens/analiz.ts`: liste (`renderAnalizPick`) yalnız `sade.ticker` boşken çıkar. `sade.ticker` bir kez dolunca hiçbir yol onu boşaltmaz. Üst bardaki "Analiz" sekmesi de son arzı açar.
2. **Sicil'de "Aç" çalışmıyor gibi görünüyor.** Çalışıyor: `sicil-select` seçili arzı değiştirir ve künyeyi yeniden çizer. Ama `renderSicil` tabloyla künyeyi `flex-wrap` olan tek satıra koyar. Pencere 1200 px'te (bugünkü varsayılan) künye tablonun altına düşer ve görünür alanın dışında kalır. 1440 px'te yan yanadır (`app/docs/screens/v2/v2_07_sicil.png`).
3. **"Seri j gün sürdüyse yarın ne olur?" hesabında "yarın da tavan" 3. günden sonra hiç değişmiyor.** Hata değil, modelin yapısı. `models/ceiling_hazard_v0.json` `day_groups`: g1 = {1}, g2 = {2, 3}, g3 = {4…10}; bir grubun içindeki her gün aynı devam olasılığını alır. Ekran bunu söylemiyor, proje sahibine bozuk gibi görünüyor. Çözüm bu görevde **modeli değiştirmek değil**, ekranda açıklamak ve geçmiş arzların gün gün oranını yanına koymaktır. Gün gün değişen model ayrı bir görevdir.
4. **Analiz'de işlem sayısı çubukları yok.** Tasarımda vardı. Orkestratör "veride yok" diye çıkarmıştı (`docs/design/ui_v2/README.md` §3, `docs/app/UI_V2_RAPOR.md` F5). Bu yanlıştı: `data/outcomes/<T>.csv`'de `trade_count_raw` sütunu var. Kaynak, bültendeki `TOPLAM SOZLESME SAYISI` sütunu (`borsai/outcomes.py` `THB_COLUMNS`); NETGL D1 = 17885, D2 = 28445.
5. **Model performansındaki "3 satırda model daha iyi, 1 satırda değil, 2 satır hükümsüz" cümlesi yanıltıcı.** "1 satırda değil" denen satır `v1_5_h99` D10 Brier'dir ve dosyadaki hükmü "ayırt edilemiyor"dur, yani "fark net değil". `sade.rs` `PerfCounts.n_other_verdict`, "ayırt edilemiyor" ile "geçemiyor"u aynı sayıya topluyor.
6. **Pencere varsayılanı 1200 × 800.** `app/src-tauri/tauri.conf.json`: width 1200, height 800, minWidth 900, minHeight 600.

## Kararlar

- **K-FIX-1 · Analiz'e dönüş.**
  - Arz açıkken başlıkta bir yol görünür: "Analiz › NETGL". Yanında bir "Tüm arzlar" düğmesi ve bir arz değiştirici bulunur (Monitör'deki arzlar).
  - Üst bardaki "Analiz" sekmesi her zaman listeyi açar. Arama kutusu ve Monitör'deki satırlar arzı doğrudan açmaya devam eder.
  - Liste ekranı yalnız düğmelerden oluşmaz. Her satırda arz kodu, şirket adı ve ilk işlem günü vardır (`monitor_view` satırlarından), en yeni ilk işlem günü üstte.
- **K-FIX-2 · Sicil künyesi görünür olur.**
  - Satır ya da "Aç" tıklanınca künye seçilen arzla yeniden çizilir.
  - Künye görünür alanın dışındaysa sayfa yumuşakça künyenin başına kayar. `prefers-reduced-motion` açıksa kayma anında olur.
  - Geniş pencerede künye tablonun yanında kalır.
- **K-FIX-3 · Hesaplayıcıda açıklama ve geçmiş karşılaştırma.** Hem Tahmin sonucu'nda (senaryo) hem Analiz'de (resmi görünüm):
  1. "Yarın da tavan" okumasının yanında "Geçmiş arzlarda" değeri: basit kural `base_km_expanding`'in aynı j için koşullu değeri, yani S_{j+1} / S_j, S_0 = 1.
     - Kaynak: aynı koşunun (senaryo) ya da aynı kaydın (resmi) içindeki `base_km_expanding` S vektörü. Kayıtların hepsinde var (16 model).
     - Hesap Rust'ta yapılır. Var olan `ceiling_display` kural satırlarını zaten aynı yoldan verir; onu ya da var olan özet komutlarını genişlet. Ön uç hesap yapmaz.
     - Etiket kuralın adını ve kapsamını söyler, örneğin "Geçmiş arzlarda (basit kural, eğitimdeki tüm arzlar)". n gösterilecekse Rust'tan gelir.
  2. Not satırı: modelin gün grupları **model dosyasındaki `day_groups`'tan** Rust'la okunur ve metne dönüşür (sabit "4–10" yazılmaz).
     - Önerilen metin: "Model günleri üç grupta ele alır: 1. gün · 2–3. gün · 4–10. gün. Aynı gruptaki her gün için aynı devam olasılığını kullanır; bu yüzden 3. günden sonra 'yarın da tavan' değişmez. 'Geçmiş arzlarda' oranı her gün için ayrı hesaplanır."
     - Not yalnız `day_groups` taşıyan modellerde görünür.
  3. Eğride kuralın koşullu eğrisi ince gri kesikli çizgi olarak eklenebilir. Zorunlu değil.
  4. Altın renk yalnız model çıktısında kalır. Kural değeri gri, karşılaştırma rengiyle (`docs/design/ui_v2/README.md` belirteçleri).
- **K-FIX-4 · İşlem sayısı çubukları.**
  - Analiz'deki fiyat koridorunun altında D1–D10 için ince çubuklar ve "İşlem sayısı" etiketi.
  - `DayRow`'a `trade_count_raw` metni aynen eklenir. Rust ayrıca her gün için 0–1 arası göreli yükseklik verir (günün sayısı / o arzın 10 günündeki en büyük sayı). Ön uç bu oranı yalnız `render/svg.ts`'te piksele çevirir.
  - Sayı biçimi `render/format.ts`'te binlik ayırıcıyla yapılır. Değer yoksa çubuk çizilmez ve tire görünür.
  - `docs/design/ui_v2/README.md` §3'teki "Analiz'deki işlem adedi çubukları → sonuç dosyasında hacim yok" satırı düzeltilir: "işlem sayısı sonuç dosyasında var (`trade_count_raw`); çizildi (FAZ9_UI_FIX)".
- **K-FIX-5 · Performans sayımları ayrılır.**
  - `PerfCounts`'ta `n_other_verdict` yerine üç alan gelir:
    - `n_undecided`: dosyadaki hüküm "ayırt edilemiyor";
    - `n_fail`: "geçemiyor";
    - `n_other`: başka verdict, örneğin "yetersiz örnek".
  - `n_pass` ve `n_no_verdict` aynen kalır.
  - Metin: "3 satırda model daha iyi · 1 satırda fark net değil · 2 satır hükümsüz". Sıfır olan parça yazılmaz. `n_fail` için "x satırda kural daha iyi". `n_other` hükümsüzlere eklenmez, ayrı yazılır: "x satır yetersiz örnek".
  - Hüküm hücresi yine dosyadaki `verdict`'tir (U19).
- **K-FIX-6 · Pencere.**
  - Varsayılan 1440 × 900, ortada açılır. Ekranın çalışma alanı daha küçükse pencere büyütülmüş (maximized) açılır. Bu, Rust `setup` kancasında monitör boyutuna bakarak yapılır.
  - `minWidth` 1024, `minHeight` 680.
  - Bu sınırlarda hiçbir sade ekranda yatay kaydırma çubuğu çıkmaz.
- **K-FIX-7 · Sınırlar** (FAZ9_APP_UI K-UI-2 aynen):
  - `app/src/screens/*` ve `app/src/render/*` değişmez. `render/svg.ts` ve `render/format.ts`'e yalnız ekleme yapılır.
  - `tr.ts`'te `SADE` nesnesinin dışındaki hiçbir satır silinmez ya da değişmez. `SADE` içinde değişen dizeler rapora listelenir.
  - Ayrıntılı görünüm aynen kalır.
  - Ön uçta aritmetik yok (`no_frontend_math`).

## Önceden onaylı pin güncellemesi (K-PIN-FIX)

Proje sahibi başlatma cümlesinde onaylar. Bunun dışında hiçbir test gevşetilmez.

- **(a)** `tests/test_faz8_model.py`, `_app_ui_commits_only`: tek önek yerine görev listesi gelir:
  ```python
  APP_TASKS = (("BORSAI_FAZ9_APP_UI_", "BORSAI_FAZ9_APP_UI_C:"), ("BORSAI_FAZ9_UI_FIX_", "BORSAI_FAZ9_UI_FIX_C:"))
  ```
  İddialar şunlar:
  1. `7d78d43..HEAD` arasında `app/`'a dokunan her commit'in konusu listedeki öneklerden biriyle başlar.
  2. `app/parity/` `7d78d43`'ten beri değişmemiştir (çalışma ağacı dahil).
  3. Commit'lenmemiş `app/` değişikliğine yalnız listedeki **son** görevin kapanış konusu (`BORSAI_FAZ9_UI_FIX_C:`) log'da yokken izin verilir.

  Sabitin yanına tek satırlık yorum: "`app/`'a dokunan her yeni görev bu listeye kendi satırını ekler (önceden onaylı pin)". `tests/reference` ve `models` iddiaları aynen kalır.
- **(b)** Vitest ve cargo'da yalnız bu görevin değiştirdiği davranışın iddiaları güncellenebilir: `PerfCounts` alanları ve sayım metni, Analiz liste/yol, Sicil kayma, hesaplayıcı satırları. Bunlar ve ilgili sade fixture'ları (`app/tests/fixtures/ui/sade_*.json`) gerçek dosyalardan yeniden üretilebilir. U13–U26, U34, parite, `golden_unchanged` ve `no_frontend_math` değişmez. Değişen her test fonksiyonu rapora yazılır.
- **(c)** `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `legacy/`, `docs/specs*`, `CLAUDE.md` ve `experiments/log.jsonl` **değişmez**.

**Bekçiler asla ayrılmaz.** Temizlik bekçisi `tests/test_faz8_break.py::test_14b…` (`app` dahil `git status` boş ister) yalnız commit öncesi ara koşulardan ayrılır; commit'ten sonra ayrılmadan koşar.

## İzinli izlenmeyenler (adım 0)

`docs/prompts/FAZ9_UI_FIX.md` (bu dosya, commit A'ya girer), `docs/prompts/TUFE_2026_09.md` ve `docs/prompts/FAZ10_FABLE_STREAK_SPEC.md` (son ikisi başka görevlerin dosyası; dokunma, commit'leme).

**TABAN.** Adım 0'daki HEAD bu görevin tabanıdır. Aşağıdaki bütün `git diff TABAN …` karşılaştırmaları ona göre yapılır. TABAN ya `b045e71`'dir ya da onun üstüne gelen tek bir `BORSAI_FAZ10_SPEC:` commit'idir. O commit yalnız `docs/specs_faz10/` ve `docs/prompts/FAZ10_FABLE_STREAK_SPEC.md`'ye dokunur (model şartnamesi; bu görevden önce koşabilir).

## ÖNCE OKU

1. `docs/app/UI_V2_RAPOR.md` (bütün), `docs/design/ui_v2/README.md`.
2. `app/src/sade/` (`app.ts`, `state.ts`, `screens/analiz.ts`, `screens/sicil.ts`, `screens/sonuc.ts`, `screens/perf.ts`, `render/analiz.ts`, `render/sicil.ts`, `render/calc.ts`, `render/perf.ts`, `sade.css`).
3. `app/src-tauri/src/commands/sade.rs` (`DayRow`, `read_days`, `arz_view_in`, `PerfCounts`, `perf_view_value`), `commands/ceiling.rs` (`ceiling_display_value`, `ceiling_summary_value`), `commands/registry.rs` (`record_ceiling_in`), `app/src-tauri/src/lib.rs` (`setup`), `app/src-tauri/tauri.conf.json`.
4. `app/tests/no_frontend_math.test.ts`, `app/tests/sade_*.test.ts`, `app/src-tauri/tests/sade.rs`, `app/scripts/test.sh`, `app/scripts/screens_v2.sh`.
5. `tests/test_faz8_model.py` (`_app_ui_commits_only`, `test_5c`), `tests/test_faz8_break.py::test_14b…`.

## Adımlar

**0. Taban.**
- `git status --porcelain --untracked-files=all` yalnız izinli izlenmeyenleri gösterir.
- HEAD = origin/main. `git diff --stat b045e71 HEAD` ya boştur ya da yalnız `docs/specs_faz10/` ve `docs/prompts/FAZ10_FABLE_STREAK_SPEC.md`'yi gösterir. Bu HEAD'i TABAN olarak rapora yaz.
- Ara paralel pytest (`.venv/bin/pytest -q -n 6 --dist loadgroup`): 952 passed.
- `bash app/scripts/test.sh` yeşil: cargo 161, vitest 365, parity 8, `golden_unchanged`.
- `gen_golden --check` 35/0.

Sayı tutmazsa ya da kırmızı varsa DUR, raporla.

**1. K-PIN-FIX (a) provası (geçici `git clone --local` klonunda).**
- Yeni `_app_ui_commits_only`'yi klona koy, sonra tek başına `test_5c`'yi şu durumlarda koş ve sonuçları rapora yaz:
  - (i) temiz: yeşil;
  - (ii) commit'lenmemiş `app/` değişikliği: yeşil;
  - (iii) `BORSAI_FAZ9_UI_FIX_A:` konulu `app/` commit'i: yeşil;
  - (iv) başka konulu `app/` commit'i: **kırmızı**;
  - (v) `app/parity/` değişikliği: **kırmızı**;
  - (vi) `BORSAI_FAZ9_UI_FIX_C:` commit'inden sonra commit'lenmemiş `app/`: **kırmızı**.
- Asıl repoda bu adımda commit yok.

**2. Kod (A).** K-FIX-1…7.
- Cargo testleri gerçek repo dosyalarıyla, aşağıdaki **beklenen sayılar**la. Vitest'te her yeni ya da değişen saf render fonksiyonu için metin ve yapı testleri olsun.
- Ara paralel pytest'te `test_14b` ayrılır.
- **Commit A:** `BORSAI_FAZ9_UI_FIX_A: analysis back nav, registry card scroll, calculator history row and day-group note, trade-count bars, perf counts split, window size, K-PIN-FIX test_5c`
  ```
  git add docs/prompts/FAZ9_UI_FIX.md tests/test_faz8_model.py docs/design/ui_v2/README.md <dokunduğun app/src, app/src-tauri, app/tests yolları>
  ```
- Commit'ten hemen sonra `test_5c` ve `test_14b` tek başına yeşil.

**3. Görüntüler ve belgeler (C).**
- `app/scripts/screens_v2.sh` ile şu görüntüler güncellenir ya da eklenir (`app/docs/screens/v2/`):
  - Analiz listesi (yeni);
  - Analiz NETGL (yol, değiştirici, işlem sayısı çubukları);
  - Analiz hesaplayıcı j = 3 ve j = 6 (model %67 ikisinde de; geçmiş %80 ve %82);
  - Tahmin sonucu j = 3;
  - Model performansı (yeni sayım cümlesi);
  - Sicil, 1200 px pencerede BKRGY seçilmiş, künye görünür alanda (yeni).
- Eski `app/docs/screens/*.png` (v2 dışı) değişmez.
- `docs/app/UI_FIX_RAPOR.md` (teslim, aşağıda). `app/README.md`'de sade görünüm bölümüne kısa not.
- `docs/SPEC_DEVIATIONS.md`'ye yalnız şartnameden sapma varsa ekleme yapılır (yeni bölüm "P").
- **Commit C:** `BORSAI_FAZ9_UI_FIX_C: screenshots and report`. `git add` yalnız dokunduğun `app/docs/screens/v2/*.png`, `app/README.md`, `docs/app/UI_FIX_RAPOR.md` ve (varsa) `docs/SPEC_DEVIATIONS.md`.

**4. Derleme.** `npm run tauri build -- --bundles app`. `borsai-app` sha256'sını rapora yaz. Kurulumu proje sahibi yapar.

**5. Son kabul.**
- Sıralı `.venv/bin/pytest -q`, **ayrılan test yok**.
- `bash app/scripts/test.sh` ve `gen_golden --check`.
- Sayıları rapora yaz. **Commit R:** `BORSAI_FAZ9_UI_FIX_R: final test runs`. `git add` yalnız `docs/app/UI_FIX_RAPOR.md` ve test günlüğü `docs/app/ui_fix_test_runs.txt`.

## Beklenen sayılar (orkestratör kayıt dosyalarından hesapladı; 0 ondalık yüzde, SPEC_APP §4)

**"Yarın da tavan", model `ceiling_hazard_v0`:**

| j | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| NETGL | %82 | %86 | %86 | %67 | %67 | %67 | %67 | %67 | %67 | %67 |
| CITAS | %92 | %94 | %94 | %85 | %85 | %85 | %85 | %85 | %85 | %85 |

Ham değerler: NETGL j = 3 → 0.6676, CITAS j = 3 → 0.8459. Kayıtlar: NETGL `20260922T121936Z_65a39d7392dd.json`, CITAS `20260922T121935Z_6356b36ec865.json`.

**"Geçmiş arzlarda", kural `base_km_expanding`:** bütün kayıtlarda aynı S = 0.8182, 0.7071, 0.6667, 0.5354, 0.4141, 0.3333, 0.2727, 0.2121, 0.1717, 0.1414.

| j | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| Oran | 0.8182 | 0.8642 | 0.9429 | 0.8030 | 0.7736 | 0.8049 | 0.8182 | 0.7778 | 0.8095 | 0.8235 |
| Ekranda | %82 | %86 | %94 | %80 | %77 | %80 | %82 | %78 | %81 | %82 |

`models/base_km_expanding.json`'da n = 99. S × 99 tam sayıdır: 81, 70, 66, 53, 41, 33, 27, 21, 17, 14. Sayım gösterilirse ("3 gün tavan yapan 66 arzın 53'ü 4. gün de tavan oldu"), Rust bunu ancak tam sayılık 1e-9 içinde tutuyorsa verir; tutmuyorsa yalnız oran gösterilir.

**`day_groups` (`ceiling_hazard_v0`):** g1 = [1], g2 = [2, 3], g3 = [4, 5, 6, 7, 8, 9, 10].

**İşlem sayısı, NETGL:** D1 17885, D2 28445 (`data/outcomes/NETGL.csv`). Öbür günler dosyadan; en büyük gün oranı 1.

**Performans sayımları (bugünkü dosyalar):** `n_rows` 6, `n_pass` 3, `n_undecided` 1 (`v1_5_h99` D10 Brier, −0.0391 [−0.0756, +0.0023], n 81), `n_fail` 0, `n_other` 0, `n_no_verdict` 2 (`break_floor_v0` F1 ürün ve `@ZERO` satırları).

## Tek oturumda bitmezse

Commit sınırlarında (A, C) dur. Raporun "nerede kaldım" bölümünü yaz. Commit'lenmemiş iş bırakma.

## Kurallar

- push, tag ve amend yok (proje sahibi yapar).
- Her commit'te açık `git add` yolları; `git add -A` ya da `.` yok.
- Yazılabilir: `app/` (K-FIX-7 sınırlarıyla), `tests/test_faz8_model.py` (yalnız K-PIN-FIX (a)), `docs/app/`, `docs/design/ui_v2/README.md` (yalnız K-FIX-4'teki satır), `docs/SPEC_DEVIATIONS.md` (yalnız ekleme), `app/README.md`.
- Salt okunur: geri kalan her şey (K-PIN-FIX (c)).
- **Hijyen:** yeni ve değişen her dosyayı `registry/oot/cohort_pre_h99.csv`'deki SEALED kodlarına karşı büyük/küçük harf duyarlı tara. Bülten adı kalıbı (`th[bm]` + 8 hane) yok. Sonucu rapora yaz.
- Belirsizlikte: kural şartnamede ya da bu dosyada yazılıysa uygula. Yazılı değilse ve sonucu etkiliyorsa DUR, seçenekli soru sor.

## Teslim (`docs/app/UI_FIX_RAPOR.md`)

1. Commit listesi (sha, konu).
2. Adım 1 provasının altı durumu ve sonuçları.
3. Madde madde (K-FIX-1…6): ne yapıldı, hangi dosya ve komut, hangi görüntüde görünüyor.
4. `SADE` içinde değişen dizeler (eski → yeni).
5. Değişen test fonksiyonları (K-PIN-FIX (a), (b)), her biri tek satır gerekçeyle.
6. Test sayıları: pytest (sıralı, ayrılan yok), cargo, vitest, parity, `golden_unchanged`, `gen_golden`.
7. `.app` sha'sı ve derleme komutu.
8. Hijyen taraması sonucu.
9. Bulduğun ama yapmadığın şeyler (kapsam dışı).

## Kabul kapısı

- Son sıralı pytest yeşil, **ayrılan yok**.
- `test.sh` yeşil.
- `gen_golden --check` 35/0.
- `git diff TABAN -- app/src/screens app/src/render`: yalnız `render/svg.ts` ve `render/format.ts` eklemeleri, silinen satır yok.
- `tr.ts`'te silinen ya da değişen satırların hepsi `SADE` nesnesinin içinde.
- `git diff TABAN --stat -- borsai models registry data scores legacy docs/specs* CLAUDE.md experiments app/parity` boş.
- Beklenen sayılar cargo testlerinde birebir (oranlar ±5e-5, yüzdeler tam).
- Altı maddenin her biri görüntüde görünüyor.
- Hijyen temiz.

# TASK_ID: BORSAI_FAZ6_FABLE_OOT_AUDIT_20260925

Model: Fable · yüksek. Klasör: ~/Desktop/BorsAi.
- **Ağ: yalnız** (a) BIST tatil tablosu PDF'leri ve (b) örneklem denetiminde KAP/SPK belgelerinin yeniden indirilmesi için. **THB/THM bülteni İNDİRİLMEZ, HEAD bile atılmaz.**
- Git: yalnız okuma komutları, `GIT_OPTIONAL_LOCKS=0` öneki; `git clone --local` serbest (mutasyon ve kuru koşu için `/tmp/borsai_faz6_audit/`). Sonda tek commit, yalnız kendi yollarınla. push/tag/amend yok.
- Yazma: YALNIZ `docs/fable_faz6_audit/` ve bu görev dosyası. `ekler/` ≤ 5 MB.
- Paralel oturum yok. Önce/sonra `git status --porcelain` ve `registry/`, `data/`, `scores/`, `models/` ağaç sha'ları eşit olmalı.

## Bağlam
- Eski kohort (2020-01-01…2023-09-21, 135 üye) protokolü:
  - `docs/specs_faz6/SPEC_OOT_PRE_H99_V0.md` (senin şartnamen, `b8763fc`, push kanıtlı).
  - `docs/specs_faz6/KARARLAR.md` D1–D8: proje sahibi kararları; **çelişkide KARARLAR geçerli**. Başlıcaları: D6 bültenler repoya ham girmez, karantina + yalnız OPEN satırları makineyle ayıklanır; D2 kasa %50 yıl içinde tabakalı; D3 CLAUDE.md "üç terazi".
- Opus'un uygulaması (push edilmeyi bekliyor):
  - `94ad4e8` S0b kararlar
  - `1d4913e` A altyapı: `borsai/{registry,freeze,market20,scoring}.py`, yeni `borsai/outcomes_oot.py`, Takvim C, bekçiler
  - `2e088c3` S1: `registry/oot/cohort_pre_h99.csv`, 135 doğrulanmış girdi + 523 kaynak belge, `docs/faz6/dogrulama/`
  
  Rapor `docs/faz6/INFRA_RAPOR.md`; yorum kararları `docs/SPEC_DEVIATIONS.md` I1–I27.
- Girdiler: Codex çıkardı, ayrı bir Claude Code oturumu resmi belgelerde birebir doğruladı (`docs/faz6/dogrulama/REPORT.md`: Codex değerlerinin %98,4'ü birebir; f3 130/135; PB 112).
- **Bu denetim S2'den (135 üye × 19 modelin tahmin kaydı, kalıcı) ÖNCE.** Soru: altyapı ve girdiler S2'yi yazmaya hazır mı?
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** (Bu denetim hiçbir modeli değiştirmez; bulgu yazar.)

## Sonuç körlüğü
- Kohort üyelerinin listeleme sonrası hiçbir fiyat, getiri, tavan ya da hacim bilgisine bakılmaz.
- `docs/faz6/dogrulama/EXPOSURE.md` §3'teki ticker listesi OKUNMAZ.
- Hangi kodun SEALED olduğu raporda yazılmaz; yalnız sayılar ve algoritmanın eşleşip eşleşmediği yazılır.

ÖNCE OKU: CLAUDE.md; docs/specs_faz6/ (KARARLAR, SPEC, FEASIBILITY, ekler/takvim_2020_2023.md, ekler/kurallar_arastirma.md); docs/faz6/INFRA_RAPOR.md, docs/faz6/OOT_TANIM_ESLEME.md; docs/SPEC_DEVIATIONS.md I; docs/faz6/dogrulama/REPORT.md; kalıp: docs/fable_faz5_audit/ (AUDIT.md, ekler/mutate.sh).

## Adımlar
1. **Uygunluk (kod ↔ şartname + KARARLAR).** Her maddeye hüküm: uygun / sapma (davranış değiştiriyor mu, lafza aykırı mı, kabul edilebilir mi). Özellikle:
   - D6 ve I13: indirme kapısı (kohortun BÜTÜN MEMBER S2 kayıtları commit'li ve push kanıtlı olmadan açılmaz), `oot_ingest_commit` tanımı, `class_oot` (model kanıtı, kayıt kanıtı, sonuç kanıtı sırası), SEALED kodun bülten açılmadan reddi, ayıklamanın yalnız o üyenin D_1…D_10 satırlarını okuması, `MACHINE_EXTRACTED` etiketi.
   - I4 kasa: şartname §9 ve D2 lafzıyla uyum. Ayrıca **`borsai` import etmeden** kendi betiğinle, yalnız metinden çekilişi yeniden üret ve kohort dosyasındaki `vault` sütunuyla karşılaştır. Aynı sonucu veren başka makul okumalar varsa not et. Kasa commit'lidir; yalnız gerçek bir kural ihlali varsa değişiklik öner.
   - Rejim etiketleri: 135 üye için kural tarihlerinden ve girdilerden bağımsız yeniden hesapla. Kapsam: MARGIN (1 üye), TICK_TABLE_MISMATCH (3), SALE_ON_EXCHANGE (49), PRICE_RANGE_BOOKBUILD (9), ALLOC_REGIME (I8), SHORT_SELL_BAN (I9), MARKET, EXPOSED_*. Kohort dosyasıyla 135/135 karşılaştır.
   - Takvim C (I15): BIST tatil tablolarını resmi siteden indir, sha'ları `ekler/takvim_2020_2023.md` pinleriyle karşılaştır. Takvim C dosyasının tam gün/yarım gün/kapanış satırlarını satır satır denetle; XU100 gün kümesiyle tutarlılık.
   - CLAUDE.md D3 metinleri birebir; `scores.json` ve uygulama dokunulmamış; POST_D1 ve listeleme öncesi akışların davranışı değişmemiş.
2. **Girdi örneklem denetimi (Codex'ten ve doğrulayıcıdan bağımsız).**
   - Tohum 20260925, yıl tabakalı 15 üye (2020: 2, 2021: 5, 2022: 4, 2023: 4).
   - Her girdi alanı (V1.5 alanları, f3 + köken + filtre, sermaye ayrımı, ek satış, PB 8 alanı, tarihler) için `registry/oot/source_docs/<T>/`'deki pinli belgeyi aç; alıntıyı ve değeri birebir bul; yayın zamanını denetle (< ilk işlem günü).
   - DATA_NOTES §2/§5 kuralları (taşıma, ek satış paydası) doğru uygulanmış mı?
   - Bu 15 üyeden 5 belgeyi resmi URL'den yeniden indir; sha pinle eşitliğini göster.
   - `borsai.features` ile f1–f3 ve PB özelliklerinin bu 15 üyede beklenen değerleri verdiğini göster.
3. **Kuru S2 koşusu (klonda).** `freeze --oot` klonda koşar (gerçek repoya yazılmaz):
   - 135 kayıt × 19 model.
   - Durum sayıları INFRA_RAPOR §6 ile eşit.
   - 5 kayıtta çıktılar doğrudan `predict` çağrısına bit-eşit.
   - `comparators` donmuş H99 değerleri ve `comparator_note`.
   - `NOT_APPLICABLE_REGIME` hücreleri doğru modellerde.
   - Kayıt şeması §5.
4. **Mutasyon denetimi** (`ekler/mutate.sh`, çıktılar `ekler/mutasyon_ciktilari.txt`). Her mutasyon ayrı uygulanır, ilgili test koşar, KIRMIZI olduğu gösterilir, geri alınır. En az:
   - (a) indirme kapısı push kanıtını aramaz
   - (b) kapı SEALED üyelerin S2 kaydını aramaz
   - (c) ayıklayıcı SEALED kodu kabul eder
   - (d) ayıklayıcı D_11 satırını da alır
   - (e) kasa tohumu ya da tabaka sırası değişir
   - (f) marj kural tarihi bir gün kayar
   - (g) TICK_TABLE_MISMATCH eşiği bozulur
   - (h) G1: `registry/oot/inputs`'a sonuç alanı eklenir
   - (i) `data/outcomes_oot` commit'i S2 atası olmadan kabul edilir
   - (j) `ScaleMixError` OOT ile backtest/canlı karışımını kabul eder
   - (k) `class_oot` kanıt sırasını yok sayar
   - (l) `freeze --oot` bir modeli atlar
   - (m) kohort penceresi tarihli bir zip repoya konur
   
   Kırmızı olmayan her mutasyon ÖNEMLİ ya da KRİTİK bulgudur.
5. **Tam test:** `.venv/bin/pytest -q` ve `bash app/scripts/test.sh` → `ekler/test_runs.txt`. S1 commit sonrası sayı raporda yoktu; bunu ölç (beklenen 594 geçti).
6. **Hüküm** `docs/fable_faz6_audit/AUDIT.md`:
   - `S2_OK` / `S2_BLOCKED` (+ neden).
   - Bulgular önem derecesiyle (KRİTİK / ÖNEMLİ / KÜÇÜK) ve her biri için öneri. Türü de yazılı olsun: kod düzeltmesi, girdi düzeltmesi (iptal satırıyla) ya da karar.
   - Uygunluk tablosu, örneklem tablosu, mutasyon tablosu, kuru koşu özeti.

Tek oturumda bitmezse: 1–3 tamamsa hükmü yaz, kalanı açık bırak; eldekini `(partial)` ile commit et.

## Kurallar
- Mevcut hiçbir dosyayı değiştirme. Bağımsız betikler `borsai`'yi import etmez (alt süreçte `sys.modules` denetimi); yalnız 2. adımdaki `borsai.features` karşılaştırması ve 3–5. adımlar repo kodunu çağırır.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- Rapor Türkçe.
- `git add -A` yok. Commit:
  ```
  git add docs/fable_faz6_audit docs/prompts/FAZ6_FABLE_OOT_AUDIT.md
  git commit -m "BORSAI_FAZ6_FABLE_OOT_AUDIT: conformity audit of out-of-time cohort infrastructure, input sample check, dry S2 run, mutation run" -- docs/fable_faz6_audit docs/prompts/FAZ6_FABLE_OOT_AUDIT.md
  ```

## Kabul kapısı
- K1 Uygunluk tablosu D1–D8 ve I1–I27'nin hepsini kapsar; kasa ve rejim etiketleri bağımsız yeniden üretildi (eşleşme sayısı yazılı).
- K2 15 üyenin bütün girdi alanları pinli belgede birebir bulundu (ya da her uyuşmazlık yazılı); 5 belge yeniden indirilip sha eşit.
- K3 Kuru S2: 135 × 19; durum sayıları ve 5 kaydın bit-eşitliği.
- K4 En az 13 mutasyon, her birinin çıktısı; kırmızı olmayanlar bulgu.
- K5 Hiçbir bülten istenmedi; commit yalnız `docs/fable_faz6_audit/` ve bu görev dosyası; korunan ağaçlar önce/sonra eşit.

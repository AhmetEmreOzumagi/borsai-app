# Faz 6 — proje sahibi kararları (SPEC_OOT_PRE_H99_V0 §11 ve orkestratör düzeltmeleri)

Tarih: 2026-09-24, 17:30–19:58 (İstanbul). Yazan: orkestratör; onaylayan: proje sahibi ("sen onaylıyorsan ben de onaylıyorum", 19:58).
Bu belge şartname sayılır. `SPEC_OOT_PRE_H99_V0.md` ile çeliştiği yerde bu belge geçerlidir. Kararlar sonuç verisi görülmeden alındı (kohort penceresinden hiçbir sonuç repoda ya da orkestratörde yok).

## D1. Kohort başlangıcı
**2020-01-01.** Kohort = ilk işlem günü 2020-01-01…2023-09-21 olan 135 üye (`ekler/evren_listesi.csv`); GMTAS `OUT_OF_SCOPE` (halka arzsız kotasyon). Yıllar: 2020: 8, 2021: 52, 2022: 38, 2023: 37.

## D2. Kasa
**%50, ilk işlem yılı içinde tabakalı**, tohum `numpy.random.Generator(PCG64(20260924))`, sıralama (`first_trading_date`, `ticker`) (şartname §9 K2).
- Kasaya giremeyenler, çekilişten önce çıkarılıp OPEN yazılır:
  - `EXPOSED_ARCHIVE`: TARKM, GIPTA, ADGYO, REEDR (şartname §11-5).
  - `EXPOSED_CODEX`: PNLSN. Codex'in girdi toplama günlüğünde bu kod için listeleme sonrası bir KAP başlığının görüldüğü yazılı; değer yok. Orkestratör bu günlüğü okudu.
- Kasa listesi, kohort dosyasıyla birlikte, girdi ve sonuç verisinden bağımsız olarak commit edilir ve push edilir.

## D3. Üç terazi (CLAUDE.md'ye eski kohort altyapısı commit'inde girecek metin)
Kural 3'ün ilk cümlesi şöyle değişir (sonraki prospektiflik cümleleri aynen kalır):
> 3. Üç terazi, asla toplanmaz: backtest (retrospektif walk-forward), canlı (prospektif) ve zaman-dışı eski kohort (2023-09-22 öncesi arzlar; tahminler sonuç repoya girmeden push edilir).

Sıra kuralı satırına ek cümle:
> Eski kohortun sonuç verisi, kohortun bütün listeleme öncesi tahmin kayıtları push edilmeden repoya alınmaz; kasadaki arzların sonuçları, doğrulanacak özellik önceden kaydedilip push edilmeden alınmaz.

## D4. Eğitimde kullanım
Şartname §11-4 aynen. OPEN küme, zaman-dışı skorlar yayımlandıktan sonra yeni model kimliklerinin eğitimine girebilir (yeni `data/training_table_v2.csv`; `training_table.csv` dokunulmaz). SEALED küme, doğrulaması yayımlanana kadar hiçbir eğitime ve keşfe girmez.

## D5. post_d1 ve arşiv maruziyeti
Şartname §11-5 aynen. `post_d1_hazard_v0` zaman-dışı sonuçları `MACHINE_SEQUENCED` etiketiyle ayrı alt tabloda. EXPOSED_ARCHIVE ve EXPOSED_CODEX arzları OPEN'da; sayaçları (`n_exposed_archive`, `n_exposed_codex`) görünür.

## D6. Bültenler repoya ham girmez; karantina ve ayıklama (orkestratör düzeltmesi; şartname §2 S3/S5 ve G5'in yerine)
**Neden.** Günlük THB/THM bülteni o gün işlem gören bütün payları taşır. Kohortta 135 üyenin 127'sinin 10 seanslık penceresi başka bir üyeninkiyle çakışıyor (orkestratör ölçümü, iş günü yaklaşımıyla). %50 rastgele kasayla, açık kümedeki bir arzın bülteni hemen her zaman kasadaki bir arzın sonucunu da taşır. Şartnamenin G5'i ("SEALED bir üyenin penceresine denk gelen zip → kırmızı") uygulanırsa açık kümenin büyük kısmı skorlanamaz.

**Karar.**
1. Kohort penceresindeki (2020-01-01…2023-09-21 ve D_10'ları) THB/THM zip'leri **repoya girmez.** Repo dışında bir karantina dizinine indirilir (ör. `~/Desktop/BorsAi_quarantine/`, git dışında).
2. Deterministik ayıklama kodu yalnız **OPEN** üyelerin satırlarını (`<T>.E`, yalnız o üyenin D_1…D_10 tarihleri) okur. Repoya ayıklanmış satırlar (`data/outcomes_oot/<T>.csv` ve ham alan kopyaları) ile her zip'in URL, sha256, bayt, Last-Modified ve indirme zamanı pinleri girer (`data/raw/bist/MANIFEST_OOT.csv`).
3. SEALED üyelerin satırları hiçbir dosyaya, günlüğe ya da ekrana yazılmaz. Ayıklama kodu SEALED kodları için satır okuduğunda hata verir (test).
4. Kasa açıldığında zip'ler yeniden indirilir, pinlenmiş sha ile eşleşmesi zorunludur; sonra SEALED satırları ayıklanır.
5. Sıra kapısı zip commit'i yerine **ayıklanmış sonuç satırlarını ekleyen commit** üzerine kurulur: bu commit, kohortun bütün S2 kayıtlarını (135 üye × 19 model) ekleyen commit'lerin torunu olmalı; S2'nin push kanıtı bu commit'in push kanıtından önce olmalı. Zip indirmesinin kendisi de kodda kapıya bağlanır: S2 kayıtları commit'li ve push kanıtlı değilse karantina indirmesi başlamaz.
6. Zaman-dışı sonuçların hepsi `outcome_basis = MACHINE_EXTRACTED` etiketi taşır ("makine gördü, insan görmedi"). Listeleme öncesi modeller için körlük ayrıca commit sırasıyla sağlanır (S2 hiçbir zip'ten önce push edilir).

## D7. Girdi toplama: Codex çıkarır, Claude Code doğrular
- Codex + GPT-6 Astra (repo dışı) 135 üye için girdileri resmi belgelerden çıkardı (`~/Desktop/BorsAi_codex/BORSAI_FAZ6_CODEX_INPUTS_B1…B4_20260924.json`; görevler `docs/prompts/FAZ6_CODEX_INPUTS_B1…B4.md`). Kapsama (orkestratör ölçtü): fiyat ve satılan pay 135/135 (fiyat 135/135 KAP baz fiyatıyla eşit); talep katı 72/135; katılımcı sayısı 66/135; planlanan yapı ~61/135; fiyat istikrarı, satmama taahhüdü ve katılım beyanı 0/135.
- Claude Code her değeri resmi kaynaktan yeniden indirilen belgede birebir doğrular. Kurallar: belge sha256 ile pinlenir; KAP yayın zamanı < ilk işlem günü; doğrulanamayan değer girdi olmaz. Eksikleri doldurur ve doldurduğu her alanı `filled_by: CLAUDE_VERIFIER` ile etiketler (sonra örneklemle çapraz denetlenir).
- SPK yıllık tabloları yalnız çapraz denetimdir, değer kaynağı değildir.
- Aday özellikler (katılımcı, grup talep katı, tahsisat, kişi başı lot, fiyat istikrarı, satmama taahhüdü, lider aracı kurum, katılım beyanı) model girdisi değildir; ayrı dosyada tutulur. H99'da aynı alanlar eski repo ana tablosunda (`HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv`) zaten var; eski kohortta aynı adlarla toplanır.

## Maruziyet kaydı
- Codex dört partide 5 `exposure_log` satırı yazdı: KAP API listelerinde bazı kohort kodları için listeleme sonrası bildirim başlıkları görüldü (ör. "Pay Bazında Devre Kesici Bildirimi"); fiyat, getiri, hacim değeri açılmadı. Yalnız PNLSN adıyla anıldı (bkz. D2).
- Orkestratör bu günlüğü okudu; başka bir kohort sonucu görmedi.

## D8. Doğrulama raporunun açık noktaları (2026-09-24 22:30; orkestratör kararı, proje sahibinin genel onayıyla)
Doğrulama raporu: `~/Desktop/BorsAi_codex/verified/REPORT.md` (görev `docs/prompts/FAZ6_VERIFY_CODEX_INPUTS.md`). Sonuç: 135/135 girdi dosyası repo doğrulayıcısından geçiyor; f3 130/135; Codex'in 1 702 girdi değerinin %98,4'ü birebir doğrulandı; rastgele 10 arzda 200/200 alan doğru.
1. **SPK bülteni kesitleri (EXPOSURE §3):** 28 üyenin listeleme sonrası bültenlerde geçen pay ihracı / borçlanma aracı satırları görüldü. Bunlar fiyat, getiri ya da tavan bilgisi değil; D_1…D_10 sonuçlarıyla ilişkisi zayıf ve dolaylı. Bu üyeler kasaya **girebilir**; maruziyet `exposure_class = SPK_CORPORATE_ACTION_ROW_SEEN` ile kaydedilir ve sayılır. Özellik tasarlayan oturumlar (Faz 7+) `verified/EXPOSURE.md` §3'ün ticker listesini okumaz.
2. **Fiyat ve satılan pay için birincil kaynak BIST listeleme bildirimi:** kabul (135/135 aynı şablon, KAP sunucu zamanı; sonuç belgeleriyle tutarlı).
3. **SPK bülteni yayın anı gün sonu üst sınırı** (`SPK_BULTEN_BASILI_TARIH_GUN_SONU_UST_SINIR`): kabul. Bütün bülten tarihleri talep toplama başlangıcından önce.
4. **FILTERED f3'lü 6 arz ve payda tanımı:** H99'daki gibi alan düzeyinde işaret; model farkı görmez; kabul.
5. **Repoya alınacaklar:** `verified/registry/oot/{inputs,source_docs,candidate_features}` olduğu gibi (≈ 196 MB). `_tools/`, `REPORT.md`, `EXPOSURE.md`, `coverage.csv`, `verification_log.jsonl` repoya `docs/faz6/dogrulama/` altında alınır (`_tools/logs` hariç, boyut ≤ 10 MB ise dahil). Aday özellik kaynakları da girer; (C)'nin doğrulanabilirliği bunu ister.
6. **Kalan aday özellikler** (fiyat istikrarı, satmama taahhüdü, sektör, katılım, dağıtım yöntemi: izahname §23–25, 135 arz OCR): ertelendi; (C) şartnamesi yazılırken ayrı görev.

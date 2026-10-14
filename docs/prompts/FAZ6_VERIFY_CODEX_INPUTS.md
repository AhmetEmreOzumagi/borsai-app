# TASK_ID: BORSAI_FAZ6_VERIFY_CODEX_INPUTS_20260924

Model: Opus 5.5 · yüksek. Klasör: ~/Desktop/BorsAi (okuma) ve `~/Desktop/BorsAi_codex/` (okuma + `verified/` altına yazma).
- **Ağ: açık** (KAP, SPK, Borsa İstanbul). Bu sohbetin kuralı: web serbest; resmi kaynak öncelikli.
- **Repoya HİÇBİR ŞEY yazılmaz, commit yok.** Bütün çıktılar `~/Desktop/BorsAi_codex/verified/` altına. Repodaki git'i yalnız okuma komutlarıyla ve `GIT_OPTIONAL_LOCKS=0` önekiyle kullan.
- Paralel: bir Sonnet oturumu repoda uygulama MANIFEST'i ve skorları commit ediyor; sonra bir Opus oturumu eski kohort altyapısını yazacak. Onlara dokunma.

## Bağlam
- Proje: Borsa İstanbul halka arz tahmin modelleri. Dondurulmuş 19 listeleme öncesi model (`models/INDEX.json`) ve `post_d1_hazard_v0` (`models/INDEX_POST_D1.json`), 2020-01-01…2023-09-21 arasında listelenen **135 arzlık eski kohortta**, sonuçlara bakılmadan test edilecek. Protokol: `docs/specs_faz6/SPEC_OOT_PRE_H99_V0.md` + **`docs/specs_faz6/KARARLAR.md` (bağlayıcı; çelişkide o geçerli)**; fizibilite `docs/specs_faz6/FEASIBILITY.md`.
- Codex + GPT-6 Astra 135 arzın girdilerini resmi belgelerden çıkardı: `~/Desktop/BorsAi_codex/BORSAI_FAZ6_CODEX_INPUTS_B1…B4_20260924.json` (görevler `docs/prompts/FAZ6_CODEX_INPUTS_B*.md`). Codex'in indirdiği belgeler `sources/`, betikleri `scripts/` altında (OCR için Apple Vision + `pdftoppm` kullanmış).
- Orkestratör kapsamayı ölçtü: fiyat ve satılan pay 135/135 (fiyat, KAP baz fiyatıyla 135/135 eşit); **talep katı (f3) 72/135**; katılımcı sayısı 66/135; planlanan yapı (PB alanları) ~61/135; sermaye ayrımı ~33–60/135; fiyat istikrarı, satmama taahhüdü ve katılım beyanı 0/135. Codex'in sık yazdığı engeller: KAP arama API'sinde 2 000 kayıt sınırı (geniş tarih sorguları), metin katmanı olmayan taranmış ekler, süre.
- **Bu görevin iki işi:** (1) Codex'in her değerini resmi belgede **doğrulamak**; (2) eksikleri **doldurmak**. Asıl önem sırası: f3 > sermaye alanları (post_ipo_share_capital, capital_increase_shares, existing_share_sale_shares, additional_sale_shares) > PB planlanan yapı > aday özellikler.

## SONUÇ KÖRLÜĞÜ (kesin kural)
- Bu 135 şirketin **ilk işlem gününden sonraki hiçbir fiyat, getiri, tavan/taban, hacim ya da performans bilgisine bakma, yazma, özetleme.**
- THB/THM bültenleri İNDİRİLMEZ. Haber, forum, aracı kurum performans raporu, fiyat sayfası AÇILMAZ.
- KAP listelerinde listeleme sonrası bildirim başlıkları (ör. devre kesici) istemeden görülürse `verified/EXPOSURE.md`'ye yaz (ticker + ne görüldü, değer yazmadan) ve raporda say. Bu kodlar kasaya giremez (KARARLAR D2).
- Belge yayın zamanı (KAP sunucu zamanı) ilk işlem gününden (İstanbul) ÖNCE olmalı; değilse o belge girdi kaynağı olamaz.

## Çıktı düzeni (repo düzeninin aynası; sonra tek kopyayla repoya alınacak)
```
~/Desktop/BorsAi_codex/verified/
  registry/oot/inputs/<T>.json            # şema borsai.inputs/1, registry/inputs/CITAS.json biçiminde
  registry/oot/source_docs/<T>/<id>_*.pdf # resmi kaynaktan YENİDEN indirilmiş belgeler + MANIFEST.json (sha256, url, published_at, accessed_at)
  registry/oot/candidate_features/<T>.json # aday özellikler (model girdisi DEĞİL), aynı kayıt biçimi
  REPORT.md, EXPOSURE.md, coverage.csv, verification_log.jsonl
```
- `inputs/<T>.json`: `registry/inputs/CITAS.json`'daki alan adları ve kayıt biçimi aynen. `stage`: talep sonucu belgesi varsa `POST_BOOKBUILD_PRE_LISTING`. `collection_rules` CITAS'takiyle aynı ilkeler + "Codex çıkardı, Claude doğruladı". Her alan için: `value` (belgedeki yazımdan; binlik nokta atılır, ondalık virgül noktaya), `source_id`, `source_document`, `source_published_at`, `source_sha256`, `source_path` (repo içi hedef yol: `registry/oot/source_docs/<T>/…`), `quote` (belgeden birebir), `cross_checks` (varsa: SPK yıllık tablo, ikinci belge), `provenance`: `CODEX_VERIFIED` | `CODEX_CORRECTED` (Codex'in değeri belgeyle tutmadı, düzeltildi; eski değer `codex_value`'da) | `FILLED_BY_CLAUDE_VERIFIER`. Bulunamayan alan `null` + `missing_reason`.
- Doğrulanmış her dosya repo doğrulayıcısından geçmeli: `borsai.registry.validate_inputs(doc)` boş liste; `inputs_pit_problems(doc, root=<verified kökü>, as_of=<first_trading_date öncesi uygun an>)` boş liste. Doğrulayıcının eski kohortta uygulanamayan bir koşulu varsa (ör. `SCOPE_START`) kodu DEĞİŞTİRME; hangi kontrolün neden uymadığını `REPORT.md`'ye yaz.
- `candidate_features/<T>.json`: `investor_count`, `investor_count_by_group`, `retail_demand_multiple`, `domestic_institutional_demand_multiple`, `foreign_institutional_demand_multiple`, `distributed_by_group`, `retail_allocation_pct`, `domestic_institutional_allocation_pct`, `foreign_institutional_allocation_pct`, `distribution_method`, `lead_broker`, `price_stability_planned`, `price_stability_days`, `issuer_lockup_days`, `shareholder_lockup_days`, `sector`, `participation_index_eligible`, `market`, `sale_method`. Adlar H99 ana tablosuyla (`data/raw/HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv`) aynı; kayıt biçimi yukarıdaki gibi.

## Adımlar
0. Klasörleri ve Codex çıktılarını oku; `docs/specs_faz6/ekler/evren_listesi.csv` (135 MEMBER) ile ticker/tarih eşleşmesini göster.
1. **Doğrulama:** Codex'in her OK değeri için belgeyi resmi URL'den yeniden indir (Codex'in yerel kopyası varsa sha'ları karşılaştır), sha256'yı pinle, değeri belge metninde bul (metin katmanı yoksa OCR). Yayın zamanını KAP'tan doğrula. Sonuç: VERIFIED / CORRECTED / UNVERIFIABLE (UNVERIFIABLE değer girdi olmaz).
2. **Doldurma**, önem sırasıyla:
   - f3: talep toplama bitişi ile ilk işlem günü arasındaki dar tarih pencerelerinde (1–5 gün) KAP sorguları. Aracı kurumların gönderdiği "Halka Arz Sonuçları", "Talep Toplama Sonuçları" ve ÖDA bildirimleri ile ekleri. Borsada satış arzlarında BIST birincil piyasa sonuç duyurusu, yalnız listeleme öncesi yayımlandıysa.
   - Sermaye alanları ve PB planlanan yapı: SPK haftalık bülteni A.1 ("İlk Halka Arzlar"), izahname, TSSD. Planlanan yapı talep toplamadan önce yayımlanmış olmalı.
   - Aday özellikler: izahname/TSSD (fiyat istikrarı, satmama taahhüdü, katılım beyanı, sektör), sonuç bildirimi (katılımcı, dağıtım).
   - Talep katı tanımı ve filtre durumu `docs/DATA_NOTES.md` §4–§5 kuralıyla (ek satış payda sorunu dahil).
3. **Denetim:** bütün dosyalar doğrulayıcıdan geçer; `coverage.csv` (ticker × alan: VERIFIED / CORRECTED / FILLED / MISSING). Rastgele 10 arzda (tohum 20260924) bütün alanları baştan ikinci kez kontrol et; sonucu `REPORT.md`'ye yaz.
4. `REPORT.md`:
   - alan başına kapsama (önce/sonra);
   - Codex doğruluk oranı (VERIFIED / CORRECTED / UNVERIFIABLE);
   - model başına "girdisi tam olan arz sayısı" (f3 isteyen 5 model, PB modelleri, V1.5 ailesi);
   - kalan boşlukların nedenleri; maruziyet;
   - süre ve istek sayısı.

Tek oturumda bitmezse: yapılan kısmı yaz, `REPORT.md`'de kalan listeyi ver. Her ticker dosyası kendi içinde tam ve doğrulayıcıdan geçer olmalı (yarım dosya bırakma).

## Kurallar
- Resmi olmayan kaynak değer kaynağı olamaz (yalnız `cross_checks`'te `secondary: true`). SPK yıllık Excel tabloları yalnız çapraz denetimdir.
- Tahmin, türetme (belgede iki nominal yazılıysa oran hariç; `derived: true` + formül), ortalama, ilişki analizi YOK.
- `borsai/`, `tests/`, repo içi hiçbir dosya değişmez.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- KAP API'sinde istekler arası 3–4 s bekle, 429'da geri çekil.
- Rapor Türkçe.

## Kabul kapısı
- K1 135 ticker için `inputs/<T>.json` var ve doğrulayıcıdan geçiyor (eksik alanlar `null` + neden).
- K2 Her değer resmi, pinlenmiş, listeleme öncesi yayımlanmış bir belgede birebir bulunuyor; `provenance` alanı dolu.
- K3 f3 kapsaması raporlandı; boşlukların her birinin nedeni yazılı.
- K4 Sonuç körlüğü: THB/THM indirilmedi; maruziyet dosyası var (boş olsa bile).
- K5 Repoda hiçbir dosya değişmedi (`git status` önce/sonra aynı; paralel oturumun kendi değişiklikleri hariç).

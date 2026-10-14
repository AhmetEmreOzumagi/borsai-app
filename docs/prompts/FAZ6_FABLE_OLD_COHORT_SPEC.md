# TASK_ID: BORSAI_FAZ6_FABLE_OLD_COHORT_SPEC_20260924

Model: Fable · yüksek. Klasör: ~/Desktop/BorsAi (arşiv `~/Desktop/Halka_Arz_Modeli` salt okunur taranabilir).
- **Ağ: açık.** Web'i serbestçe kullan (resmi kaynaklar öncelikli: KAP, SPK, Borsa İstanbul; ikincil kaynak etiketlenir). Her iddia için URL + erişim zamanı.
- Git: YALNIZ okuma komutları, her zaman `GIT_OPTIONAL_LOCKS=0` öneki. Sonda tek commit, yalnız kendi yollarınla. push/tag/amend yok.
- Yazma: YALNIZ `docs/specs_faz6/` (+ `ekler/`) ve bu görev dosyası. Geçici işler `/tmp/borsai_faz6/` altında. `ekler/` ≤ 5 MB.
- **Paralel oturum:** Opus `docs/prompts/FAZ5_FREEZE.md`'yi koşuyor (`models/`, `tests/`, `experiments/`, `docs/MODELS.md`, `docs/SPEC_DEVIATIONS.md`, `docs/faz5/` yazar ve commit eder). Ağaç kirli görünebilir; DURMA. Onun dosyalarına dokunma, commit'ine alma. `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.

## Bağlam
- Bütün modellerimiz H99 üzerinde tasarlandı ve eğitildi: 99 arz, ilk işlem 2023-09-22…2026-08-06. H99'un başlangıç tarihi bir kural değişikliği değil. Eski repo QUICK'ten (2026-08-06) geriye doğru "son 100 arz"ı saydı ve 99'unu bağlayabildi (`data/raw/HISTORICAL99_FROZEN_COHORT_V1_canonical_membership.csv`: `original_target_universe_size` 100, `known_membership_gap_count` 1).
- Öncesinde yaklaşık 125–135 arz var. İkincil kaynaklara göre: 2020'de 8, 2021'de 52, 2022'de 40 civarı, 2023'te 54–55 (bunların ~19'u H99'da). Bu sayıları resmi kaynaktan doğrula.
- Dondurulmuş modeller: `models/INDEX.json`'da 19 listeleme öncesi model; `post_d1_hazard_v0` bu sırada `models/INDEX_POST_D1.json`'a donduruluyor. Hiçbiri bu eski arzları görmedi (eski repo için bunu sen denetleyeceksin).
- **Amaç:** bu eski arzları, sonuçlarına bakmadan, dürüst bir protokolle projeye almak. Üç kullanım:
  - (A) **Donmuş modellerin dış örneklem testi**: tahminler, eski arzların sonuçları repoya girmeden kaydedilir, sonra skorlanır. Canlı sicil ayda ~3 arzla büyüyor; bu, benzer kanıtı haftalar içinde verir. Dönem farkı (2021 halka arz dalgası) ayrıca bilgidir: rejim değişince modeller ne kadar bozuluyor.
  - (B) **Eğitim verisini büyütmek** (sonraki model kimlikleri; CLAUDE.md kural 5).
  - (C) **Azınlık sınıfı sorusu** (proje sahibinin fikri): D1'de tavan yapmayan ya da arz fiyatının altına düşen arzları ayıran listeleme öncesi özellikler var mı? H99'da D1'de tavan yapmayan 18, D1'de arz altında kapanan 10, D10'da arz altında 29. Bu kadar az olayla H99'da keşfedip yine H99'da test etmek sahte iyileşme üretir. Doğru tasarım: bir kümede keşif, dokunulmamış başka kümede doğrulama.
- Proje kuralları `CLAUDE.md`'de. İki terazi (backtest, canlı) asla toplanmaz. Eski arzlar bu ikisinin hiçbiri değildir: üçüncü, ayrı bir ölçek olur. Bunun kurala nasıl gireceği proje sahibinin kararıdır, sen öner.

## SONUÇ KÖRLÜĞÜ (en önemli kural)
Bu görevde eski arzların **listeleme sonrası hiçbir fiyat, getiri, tavan ya da hacim bilgisine bakılmaz**:
- Kohort penceresindeki tarihli THB/THM bültenleri indirilmez ve açılmaz. Biçim denetimi için yalnız kohort başlangıcından ÖNCEKİ bir tarihin bülteni (ya da yalnız başlık satırları) kullanılır. Hangi tarihi kullandığını yaz.
- "2021 halka arzları kaç tavan yaptı", "en çok kazandıran halka arzlar", aracı kurum performans raporları gibi sayfalar açılmaz. Arama sonuçlarında istemeden görülürse "Maruziyet" bölümüne yazılır.
- Model eğitimi, tahmin ya da skor hesabı yok.
- Senin (dil modeli olarak) bu dönem hakkındaki ön bilgin bir maruziyettir; beklentileri yazarken bunu açıkça not et.

ÖNCE OKU:
- CLAUDE.md
- docs/DATA.md, docs/DATA_NOTES.md (H99 alanları ve kaynakları)
- docs/specs/SPEC_SCORING.md (tamamı), docs/specs/ altındaki SPEC_V1_6, SPEC_PB_V0, SPEC_CEILING_V0, SPEC_MARKET20_V0 girdi bölümleri (V1.5 girdileri: docs/DATA.md ve borsai/features.py); docs/specs_faz4/SPEC_CEILING_PATH_V0.md §2 (fiyat adımı, limit yolu); docs/specs_faz5/SPEC_POST_D1_V0.md §2, §7
- docs/prompts/FAZ2A_REGISTRY_INPUTS.md ve `registry/inputs/`, `registry/source_docs/<T>/MANIFEST.json` (bugünkü girdi toplama biçimi)
- borsai/features.py, borsai/registry.py (`model_inputs`, `inputs_pit_problems`), borsai/outcomes.py (bülten indirme, alan eşlemesi) — yalnız okumak için
- `data/raw/official_bist_xu100_graphic_pinned_through_20260819.json` (XU100 1986'dan beri; f6 için yeterli mi, denetle)
- Arşiv: CLAUDE.md'nin andığı envanter `docs/checkup_20260921/CHECKUP.md` bu repoda yok; arşivde (`~/Desktop/Halka_Arz_Modeli`) ara, yoksa arşivi doğrudan tara

## Teslimler

### 1. `docs/specs_faz6/FEASIBILITY.md` — ne var, ne yok, ne kadar sürer
- **a. Evren:** 2020-01-01…2023-09-21 arasında Borsa İstanbul pay piyasasında ilk kez işlem gören bütün arzların resmi listesi (kaynak: SPK ihraç ve halka arz verileri, BIST, KAP). Yıllara göre sayı. H99'un en eski üyeleriyle sınırın denetimi. Yapabiliyorsan H99'un eksik 100. üyesini de bul (sonuç bilgisine bakmadan, yalnız liste). Liste `ekler/evren_listesi.csv`: ticker, şirket, ilk işlem tarihi, pazar, kaynak URL, erişim zamanı.
- **b. Girdi alanları:** her donmuş modelin girdileri (V1.5 alanları ve talep katı + filtre durumu; PB modellerinin planlanan yapı alanları, zaman damgalı; f6 için XU100; tavan-yolu için arz fiyatı ve fiyat adımı; post_d1 için D1 bülten alanları): eski arzlar için hangi resmi belgede (izahname, fiyat tespit raporu, talep toplama sonuç bildirimi, SPK bülteni) ve yayın zamanı ne. Her yıldan (2020, 2021, 2022, 2023) en az 2 arzda **yalnız listeleme öncesi belgelerle** örnek denetim. Point-in-time sorunları (belge sonradan güncellenmiş mi, yayın zamanı kanıtlanabiliyor mu).
- **c. Sonuç verisi:** BIST THB/THM arşivinin 2020–2023 için erişilebilirliği ve biçimi (URL kalıbı, dosya adı, kodlama, sütun adları; `borsai/outcomes.py` eşlemesiyle fark). Yalnız kohort öncesi bir tarihle ve başlık düzeyinde. sha pinleme planı.
- **d. Kural ve rejim farkları:** o dönemle bugün arasında modellerin tanımını etkileyebilecek her kural, tarihiyle ve resmi kaynağıyla: günlük fiyat marjı ve ilk gün baz fiyatı, fiyat adımı tablosu (Faz 4 limit yolu buna bağlı), THM marj hesabı, pazar/segment, tahsis yöntemi (eşit/oransal, bireysel pay), satış yöntemi (Borsada satış / talep toplama), SPK düzenlemeleri (fiyat istikrarı, satmama taahhüdü, 2022–2023 değişiklikleri), açığa satış yasakları, devre kesici. Her biri için her donmuş modele etkisi: yok / etiketle / model bu arzda uygulanamaz.
- **e. Eski repo maruziyeti:** `~/Desktop/Halka_Arz_Modeli` 2023-09-22 öncesi herhangi bir arzın girdisini ya da sonucunu toplamış, incelemiş ya da modelde kullanmış mı? Dosya yollarıyla kanıt. Kullandıysa hangi kısmı ve bunun (A)'ya etkisi.
- **f. Yeni aday özellikler (C için; ilişkiye BAKMADAN):** katılımcı sayısı (kategori başına), kişi başı lot ve bireysel tahsisat payı, aynı hafta içinde listelenen arz sayısı, katılım endeksine uygunluk, fiyat istikrarı (var/yok, süre, tutar), satmama taahhüdü (kapsam, süre), lider aracı kurum. Her biri için: resmi kaynak, listeleme öncesi yayın zamanı, H99 ve eski kohortta elde edilebilirlik, toplama maliyeti ve tavan/kırılma mekaniğiyle ilişkisinin sonuç görmeden gerekçesi.
- **g. İş planı:** toplama için görev bölümü (hangi model, hangi yıllar paralel, hangi yollar), tahmini süre, commit sırası.

### 2. `docs/specs_faz6/SPEC_OOT_PRE_H99_V0.md` — protokol (sonuç görülmeden, bağlayıcı taslak)
- **Kohort üyeliği:** deterministik kural, resmi listeden; sonuç verisinden önce dondurulur ve push edilir. Payda: her üye bir satır; eksik girdi etiketli "atlandı" ya da RET.
- **Sıra (kodla zorlanacak):** şartname push → üyelik + girdiler (yalnız listeleme öncesi; belgeler ve sha'lar) push → 19 listeleme öncesi donmuş modelin tahminleri (yeni kayıt türü; `registry/records/` DEĞİL) push → D1 bültenleri + `post_d1_hazard_v0` tahminleri push → D2..D10 sonuçları → skorlama. Her adımın bekçisi (`tests/test_outcome_guard.py` kalıbı) tanımlanır.
- **Üçüncü ölçek:** adı, tanımı, backtest ve canlıyla neden ve nasıl hiç birleşmeyeceği (`ScaleMixError`), uygulamada nasıl gösterileceği.
- **Skorlama:** SPEC_SCORING §7–§8 tanımları; her modelin birincil hücresi (backtest/canlıdakiyle aynı); karşılaştırılanlar H99'da donmuş basit kurallar (yeniden eğitilmez); aralık yöntemi; n kuralları.
- **Rejim farkı kuralları** (1d'den): hangi arzda hangi model uygulanamaz ya da etiketlenir — sonuçtan önce.
- **Önceden yazılmış beklenti:** her modelin birincil hücresi için yön ve aralık, gerekçesiyle (dönem farkı dahil). LLM ön bilgisi maruziyeti notuyla.
- **Kasa (vault) önerisi:** (A) bütün eski arzların sonuçlarını açarsa, onlar da "görülmüş" olur ve (C)'deki yeni özellikleri doğrulamak için temiz küme kalmaz. Seçenekleri değerlendir: ör. eski kohortun bir kısmını (bir yıl ya da rastgele tohumlu yarı) mühürlü tutmak: girdiler toplanır, sonuçlar yeni bir özellik ön-kayıtlanana kadar repoya alınmaz. Kaç arz ayrılırsa (A) ve (C) ne kaybeder, ne kazanır; önerini sayılarla yaz.
- **Açık sorular** (proje sahibine, en çok 5, her birine önerinle): kohort başlangıç tarihi (2020 mi 2021 mi), üçüncü ölçeğin CLAUDE.md'ye giriş cümlesi, kasa oranı, eski arzların sonraki eğitimlerde kullanılması, gerekirse diğerleri.

### 3. `docs/specs_faz6/ekler/`
Evren listesi, kaynak URL'leri ve erişim zamanları (`kaynaklar.json`), örnek belge sha'ları, biçim probu çıktıları, arşiv tarama kanıtları. Büyük belge kopyalama; ekler ≤ 5 MB.

## Adımlar
0. `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -3`, `git status --porcelain` (paralel oturum yüzünden kirli olabilir; kaydet, durma).
1. Evren ve eski repo maruziyeti (1a, 1e).
2. Girdi, sonuç verisi ve kurallar (1b, 1c, 1d).
3. Yeni aday özellikler (1f) ve iş planı (1g).
4. Protokol şartnamesi (2).
5. Bekçi kalıbı denetimi (`grep -rE 'th[bm]20[0-9]{6}' docs/specs_faz6` boş olmalı), commit, rapor.

Tek oturumda bitmezse: FEASIBILITY 1a–1e tamamsa `(partial)` commit, kalanı raporda.

## Kurallar
- Sonuç körlüğü (yukarıda). İhlal olursa ne gördüğünü açıkça yaz; gizleme.
- `borsai/`, `tests/`, `models/`, `data/`, `registry/`, `scores/`, `experiments/`, `app/`, `docs/specs*` (faz6 hariç) salt okunur.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- Rapor Türkçe. Resmi olmayan kaynak "ikincil" etiketlenir.
- `git add -A` yok. Commit:
  ```
  git add docs/specs_faz6 docs/prompts/FAZ6_FABLE_OLD_COHORT_SPEC.md
  git commit -m "BORSAI_FAZ6_SPEC: pre-H99 IPO cohort feasibility and out-of-time evaluation protocol, outcome-blind" -- docs/specs_faz6 docs/prompts/FAZ6_FABLE_OLD_COHORT_SPEC.md
  ```

## Teslim (rapor)
- Commit hash'i ve `git show --stat`.
- Evren: yıllara göre arz sayısı, kaynak.
- Veri: girdiler ve sonuçlar için "var / kısmen / yok" tablosu.
- Rejim farkları tablosu ve modellere etkisi.
- Eski repo maruziyeti hükmü.
- Kasa önerisi ve açık sorular.
- Tahmini toplama süresi ve iş bölümü.
- Maruziyet beyanı.

## Kabul kapısı
- K1 Evren listesi resmi kaynaktan, yıllara göre sayılarla; her satırda URL ve erişim zamanı.
- K2 Her donmuş model girdisi için kaynak ve point-in-time durumu yazılı; en az 8 arzda örnek denetim.
- K3 Kural farklarının her biri resmi kaynakla ve modellere etkisiyle.
- K4 Protokol: üyelik, sıra, bekçiler, üçüncü ölçek, skorlama, önceden yazılmış beklenti, kasa önerisi.
- K5 Kohort penceresinden hiçbir sonuç bilgisi okunmadı (maruziyet beyanı); commit yalnız `docs/specs_faz6/` ve bu görev dosyası.

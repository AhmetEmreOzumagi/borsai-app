# TASK_ID: BORSAI_FAZ7_FABLE_C_SPEC_20260927

Model: Fable · yüksek. Klasör: ~/Desktop/BorsAi.
- **Ağ:** yok.
- **Git:** YALNIZ okuma komutları ve her zaman `GIT_OPTIONAL_LOCKS=0` öneki. Sonda commit yalnız kendi yollarınla. push/tag/amend yok.

## Rol
"(C)" sorusunun keşfini yaparsın ve doğrulamasını önceden kaydeden şartnameyi yazarsın. Soru SPEC_OOT_PRE_H99_V0 §9'daki şu: "D1'de tavan yapmayan ya da arz fiyatının altına düşen azınlığı ayıran bir listeleme öncesi özellik var mı?"

Proje sahibi aynı soruyu kendi sözleriyle şöyle sordu: "Düşen halka arzların ortak özellikleri ne? Yükselenlerden hangi özellikleriyle ayrılıyorlar?"
- Keşif kümesi: H99 (99) + eski kohortun açık kümesi (71).
- Doğrulama kümesi: kasa (64). Kasa tek seferlik açılır ve bu şartnameyle `ceiling_hazard_v1` ailesinin kasa testi birlikte doğrulanır (SPEC_HAZARD_V1 §7.1, §7.4; `docs/specs_faz7/KARARLAR.md` K1).
- Bu şartname push edilmeden kasa açılmaz. Açıldıktan sonra (C) için ikinci bir temiz küme ancak canlı sicilden kurulabilir.

Sen şartname ve keşif yazarısın. Uygulamayı Opus yapacak, bağımsız yeniden üretimi yine sen yapacaksın.

## Hijyen (sert kurallar)
- **Kasa üyelerinin hiçbir dosyası açılmaz, okunmaz:** özellik dosyaları, girdiler, kayıtlar ve kaynak MANIFEST'leri dahil.
  - Açık küme listesi `data/outcomes_oot/*.csv` adlarıdır (71).
  - Kasa hakkında izinli tek şey betikle hesaplanan **sayımlardır**: kasada yıl, rejim ve alan başına dolu değer sayısı. Güç hesabı için gerekir. Kod adı ya da değer basılmaz.
- Hangi kodun kasada olduğu hiçbir dosyaya, çıktıya ya da metne yazılmaz ve ekrana basılmaz.
- **Okunmaz:**
  - `docs/faz6/dogrulama/EXPOSURE.md` (tamamı);
  - `docs/faz7/prospectus/EXPOSURE.md`;
  - Codex'in `exposure_log` alanları ve satırları;
  - `~/Desktop/BorsAi_quarantine`, `~/Desktop/BorsAi_codex`.
- Canlı sicilin 7 arzı (`data/outcomes/`) keşfe girmez; onlar zaten (C) modelleri için RETRO olacak.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.

## Paralel
- Bir Opus oturumu `docs/prompts/FAZ7_FREEZE.md`'yi koşuyor: `borsai/`, `tests/`, `models/`, `experiments/`, `docs/MODELS.md`, `docs/SPEC_DEVIATIONS.md`, `docs/PROVENANCE.md`, `docs/faz7/`, `data/raw/tuik/build_tufe_csv.py`. Onlara dokunma.
- Commit'in yalnız `docs/specs_faz7_c/` ve bu görev dosyası. `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.

ÖNCE OKU:
- CLAUDE.md
- docs/specs_faz6/SPEC_OOT_PRE_H99_V0.md (özellikle §2, §6, §8, §9), docs/specs_faz6/KARARLAR.md (D2, D4, D6), docs/specs_faz6/FEASIBILITY.md
- docs/specs_faz7/SPEC_HAZARD_V1.md (kalıp olarak §5–§7, §10–§13) ve KARARLAR.md
- docs/fable_faz7_audit/AUDIT.md §6 (dönem etkisi dersi: 2023'ün uzun serileri havuzlu modeli bozdu)
- docs/SCORES_OOT.md, docs/fable_faz6_s6/AUDIT.md (açık kümede donmuş modellerin davranışı)
- docs/faz7/prospectus/README.md ve REPORT.md (alan tanımları §3, boşluk nedenleri §4)
- docs/specs/SPEC_SCORING.md (§2, §3, §7, §8: hüküm dili, n kuralları, bootstrap)
- docs/MODELS.md (V1.5'in P(kapanış > arz), `ceiling_hazard_v0` S_1 ve PB modelleri: karşılaştırıcı adayları)
- Veri (listeleme öncesi):
  - `data/raw/HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv` ve provenance/readiness dosyaları;
  - `data/raw/PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv`;
  - `data/training_table.csv`, `data/training_table_v2.csv`;
  - yalnız açık üyeler için `registry/oot/inputs/`, `registry/oot/candidate_features/` (Faz 6) ve `registry/oot/candidate_features_faz7/` (Faz 7, 7 alan);
  - `registry/oot/cohort_pre_h99.csv` (yalnız açık satırlar ve sayımlar).
- Veri (sonuç):
  - H99: `data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_*`;
  - açık küme: `data/outcomes_oot/<T>.csv`.
- Canlı girdi şeması: `registry/inputs/*.json` ve `borsai/registry.py` (canlı uygulanabilirlik için).

## Adımlar

**1. Olay tanımları ve sayımlar [ÖLÇTÜM]**
- Aday hedefler:
  - (y1) D1'de tavan yok (L = 0);
  - (y2) D1 kapanışı < arz fiyatı;
  - (y3) D5 kapanışı < arz fiyatı;
  - (y4) D10 kapanışı < arz fiyatı.
- Her biri için H99 ve açık kümede sayı ve oran; yıl ve rejim (`alloc_regime`) kırılımı.
- Kasa için yalnız beklenen olay sayısı: açık küme ve H99 oranlarından, kasanın yıl/rejim sayımlarıyla ağırlıklı. Kasanın sonuç satırları yoktur ve açılmaz.
- **Birincil hedef tek olur**, ilan edilmiş ikinci hedef en çok 2. Gerekçe:
  - hüküm eşiği (SPEC_SCORING §8: n ≥ 30 ve aralık 0'ı dışlarsa "geçiyor");
  - kasada beklenen olay sayısı;
  - ürün değeri ("düşer mi" sorusu);
  - var olan modellerin bu olayı zaten ne kadar iyi gördüğü.

**2. Özellik envanteri ve tanım uyumu**
- Listeleme öncesi her aday alan için H99 ile açık kümede kapsama ve tanım uyumu:
  - Faz 7'nin 7 alanı;
  - Faz 6 aday alanları (grup talep katları, tahsis oranları, yatırımcı sayısı, dağıtılan grup, pazar, satış yöntemi, lider aracı kurum);
  - model girdileri (f1 büyüklük, f2, f3 talep katı, PB, market20, rejim).
- Özellikle şunlara bak:
  - `shareholder_lockup_days` toplama kuralı (REPORT §3: "ilk gevşeyen gün", `components`) ile H99 master'daki değerlerin kodlama kuralı;
  - 30.03.2023 tarihli 20/412 ilke kararının 180 günlük zorunlu kısıtı (rejimle karışma riski);
  - `distribution_method` kategorileri;
  - `sector`'ün ayrıntı düzeyi;
  - `participation_index_eligible`'ın yapısal boşluğu (2022-06 öncesi beyan yok).
- Uyumsuz alan ya dışlanır, ya da iki kümede aynı kuralla yeniden türetilir. H99 için yeniden türetme `components` gibi bir kaynak gerektiriyorsa bunu **ön koşul görevi** olarak yaz: kapsam, maliyet, kim yapar. Bu durumda şartname o alanı ancak ön koşul tamamlanınca kullanır.
- **Canlı uygulanabilirlik:** seçilen her özellik yeni bir arz için listeleme öncesi resmi belgeden (izahname, SPK bülteni, KAP) T'den önce elde edilebilir olmalı.
  - Canlı girdi şemasında (`registry/inputs`) alan yoksa, şema genişlemesi uygulama görevinin parçası olarak yazılır: alan adı, tür, kaynak, PIT kuralı.
  - Canlıda elde edilemeyen özellik şartnameye giremez.

**3. Keşif** [KEŞİF etiketli; H99 + açık küme]
- **Tek değişkenli:** her aday özellik için düşenler ile diğerlerinin dağılımı ve oran farkı. Kategorik alanlarda seviye oranları.
- **Dönem dayanıklılığı:** her bulgu H99 ve açık kümede ayrı ayrı ve rejim kırılımıyla. Yalnız bir dönemde görülen ayrım zayıf aday sayılır. Havuzlu v1'in dersi (AUDIT §6) açıkça dikkate alınır.
- **Çok değişkenli:** en çok 3 özellikli küçük modeller (L2 lojistik ya da tek eşikli kural). Karşılaştırıcılar:
  - taban oran;
  - var olan donmuş modellerin olasılığı: (y1) için `ceiling_hazard_v0` S_1; (y2)–(y4) için V1.5 P(kapanış > arz);
  - uygun PB modeli.
- **Çokluk dürüstlüğü:** denenen her özellik, eşik ve model varyantını say ve listele (`docs/specs_faz7_c/ekler/denenenler.csv`). Şartnamede toplam sayı ve seçilenin bu listeden nasıl seçildiği yazılır.
- **Sade özet:** `docs/specs_faz7_c/KESIF.md`'nin başında proje sahibi için, Türkçe, 10–15 satır: "Düşenlerin ortak yanları, yükselenlerden ayrılan yanları, ne kadar güvenilir oldukları."
  - Etiket: keşif, H99 + açık küme, doğrulanmadı.
  - Uzun rapor ve tablolar altında.

**4. Şartname** — `docs/specs_faz7_c/SPEC_C_V0.md` (SPEC_HAZARD_V1 kalıbı)
- **Model kimlikleri:** 1–3 aday, az parametreli; yeni fikir yeni kimliktir.
- Hedef, özellikler (tam tanım, ham alan, dönüşüm, kırpma, eksik değer davranışı, ret kodları) ve eğitim kümesi. Eğitim kümesi için H99 mi, H99 + açık mı? Karar önceden yazılmış bir yakın dönem testiyle verilir; v1'deki "bozuyor / tolerans içinde / belirsiz" kalıbı.
- Model biçimi, amaç, ızgara, iç CV, çözücü.
- **Önceden yazılmış testler:**
  - (i) yakın dönem (H99 walk-forward, ilk işlem ≥ 2024-01-01);
  - (ii) kasa (tek seferlik): birincil hücre, karşılaştırıcı, n ve beklenen olay sayısı, "geçiyor" koşulu;
  - (iii) canlı.
- **Önceden yazılmış beklenti** (§6 kalıbı): her hücre için beklenen fark, aralık ve gerekçe. Beyan: keşif kümesini gördün, kasayı görmedin.
- **Başarısızlık tanımları** aynı sözcüklerle.
- **Kasa planı:** v1 ile birlikte tek seferde açılış sırası. SPEC_HAZARD_V1 §7.1 adım 3–6 ile tutarlı:
  - (C) modellerinin dondurulması ve eski kohort kayıtları kasa açılışından önce;
  - model başına kapı;
  - `oot_pre_h99_sealed` anahtarı.
- **Maruziyet beyanı** (§10 kalıbı): ne gördün, neyi görmedin; açık küme sonuçlarını S6'dan beri biliyorsun.
- **Uygulama bölümü** (Opus için):
  - dosya ve fonksiyon listesi;
  - canlı girdi şeması genişlemesi;
  - eski kohort kayıtlarında (C) girdilerinin kaynağı: `registry/oot/candidate_features_faz7/` ve Faz 6 dosyaları; kasa üyeleri için de yalnız listeleme öncesi alanlar okunur.
- **Uygulamadaki gösterim** (kısa): hangi çıktı, hangi sözcüklerle, hangi terazi etiketiyle.
- **Kabul testleri** (kanıtlanabilir) ve **sözde kod**.
- **Açık sorular:** en çok 5; her birine önerin. Proje sahibi adına orkestratör cevaplar.
- **Ön koşul görevleri** (varsa, adım 2'den).

**5. Ekler** — `docs/specs_faz7_c/ekler/`
- Keşif betikleri; `borsai` import edebilir ama hiçbir dosyaya yazmaz.
- Tablolar, `denenenler.csv`.
- Kasa sayım betiği ve çıktısı (yalnız sayı).

## Kurallar
- Yazılabilir: yalnız `docs/specs_faz7_c/` ve bu görev dosyası. Geri kalan her şey salt okunur.
- Keşif betikleri repoya ya da `experiments/log.jsonl`'a yazmaz. Denenen varyantlar `denenenler.csv`'dedir; uygulama görevi bunları günlüğe `kind: exploration` satırları olarak ekler.
- Rapor ve şartname Türkçe.
- `git add -A` yok. Commit:
  ```
  git add docs/specs_faz7_c docs/prompts/FAZ7_FABLE_C_SPEC.md
  git commit -m "BORSAI_FAZ7_C_SPEC: falling-IPO minority discovery on H99 and the open set, pre-registered spec for the one-time vault test" -- docs/specs_faz7_c docs/prompts/FAZ7_FABLE_C_SPEC.md
  ```

## Tek oturumda bitmezse
Keşif (1–3) tamamsa `KESIF.md`'yi ve şartnamenin eldeki taslağını `(partial)` mesajıyla commit et. Taslak olduğu şartname başında açıkça yazılı olsun. Kasa açılışı tamamlanmış şartname olmadan başlamaz.

## Teslim (rapor)
- Commit hash'i ve `git show --stat`.
- Birincil hedef ve gerekçesi; H99, açık küme ve kasa için beklenen olay sayıları.
- Seçilen model kimlikleri ve özellikleri (tek satır tanım).
- Denenen varyant sayısı.
- Ön koşul görevleri (varsa) ve canlı girdi şeması genişlemesi.
- Açık sorular (önerileriyle).
- Hijyen beyanı: kasa dosyası açılmadı, yalnız sayım.

## Kabul kapısı
- **K1** Birincil hedef tek. Olay sayıları H99, açık küme ve kasa (beklenen) için yazılı.
- **K2** Her seçilen özellik iki kümede aynı tanımla var, canlıda elde edilebilir. Değilse ön koşul görevi yazılı.
- **K3** Şartname testleri, beklentileri, başarısızlık tanımlarını, kasa planını, maruziyet beyanını ve kabul testlerini içeriyor. Çokluk sayısı yazılı.
- **K4** `KESIF.md`'nin başında proje sahibi için sade özet var.
- **K5** Kasa üyelerinin dosyası açılmadı; commit yalnız izinli yollarda.

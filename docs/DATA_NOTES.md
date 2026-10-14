# Veri anlamı notları

Bu sayfa, eski repodaki veri tanımı hükümlerinin özetidir. Yönetişim hükümleri (seviye sınıfları, terfi kapıları, tek kullanımlık yetkiler) bilerek dışarıda bırakıldı. Kaynak yolları eski repoya (`~/Desktop/Halka_Arz_Modeli`, arşiv) göredir. Defter = `artifacts/governance/DECISION_LEDGER.csv`; satır numarası fiziksel satırdır (1 = başlık).

**1. f2 (halka açıklık oranı) formülü ön kayıtta tanımlı değil.**
- Ne V1 ön kaydı ne de `config/model_v1_5_spec.json` f2'yi tanımlıyor.
- Fiilen kullanılan tanım `config/ipo_master_schema.toml:159-161`'de: `shares_offered / post_ipo_share_capital × 100`.
- H99'un `feature_readiness.f2_formula` sütunu ve beş dondurulmuş kanıt satırı (BKRGY ×3, INTET ×2) f2'yi bu formülle hesaplıyor.
- `feature_assembly.py`'deki alternatif yol hiç çalıştırılmamış.
- Yeni repoda formül kodda açıkça yazılmalı.
- `shares_offered` 6 arzda ek satışı içerdiği için (madde 4), bu arzların f2'si de ek satışı içerir.
- Kaynak: defter satırı 40 (`BORSAI_F2_DEFINITION_LOOKUP_20260911_V1`, ACIK).

**2. NETGL'de planlanan ayrım: sermaye artırımı ile ortak satışı ayrımı arz öncesi belgeden taşındı.**
- NETGL'in `capital_increase_shares` değeri kesin talep sonucu bildiriminden okunmadı. Arz öncesi belgeden taşındı (SPK Bülteni 2026/56).
- Taşımaya ancak üç koşulun hepsi tutunca izin var:
  - (a) resmi sonuç bildirimi planlanan arzın tamamının satıldığını söylüyor;
  - (b) `shares_offered_final` planlanan toplamla aynı;
  - (c) ek satışın kullanılmadığı resmi belgede yazılı.
- Taşınan değer `PLANNED_SPLIT_CARRIED_FULL_SUBSCRIPTION` bayrağını alır. Kural sonraki her vakaya aynı koşullarla uygulanır.
- Yeni arz girişinde alan başına "kaynak belge türü" tutulmalı: sonuç bildirimi mi, arz öncesi belge mi?
- Kaynak: defter satırları 173–174 (`BORSAI_NETGL_PLANNED_SPLIT_RULING_20260916_V1`). 174'ün seviye sonucu yönetişimdir, buraya alınmadı.

**3. Ayrım sonuç bildirimlerinde çoğunlukla basılmıyor (S1: p = 0.30).**
- Soru: sermaye artırımı ile ortak satışı ayrımı sonuç bildirimlerinde ayrı kalem olarak ne sıklıkta yayımlanıyor?
- Ölçüm ön kayıtla donduruldu (satır 218). Örnek: 79'luk genişletmenin her 4. arzı (n = 20) ve 5 prospektif arz.
- S1 sonucu (satır 231):
  - tarihsel kol: 6 PUBLISHED, 3 PARTIAL, 11 NOT_PUBLISHED, yani p = 0.30;
  - prospektif kol: 2/5, yani p = 0.40.
- Bağımsız tekrar S2 henüz koşmadı; prompt'u satır 237'de mühürlendi.
- Veri anlamı: `capital_increase_shares` birçok satırda sonuç bildiriminden değil, arz öncesi belgeden (izahname/TSSD) gelen planlanan değerdir.
- Kaynak: defter satırları 218 (`BORSAI_SPLIT_PREVALENCE_PREREG_20260920_V1`) ve 231 (`…_COLLECT_20260920_S1`).

**4. Ek satış 6 arzda `shares_offered` içinde.**
- H99'da 93 arzda `shares_offered = capital_increase_shares + existing_share_sale`.
- 6 arzda ise buna kullanılan ek satış da ekli: GLRMK, ARMGD, HOROZ, OZYSR, MEGMT, BORLS.
- Bu 6 arzın f1'i (arz büyüklüğü) ve f2'si ek satışı içerir; f4'ün (sermaye artırımı payı) paydası büyür.
- `additional_sale_shares` 95 arzda dolu, ama bunların 89'u sıfır. Özellik olarak bilgisi 6 satırda (AUDIT §1.2-f).
- `shares_offered_final`'ın ek satışı içerip içermediği hiçbir sözleşmede yazılı değil. Yeni arz formu bunu tanımlamalı.
- Kaynaklar: `docs/checkup_20260921/CHECKUP.md:108`; `docs/checkup_20260921/detay/A1_V0_LIVEV0_V1x.md:264, 284`. Altı ticker bu repoda `data/raw/…_canonical_pretrade_master.csv`'den yeniden ölçüldü.

**5. f3 (toplam talep katı) karışık tanımlı.**
- Modelin en bilgilendirici girdisi, ama 97 dolu değer aynı şeyi ölçmüyor:
  - Köken: `SOURCE_REPORTED` 71, hesaplanmış 24 (`CALCULATED_FROM_SOURCE_TOTALS` 16, `…_PRIMARY_TOTALS` 8), `SOURCE_REPORTED_APPROX` 2.
  - Filtre durumu: 59'u `NOT_SPECIFIED`, 36'sı `UNFILTERED`.
  - `total_demand_definition` sütununda yaklaşık 30 farklı metin var. Payda kimi zaman ek satışı içeriyor, kimi zaman içermiyor (`…INCLUDING_ADDITIONAL_SALE` 2, `…EXCLUDING_…` 2, `…VS_PRE_ADDITIONAL_SALE_OFFER_SIZE` 1). Bir kısmı kaynakta yuvarlatılmış değer (`KAYNAK_YUVARLATILMIS_…`).
- V1.5 ön işlemesi `total_demand_filter_status`'u gizli altıncı girdi olarak alıyor. Ama H99'da tam `FILTERED` literal'i hiç geçmediği için filtre hiçbir satırı boşaltmıyor.
- Aynı yerdeki `mode = max(set(...), key=count)` eşitlik durumunda küme sırasına bağlı (`scripts/modeling/preprocessing.py:370`).
- Uygulama formundaki "talep katı" alanının tanımı (hangi kat, filtreli mi, payda neyi içeriyor) yeni arz girişi aşamasında sabitlenmeli.
- Kaynaklar: `docs/fable_audit_20260921/AUDIT.md:84` (§2.3) ve `:74` (§1.2-j). Sayımlar bu repoda `data/training_table.csv` ve `data/raw/…_canonical_pretrade_master.csv`'den yeniden ölçüldü.

**6. GOLDA dersi: eski rapordaki 10.12 TL arz fiyatı değil, D1 kapanışıydı.**
- Eski bir raporda GOLDA'nın arz fiyatı 10.12 TL yazıyordu. Resmi arz fiyatı 9.20 TL'dir (KAP 1623769).
- 10.12 aslında D1 kapanışıydı: 9.20 × 1.10 = 10.12, yani tavan.
- Bu repoda doğrulandı: `ipo_price_tl` = 9.2, D1 `close` = 10.12, `ceiling_close_D1` = 1.
- Ders:
  - Eski raporlardaki sayılar kaynak sayılmaz; değer birincil belgeden alınır.
  - Bir sonuç değeri girdi alanına sızabilir. Tavan kapanışı arz fiyatı × 1.1'e eşit olduğu için bu hata göze batmaz.
  - Daha yeni resmi veri eski rapor değeriyle üzerine yazılmaz.
- Kaynaklar: eski `CLAUDE.md:609-615` ("Historical audit example", satır 611 ve 613); `PROJECT_CHECKPOINT_20260812.md:190-194` (satır 192).

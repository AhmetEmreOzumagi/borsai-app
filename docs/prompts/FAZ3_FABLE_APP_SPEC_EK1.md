# EK 1: BORSAI_FAZ3_FABLE_APP_SPEC_20260922 (proje sahibinin isteği, 2026-09-22)

SPEC_APP'e aşağıdaki özellik eklenir. Diğer bütün kurallar ana görev dosyasındaki gibi kalır.

## Koşullu tavan güncellemesi ("3 gün tavan gitti, 5'e ulaşma olasılığı %X")

**Tanım**
- Tavan modelleri (`ceiling_hazard_v0`, `pb_ceiling_v0`, ileride gelecek tavan-yolu modelleri) S_k = P(L ≥ k) verir.
- Seri j gün sürdüyse koşullu olasılık: P(L ≥ k | L ≥ j) = S_k / S_j, k > j.
- P(L = k | L ≥ j) ve "yarın bozulma olasılığı" = 1 − S_{j+1}/S_j aynı vektörden çıkar.

**Ekran**
- Arz sayfasında bir "gün gün" şeridi: D1..D10 için tavan kapandı / kapanmadı / bekliyor.
- Seçilen gün sayısı j için bütün tavan modellerinin koşullu eğrisi yan yana, basit kuralın koşullu değeriyle birlikte (koşullu KM).
- İleride gelecek tavan-yolu modelleri için ayrıca L ≥ j koşulunda D_h getiri dağılımı ve p_up gösterilir (Faz 4 şartnamesi: `docs/specs_faz4/`).

**Veri kaynağı: gözlenen seri.** Birini seç ve gerekçelendir. Öneri:
- Birincil: repodaki `data/outcomes/<TICKER>.csv` (Faz 2B üretiyor; resmi THM).
- İkincil: kullanıcının elle "bugün tavan kapattı" beyanı. "Kullanıcı beyanı" etiketiyle gösterilir, hiçbir skora girmez.

**Kurallar**
- Resmi sicil görünümünde güncelleme DONDURULMUŞ kaydın S vektöründen hesaplanır. Model yeniden çalıştırılmaz, girdi değiştirilmez.
- Senaryo modunda kullanıcının girdisinden hesaplanır ve "senaryo" olarak ayrılır.
- S_j = 0 ya da j ≥ 10 ise değer tanımsızdır; "—" gösterilir.

**Doğruluk gösterimi**
- Koşullu skorlar `scores.json`'da ayrı bir blokta gelecek. Tanım: Faz 4 şartnamesi §7.
- Koşulsuz skorlarla aynı tabloda toplanmaz.
- Blok yoksa "henüz koşullu skor yok" gösterilir.

**Kabul testleri (U-numarası ver)**
- S_k/S_j Python ile |Δ| ≤ 1e-12.
- j = 0'da koşulsuz S_k ile aynı.
- Resmi görünümde dondurulmuş S dışında bir kaynağın kullanılmadığı test edilir.
- Kullanıcı beyanıyla girilen serinin hiçbir skora ve sicile girmediği test edilir.

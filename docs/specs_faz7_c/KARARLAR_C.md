# KARARLAR_C — SPEC_C_V0 açık soruları (§14)

Yazım: 2026-09-27. Orkestratör, proje sahibinin yetkisiyle ("planları kendin düzenle") yazdı. Bu belge şartname sayılır, `SPEC_C_V0.md` ile çeliştiği yerde bağlayıcıdır ve `SPEC_DOCUMENTS_FAZ7C`'ye girer. Kasa açılmadan önce commit ve push edilmiş olmalıdır. İçeriği sonradan değişmez; değişiklik yeni model_id demektir.

| # | Soru (§14) | Karar | Gerekçe |
|---|---|---|---|
| C1 | Hedefte eşitlik durumu | **y4 = 1 − Y_D10** (kapanış ≤ arz olay sayılır); ikincil y3 = 1 − Y_D5 | Kod tanımı hazır; `base_rate` ve V1.5 p_up ile birebir karşılaştırılabilir; fark açık kümede 1 arz |
| C2 | `fall_d10_v0_h99`'un bütçesi (6.5 olay/parametre) | **kabul**; aday olarak kalır, rolü yakın dönem hücresinin karşılaştırıcısı ve merdivenin H99 basamağı | Yakın dönem testi (`pooled − h99`) bu adayı gerektirir; §5.5 seçim kuralı onu da değerlendirir |
| C3 | İkincil hedef | **D5 (y3)** | Aynı modelin başlığı; ek çıktı türü gerekmez; y1'i tavan ailesi zaten kapsıyor |
| C4 | Ek satış alanı boş | **RET** (`REFUSED_ADDITIONAL_SALE_MISSING`); 0 varsayılmaz | "Yok" ile "bulunamadı" karışmaz; kayıp H99'da 4, açık kümede 1, kasada 2 üye |
| C5 | Ön koşul P1'in zamanlaması | **Kasa P1'i beklemez.** P1 ve P2 kasa açılışından SONRAYA ertelenir. P1 sonrası yazılacak (C) v1 adayları kasada test edilemez, yalnız canlı teraziyle ölçülür; bu maliyet kabul edilir. | Kasada beklenen ≈ 12 olay: hangi aday olursa olsun güç düşük. P1 birkaç günlük veri işi; v1 hazard'ın kasa hükmünü ve (C) v0'ı bekletmesinin karşılığı küçük. |

Ek notlar (bağlayıcı):
- **Hijyen olayları:** Fable C oturumu kohort dosyasının ilk üç satırını basarken 2 SEALED kodu, orkestratör de bir denetim çıktısında 10 SEALED kodu gördü. Hiçbir koda bağlı bilgi (özellik, sonuç) görülmedi ve hiçbir dosyaya yazılmadı. Kasa sonucu maruziyeti değildir. Kayda geçer.
- **Çokluk:** keşifte 2 054 varyant denendi (`ekler/denenenler.csv`). Uygulama görevi bunları `experiments/log.jsonl`'a `kind: exploration` satırları olarak ekler ve kart sayaçları bunları sayar (CLAUDE.md kural 4).
- **Gösterim:** (C) kartı ve Rust desteği uygulama EK3 görevindedir (SPEC_C_V0 §9'daki "EK4" bu görevle birleşti).

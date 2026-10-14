# Faz 7 — proje sahibi kararları (SPEC_HAZARD_V1 §13 açık soruları)

Tarih: 2026-09-25, ~21:15 (İstanbul). Yazan: orkestratör. Yetki: proje sahibi, 2026-09-25 18:59: "planları kendin düzenle". Bu belge şartname sayılır; `SPEC_HAZARD_V1.md` (`6a16c16`) ile çeliştiği yerde bu belge geçerlidir. Kararlar, v1 adaylarının hiçbir kodu ya da skoru yokken alındı.

## K1. Kasa açılışı (§13-1, §7.4)
**Kabul.** Kasa, "düşenler" (C) özellik şartnamesi de push kanıtlı olduktan sonra, v1 adaylarıyla **birlikte ve tek seferde** açılır. v1'in dondurulması, canlı kayıtları ve yakın dönem testi kasayı beklemez.

## K2. `pb_ceiling_v1` (§13-2, §2.4)
**Bu şartnamenin dışında kalır; aday bütçesi 3.** Gerekçe:
- Hata f3'lü ailede.
- PB modelleri talep sonucu açıklanmadan önceki kullanım içindir; ürünün ana kullanımı f3'lü modellerdir.
- Tek seferlik kasada karşılaştırma sayısını küçük tutmak doğruluk iddiasını korur.

Bedeli kabul edilir: `pb_ceiling_v1` yazılırsa yalnız canlı teraziyle ölçülür.

## K3. Deflatör (§13-3, §3.2)
**TÜİK TÜFE genel endeksi** (2025=100); ay kuralı T'nin ayı − 2. USD ve XU100 reddedildi.

## K4. Uygulama birincil seçim kuralı (§13-4, §5.5)
**Kabul**, şu açıklamayla. "Birincil", uygulamanın "Tavan serisi" kartında öne çıkarılan modeldir. Hiçbir model listeden kalkmaz ve başka bir modelin yerine geçmez (STRATEJI §2 "terfi yok, yan yana modeller"). Kart, üç terazinin sonucunu her zaman yanında gösterir. Uygun aday yoksa kart `ceiling_hazard_v0`'ı öne çıkarır ve kasada geçen/geçemeyen adayları bir satırda yazar.

## K5. `post_d1_hazard_v1` (§13-5, §2.5)
**Kasa seçiminden sonra**, ayrı ve kısa bir şartnameyle yazılır. Ebeveyn v0 kalırsa yazılmaz.

## Ek notlar
- **Codex izahname görevi (FAZ7_CODEX_PROSPECTUS_B1–B4) maruziyeti.** Codex 8 `exposure_log` satırı yazdı: listeleme sonrası KAP başlıkları (devre kesici, sermaye artırımı, toptan satış); değer açılmadı. Kasa çekilişi değişmez (D2 çekilişi yapıldı). Bu satırlar doğrulama görevinin `EXPOSURE.md`'sine aynen taşınır; kasaya düşen üye sayısı yalnız sayı olarak raporlanır. **(C) özelliklerini tasarlayan oturum Codex'in `exposure_log` satırlarını ve `EXPOSURE.md` dosyalarını okumaz.**
- Şartname `6a16c16`, uygulama başlamadan önce push edilir ve kanıtlanır (önceden kayıt).

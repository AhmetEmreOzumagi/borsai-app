# Değişiklikler

Sürüm numarası uygulamanınkidir (`app/src-tauri/tauri.conf.json`, `app/package.json`, `app/src-tauri/Cargo.toml`). Her sürüm,
özel kaynak repodaki bir commit'in aynasıdır; kaynak commit README'nin "Kaynak ve kanıt" bölümünde yazar.

## v0.1.0 — 2026-10-13

İlk herkese açık sürüm.

- **Uygulama** (macOS Apple Silicon `.dmg`, Windows x64 `.exe`; ikisi de imzasız): kişisel modda (Python ve git gerekmez, ağ
  yok) yeni arz girişi, tahmin sonucu, seri hesaplayıcı ve kayıtlarım; gömülü salt okunur sicil anlık görüntüsüyle Monitör,
  Analiz, Sicil ve Model performansı (son sonuç 30.09.2026, 7 arz). Repo modu (dondurma ve kayıt sihirbazları) macOS ve Linux
  içindir.
- **Modeller:** listeleme öncesi 27, D1 sonrası 1, kırılma akşamı 2 dondurulmuş kayıt (`models/INDEX*.json`).
- **Skorlar:** geçmiş veri testi, canlı sicil (7 arz; metrik yok, n < 10), zaman-dışı kohort (açık küme 71 arz, kasa 64 arz)
  ve kırılma akşamı sicili; ayrıntı `docs/SCORES*.md`.
- **Ayna:** ham bültenler, KAP/SPK PDF'leri, KAP API yanıtı, SPK xlsx tabloları ve doğrulama günlükleri dışarıda
  (`DATA_NOTICE.md`); bunları ya da özel repo geçmişini isteyen testler açıkça atlanır (README, "Yeniden üretim").
- **Lisans:** kaynak kod Apache-2.0.

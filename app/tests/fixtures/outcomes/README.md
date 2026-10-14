# Sentetik gözlenen seri fixture'ları (U40)

Kurgusal `SNTA1` arzı; resmi veri değildir, tarihler 2030. Sütunlar `data/outcomes/<T>.csv` ile aynı
(`borsai/outcomes.py`). Her alt dizin bir durum: `pending` (3 tavan + PENDING → j = 3), `broken`
(2 tavan + 1 tavan değil → L = 2), `na_limit` (1 tavan + NA_LIMIT → j = 1, etiketsiz gün), `all10`
(10 tavan → j = 10, koşullu tanımsız). Uygulama `data/outcomes/`'a hiç yazmaz; bu dosyalar yalnız
`src-tauri/tests/stage2.rs` tarafından okunur.

U52 için kurgusal `SNTB1`: `sntb1` (D1–D2 tavan, D3 PENDING → resmi j = 2; beyan "D3 seri sürüyor"
bu j'yi değiştirmez) ve pozitif kontrol `sntb1_ok` (D3 de OK-tavan → resmi j = 3).

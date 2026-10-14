# Katkı

**In English.** This repository is a generated mirror of a private source repository. Issues are welcome; pull requests cannot
be merged here directly, because every mirror commit is regenerated from the source repository. Accepted changes are ported
there and appear in the next mirror commit.

## Nasıl

- **Hata, soru, öneri:** [Issues](https://github.com/AhmetEmreOzumagi/borsai-app/issues). Uygulama hatasında sürümü ve
  Ayarlar → Hakkında'daki derleme commit'ini yazın; veri hatasında arz kodunu, seansı ve resmi kaynağı (bülten ya da KAP
  bildirimi adresi) verin.
- **Değişiklik önerisi (PR):** açabilirsiniz; ama burada birleştirilmez. Ayna her seferinde özel kaynak repodan
  `scripts/mirror/build_mirror.py` ile yeniden üretilir; kabul edilen değişiklik oraya taşınır ve bir sonraki ayna commit'inde
  görünür.
- **Ham veri eklemeyin:** Borsa İstanbul bülten zip'leri ve KAP/SPK belgeleri bu repoya girmez (`DATA_NOTICE.md`).

## Projenin kuralları

Kurallar [`CLAUDE.md`](CLAUDE.md)'dedir ve kodla zorlanır. Katkının bilmesi gerekenler:

- Bir modelin özelliği, ön işlemesi, ızgarası, eğitim kesimi ya da veri sürümü değişirse **yeni model kimliği** verilir; eskisi ve
  skorları listede kalır. Dondurulmuş model ve kayıt dosyaları değiştirilmez, silinmez.
- Doğruluk yalnız resmi bültenden gelen sonuçla, basit kurallara karşı eşleşik ve "fark + aralık + n" ile raporlanır;
  "geçiyor" yalnız aralık 0'ı dışlarsa denir. Geçmiş veri testi, canlı sicil ve zaman-dışı kohort asla toplanmaz.
- Testler: `python -m pytest -q` (Python 3.12, `requirements.lock`), `cd app/src-tauri && cargo test --workspace`,
  `cd app && npm test`. Aynada bazı testler açıkça atlanır (README, "Yeniden üretim").
- Yeni kod Windows'ta da çalışmalıdır: yollar `pathlib` / `Path::join`, kabuk sözdizimi yok.

Katkılar Apache-2.0 (LICENSE) altında kabul edilir.

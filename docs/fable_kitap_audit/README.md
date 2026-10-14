# fable_kitap_audit — proje kılavuzunun bağımsız denetimi

`kitap/` altındaki on bölüm, 7 Ekim 2026'da orkestratör (claude.ai sohbeti) ve yardımcı ajanları tarafından repoya bakılarak yazıldı. Bölümler projenin tamamını anlatır: veri, modeller, ölçüm, kurallar ve uygulama. Repo durumu `ee3796d`, toplam 121 bin kelime. Proje sahibine Word olarak da verildi.

**Bu metin birincil kaynak değildir.** Bağlayıcı olan kod, veri, şartnameler (`docs/specs*`) ve proje belgeleridir (`docs/*.md`). Kılavuz ile repo çelişirse repo geçerlidir. Denetimlerin bulduğu kılavuz hataları raporlarda listelenir; `kitap/` dosyaları sonradan düzeltilmez.

Dört Fable denetimi kılavuzu bir iddia listesi olarak kullanır ve her iddiayı repoya karşı ölçer. Asıl aranan şey projenin kendi hatalarıdır:

| Rapor | Kapsam | Görev |
|---|---|---|
| `AUDIT_1_VERI.md` | Bölüm 3 (veri), §1.5–1.6 | `docs/prompts/FAZ9_KITAP_AUDIT_1_VERI.md` |
| `AUDIT_2_ONCESI.md` | Bölüm 4 (listeleme öncesi modeller) | `docs/prompts/FAZ9_KITAP_AUDIT_2_ONCESI.md` |
| `AUDIT_3_SONRASI.md` | Bölüm 5 ve 6 (listeleme sonrası modeller, ölçüm ve kurallar) | `docs/prompts/FAZ9_KITAP_AUDIT_3_SONRASI.md` |
| `AUDIT_4_UYGULAMA.md` | Bölüm 7 ve 8 (uygulama) | `docs/prompts/FAZ9_KITAP_AUDIT_4_UYGULAMA.md` |

Ortak kurallar: `docs/prompts/FAZ9_KITAP_AUDIT_ORTAK.md`.

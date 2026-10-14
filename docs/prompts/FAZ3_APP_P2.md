# TASK_ID: BORSAI_FAZ3_APP_P2_20260923

Model: Opus 5 · Extra. Klasör: ~/Desktop/BorsAi. Ağ: yalnız npm/crates (gerekirse). push/tag/amend yok.

## Bağlam
- P1 tamam (4c44bcc). Üç `ceiling_path` modeli Rust'ta, parite 19/19, maks |Δ| 1.1e-13. Koşullu karışım paritesi Δ = 0.
- U52 tamam (50e6af9). Beyan yalnız etiket. `u52_declaration.test.ts` içinde P2'ye bırakılmış bir `it.todo` var.
- Skorlar (0c3cb99): `scores.json`'da üç modelin backtest hücreleri artık DOLU.
  - `ceiling_path_v0` 32 hücre, `@INF` 16, PB 24.
  - Birincil hücre yalnız `ceiling_path_v0`: D5 MAE vs `base_train_median`, −0.1158 [−0.1611, −0.0738], n = 85, "geçiyor".
  - EK 2 §4.4 ve §5 "bugün null / hücre yok" diyordu. O durum değişti: kart ve "backtest tipik hata" satırı `scores.json`'daki değeri gösterir. Hücre yoksa yine "—".
- Bu görev EK 2'deki **Aşama P2: gösterim**. Kapsam:
  - Grup A sütunları (§4.1)
  - Grup C "tavan yolu: getiri dağılımı" (§4.2)
  - "Getiri (koşullu)" sekmesi (§4.3)
  - sicil ekranı, model kartı, metinler (§4.4)
  - U48, U49, U50; U52'nin P2'ye bırakılan kısmı; U7 güncellemesi (5 RET + 14 dolu)

ÖNCE OKU:
- CLAUDE.md
- docs/app/SPEC_APP_EK2.md §4, §5, §6 (U48–U50), §7, §9 (açık soruların kararları: 1, 2, 4, 5 önerildiği gibi; 3 proje sahibi kararıyla "Hayır")
- docs/app/SPEC_APP.md §3b, §3c, §3g (U52 dahil), §4
- app/ kodu; özellikle `render/results.ts`, `render/ceiling.ts`, `screens/registry.ts`, `commands/ceiling.rs`, `crates/borsai_predict/src/path.rs`

## Adımlar
1. **Rust komutları.**
   - `path_display`: "≈ fiyat" görüntüleme türevi.
   - `path_conditional(model_id, source, j_or_t, state)`: kapanışları kendisi okur (`data/outcomes/<T>.csv` `close_raw`, salt okuma). Hangi h'lerin dosyadan, hangilerinin varsayım olduğunu döner.
   - Beyan parametresi YOK (U52-5).
   - Resmi görünümde yalnız kayıttaki `output` ve gömülü `post_break.cells`. `predict_all` çağrılmaz. Kayıttaki `params_sha256` gömülüyle eşit değilse hesaplanmaz.
2. **Grup A ve Grup C** (§4.1–§4.2). Ön uç yalnız piksel hesaplar (U25 kalıbı genişler).
3. **"Getiri (koşullu)" sekmesi** (§4.3). Durum 1 ve 2; varsayımsal j etiketi; `limit_path_mismatch` kutusu. Beyan resmi verinin önündeyse kart boş: "resmi kapanış bekleniyor".
4. **Sicil ve model kartı** (§4.4).
   - Aşama 3'teki "bu modelin gösterimi Faz 4 portuyla gelecek" metni kalkar.
   - Model kartı birincil hücreyi `scores.json`'dan gösterir.
5. **Testler:**
   - U48, U49, U50
   - U52'deki `it.todo` gerçek teste döner: tavan-yolu modellerinin koşullu medyan/p_up/q10/q90 metinleri yasak kümeye girer, pozitif kontrolle birlikte
   - U7: VEYAS → 5 RET + 14 dolu
   - Commit öncesi tam koşu: `bash app/scripts/test.sh`, iki e2e betiği, `.venv/bin/pytest -q`
6. **Ekran görüntüleri** `app/docs/screens/` altına: VEYAS Grup A ve C; NETGL Grup C; NETGL koşullu getiri (j = 3); NETGL arz sayfası (resmi kayıt 16 modelli, "kayıt Faz 4 modellerini içermiyor"); geçici klonda 19 modelli yeni kayıtla arz sayfası. Asıl repoda dondurma yapılmaz.
7. Commit.

Bu aşama tek oturumda bitmezse:
- Yeşil ve tutarlı bir ara noktada commit at. Mesaja `(partial)` ekle.
- Kalanları raporda listele.

## Kurallar
- YALNIZ `app/` altına yaz. Tek istisna bu görev dosyası.
- `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `docs/`, `tests/` salt okunur.
- Ön uçta hesap yok; bütün sayılar Rust'tan.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- Değer uydurulmaz: `scores.json`'da olmayan hücre "—".
- `git add -A` yok. Commit:
  ```
  git add app docs/prompts/FAZ3_APP_P2.md
  git commit -m "<mesaj>" -- app docs/prompts/FAZ3_APP_P2.md
  ```
  - `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Mesaj: `BORSAI_FAZ3_P2: ceiling path display (group A/C, conditional return tab, registry and model card) (SPEC_APP EK2 stage P2)`
- Rapor Türkçe.

## Teslim (rapor)
- Commit hash'i ve `git show --stat` özeti.
- U-testleri tablosu: U7, U48–U50, U52 (todo kapandı mı).
- Ekran görüntülerinin yolları.
- Test sayıları ve süreleri: cargo, npm, pytest.
- Sapmalar ve kalan işler.

## Kabul kapısı
- K1 U48–U50 yeşil; U52'de `todo` kalmadı; U7 5 RET + 14 dolu.
- K2 Resmi görünümde `predict_all` çağrı sayacı 0; beyan hiçbir hesap yolunda yok.
- K3 Ön uçta hesap yok (U25 genişletilmiş tarama).
- K4 Aşama 0–3 ve P1 testleri, e2e betikleri ve tam pytest yeşil.
- K5 Commit yalnız `app/` ve bu görev dosyası.

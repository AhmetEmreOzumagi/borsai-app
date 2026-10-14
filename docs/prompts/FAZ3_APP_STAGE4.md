# TASK_ID: BORSAI_FAZ3_APP_STAGE4_20260923

Model: Opus 5 · Extra. Klasör: ~/Desktop/BorsAi. Ağ: yalnız npm/crates (gerekirse). push/tag/amend yok.

## Bağlam
- Uygulama aşama 0–3 ve Aşama P (P1, P2) tamam. Son commit 510f890. 19 model gömülü ve gösteriliyor.
- Bu görev `docs/app/SPEC_APP.md` §7'deki **aşama 4: Doğruluk paneli**. Kapsam:
  - §3d panel: iki bağımsız terazi, küçük-n kuralları, birincil hücre, RETRO/atlanan/self-reported bölümleri
  - §2.3 `scores.json` okuyucu: REPO/EMBEDDED kaynak seçimi, başlık bilgisi, fail-closed bütünlük denetimi
  - §2.5 sürüm uyumsuzluğu (scores kısmı)
  - EK 2 §5: Faz 4 blokları ve ileride gelecek `models[].conditional`
  - U13–U26, U35 (scores kısmı), U51
- Bugünkü gerçek `scores/scores.json` [orkestratör ölçtü]:
  - 19 model bloğu. Canlı `n_scored` 0–7 arası; hiçbir modelde n ≥ 10 yok, yani canlıda yalnız satır tabloları.
  - Faz 4 backtest hücreleri dolu: `ceiling_path_v0` 32, `@INF` 16, `pb_ceiling_path_v0` 24.
  - Birincil hücre yalnız `ceiling_path_v0`: D5 MAE vs `base_train_median`, −0.1158 [−0.1611, −0.0738], n = 85, "geçiyor".
  - `retro_info` 21 satır, `skipped` 19 satır. `v1_5_h99`'da 2 `self_reported_rows` var.

### Şartname yazıldıktan sonra eklenen alanlar (bağlayıcı)
Bu alanlar `docs/SPEC_DEVIATIONS.md` satır 83'te listeli. SPEC_APP bunları bilmiyordu. Gösterim kuralları:
1. `live.invalid_use_rows`: canlı bölümün altında ayrı, gri, katlanır alt tablo. Başlık: "Geçersiz kullanım (model bugün RET eder; hiçbir metriğe ve n'e girmez)". Satırdaki `note` aynen.
2. Üst düzey `separate_models`: panelin sonunda ayrı bölüm. Başlık: "Ayrı modeller (INDEX dışı; metrik yok)". Satır tablosu ve `note`. Hiçbir modelin sütununa ya da n'ine karışmaz.
3. `live.descriptive` (MedAE, kalibrasyon; SPEC_DEVIATIONS E13): canlı hücre tablosunun altında ayrı alt tablo, "Betimleyici (aralıksız, hükümsüz)". Renk yok, hüküm yok.
4. `live.self_reported_cells`: self-reported alt bölümünde, kendi n'iyle (`n_self_reported_scored`) aynı küçük-n kuralları.
5. `live.cancelled_records`: canlı bölümde "iptal edilen kayıtlar" listesi (dosya, neden, zaman).
6. Bütünlük denetimi (§2.3) aynı §8 ilkesiyle genişler:
   - `n_scored < 10` iken `descriptive` boş değilse → hata
   - `n_self_reported_scored < 10` iken `self_reported_cells` boş değilse → hata
   Bu iki kuralı rapora "görev kararı" olarak yaz.
7. Diğer ek alanlar (`definitions`, `outcomes`, satırlardaki `class_evidence` vb.) okunmaz ya da yalnız tooltip'te görünür. Uygulama hiçbirinden sayı TÜRETMEZ.

### Faz 4 ve koşullu blok (EK 2 §5, U51)
- `kind = "ceiling_path"` blokları getiri/p_up modeli gibi okunur. Birincil hücre `ceiling_path_v0`'da vurgulanır; diğer ikisinde yok.
- `retro_info` model başına gruplu, ayrı, gri: "RETRO (bilgi amaçlı; hiçbir teraziye girmez)".
- `models[].conditional` bugün yok → "henüz koşullu skor yok".
  - Sentetik fixture EK 2 §5 şemasıyla `app/tests/fixtures/` altında üretilir, `synthetic: true`.
  - j = 1 (n = 4) satır tablosu; j = 3 (n = 12) "yetersiz örnek"; yanlış sürüm → mesaj.
  - Koşullu blok koşulsuz tabloyla hiçbir satırda toplanmaz; U14/U22 taraması genişler.

ÖNCE OKU:
- CLAUDE.md
- docs/app/SPEC_APP.md: §2.3, §2.5, §3d, §4, §5.3 (U13–U26), §5.5 (U35), §7
- docs/app/SPEC_APP_EK2.md §5 ve U51
- docs/specs/SPEC_SCORING.md §7–§8
- docs/SPEC_DEVIATIONS.md (E13 ve satır 83)
- docs/app/ekler/scores_n7_sentetik.json, n12, n35 (fixture'lar; `app/tests/fixtures/` altına kopyalanır, alan adları gerçek şemaya uyarlanır, kurallar değişmez)
- scores/scores.json (gerçek dosya; salt okunur)
- app/ kodu; özellikle `commands/scores.rs` (bugün yalnız ipucu okuyor), `render/results.ts` (model kartı)

## Adımlar
1. **Rust:** `scores.json` okuyucu ve bütünlük denetimi (§2.3 + yukarıdaki 6. madde).
   - REPO/EMBEDDED kaynak; başlıkta kaynak, `generated_at_utc`, `as_of_session`, sha ilk 12.
   - `inputs.models_index_sha256` ≠ gömülü INDEX sha ise sarı uyarı.
   - Sürüm uyumsuzluğu §2.5.
   - Uygulama hiçbir hücreyi hesaplamaz, düzeltmez, doldurmaz.
2. **Doğruluk ekranı** (menüdeki "Doğruluk"):
   - Bölüm 1 backtest ve Bölüm 2 canlı, ayrı renk sınıfları.
   - Küçük-n üç hâli; birincil hücre rozeti; "puan" birimi.
   - Model kartı ve rejim uyarısı panelin üstünde.
   - Bölümler: self-reported, RETRO, atlanan, geçersiz kullanım, iptal edilen, ayrı modeller, koşullu.
   - Model seçici sonuç ekranındakiyle aynı.
3. **Testler:**
   - U13–U26, U35 (scores), U51.
   - U19: "geçiyor" dizesi kaynakta yalnız `tr.ts`'deki verdict eşlemesinde. P2'nin model kartındaki birincil hücre gösterimi de `verdict` alanından gelmeli; değilse düzelt.
   - U25: fixture'daki her `model_value` DOM'da; TS/Rust'ta metrik hesap fonksiyonu yok.
   - Gerçek `scores/scores.json` ile render testi: 19 blok, canlıda hiçbir hücre/hüküm yok, satır tabloları var, `ceiling_path_v0` birincil hücresi −0.1158 [−0.1611, −0.0738] n = 85 ve "geçiyor" metni `verdict`'ten.
   - Commit öncesi tam koşu: `bash app/scripts/test.sh`, iki e2e betiği, `.venv/bin/pytest -q`.
4. **Ekran görüntüleri** `app/docs/screens/` altına:
   - gerçek dosyayla panelin tamamı (V1.5 ve `ceiling_path_v0` kartları açık)
   - n7, n12, n35 sentetik fixture'lar
   - koşullu sentetik blok
   - bütünlük hatası ekranı
5. Commit.

Bu aşama tek oturumda bitmezse:
- Yeşil ve tutarlı bir ara noktada commit at. Mesaja `(partial)` ekle.
- Kalanları raporda listele.

## Kurallar
- YALNIZ `app/` altına yaz. Tek istisna bu görev dosyası.
- `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `docs/`, `tests/` salt okunur.
- İki terazi hiçbir yerde toplanmaz, ortalanmaz, tek hükümde birleşmez (U14).
- Ön uçta hesap yok; bütün sayılar dosyadan ya da Rust'tan.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- `git add -A` yok. Commit:
  ```
  git add app docs/prompts/FAZ3_APP_STAGE4.md
  git commit -m "<mesaj>" -- app docs/prompts/FAZ3_APP_STAGE4.md
  ```
  - `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Mesaj: `BORSAI_FAZ3_S4: accuracy panel with separate backtest and live scales, small-n rules and fail-closed integrity (SPEC_APP stage 4)`
- Rapor Türkçe.

## Teslim (rapor)
- Commit hash'i ve `git show --stat` özeti.
- U-testleri tablosu: U13–U26, U35, U51.
- Gerçek dosyayla render sonucu: model başına canlı n ve gösterilen hâl; birincil hücre satırı.
- "Görev kararı" olarak eklenen iki bütünlük kuralı ve ek alanların gösterimi.
- Ekran görüntülerinin yolları.
- Test sayıları ve süreleri: cargo, npm, pytest.
- Sapmalar ve kalan işler.

## Kabul kapısı
- K1 U13–U26, U35, U51 yeşil; önceki bütün testler yeşil.
- K2 Gerçek `scores.json` ile canlıda hiçbir metrik ya da hüküm görünmüyor (n < 10); backtest birincil hücresi doğru.
- K3 Bütünlük denetimi fail-closed; sentetik ihlaller panel yerine hata gösteriyor.
- K4 Uygulama skor hesaplamıyor (U25); iki terazi birleşmiyor (U14).
- K5 Commit yalnız `app/` ve bu görev dosyası; tam pytest yeşil.

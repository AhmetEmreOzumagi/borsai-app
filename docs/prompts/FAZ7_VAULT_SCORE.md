# TASK_ID: BORSAI_FAZ7_VAULT_SCORE_20260929

Model: Opus 5.5 · Extra. Klasör: ~/Desktop/BorsAi. **Ağ gerekmez ve KULLANILMAZ.** push/tag/amend yok.

## Rol
Kasa açıldı (`docs/prompts/FAZ7_VAULT_OPEN.md`, rapor `docs/faz7_vault/RAPOR.md`). Bu görev zaman-dışı skorları üretir. İçerik:
- 27 modelin kasa blokları;
- 19 eski modelin açık + kasa toplamı;
- `post_d1_hazard_v0`'ın kasa ve toplam blokları;
- önceden yazılmış beklentilerle karşılaştırma;
- iki seçim kuralının sayılardan değerlendirilmesi.

**Uygulama ve MODELS.md bu görevde değişmez.** Seçim kuralının sonucu, Fable denetimi `VAULT_SCORE_OK` dedikten sonra uygulanır.

## Bağlam
- **Sıra** (hepsi push kanıtlı):
  - S2 ilk kayıtlar: kanıt 2026-09-24T22:39:24Z.
  - Ek kayıtlar `28aaa3b`: kanıt 2026-09-29T06:40:55Z.
  - VA1 `2f914dd`: kasa D_1 satırları + işaret dosyası; kanıt 15:30:41Z. Listeleme öncesi modellerin kasa girişi budur.
  - VA2 `5a96e25`: kasa post_d1 kayıtları; kanıt 15:30:43Z.
  - VB `71b9071`: kasa D_1…D_10 satırları. `post_d1_hazard_v0`'ın kasa girişi budur; kanıtı proje sahibinin son push'unda.
- Skor kodu hazır ve sentetik testli: `1b2fe00` (C) + `439a808` (C2); SPEC_DEVIATIONS L ve M. Kasa açıldığı için `scoring --oot` şu anahtarları kendiliğinden yazar: `oot_pre_h99` (açık), `oot_pre_h99_sealed`, `oot_pre_h99_all`, `post_d1`, `post_d1_sealed`, `post_d1_all`.
- **Birincil hücreler değişmez:**
  - eski 8 model: SPEC_OOT_PRE_H99_V0 §6 / `OOT_PRIMARY_CELLS`;
  - v1: SPEC_HAZARD_V1 §5.2;
  - (C): SPEC_C_V0 §5.2;
  - post_d1: `OOT_POST_D1_PRIMARY`.
  - İlan edilmiş ikinciller "ikincil" etiketlidir; geri kalan her hücre "keşif".
- CLAUDE.md kural 3: üç terazi asla toplanmaz. Kural 6: "geçiyor" yalnız aralık 0'ı dışlıyorsa (ve n ≥ 30).
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.**
- **Bu göreve özel kural:** sonuçlar artık görünür. Skor tanımları (kayıp, eşleşme, sınıf, bootstrap, n kuralları, hücre listeleri) DEĞİŞTİRİLMEZ. `scoring.py`'de bir hata bulursan düzeltme; DUR ve rapora yaz. Düzeltmeyi sonuçları görmemiş bağımsız bir el yapar.

## Paralel
Fable aynı anda `docs/prompts/FAZ7_FABLE_VAULT_RECOMPUTE.md`'yi koşuyor (kör bağımsız yeniden hesap).
- Onun dizinine (`docs/fable_faz7_vault/`) ve görev dosyasına dokunma.
- Commit'lerde yalnız kendi yollarını ver. `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.

## İzinli izlenmeyen
Bu iki görev dosyası (`docs/prompts/FAZ7_VAULT_SCORE.md`, `docs/prompts/FAZ7_FABLE_VAULT_RECOMPUTE.md`) ve `docs/fable_faz7_vault/` altındaki her şey. Başka bir şey varsa DUR.

## Orkestratörün ölçtükleri (kasa üyelerinin birincil kayıtlarından; 2026-09-29 ~20:50)
Kasa 64 üye. 640 sonuç satırının hepsi `OK`; her üyede 10 seans.

| Model | PREDICTED | REFUSED (kod) | NOT_APPLICABLE_REGIME |
|---|---|---|---|
| v1_5_h99, v1_6_h99, v1_5_market20_v0, ceiling_hazard_v0 | 62 | 2 (F3_MISSING) | 0 |
| ceiling_hazard_v1_clip / _real / _pooled | 62 | 2 (F3_MISSING) | 0 |
| pb_v0, pb_ceiling_v0 | 53 | 11 (PB_IDENTITY 6, PB_PRICE_RANGE 5) | 0 |
| ceiling_path_v0 | 60 | 1 (F3_MISSING) | 3 (birinde ret alanı F3_MISSING) |
| pb_ceiling_path_v0 | 51 | 10 (PB_IDENTITY 5, PB_PRICE_RANGE 5) | 3 (birinde ret alanı PB_IDENTITY) |
| base_always_ceiling ve dört @INF (v0, pb, path, v1_pooled) | 63 | 0 | 1 |
| fall_d10_v0_h99, fall_d10_v0_pooled | 60 | 4 (F3_MISSING 2, ADDITIONAL_SALE_MISSING 2) | 0 |
| fall_d10_v0_addsale | 62 | 2 (ADDITIONAL_SALE_MISSING) | 0 |
| fall_d10_v0_pooled@ZERO ve 7 kural (base_train_median, _mean, base_zero, base_rate, base_last10_rate, base_km_expanding, base_km_last10) | 64 | 0 | 0 |

Kasa post_d1 kayıtları (VA2): PREDICTED 45, REFUSED 2 (F3_MISSING), NOT_APPLICABLE 17 (D1_NOT_CEILING).

## Görev kararları (SPEC_DEVIATIONS bölüm M'ye sıradaki numaralarla)
- **T1: Skor komutu.** Yalnız `.venv/bin/python -m borsai.scoring --oot` koşulur; `scores/scores_oot.json` ve `docs/SCORES_OOT.md` yazılır. Bayraksız `main()` koşulmaz: `scores.json`, `scores_post_d1.json` ve `SCORES.md` bayt-eşit kalır.
- **T2: Önceden yazılmış akıl-sağlığı denetimleri.** Commit'ten önce yapılır; biri tutmazsa commit etme, DUR.
  - **`oot_pre_h99_sealed`:**
    - 27 modelin her birinde kasa satırı 64. `n_oot_retro = 0`, `n_skipped = 0`, `n_pending = 0`, `n_target_unavailable = 0`.
    - REFUSED ve NOT_APPLICABLE_REGIME sayıları yukarıdaki tabloyla birebir; `n_scored` = PREDICTED.
    - Her satırın `class_evidence`'ında kaydın kanıtı sonuç girişinin kanıtından önce ve kohort kapısı doğru. Kaynak kayıt, modeli içeren en erken kayıt: eski 19 model için S2, yeni 8 model için ek kayıt.
  - **`oot_pre_h99_all`:**
    - Tam olarak 19 eski model. Yeni 8 model `excluded_models`'ta, nedeniyle.
    - Her eski modelde n = açık n + kasa n.
  - **`oot_pre_h99` (açık küme):**
    - 19 eski modelin blokları commit'li Faz 6 dosyasındakilerle aynı (hücreler, satırlar, sayaçlar).
    - Yeni 8 modelin her birinde `n_oot_retro = 71` ve skorlanan satır 0.
  - **post_d1:**
    - `post_d1` (açık) commit'li dosyadakiyle aynı.
    - `post_d1_sealed`: 47 satır (45 skorlanan + 2 ret), `n_not_applicable = 17`, `n_oot_retro = 0`.
    - `post_d1_all` = açık + kasa.
  - **Kod ve diğer dosyalar:** `code.borsai_dirty = false`. `scores.json`, `scores_post_d1.json`, `SCORES.md` önce ve sonra bayt-eşit.
  - Tablo `docs/faz7_vault/ekler/skor_denetim.txt`'ye yazılır (sayılar ve hücre değerleri; üye başına değer yok).
- **T3: Önceden yazılmış beklentilerle karşılaştırma.** Raporda her satır için:
  - beklenen fark ve aralık, aynen;
  - gözlenen fark [%95 aralık] ve n;
  - konum: "aralık içinde" / "altında: beklenenden iyi" / "üstünde: beklenenden kötü".
  
  Kaynaklar:
  - SPEC_HAZARD_V1 §6.1 tablosunun bütün satırları (`ceiling_hazard_v0 − KM` kasada dahil);
  - SPEC_C_V0 §6.1 tablosunun bütün satırları;
  - SPEC_DEVIATIONS M12 (post_d1 kasada: −0.035 [−0.065, −0.005]);
  - SPEC_OOT_PRE_H99_V0 §8 (eski 8 birincil hücre). Bu tablo açık küme için yazıldı; kasa için aynı beklenti okunur, raporda bunu belirt.
- **T4: "Beklentiden çok iyi" işaretleri** (şartnamelerin sözcükleriyle):
  - v1 §6.4 (e): birincilde fark < −0.10 ya da aralığın üst ucu < −0.06;
  - (C) §6.4 (e): fark < −0.08 ya da üst uç < −0.04;
  - post_d1 M12: fark < −0.08 ya da üst uç < −0.045.
  
  İşaret varsa raporda belirt. Bağımsız yeniden hesap zaten paralel Fable görevidir; seçim, Fable `VAULT_SCORE_OK` demeden uygulanmaz.
- **T5: Başarısızlık tanımları.** v1 §6.4 (a)–(d) ve (C) §6.4 (a)–(d) her aday için tek tek değerlendirilir: tuttu / tutmadı, sayıyla.
- **T6: Seçim kuralları** (yalnız dosyadaki sayılardan; yeni hesap yok). k3 değerleri `scores/scores.json` `models[].backtest.near_era` bloğundan alınır.
  - **v1 §5.5:** her aday için k1, k2 (kasada RPS − `ceiling_hazard_v0` aralığının üst ucu < 0) ve k3; "uygun" ya da "uygun değil". Uygunlar arasında en düşük kasa RPS noktası; eşitlik kuralı |Δ| < 0.002 → clip < real < pooled. Hiçbiri uygun değilse `ceiling_hazard_v0` birincil kalır.
  - **(C) §5.5:** her aday için k1, k2 (kasada D10 Brier − `v1_5_h99` aralığının üst ucu < 0) ve k3; eşitlik kuralı addsale < h99 < pooled. Uygun aday yoksa "kasada geçen aday yok".
  - Raporda "seçim önerisi (Fable denetimi bekleniyor)" başlığıyla yazılır. Uygulamaya ve MODELS.md'ye dokunulmaz.
- **T7: M6 testi.** Kapalı kasa bellek koşusunun commit'li dosyayla karşılaştırılması, eski dosyaya karşı bilinen farklara izin veriyordu. Yeni `scores_oot.json` commit'lenince bu izinler gereksizleşir.
  - Testi yeni dosyayla, gerektiği kipte (açık kasa) tam eşitlik isteyecek biçimde sıkılaştır. Gevşetme yok; iddia ancak daha katı olabilir.
  - Ayrı commit T. Başka testler skor içeriğini pinliyorsa ve kırmızıysa yalnız sayı/sha pini olarak ve aynı commit'te güncellenir; mantık değişirse DUR.
- **T8: Proje sahibi için sade paragraf** (raporun başında). Hangi model kasada ne durumda; iki seçim kuralının önerisi. Her cümlede terazinin adı geçer ("kasada, zaman-dışı terazide"). Backtest ya da canlı sayısıyla toplanmaz.

## ÖNCE OKU
- CLAUDE.md
- `docs/specs_faz7/SPEC_HAZARD_V1.md` §5.2, §5.5, §6.1, §6.4; `docs/specs_faz7_c/SPEC_C_V0.md` §5.2, §5.5, §6.1, §6.4; iki KARARLAR belgesi (K4)
- `docs/specs_faz6/SPEC_OOT_PRE_H99_V0.md` §6, §8; `docs/specs/SPEC_SCORING.md` §7, §8
- `docs/SPEC_DEVIATIONS.md` bölüm I (I10–I13), L, M
- `docs/faz7_vault/RAPOR.md` (özellikle §B6); `docs/faz6/S6_RAPOR.md` (kalıp)
- `borsai/scoring.py`: eski kohort bölümü, `oot_vault_blocks`, `all_eligible`, `oot_post_d1_block`, `render_oot_doc`
- `tests/test_faz7_vault.py`, `tests/test_faz7_oot.py`, `tests/test_faz6_s6.py`

## Adımlar
0. **Taban.**
   - HEAD, VB'nin kanıt commit'i (`BORSAI_PUSH_PROOFS: Faz 7 vault outcome rows (71b9071)`) ya da torunu. `git status --porcelain` yalnız izinli izlenmeyenleri gösterir.
   - VB'nin push kanıtının `created_at`'i VA2'ninkinden (2026-09-29T15:30:43Z) sonra olmalı; değilse DUR.
   - `.venv/bin/python -c "from borsai import outcomes_oot as oo; print(len(oo.s2_gate_problems()), len(oo.vault_s3_gate_problems()))"` → `0 0`.
   - Tam `.venv/bin/pytest -q`, `bash app/scripts/test.sh`, `gen_golden --check` yeşil. Sayılar `docs/faz7_vault/ekler/skor_test_runs.txt`'ye.
1. **Skor:** `.venv/bin/python -m borsai.scoring --oot`. T2 denetimleri tutmazsa DUR.
2. **Commit S.** Yalnız bu yeni skor dosyaları yüzünden kırmızı olan temizlik bekçileri deselect edilir. Deselect'li tam koşu yeşil → **commit S** (yalnız `scores/scores_oot.json`, `docs/SCORES_OOT.md`) → deselect'siz tam pytest + test.sh yeşil. Eski kohort ve kasa bekçileri asla deselect edilmez. Başka kırmızı varsa DUR.
3. **Commit T** (T7; gerekirse). Tam pytest + test.sh yeşil.
4. **Rapor** `docs/faz7_vault/SKOR_RAPOR.md` (commit R). İçerik:
   - S ve T hash'leri; T8 paragrafı;
   - T2 tablosu;
   - kasa birincil hücreleri: 27 model ve post_d1 (fark [%95 aralık], n, blok sayısı, hüküm);
   - ilan edilmiş ikinciller;
   - 19 eski modelin toplam (`_all`) birincilleri;
   - T3 karşılaştırması, T4 işaretleri, T5, T6;
   - yıl ve rejim kırılımları (etiketleriyle; n < 30 "yetersiz örnek");
   - kalibrasyon bilgi satırları;
   - test sayıları;
   - model geliştirme için gözlemler ("keşif" etiketiyle; yeni model fikri ancak yeni model_id ve yalnız canlı teraziyle ölçülebilir).

## Kurallar
- **Yazılabilir:** `scores/scores_oot.json` ve `docs/SCORES_OOT.md` (yalnız CLI ile); `tests/` (yalnız T7); `docs/SPEC_DEVIATIONS.md`; `docs/faz7_vault/SKOR_RAPOR.md`, `docs/faz7_vault/ekler/skor_*`; bu görev dosyası.
- **Salt okunur:** `borsai/` (skor tanımı değişmez; hata → DUR), `models/`, `registry/`, `data/`, `scores/scores.json`, `scores/scores_post_d1.json`, `docs/SCORES.md`, `docs/MODELS.md`, `app/`, `docs/specs*`, `CLAUDE.md`, `legacy/`, `docs/fable_faz7_vault/`.
- Skor dosyaları elle düzenlenmez.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- Oturum içinde proje sahibine karar sorman gerekirse soruyu ve seçenekleri açıkça yaz. Proje sahibi orkestratöre danışarak cevaplayacak.
- `git add -A` yok. Commit'ler:
  ```
  git add scores/scores_oot.json docs/SCORES_OOT.md
  git commit -m "BORSAI_FAZ7_VAULT_SCORES: out-of-time scores with the vault (sealed and all keys, post_d1 sealed and all); third scale, never merged" -- scores/scores_oot.json docs/SCORES_OOT.md
  git add tests docs/SPEC_DEVIATIONS.md
  git commit -m "BORSAI_FAZ7_VAULT_SCORES_TESTS: committed-file equality test tightened to the new scores_oot.json (no allowance)" -- tests docs/SPEC_DEVIATIONS.md
  git add docs/faz7_vault docs/prompts/FAZ7_VAULT_SCORE.md
  git commit -m "BORSAI_FAZ7_VAULT_SCORE_REPORT: vault primary cells, comparison with pre-registered expectations, selection rules (pending audit)" -- docs/faz7_vault docs/prompts/FAZ7_VAULT_SCORE.md
  ```
  Değişmeyen bir yol pathspec'te hata verirse o yolu çıkar.
- Push yok. Rapor Türkçe.

## Kabul kapısı
- **K1** Taban yeşil; VB kanıtı VA2 kanıtından sonra.
- **K2** T2 denetimlerinin hepsi tuttu. Kasa satırlarında n_oot_retro 0. Diğer skor dosyaları bayt-eşit.
- **K3** `scores_oot.json` ve `SCORES_OOT.md` commit'li. T3–T6 raporda. Skor tanımı değişmedi (`git diff 439a808..HEAD -- borsai` boş).
- **K4** Sıra S → (T) → R; yalnız izinli yollar; push yok.

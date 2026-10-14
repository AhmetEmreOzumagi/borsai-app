# TASK_ID: BORSAI_FAZ7_FABLE_VAULT_RECOMPUTE_20260929

Model: Fable · yüksek. Klasör: ~/Desktop/BorsAi. **Ağ yalnız 10 bülten zip'inin resmi URL'den yeniden indirilmesi için** (Faz 1 adım 5; URL'ler `data/raw/bist/MANIFEST_OOT.csv`'de). İndirmeler repo ve karantina dışındaki geçici bir dizine gider (ör. `/tmp/borsai_fable_vault/`). Başka ağ yok. push/tag/amend yok.

## Rol
Kasanın (64 arz) zaman-dışı skorlarını ve iki seçim kuralını, uygulayıcıdan bağımsız ve **onun sonucunu görmeden** yeniden hesaplarsın.
- Opus aynı anda `docs/prompts/FAZ7_VAULT_SCORE.md`'yi koşuyor. `scores/scores_oot.json`, `docs/SCORES_OOT.md` ve `docs/faz7_vault/SKOR_RAPOR.md`'yi o üretecek.
- Yazan el ile denetleyen el ayrıdır.
- Uygulamanın öne çıkaracağı tavan ve düşüş modeli senin denetiminden sonra seçilir.

## Bağlam
- **Sıra** (hepsi push kanıtlı):
  - S2 ilk kayıtlar: kanıt 2026-09-24T22:39:24Z.
  - Ek kayıtlar `28aaa3b`: 2026-09-29T06:40:55Z.
  - VA1 `2f914dd`: kasa D_1 satırları + işaret dosyası; 15:30:41Z.
  - VA2 `5a96e25`: kasa post_d1 kayıtları; 15:30:43Z.
  - VB `71b9071`: kasa D_1…D_10; kanıtı `BORSAI_PUSH_PROOFS: Faz 7 vault outcome rows (71b9071)` commit'inde.
  - Rapor `docs/faz7_vault/RAPOR.md`.
- **Tanımlar (şartnamelerden al):**
  - SPEC_OOT_PRE_H99_V0 §2 (`class_oot`), §6; KARARLAR D5, D6;
  - SPEC_HAZARD_V1 §5.2, §5.5, §6.1, §6.4, §7.2, §7.3;
  - SPEC_C_V0 §1.2, §5.2, §5.5, §6.1, §6.4; KARARLAR_C C1 (hedef y4 = 1 − Y_D10, kapanış ≤ arz olay);
  - SPEC_POST_D1_V0 §4;
  - SPEC_SCORING §2, §3, §7, §8: D_h, hedefler, RPS, Brier, eşleşik fark, ay-blok bootstrap (B = 4000, numpy PCG64, tohum 20260921, yüzdelikler 2.5/97.5; blok = gerçekleşen D_1'in takvim ayı), n ≥ 10 ve ≥ 6 blok, "geçiyor" yalnız n ≥ 30 ve aralık 0'ı dışlıyorsa;
  - SPEC_DEVIATIONS I10–I13, L1, M1 (sonuç girişi), M12 (post_d1 beklentisi).
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.**

## Körlük kuralı (Faz 1 boyunca)
- Şunları açma, okuma, `cat`/`grep` etme: `scores/scores_oot.json`, `docs/SCORES_OOT.md`, `docs/faz7_vault/SKOR_RAPOR.md`, `docs/faz7_vault/ekler/skor_*`.
- `borsai`'yi import etme. `borsai/scoring.py`'nin eski kohort bölümünü okuma; tanımları şartnamelerden al.
- Okuyabileceklerin: kayıtlar (`registry/oot/records`, `registry/oot/post_d1`), sonuç satırları (`data/outcomes_oot`, `registry/oot/d1_rows`), model JSON'ları, git geçmişi, push kanıtları ve `scores/scores.json`. Sonuncusu yalnız yakın dönem bloğu (`models[].backtest.near_era`) içindir; bu görevden öncedir.
- Bir tanım şartnamede belirsizse yorumunu yaz. Faz 2'de kodla farkı bulguya çevir.

## İzinli izlenmeyen / değişmiş
- Bu görev dosyası ve `docs/prompts/FAZ7_VAULT_SCORE.md`.
- Opus'un yolları: `scores/scores_oot.json`, `docs/SCORES_OOT.md`, `tests/`, `docs/SPEC_DEVIATIONS.md`, `docs/faz7_vault/`. Bunlara bakma.
- Başka bir şey varsa DUR.

## Faz 1 — kör yeniden hesap (yalnız kasa, 64 üye)
0. **Taban.** HEAD, VB'nin kanıt commit'i ya da torunu.
1. **Sınıf.** Her (model, kasa üyesi) çifti için `class_oot`'u git DAG'ından (`git merge-base --is-ancestor`) ve `registry/push_proofs/*.json` `created_at` değerlerinden hesapla. Kapsam: INDEX'in 27 modeli ve `post_d1_hazard_v0`.
   - Kayıt = o modeli içeren en erken etkin kayıt.
   - Listeleme öncesi modellerin sonuç girişi = kasa d1_rows'unu ya da outcomes_oot'u ekleyen ilk commit.
   - post_d1'in sonuç girişi = D_1 sonrası sonuç (d1_rows hariç).
   - Kohort kapısı: her MEMBER için modeli içeren kayıt girişin atası ve kanıtı önce.
   - Sayılar: OOT_BLIND / OOT_RETRO. Beklenen: kasada RETRO 0.
2. **Satır durumları.** Model başına: SCORED / REFUSED / NOT_APPLICABLE_REGIME / TARGET_UNAVAILABLE / PENDING / SKIPPED. post_d1 için satır kapısı SPEC_POST_D1_V0'daki gibi: yalnız D1 tavan etiketi 1 olan üye satırdır.
3. **Hücreler** (kasa; arz başına kayıp çiftleri, n, blok sayısı, ortalama fark = model − karşılaştırılan, %95 aralık). Karşılaştırıcı değerleri kayıttan alınır; kural değerleri donmuş H99 değerleridir.
   - **v1 (3 aday):**
     - birincil RPS − `base_km_expanding`;
     - RPS − `ceiling_hazard_v0` (k2 hücresi);
     - Brier k = 10 − `base_km_expanding`;
     - merdiven: `v1_real − v1_clip`, `v1_pooled − v1_real`, `v1_pooled − v1_pooled@INF`;
     - kalibrasyon bilgisi: ort. S_5 ve gözlenen P(L ≥ 5).
   - **`ceiling_hazard_v0` − `base_km_expanding`** (kasada; SPEC_HAZARD_V1 §6.1'in ilk satırı).
   - **(C) (3 aday):**
     - birincil D10 Brier − `base_rate`;
     - D10 Brier − `v1_5_h99` (k2 hücresi);
     - `pooled − h99`, `pooled − pooled@ZERO`;
     - D5 Brier − `base_rate`;
     - `v1_5_h99 − base_rate` (D10, bilgi);
     - kalibrasyon bilgisi: ort. P(y4) ve gözlenen oran.
   - **Eski 8 birincil hücre** (SPEC_OOT_PRE_H99_V0 §6) kasada.
   - **`post_d1_hazard_v0`:** j = 1 koşullu RPS − `ceiling_hazard_v0` koşullu, kasada.
4. **Seçim kuralları** (kendi sayılarınla).
   - v1 §5.5 ve (C) §5.5: her aday için k1, k2, k3; uygun olanlar; eşitlik kuralları; sonuç.
   - k3 değerleri `scores/scores.json` `near_era` bloklarından.
5. **Kaynak denetimi.**
   - `MANIFEST_OOT.csv`'de kasa açılışında eklenen satırlardan (veri satırı 915–1168; ilk 914 satır açık kümenindir) `random.Random(20260929).sample` ile 10 satır seç ve resmi URL'den geçici dizine indir.
   - sha256 pinle eşit olmalı.
   - O bülten tarihine düşen kasa üyelerinin `<T>.E` satırlarında `close_raw`, `upper_limit_raw`, `reference_raw` ve `trade_count_raw` sonuç CSV'leriyle aynı olmalı. TARIH alanı ISO ya da d.mm.yyyy olabilir (SPEC_DEVIATIONS M14); kendi çözümlemeni yaz.
   - Sonra geçici dosyaları sil. Çıktı yalnız sayılar.
6. **Yaz ve commit (körlük kanıtı).** `docs/fable_faz7_vault/` altına: `recompute.py`, `kaynak_denetimi.py`, `BAGIMSIZ.json` (sınıf ve durum sayıları, hücreler, seçim kuralları), `faz1_ozet.md` (tanım yorumları dahil).
   ```
   git add docs/fable_faz7_vault docs/prompts/FAZ7_FABLE_VAULT_RECOMPUTE.md
   git commit -m "BORSAI_FAZ7_FABLE_VAULT_BLIND: independent vault recompute and selection rules before reading the vault scores" -- docs/fable_faz7_vault docs/prompts/FAZ7_FABLE_VAULT_RECOMPUTE.md
   ```
   `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme. Opus'un yollarını commit'e koyma.

## Faz 2 — karşılaştırma
`BORSAI_FAZ7_VAULT_SCORE_REPORT` commit'i yoksa burada dur. Oturum biter; proje sahibi Opus bitince aynı pencereye "Kaldığın yerden devam et" yazar.

Varsa şunları oku: `scores/scores_oot.json`, `docs/SCORES_OOT.md`, `docs/faz7_vault/SKOR_RAPOR.md` ve `git diff 439a808..HEAD -- borsai tests`. Denetle:
- Sınıf ve durum sayıları birebir.
- Faz 1'deki bütün hücrelerde n, blok sayısı ve ortalama fark |Δ| ≤ 1e-9.
- %95 aralık: aynı üretici, tohum ve blok sırasıyla |Δ| ≤ 1e-9. Sıra kuralı farkı yüzünden tutmazsa nedeni bul ve yaz. Sınırlar |Δ| ≤ 0.005 içindeyse ve hüküm değişmiyorsa KÜÇÜK; hüküm ya da bir seçim kuralı değişiyorsa ÖNEMLİ.
- `oot_pre_h99_all` yalnız 19 eski model ve n = açık + kasa.
- Hüküm dili (geçiyor / geçemiyor / ayırt edilemiyor / yetersiz örnek; terazi adı).
- SKOR_RAPOR'un beklenti karşılaştırması (T3), "beklentiden çok iyi" işaretleri (T4) ve başarısızlık tanımları (T5) doğru mu?
- **İki seçim kuralının sonucu Faz 1'deki sonucunla aynı mı?**
- "Beklentiden çok iyi" işaretli bir hücre varsa mekanizmayı kısaca açıkla: kazancı hangi yıl ya da hangi arz tipi taşıyor (yalnız sayılarla, üye adı olmadan).
- `borsai/` farkı boş olmalı (skor tanımı değişmemeli). `tests/` farkı yalnız T7 sıkılaştırması olmalı.

**Hüküm:** `VAULT_SCORE_OK` ya da bulgular (KRİTİK / ÖNEMLİ / KÜÇÜK; tür: kod / karar / bilgi). `docs/fable_faz7_vault/AUDIT.md`:
```
git add docs/fable_faz7_vault
git commit -m "BORSAI_FAZ7_FABLE_VAULT_AUDIT: comparison of independent vault recompute with vault scores and selection rules" -- docs/fable_faz7_vault
```

## Kurallar
- Yazılabilir yalnız `docs/fable_faz7_vault/`, bu görev dosyası ve geçici dizin (repo dışı). Geri kalan her şey salt okunur.
- Karantina dizinine (`~/Desktop/BorsAi_quarantine`) dokunma; kaynak denetimi resmi URL'den yeniden indirir.
- Raporda üye başına değer tablosu yok. Kasa kodları artık gizli değil ama gereksizse yazma.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- Oturum içinde proje sahibine karar sorman gerekirse soruyu ve seçenekleri açıkça yaz. Proje sahibi orkestratöre danışarak cevaplayacak.
- Rapor Türkçe.

## Kabul kapısı
- **K1** Faz 1 commit'i, Opus'un skor çıktılarına bakılmadan atıldı (commit sırası ve görev kuralı).
- **K2** Hücreler, sınıf ve durum sayıları ve iki seçim kuralı bağımsız hesaplandı. Kaynak denetiminde 10/10 sha ve kasa satırları eşit.
- **K3** Faz 2 karşılaştırması toleranslarla yapıldı; hüküm ve bulgular AUDIT.md'de.

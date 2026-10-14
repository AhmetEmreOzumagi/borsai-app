# TASK_ID: BORSAI_FAZ6_FABLE_S6_RECOMPUTE_20260925

Model: Fable · yüksek. Klasör: ~/Desktop/BorsAi. **Ağ yalnız 10 bülten zip'inin resmi URL'den yeniden indirilmesi için** (Faz 1 adım 4; `data/raw/bist/MANIFEST_OOT.csv`'deki URL'ler). İndirmeler repo ve karantina dışındaki geçici bir dizine gider (ör. `/tmp/borsai_fable_s6/`). Başka ağ yok. push/tag/amend yok.

## Rol
Donmuş modellerin eski kohort açık kümesindeki (71 arz) skorunu, uygulayıcıdan bağımsız ve **onun sonucunu görmeden** yeniden hesaplarsın. Opus aynı anda `docs/prompts/FAZ6_S6_SCORING.md`'yi koşuyor; `scores/scores_oot.json`, `docs/SCORES_OOT.md` ve `docs/faz6/S6_RAPOR.md`'yi o üretecek. Yazan el ile denetleyen el ayrıdır.

## Bağlam
- Sıra:
  - S2 kayıtları `1dcceff` (kanıt 2026-09-24T22:39:24Z);
  - S3a d1_rows `9e1e992` ve S3b post_d1 kayıtları `7ade6a8` (kanıt commit'i `3c82378`);
  - S5 sonuç satırları `77b54f7` (kanıt commit'i `BORSAI_PUSH_PROOFS: Faz 6 S5 outcome rows (77b54f7)`).
  
  Raporlar: `docs/faz6/S2_RAPOR.md`, `docs/faz6/S3_S5_RAPOR.md`. Sonuç takvimi 2023-04-24'ü seans sayar (EK1).
- Tanımlar:
  - SPEC_OOT_PRE_H99_V0 §2 (`class_oot`) ve §6 (birincil hücreler, n kuralları);
  - KARARLAR D5, D6;
  - SPEC_DEVIATIONS I10–I13, I22, I23 (tanım metinleri);
  - docs/specs/SPEC_SCORING.md §2, §3, §7, §8: D_h, hedefler, kayıplar, eşleşik fark, ay-blok bootstrap (B = 4000, numpy PCG64, tohum 20260921, yüzdelikler 2.5/97.5), n ≥ 10 ve ≥ 6 blok;
  - SPEC_CEILING_PATH_V0 §5; SPEC_POST_D1_V0 §4.
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.**
- Hijyen: hangi kodun SEALED olduğu yazılmaz. SEALED bir kodun satırı hiçbir bültende aranmaz ya da okunmaz. `docs/faz6/dogrulama/EXPOSURE.md` §3 okunmaz.

## Körlük kuralı (Faz 1 boyunca)
- Şunları açma, okuma, `cat`/`grep` etme: `scores/scores_oot.json`, `docs/SCORES_OOT.md`, `docs/faz6/S6_RAPOR.md`, `docs/faz6/ekler/s6_*`, Opus'un bu görevde `borsai/scoring.py`'ye yaptığı değişiklikler.
- `borsai`'yi import etme. `borsai/scoring.py`'nin eski kohort bölümünü okuma; tanımları şartnamelerden al.
- Bir tanım şartnamede belirsizse yorumunu yaz. Faz 2'de kodla farkı bulguya çevir.

## İzinli izlenmeyen / değişmiş
- Bu görev dosyası ve `docs/prompts/FAZ6_S6_SCORING.md`.
- Opus'un yolları: `borsai/scoring.py`, `tests/`, `docs/SPEC_DEVIATIONS.md`, `scores/scores_oot.json`, `docs/SCORES_OOT.md`, `docs/faz6/`. Bunlara bakma.
- Başka bir şey varsa DUR.

## Faz 1 — kör yeniden hesap
0. **Taban.** HEAD, `77b54f7`'nin kanıt commit'inin ya da torununun üstünde.
1. **Sınıf.** Açık kümenin her (model, arz) çifti için `class_oot`'u git DAG'ından (`git merge-base --is-ancestor`) ve `registry/push_proofs/*.json` `created_at` değerlerinden hesapla:
   - 19 listeleme öncesi model için sonuç girişi = d1_rows ya da outcomes_oot'u ekleyen ilk commit.
   - `post_d1_hazard_v0` için = D_1 sonrası sonuç (d1_rows hariç).
   - Kohort kapısı: bütün 135 MEMBER'ın S2 kaydı, sonuç commit'inin atası.
   
   Sayılar: OOT_BLIND / OOT_RETRO.
2. **Satır durumları.** Model başına açık kümede SCORED / REFUSED / NOT_APPLICABLE_REGIME / TARGET_UNAVAILABLE / PENDING / SKIPPED. Kaynaklar: `registry/oot/records`, `registry/oot/post_d1`, `data/outcomes_oot/*.csv`.
3. **Birincil hücreler.** 9 hücre: SPEC_OOT §6 / I11'deki 8 listeleme öncesi hücre ve `post_d1_hazard_v0` için j = 1 koşullu RPS vs `ceiling_hazard_v0` koşullu. Her hücre için arz başına kayıp çiftleri, n, blok sayısı, ortalama fark (model − kural; negatif = model iyi) ve %95 aralık.
   - Karşılaştırıcı değerleri kayıttan alınır (kural 1; donmuş H99 değerleri).
   - Blok = gerçekleşen D_1'in takvim ayı.
4. **Kaynak denetimi.** `MANIFEST_OOT.csv`'den `random.Random(20260925).sample` ile 10 satır seç ve resmi URL'den geçici dizine indir.
   - sha256 pinle eşit olmalı.
   - O bülten tarihine düşen açık küme üyelerinin `<T>.E` satırlarında (yalnız açık küme kodları aranır) `close_raw`, `upper_limit_raw`, `reference_raw` ve `trade_count_raw` S5 CSV'leriyle aynı olmalı.
   - Sonra geçici dosyaları sil. Çıktı yalnız sayılar.
5. **Yaz ve commit (körlük kanıtı).** `docs/fable_faz6_s6/` altına: `recompute.py`, `kaynak_denetimi.py`, `BAGIMSIZ.json` (sınıf ve durum sayıları, 9 hücre), `faz1_ozet.md` (tanım yorumları dahil).
   ```
   git add docs/fable_faz6_s6 docs/prompts/FAZ6_FABLE_S6_RECOMPUTE.md
   git commit -m "BORSAI_FAZ6_FABLE_S6_BLIND: independent out-of-time recompute before reading S6 outputs" -- docs/fable_faz6_s6 docs/prompts/FAZ6_FABLE_S6_RECOMPUTE.md
   ```
   `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme. Opus'un yollarını commit'e koyma.

## Faz 2 — karşılaştırma
`BORSAI_FAZ6_S6_REPORT` commit'i yoksa burada dur. Oturum biter; proje sahibi S6 bitince aynı pencerede "Kaldığın yerden devam et" der. Varsa şunları oku: `scores/scores_oot.json`, `docs/SCORES_OOT.md`, `docs/faz6/S6_RAPOR.md` ve Opus'un kod farkı (`git diff 3c82378..HEAD -- borsai/scoring.py`). Denetle:
- Sınıf ve durum sayıları birebir.
- 9 birincil hücrede n, blok sayısı ve ortalama fark |Δ| ≤ 1e-9.
- %95 aralık: aynı üretici, tohum ve blok sırasıyla |Δ| ≤ 1e-9. Sıra kuralı farkı yüzünden tutmazsa nedeni bul ve yaz. Sınırlar |Δ| ≤ 0.005 içindeyse ve hüküm değişmiyorsa KÜÇÜK; hüküm değişiyorsa ÖNEMLİ.
- `SCORES_OOT.md`'nin hüküm dili (geçiyor / geçemiyor / ayırt edilemiyor / yetersiz örnek; terazi adı).
- S6_RAPOR'daki §8 karşılaştırması doğru mu? "Beklentiden çok iyi" işaretli bir hücre varsa mekanizmayı kısaca açıkla: kazancı hangi dönem ya da hangi arz tipi taşıyor (yalnız sayılarla, SEALED yok).
- Opus'un kod farkında skor tanımı değişmemiş olmalı (yalnız CLI, render, F5 ayrıştırıcısı).
- SEALED kodu hiçbir yeni dosyada yok.

**Hüküm:** `S6_OK` ya da bulgular (KRİTİK / ÖNEMLİ / KÜÇÜK; tür: kod / karar / bilgi). `docs/fable_faz6_s6/AUDIT.md`:
```
git add docs/fable_faz6_s6
git commit -m "BORSAI_FAZ6_FABLE_S6_AUDIT: comparison of independent recompute with S6 scores" -- docs/fable_faz6_s6
```

## Kurallar
- Yazılabilir yalnız `docs/fable_faz6_s6/`, bu görev dosyası ve geçici dizin (repo dışı). Geri kalan her şey salt okunur.
- Karantina dizinine (`~/Desktop/BorsAi_quarantine`) dokunma; kaynak denetimi resmi URL'den yeniden indirir.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- Rapor Türkçe.

## Kabul kapısı
- **K1** Faz 1 commit'i, Opus'un S6 çıktılarına bakılmadan atıldı (commit sırası ve görev kuralı).
- **K2** 9 birincil hücre, sınıf ve durum sayıları bağımsız hesaplandı. Kaynak denetiminde 10/10 sha ve açık küme satırları eşit.
- **K3** Faz 2 karşılaştırması toleranslarla yapıldı; hüküm ve bulgular AUDIT.md'de.

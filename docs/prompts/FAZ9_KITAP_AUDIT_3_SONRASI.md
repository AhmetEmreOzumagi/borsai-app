# FAZ9_KITAP_AUDIT_3_SONRASI — Listeleme sonrası modeller, ölçüm ve kuralların bağımsız denetimi

**Model: Claude Code / Fable · yüksek**

- **TASK_ID:** `BORSAI_FAZ9_KITAP_AUDIT_3_20261008`
- **Klasör:** repo kökü `~/Desktop/BorsAi`. Ağ yok.
- **Ortak kurallar:** önce `docs/prompts/FAZ9_KITAP_AUDIT_ORTAK.md`'yi oku. Bu görevde `<n>` = 3, `<AD>` = SONRASI.
- **Rapor:** `docs/fable_kitap_audit/AUDIT_3_SONRASI.md`. Ekler `docs/fable_kitap_audit/ekler/3/` altına.

## Kapsam

- `kitap/05_listeleme_sonrasi_modeller.md`'nin tamamı.
- `kitap/06_olcum_ve_kurallar.md`'nin tamamı.

Projenin dürüstlük iddiası bu iki bölümde. Asıl soru şu: **CLAUDE.md'deki kurallar gerçekten kodla zorlanıyor mu, ve yayımlanan skorlar kayıtlardan yeniden üretilebiliyor mu?**

## ÖNCE OKU

- CLAUDE.md
- `docs/fable_kitap_audit/README.md`
- `kitap/05_listeleme_sonrasi_modeller.md` ve `kitap/06_olcum_ve_kurallar.md`
- `docs/specs/SPEC_SCORING.md` (tamamı)
- `docs/specs_faz5/SPEC_POST_D1_V0.md`
- `docs/specs_faz8/SPEC_BREAK_V0.md` ve `KARARLAR.md`
- `docs/specs_faz6/SPEC_OOT_PRE_H99_V0.md` ve `KARARLAR.md`
- `docs/SPEC_DEVIATIONS.md`
- `docs/SCORES.md`, `docs/SCORES_BREAK.md`, `docs/SCORES_OOT.md`
- Kod: `borsai/backtest.py`, `metrics.py`, `scoring.py`, `freeze.py`, `registry.py`, `push_proof.py`, `rules.py`, `post_d1.py`, `post_break.py`, `predict_post_d1.py`, `predict_break.py`
- Önceki denetimler (yeniden yapma; sonuçlarını iddia olarak kullan): `docs/fable_faz5_audit/`, `docs/fable_faz6_audit/`, `docs/fable_faz7_vault/`, `docs/fable_faz8_audit/`

## Adım 0

`FAZ9_KITAP_AUDIT_1_VERI.md`'nin Adım 0'ıyla aynı: HEAD, fark listesi ve izlenmeyen dosyalar. Koruma ölçümü → `ekler/3/koruma_once.txt`.

## Adımlar

Sıra önem sırasıdır. Her adım bitince raporu güncelle.

**1. Kurallar kodla zorlanıyor mu? (§6.2)**

CLAUDE.md'nin her maddesi için:
- onu zorlayan kod ya da testi bul;
- klonda kuralı bozan bir mutasyon yap;
- testin kırmızıya döndüğünü göster.

Maddeler: kural 1–6, sıra kuralı, "yalnız resmi kaynak", "legacy değiştirilmez". En az şu mutasyonlar:
- (a) bir kayıttan bir model çıkarılmış;
- (b) kayıtta parametre hash'i yanlış;
- (c) push kanıtı olmayan kayıt LIVE sayılmaya çalışılıyor;
- (d) iki terazi aynı metrikte toplanıyor;
- (e) parametresi değişmiş model aynı model_id ile;
- (f) `legacy/` içinde bir bayt değişmiş;
- (g) resmi olmayan kaynaktan bir sonuç satırı;
- (h) bir dondurulmuş kayıt silinmiş;
- (i) deney günlüğünden bir satır silinmiş.

Zorlanmayan maddeyi açıkça yaz. CLAUDE.md "kodla zorlanır" dediği için bu bir [P] bulgusudur.

**2. Canlı sicili sıfırdan yeniden üret (§6.10, §6.11).** `borsai` import edilmez.
- `registry/records/`, `registry/push_proofs/`, `data/outcomes/` ve git DAG'ını kullan. Her (model, arz) çiftinin sınıfını §6.10.2'deki formülle ve SPEC_SCORING §5'e göre kendin hesapla: LIVE, LATE_RECORD, RETRO, LEGACY_SELF_REPORTED, geçersiz kullanım, REFUSED, SKIPPED, PENDING, TARGET_UNAVAILABLE.
- `scores/scores.json` ile karşılaştır: sınıflar, n'ler, metrikler.
- Kılavuzun iki iddiası:
  - "asıl modellerde LIVE n = 0, 7 kaydın hepsi LATE";
  - "tek LIVE satır, NETGL'in eski repodan gelen V1.5 kaydı".

  İkisini de ölç. NETGL × `v1_5_h99` LIVE sayılıyorsa, CLAUDE.md'deki "Bir arz bir model için ancak modelin JSON'u o arzın sonucu repoya girmeden önce dondurulduysa prospektiftir" kuralına uygun mu?
- Push kanıtının kendisi nasıl doğrulanıyor (`push_proof.py`)? Kanıt sahte ya da eski olabilir mi? Kanıt dosyalarının sayısı ile günlük satır sayısını ölç.
- Kural 1'in ikinci cümlesi: her kayıt, kendi aşamasının INDEX'indeki bütün modelleri ve parametre hash'lerini içeriyor mu? `registry/` altındaki bütün kayıtlar için ölç.

**3. Walk-forward kesimi ve fold planı (§6.5).** Burada sızıntı en kolay saklanır.
- Listeleme öncesi backtest'lerde eğitim satırı j için şu koşul her fold'da sağlanıyor mu: **j'nin kullanılan etiketinin son seansı < test arzının T'si**? Listeleme tarihi değil, etiket tarihi önemli. Örneğin D10 ve L için D10 seansı.
- Ledger'lardan her ailede bütün fold'ları tara.
- MIN_TRAIN_N = 10 ile n = 87 çıkıyor mu?
- `post_d1` ve `break` için de kendi kesim kurallarını (şartname §'leri) ledger'da denetle.

**4. Metrikler ve belirsizlik (§6.6–§6.8).**
- RPS, Brier, log-loss ve MAE tanımları: şartname, kod ve kılavuz tutarlı mı? Log-loss'ta olasılık kırpma var mı?
- Blok bootstrap'ı kendin yaz: ay blokları, 4000 tekrar, `random.Random(20260921)`, şartnamedeki yüzdelik indeksleri. Her aileden en az bir başlık hücresini (toplam en az 5 hücre) ledger'dan yeniden üret.
- Hüküm dili ve küçük n kuralları kodda mı uygulanıyor, yoksa yalnız metinde mi?

**5. Ön kayıt ve çoklu karşılaştırma (§6.9).**
- Her şartnamenin birincil hücresi, sonuçlar görülmeden önce commit'lenmiş mi? Şartname commit'i, ledger commit'inin atası mı?
- Birincil tanım sonradan değişmiş mi (`git log -p` şartname dosyalarında)?

**6. Listeleme sonrası modeller (bölüm 5).**
- **`post_d1_hazard_v0`:**
  - d1_lock = (D1 en düşük == üst limit) ve d1_turnover = ln(D1 hacmi / shares_offered).
  - Offset yapısı.
  - Şartname, kod ve JSON üçlüsü tutarlı mı?
  - Nihai fit'i yeniden yap ve birincil hücreyi ledger'dan yeniden üret.
- **`break_floor_v0` ve `@ZERO`:** Faz 8 denetimi backtest'i bit-eşit üretti; onu tekrarlama. Şunlara bak:
  - dondurulmuş JSON o denetimdeki önizlemeyle aynı mı?
  - canlı aşama (`python -m borsai.scoring --break`) bu JSON'u doğru kullanıyor mu?
  - `registry/post_break/`'teki 7 makine kaydını sıfırdan üret: tahminler bit-eşit mi? MACHINE_SEQUENCED, RETRO ve LIVE sınıfları CLAUDE.md kural 1'in POST_BREAK cümlesine göre doğru mu?
  - "7'nin 7'si RETRO" iddiası.
- **Yapısal sıfır ve yastık aritmetiği (§5.4):** formülü ve kılavuzdaki örnekleri yeniden hesapla.
- **§5.6:** kılavuzun Fable denetimleri hakkında söyledikleri, denetim raporlarıyla tutuyor mu?

**7. Eski kohort ve kasa (§6.12).**
- 135 arz, 64 kasa (yalnız sayı), açılanlar.
- Sıra kuralı: eski kohortun bütün listeleme öncesi kayıtları, sonuç verisinden önce push edilmiş mi?
- `scores/scores_oot.json`'ı açık arzlar için kayıtlardan yeniden üret.

**8. Defterler ve testler (§6.13–§6.15).**
- `experiments/log.jsonl` gerçekten yalnız ekleniyor mu? `git log -p` ile hiçbir satır silinmemiş ya da değişmemiş olmalı.
- Her backtest satırındaki spec ve veri hash'leri dosyalarla tutuyor mu?
- SPEC_DEVIATIONS'ta model_id değiştirmeden davranış değiştiren bir sapma var mı (kural 5)?
- §6.15'teki bekçiler var mı? pytest sayısını yalnız toplama ile ölç (`--collect-only -q`).

## Commit

```
git add docs/prompts/FAZ9_KITAP_AUDIT_3_SONRASI.md docs/fable_kitap_audit/AUDIT_3_SONRASI.md docs/fable_kitap_audit/ekler/3
git commit -m "BORSAI_FAZ9_KITAP_AUDIT_3: independent audit of post-listing models, scoring and rule enforcement against the project guide" -- docs/prompts/FAZ9_KITAP_AUDIT_3_SONRASI.md docs/fable_kitap_audit/AUDIT_3_SONRASI.md docs/fable_kitap_audit/ekler/3
```

## Kabul kapısı

- **K1:** Her CLAUDE.md maddesi için zorlayan kod gösterildi ya da yokluğu yazıldı. Mutasyonların sonuçları `ekler/3/` altında.
- **K2:** Canlı sicil ve POST_BREAK kayıtları sıfırdan yeniden üretildi; `scores*.json` ile karşılaştırıldı.
- **K3:** Kesim kuralı her ailenin bütün fold'larında tarandı; en az 5 hücre kendi bootstrap'ınla yeniden üretildi.
- **K4:** Koruma eşit, hijyen sayımları 0, commit yalnız izinli yollarda.

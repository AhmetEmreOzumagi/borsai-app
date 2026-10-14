# TASK_ID: BORSAI_FAZ3_APP_P1_20260923

Model: Opus 5 · Extra. Klasör: ~/Desktop/BorsAi. Ağ: yalnız npm/crates (gerekirse). push/tag/amend yok.

## Bağlam
- Aşama 3 (dondur akışı) tamam: a41f183, 2a7cf0c.
- Fable'ın eki `docs/app/SPEC_APP_EK2.md` (c89ff5a): Faz 4'ün üç `ceiling_path` modeli uygulamaya port edilecek. Yeni **Aşama P**:
  - P1 = port + parite (U41–U47): bu görev
  - P2 = gösterim (U48–U50): sonraki görev
- **Proje sahibi kararı (2026-09-23), SPEC_APP §3g ve U52:**
  - Kullanıcı beyanı yalnız "seri sürüyor" etiketidir. Hiçbir olasılık ya da getiri hesabına girmez, resmi j'yi değiştirmez.
  - Beyan resmi verinin önündeyse koşullu bölüm boş kalır ve "resmi kapanış bekleniyor" yazar.
  - Bugünkü kod buna aykırı: `commands/ceiling.rs` "hesapta kullanılan: beyan varsa beyan, yoksa dosya" diyor, beyan türleri CEILING/NOT_CEILING/PENDING.
- Paralel oturum: Sonnet/Opus `docs/prompts/FAZ4_SCORES_CELLS.md` görevini yapıyor.
  - O oturum yalnız `borsai/scoring.py`, `tests/`, `scores/scores.json`, `docs/SCORES.md`, `docs/SPEC_DEVIATIONS.md` değiştirir.
  - `scores/scores.json` oturum sırasında değişebilir; uygulama onu derlemeye gömüyor. Commit öncesi tam test koşusunu o anki dosyayla yap. `scores.json`'a bağlı bir test kırılırsa, dosyayı değil testin varsayımını raporla.

ÖNCE OKU:
- CLAUDE.md
- docs/app/SPEC_APP.md §3g (güncel, U52 dahil), §5.6
- docs/app/SPEC_APP_EK2.md tamamı. §1–§3 ve §6–§7 bağlayıcı. §4 bilgi içindir (P2).
- docs/specs_faz4/SPEC_CEILING_PATH_V0.md §2–§4, §7
- borsai/predict_path.py (referans), borsai/survival.py
- app/ kodu; özellikle `commands/ceiling.rs`, `render/ceiling.ts`, `screens/results.ts`, `screens/registry.ts`, `crates/borsai_predict/`, `parity/gen_golden.py`, `build_embed.rs`

## Bölüm A — beyan düzeltmesi (U52). Önce bu, ayrı commit.
1. `streak_view` ve koşullu komutlar beyanı hesaba almaz.
   - j yalnız `data/outcomes/<T>.csv`'den gelir (resmi j).
   - Koşullu hesap yapan komutların imzasında beyan parametresi olmaz (U52-5).
2. Beyan türü tek: "seri sürüyor". NOT_CEILING ve PENDING beyanları kalkar.
   - Eski kişisel kayıtlarda bu değerler varsa yüklemede yok sayılır ve sarı not düşer.
   - Şema sürümü değişmez: kabul edilen değerler daralıyor, alan aynı.
3. Arayüz:
   - Beyanlı gün turuncu çerçeve ve "seri sürüyor (kullanıcı beyanı)".
   - Kaynak satırı: "D<k>: kullanıcı beyanı, hesaba katılmadı".
   - Beyan resmi verinin önündeyse koşullu olasılık bölümü boş kalır ve "resmi kapanış bekleniyor" yazar.
   - Resmi veriyle çelişen beyan gösterilmez; yerine "beyan resmi veriyle çelişiyor; resmi değer esas" uyarısı.
   - "Varsayımsal j" kaydırıcısı olduğu gibi kalır. O beyan değildir.
4. U52 testi SPEC_APP §5.6'daki tanımıyla, altı maddesinin hepsi.
   - Faz 4 kısmı (koşullu getiri) P2'ye kalır. Testte bu kısım için açık bir `todo`/`skip` işaretle, gerekçesi "P2".
   - Pozitif kontrol (U52-4) zorunlu: arama sayı bulabildiğini göstermeli.
   - Etkilenen eski testler (U39, U40, `ceiling.test.ts`, `stage2.rs`) yeni kurala göre güncellenir. Her değişikliği raporda gerekçesiyle listele; test gevşetilmez.
5. `bash app/scripts/test.sh` yeşil. Commit (mesaj aşağıda).

## Bölüm B — Aşama P1: port ve parite (EK 2 §1–§3, U41–U47)
1. `borsai_predict`'e `ceiling_path` türü:
   - `dec.rs` ekleri
   - limit yolu, hücreler, havuzlama, karışım, kuantil
   - `conditional` ve `conditional_after_break`
   - ret/uyarı kodları (EK 2 §2)
2. `gen_golden.py` 19 modele (EK 2 §3.1–§3.2, §3.4).
   - 16 eski altın dosya ve `_patched_params.jsonl`'ın ilk 19 satırı BAYT-EŞİT kalır (U46).
   - Değişirse DUR ve nedenini raporla.
3. `PINNED_MODEL_IDS` 16 → 19. "16" sabitleri EK 2 §3.5'teki listeye göre güncellenir.
   - Parite ve ekran kodunda 16/19 sabiti YOK; desteklenen küme gömülü veriden (aşama 3 kuralı).
4. Kayıt paritesi (EK 2 §3.7):
   - eski 7 kayıt: `16/16 + kayıtta yok: 3`, uyuşmazlık değil
   - geçici klonda yeni kayıt: `19/19`
   - `e2e_freeze_tmp_repo.sh` bunu yazdırır
5. Testler: U41–U47 ve bütün eski testler yeşil. Commit öncesi tam koşu:
   - `bash app/scripts/test.sh`
   - iki e2e betiği
   - `.venv/bin/pytest -q`
6. Rapor EK 2 §7'deki önceden yazılmış beklentiyi satır satır karşılaştırır: 19/19, maks |Δ|, bit-eşit oranları, altın satır sayıları, `n_atoms`, VEYAS ve NETGL değerleri.
   - Tolerans gevşetilmez. Parite tutmuyorsa Rust düzeltilir. Python'da eksik bulunursa "Ö-görevi" olarak raporlanır, düzeltilmez.

Bölüm B tek oturumda bitmezse:
- Yeşil ve tutarlı bir ara noktada commit at. Mesaja `(partial)` ekle.
- Kalanları raporda listele.

## Kurallar
- YALNIZ `app/` altına yaz. Tek istisna bu görev dosyası.
- `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `docs/`, `tests/` salt okunur. Dondur/iptal yalnız geçici klonda.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- `git add -A` yok. Commit'ler:
  ```
  git add app docs/prompts/FAZ3_APP_P1.md
  git commit -m "<mesaj>" -- app docs/prompts/FAZ3_APP_P1.md
  ```
  - `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Mesajlar:
  - A: `BORSAI_FAZ3_U52: user declaration is label only, never enters conditional probability or return (owner decision)`
  - B: `BORSAI_FAZ3_P1: ceiling path models ported to Rust with golden parity 19/19 (SPEC_APP EK2 stage P1)`
- Rapor Türkçe.

## Teslim (rapor)
- İki commit'in hash'i ve `git show --stat` özeti.
- A: U52'nin altı maddesinin sonucu; değiştirilen eski testler ve gerekçeleri.
- B: U41–U47 tablosu; `parity_report.json` özeti (19 model, maks |Δ|, bit-eşit oranı); EK 2 §7 karşılaştırma tablosu.
- U46 kanıtı (16 dosya bayt-eşit).
- Test sayıları ve süreleri: cargo, npm, pytest.
- Sapmalar ve kalan işler.

## Kabul kapısı
- K1 U52 yeşil (Faz 4 kısmı P2'ye işaretli); beyan hiçbir hesap yolunda yok.
- K2 U41–U47 yeşil; 19/19 parite, maks |Δ| ≤ 1e-9.
- K3 16 eski altın dosya bayt-eşit (U46).
- K4 Aşama 0–3 testleri ve e2e betikleri yeşil; tam pytest yeşil.
- K5 Commit'ler yalnız `app/` ve bu görev dosyası.

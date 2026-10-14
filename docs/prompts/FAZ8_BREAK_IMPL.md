# TASK_ID: BORSAI_FAZ8_BREAK_IMPL_20261001

Model: Opus 5.5 · Extra. Klasör: ~/Desktop/BorsAi. push/tag/amend yok.
- **Ağ:** yalnız adım 0b'deki iki Borsa İstanbul PDF'i (`www.borsaistanbul.com/files/`). Başka ağ yok.

## Rol
Kırılma akşamı modelini kodlar ve backtest'ini yaparsın. Şartname: `docs/specs_faz8/SPEC_BREAK_V0.md` + `KARARLAR.md` (Fable, `7d78d43`).

Bu görev şartnamenin **A + B** kısmıdır (§0.4):
- kırılma tablosu, özellikler, model, ürün karşılaştırıcısı, yastık kuralı, kurallar, testler;
- walk-forward backtest, ledger, `docs/MODELS.md` Faz 8 bölümü, günlük.

**Yapılmaz:** dondurma, canlı skorlama, makine kayıt yazıcı, uygulama. Bunlar sonraki görevlerdir.

## Proje sahibi kararları (2026-10-01; KARARLAR §C'ye yazılır)
- **C1:** Birincil hedef ertesi seans taban kapanışı (y_F1). D10 için yeni fit edilmiş model yok; yalnız yastık kuralı + mevcut ürün.
- **C2:** `MACHINE_SEQUENCED` satırları `live_break` ölçeğinde n'e sayılır. CLAUDE.md kural 1'e SPEC_BREAK_V0 §9.4'teki cümle **aynen** eklenir.
- **C3:** L = 0 (b = 1) kapsamda.
- **C4:** `FON_KRIZI_2026` uyarısı proje sahibi tarih verene kadar açık.
- **C5:** Rev. 54 bant ve baz fiyat doğrulaması bu görevin adım 0b'sinde yapılır.

**Orkestratör notu (maruziyet eki; KARARLAR'a ek not olarak yazılır):** Orkestratörün 1 Ekim keşfinde, taban üstünde bozulan arzlarda ertesi seans taban oranı **6/47 ≈ 0.128** idi (düşüşle bozulan 5/31, yükselişle 1/16). Şartname §6'da bu oran ≈ 0.08 diye çıkarılmıştı.
- Bu oranla ideal kazanç −0.051 yerine ≈ −0.042 olur; merkez beklenti `@ZERO`'ya karşı ≈ −0.03'tür.
- §6'daki beklenti aralıkları **değişmez**; bu not yalnız kayıt içindir ve backtest'ten önce yazılır.

## Bağlam [orkestratör ölçtü]
- Taban `origin/main` = `7d78d43`.
- `borsai/predict_path.py` uygulamanın altın MANIFEST'inde pinli tahmin kaynaklarından biri (`predict_sources_sha256`; 11 dosya: features, horizons, predict, predict_fall, predict_hazard, predict_market20, predict_path, predict_pb, predict_post_d1, survival, tufe).
  - **Bu 11 dosya değişmez.** `mixture_atoms`, `conditional_after_break` ve `lower_limit` zaten dışa açık; yeni kod bunları çağırır.
  - Pinli bir kaynağa dokunmak gerekiyorsa DUR.
- Mevcut fit yolu: `borsai/backtest.py` (`_fit_logit`, `final_fit_fall` kalıbı).
- **Test komutları** (`docs/ENV.md`):
  - ara koşular `.venv/bin/pytest -q -n 6 --dist loadgroup`;
  - her commit'ten önceki son kabul koşusu sıralı `.venv/bin/pytest -q`.

## İzinli izlenmeyen
Yalnız bu görev dosyası. Başka bir şey varsa DUR.

## ÖNCE OKU
- CLAUDE.md
- `docs/specs_faz8/SPEC_BREAK_V0.md` (tamamı), `KARARLAR.md`, `ekler/profil_kirilma.txt`
- `docs/specs_faz4/SPEC_CEILING_PATH_V0.md` §3, §7; `docs/specs_faz7_c/SPEC_C_V0.md` (fit yolu ve rapor kalıbı)
- `docs/MODELS.md` (Faz 5 ve Faz 7C bölümlerinin rapor kalıbı)
- `docs/SPEC_DEVIATIONS.md` (H20 erişim sayacı, H27, C7)
- `docs/ENV.md`
- `borsai/predict_path.py`, `borsai/backtest.py`, `borsai/metrics.py`, `borsai/report_faz7c.py`, `borsai/specs.py`, `borsai/post_d1.py`

## Adımlar
0. **Taban ve kararlar (commit K).**
   - `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -1` = `origin/main`; ağaçta yalnız bu görev dosyası.
   - Taban testleri: paralel pytest, `bash app/scripts/test.sh`, `.venv/bin/python app/parity/gen_golden.py --check`. Sayılar `docs/faz8/test_runs.txt`'ye.
   - `docs/specs_faz8/KARARLAR.md` §C: karar sütununa yukarıdaki C1–C5 (tarih 2026-10-01) ve orkestratör notu. Başka satır değişmez.
   - `CLAUDE.md` kural 1'in sonuna §9.4 cümlesi aynen. Başka değişiklik yok.
   - Commit K: KARARLAR, CLAUDE.md, bu görev dosyası.

   **0b. Bant doğrulaması (C5; commit K'ye girer).**
   - İndir: `pay-piyasasi-proseduru.pdf` ve `borsa-istanbul-as-pay-piyasasi-yonergesi.pdf`. `pdftotext` ya da Python ile metne çevir; PDF'ler repoya girmez.
   - Yaz: `docs/faz8/BANT_DOGRULAMA.md`:
     - revizyon numarası ve tarihi;
     - sondaki değişiklik listesinden rev. 54 (21.09.2026) maddeleri;
     - fiyat marjı ve ±%10 uygulaması;
     - ilk gün baz fiyat kuralı;
     - limitlerin fiyat adımına yuvarlanması.

     Her madde alıntıyla ve dosya sha256'sıyla.
   - **Bant ya da baz fiyat kuralı değiştiyse DUR** ve raporla (§2.4 ve §5.1 sabitleri etkilenir). Değişmediyse "doğrulandı" yaz ve devam et.
   - PDF'e ulaşılamazsa engel değildir: "doğrulanamadı" yaz, devam et. Dondurmadan önce yeniden ele alınır.
1. **A: kod ve testler (commit A).**
   - Yeni modüller:
     - `borsai/post_break.py`: kırılma tablosu, yükleyici beyaz listesi, plan, karşılaştırıcılar, yastık kuralı;
     - `borsai/predict_break.py`: stdlib tahmin;
     - `borsai/report_faz8.py`.
   - `specs.py`'a Faz 8 girişleri (`SPEC_DOCUMENTS_FAZ8`, `OPERATIONAL_RULES_FAZ8` sonuç görülmeden).
   - Kabul testleri SPEC_BREAK_V0 §13'teki 1–10, 14, 15 (`tests/test_faz8_*.py`). 11–13 canlı skorlama görevine, 16 uygulamaya kalır.
   - Bu adımda backtest koşulmaz; testler sentetik ya da yalnız tablo düzeyinde.
2. **B: backtest (commit B).**
   - §7.2 planı; ledger (sütun sırası sabit) `docs/faz8/` altında.
   - §5.2 hücreleri, aylık blok bootstrap (C7).
   - `docs/MODELS.md` "Faz 8: kırılma akşamı" bölümü `report_faz8.py` ile; §6 tablosu satır satır "tuttu/tutmadı".
   - `experiments/log.jsonl`: `kind: backtest` (`spec_document_sha256`) + üç duyarlılık (`kind: sensitivity`).
   - "Beklentiden çok iyi" tetiklenirse raporda açıkça yaz; yine de dondurma yok. Bağımsız yeniden üretim her durumda sıradaki Fable görevidir.
3. **Son kabul:** sıralı `.venv/bin/pytest -q`, `bash app/scripts/test.sh`, `gen_golden --check`.
4. **Rapor** `docs/faz8/IMPL_RAPOR.md` (commit R). İçerik:
   - hash'ler;
   - bant doğrulaması sonucu;
   - kırılma tablosu kabul sayıları (§13-1);
   - fold sayıları;
   - §6 tablosu: beklenen ile gerçekleşen;
   - birincil hücre ve `@ZERO` hücresi (fark, %95 aralık, n, ay);
   - katsayı işaretleri ve seçilen C'ler;
   - yakın dönem ve 2023 ayrımı;
   - duyarlılıklar;
   - ledger sha'ları;
   - sapmalar;
   - sıradaki görev için notlar (Fable yeniden üretimi, canlı skorlama, makine kayıt).

## Kurallar
- **Yazılabilir:**
  - yeni `borsai/post_break.py`, `borsai/predict_break.py`, `borsai/report_faz8.py`;
  - `borsai/specs.py` (yalnız Faz 8 ekleri);
  - yeni `tests/test_faz8_*.py`;
  - `experiments/log.jsonl` (yalnız kodla, append);
  - `docs/MODELS.md` (yalnız Faz 8 bölümü, kodla);
  - `docs/faz8/`;
  - `docs/SPEC_DEVIATIONS.md` (gerekirse yeni N bölümü);
  - adım 0'da `docs/specs_faz8/KARARLAR.md` §C ve `CLAUDE.md` kural 1 eki;
  - bu görev dosyası.
- **Salt okunur:**
  - `models/`, `registry/`, `data/`, `scores/`, `app/`;
  - 11 pinli tahmin kaynağı ve diğer mevcut `borsai/` modülleri (yalnız içe aktarma);
  - `docs/specs*` (KARARLAR §C hariç);
  - `legacy/`.

  Mevcut bir modülde değişiklik gerekiyorsa DUR ve sor.
- Eğitim yalnız H99 (2026-08-19 kesimi). `data/outcomes/` (canlı 7 arz) ve eski kohort, kasa, OOT dosyaları **okunmaz**.
- Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- `git add -A` yok. Commit'ler pathspec'li:
  ```
  git add <yollar>
  git commit -m "BORSAI_FAZ8_<K|A|B|REPORT>: <özet>" -- <yollar>
  ```
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Soru sorman gerekirse seçenekleri açık yaz; proje sahibi orkestratöre danışarak cevaplar.
- Push yok. Rapor Türkçe.

## Tek oturumda bitmezse
Her adım commit'le biter. Yeniden başlarken `git log`'dan son commit'i bul ve sonraki adımdan devam et. Bağlam dolarsa adım sonunda dur, `docs/faz8/test_runs.txt`'ye "kalan adımlar" yaz.

## Kabul kapısı
- **K1** Commit K: KARARLAR §C ve CLAUDE.md eki yalnız verilen metinle; bant doğrulaması yazılı (doğrulandı ya da doğrulanamadı).
- **K2** §13'teki 1–10, 14 ve 15 yeşil; 11 pinli tahmin kaynağı ve `gen_golden --check` değişmedi.
- **K3** Backtest: ledger, MODELS.md Faz 8 bölümü (§6 satır satır), günlük satırları; birincil ve `@ZERO` hücreleri raporda.
- **K4** Son sıralı pytest, test.sh ve `gen_golden --check` yeşil. Commit'ler yalnız izinli yollarda; push yok.

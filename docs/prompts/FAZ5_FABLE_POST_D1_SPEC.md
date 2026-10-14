# TASK_ID: BORSAI_FAZ5_FABLE_POST_D1_SPEC_20260924

Model: Fable · yüksek. Klasör: ~/Desktop/BorsAi. Ek dizin ~/Desktop/Halka_Arz_Modeli (arşiv, salt okunur).
- Ağ: yalnız borsaistanbul.com'daki KURAL metinleri (seans saatleri, bülten yayım saati, fiyat marjı esasları). Fiyat ya da bülten verisi indirilmez.
- Git: yalnız okuma komutları ve her zaman `GIT_OPTIONAL_LOCKS=0` öneki. Sonda tek commit, yalnız kendi yollarınla.
- Yazma: YALNIZ `docs/specs_faz5/` (şartname ve `ekler/`) ve bu görev dosyası. Kod yok (profil betikleri `ekler/` altında olabilir), push/tag/amend yok.

## Bağlam
**Bugünkü modellerin bilgi sınırı.** 19 kayıtlı modelin hepsi yalnız LİSTELEME ÖNCESİ bilgiyle tahmin yapıyor: arz fiyatı, pay sayısı, sermaye, talep katı ve PB alanları. İlk işlem gününden sonra ürünün yaptığı tek şey koşullu güncelleme: seri j gün sürdüyse P(L ≥ k | L ≥ j) = S_k / S_j (SPEC_CEILING_PATH_V0 §7). Bu güncelleme ilk günün NASIL geçtiğini hiç kullanmıyor.

**Fikir: ilk gün sonrası güncelleme.** D1'in resmi THB/THM verisi D2 açılmadan önce bellidir. Mekanik olarak anlamlı olabilecek bilgiler:
- Gün boyu tavanda kilitli mi kaldı? (en düşük = üst limit; açılış = üst limit)
- Hacmin arz edilen paya oranı (el değiştirme)
- İşlem sayısı
- Ağırlıklı ortalama fiyatın limite uzaklığı

Kullanıcının asıl sorusu şu: "Bugün tavan gitti, yarın ve sonrası ne olur?"

**Veri [orkestratör ölçtü, yalnız sütun adları ve satır sayısı; hiçbir ilişkiye bakılmadı].** `data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv`:
- 990 satır = 99 arz × 10 seans.
- Sütunlar: `thb_raw_open/high/low/close/volume/turnover/aof/trade_count`, `thm_raw_reference_price/upper_limit/lower_limit`, düzeltilmiş karşılıkları, `row_status`, `security_trading_status`, kaynak URL + sha.
- Canlı taraf `data/outcomes/<T>.csv` bugün yalnız `close_raw, upper_limit_raw, reference_raw, trade_count_raw, halt_flag…` taşıyor; açılış, en düşük, hacim, AOF yok (`borsai/outcomes.py` `THB_COLUMNS`).
- Repo, `docs/` ve `experiments/log.jsonl` (64 satır: 58 backtest, 5 sensitivity, 1 conditional_eval) taramasında D1 işlem verisini özellik olarak kullanan bir model bulunamadı. Arşivi sen tara.

**Bu görevin amacı.** "İlk gün sonrası" model hattının şartnamesini yazmak: `docs/specs_faz5/SPEC_POST_D1_V0.md`. Yol her zamanki gibi: şartname (sen, sonuç görmeden) → Opus uygulama ve backtest → Fable sıfırdan yeniden üretim → dondurma.

**Asıl karşılaştırıcı, bugün üründe olan koşullu güncellemedir.** Yeni model basit kuralları geçse bile, dondurulmuş `ceiling_hazard_v0`'ın j = 1 koşullu S'sini geçmiyorsa ürüne bir şey katmaz. Birincil hücre buna karşı tanımlanmalı.

### Paralel oturum
Opus, `docs/prompts/FAZ2C_CONDITIONAL_SCORING.md` görevini koşuyor; `borsai/`, `tests/`, `scores/`, `docs/SCORES.md`, `docs/SPEC_DEVIATIONS.md` altına yazıyor ve commit atıyor. Bunları okuyabilirsin, dokunma. `scores/` değişikliklerini şartnamenin girdisi olarak kullanma.

ÖNCE OKU:
- CLAUDE.md
- docs/specs/SPEC_SCORING.md (tamamı; özellikle §3 tavan etiketi, §5 sınıflar, §7–§8)
- docs/specs/SPEC_CEILING_V0.md (hazard yapısı, gün grupları, ızgara, ret)
- docs/specs_faz4/SPEC_CEILING_PATH_V0.md (kalıp: "önceden yazılmış beklenti", maruziyet, sözde kod; §7 koşullu güncelleme)
- docs/MODELS.md: `ceiling_hazard_v0` ve "Koşullu güncelleme (keşif): H99, j = 1..9" tabloları. Bunlar karşılaştırıcının bilinen başarımıdır, beklentiyi bunlardan türet.
- docs/DATA.md, docs/DATA_NOTES.md, docs/SPEC_DEVIATIONS.md
- borsai/outcomes.py, borsai/registry.py, borsai/freeze.py (canlı veri ve kayıt akışı), borsai/survival.py, borsai/predict_hazard.py
- Arşiv: `~/Desktop/Halka_Arz_Modeli` altında D1 işlem verisiyle ilgili eski tasarım ya da deney var mı (maruziyet için)

## Şartnamenin cevaplaması gerekenler
1. **Kapsam.** Hangi arzlar (öneri: D1 tavan kapatanlar, L ≥ 1; H99'da 81), hangi çıktılar. Öneri:
   - Birincil: S_k | L ≥ 1 ve D1 bilgisi, k = 2..10, ve "yarın bozulur mu" = 1 − S_2/S_1
   - İkincil: tavan-yolu eşlemesiyle D3/D5/D10 getiri ve p_up (Faz 4 gibi yeni serbest parametresiz eşleme)
   - D1 tavan kapatmayan arzlar v0'da kapsam dışı mı?
2. **Özellikler (≤ 2, sonuç görmeden, mekanizmayla gerekçeli).** Tanım, THB/THM alanı, birim, dönüşüm, eksik/işlemsiz/durdurma hâlleri.
   - Özellik–sonuç ilişkisine BAKMA. Yalnız özelliklerin kendi dağılımı (tek değişkenli profil, `ekler/`) serbest.
   - `low == upper_limit` gibi eşitliklerde tick/yuvarlama kuralı (`thb_raw` mı düzeltilmiş mi).
3. **Model sınıfı ve parametre bütçesi.** Varsayılan: dondurulmuş `ceiling_hazard_v0` üstüne, D1 özelliklerinin j ≥ 2 hazard'ına eklenmesi; ızgara/λ iç CV ile, SPEC_CEILING_V0 kalıbında. Yeni serbest parametre bütçesi (öneri ≤ 2) ve neden. Sıfır/kovaryatsız eşdeğer model (`@INF` benzeri) zorunlu mu?
4. **Karşılaştırmalar ve birincil hücre.**
   - Birincil: koşullu RPS_1 (k = 2..10), yeni model − `ceiling_hazard_v0` koşullu (S_k/S_1), aynı arzlar.
   - Kurallar: koşullu KM (iki kural), koşullu `@INF`, her-zaman-tavan.
   - İkincil: koşullu Brier (k = 2, k = 10).
5. **Önceden yazılmış beklenti** (SPEC_CEILING_PATH_V0 §6 kalıbı): her hücre için beklenen fark aralığı ve "aralık 0'ı dışlar mı". Sayılar MODELS.md'deki karşılaştırıcı başarımından ve mekanikten türetilir. Hiçbir yeni skor hesaplanmaz.
6. **Backtest planı.** Walk-forward (Faz 1B fold planı, seans tarihi < T), eğitim yalnız L ≥ 1 arzlar, sızıntı noktaları: D1 özelliği yalnız D1'den; ön işleme fold içinde; KM ve karşılaştırıcılar aynı eğitim kümesinden. SPEC_DEVIATIONS C7 aralıkları.
7. **Canlı kayıt ve zaman kanıtı (yeni aşama).** Bugünkü sicil yalnız listeleme öncesi kaydı LIVE sayıyor (SPEC_SCORING §5); D1 sonrası kayıt o kurala göre LATE olur. Tanımla:
   - Kayıt aşaması (ör. `POST_D1`): girdi = resmi D1 bülteninin kendisi (dosya, sha256, yayım zamanı). Kayıt dosya adı ve şeması; aynı arza PB ve talep katlı kayıtlarla birlikte var olma.
   - Zaman kanıtı: push, D2 açılış seansından ÖNCE. Seans ve bülten yayım saatlerini kural metninden al; alamazsan [ÇIKARIM] diye işaretle ve açık soruya yaz.
   - Sınıf hesabı (`POST_D1` kaydı için LIVE/LATE/RETRO), yalnız h ≥ 2 hedefler; D1 hedefi bu modellerde skorlanmaz.
   - SPEC_SCORING'e ek; `docs/specs/` değişmez, ek bu dizinde durur.
   - `borsai/outcomes.py` ve `registry`'de gerekecek alanlar (açılış, en düşük, hacim, AOF…) ve kaynakları.
8. **Uygulama etkisi (kısa).** Yeni tür çıktı mı, var olan S/koşullu görünümü mü? EK 3 gerekecek mi? Yalnız ana hatlar.
9. **Ret ve uyarılar.** D1 durdurma/yarım gün/işlem yok; f3 yokken davranış (ana model mirası).
10. **Maruziyet.** H99'da bu arzlar üzerinde denenmiş varyant sayısı (`experiments/log.jsonl`), D1 alanlarının önceki kullanımı (arşiv), bu şartnamenin kendi maruziyeti (profiller).
11. **Kabul testleri** (Opus için, kanıtlanabilir) ve **sözde kod**.
12. **Açık sorular** (proje sahibine, en çok 5).

Şartname kendi içinde karar verir; "Opus seçsin" bırakılmaz.

## Adımlar
0. Taban:
   - `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -3`, `git status --porcelain`
   - İzinli izlenmeyen/değişen: `docs/prompts/FAZ5_FABLE_POST_D1_SPEC.md`, `docs/prompts/FAZ2C_CONDITIONAL_SCORING.md` ve paralel oturumun yolları. Başka bir şey varsa DUR.
1. Okuma ve arşiv taraması.
2. Tek değişkenli özellik profili (`ekler/profil_*.txt`, betik `ekler/`): 99 arzın D1 alanları, sonuç sütunlarıyla BİRLEŞTİRMEDEN. Tek istisna: L ≥ 1 alt kümesini seçmek için `ceiling_close_D1` kullanılabilir.
3. Şartname.
4. Commit.

## Kurallar
- `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `tests/`, `app/`, `docs/specs/`, `docs/specs_faz4/`, `docs/app/` salt okunur.
- Hiçbir model fit edilmez, hiçbir walk-forward skoru hesaplanmaz, özellik–sonuç ilişkisine bakılmaz. Bunu şartnamenin başında beyan et.
- `docs/specs_faz5/` altına en çok ~1 MB.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma (`tests/test_outcome_guard.py` bütün repoyu tarar; bülten dosya adlarını `th?YYYYMMDD` diye yaz).
- `git add -A` yok. Commit:
  ```
  git add docs/specs_faz5 docs/prompts/FAZ5_FABLE_POST_D1_SPEC.md
  git commit -m "BORSAI_FAZ5_SPEC: post-D1 update model spec with pre-registered expectations, before implementation" -- docs/specs_faz5 docs/prompts/FAZ5_FABLE_POST_D1_SPEC.md
  ```
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Rapor Türkçe.

## Teslim (rapor)
- Commit hash'i.
- 10 satırlık özet: kapsam, özellikler, model sınıfı, parametre bütçesi, birincil hücre ve beklentisi, canlı kayıt aşaması.
- Arşiv taraması sonucu (önceki kullanım var mı).
- Açık sorular.

## Kabul kapısı
- K1 Şartname 1–12 maddenin hepsini cevaplıyor; hiçbir karar Opus'a bırakılmamış.
- K2 Birincil hücre, bugünkü koşullu güncellemeye (`ceiling_hazard_v0` S_k/S_1) karşı; beklenti sayısal ve aralıklı.
- K3 Özellik–sonuç ilişkisine bakılmadığı beyan edilmiş; profiller tek değişkenli.
- K4 Canlı `POST_D1` kaydının zaman kanıtı ve sınıf kuralı tanımlı.
- K5 Commit yalnız `docs/specs_faz5/` ve bu görev dosyası.

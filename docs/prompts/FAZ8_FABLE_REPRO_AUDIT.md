# TASK_ID: BORSAI_FAZ8_FABLE_REPRO_AUDIT_20261002

Model: Fable · yüksek. Klasör: ~/Desktop/BorsAi. Ağ yok.
- **Git:** yalnız okuma komutları ve her zaman `GIT_OPTIONAL_LOCKS=0` öneki. Sonda tek commit, yalnız kendi yollarınla. push/tag/amend yok.
- **Yazma:** YALNIZ `docs/fable_faz8_audit/` (`AUDIT.md` ve `ekler/`) ve bu görev dosyası.
  - Geçici işler `/tmp/borsai_faz8_audit/` altında yapılır ve sonda silinir.
  - `ekler/` en çok 3 MB.
- **Paralel oturum:** yok.
- **Koruma:** koşu öncesi ve sonrası `registry/`, `data/`, `scores/`, `models/` ve `app/` ağaç sha'ları ile `git status --porcelain` ölçülür; ikisi eşit olmalı.

## Neden bu denetim
`break_floor_v0`'ın birincil hücresi şartnamenin "beklentiden çok iyi" eşiğini tetikledi (SPEC_BREAK_V0 §6). Şartname gereği **dondurmadan önce senin bağımsız, sıfırdan yeniden üretimin** ledger'larla |Δ| ≤ 1e-9 eşleşmeli. Bu denetim dondurmanın kapısıdır.

## Bağlam
- **Şartnamen:** `docs/specs_faz8/SPEC_BREAK_V0.md` + `KARARLAR.md` (`7d78d43`, push'lu).
- **Proje sahibi kararları:** KARARLAR §C (C1–C5) ve orkestratör maruziyet notu; commit K `5d84e88`.
- **Uygulama Opus'a ait** (görev `docs/prompts/FAZ8_BREAK_IMPL.md`, rapor `docs/faz8/IMPL_RAPOR.md`):
  - K `5d84e88`: kararlar, CLAUDE.md kural 1 eki, bant doğrulaması (`docs/faz8/BANT_DOGRULAMA.md`).
  - A `fa623df`: kod ve kurallar, sonuçtan önce.
    - Proje sahibinin üç test kararı (SPEC_DEVIATIONS N19):
      - kasa testi `git_head` kalıbı;
      - `report.py` kancası ve 7 testte sınırlı sayaç istisnası;
      - §7.2 formülü aynen.
    - K ve A, B'den önce push edildi (push kanıtı dosyası yok; sıra git DAG'ından).
  - B `df338c2`: resmi walk-forward, `docs/faz8/backtest/` (ledger'lar, önizlemeler, MANIFEST), günlük (1 backtest + 3 duyarlılık), MODELS.md Faz 8 bölümü, SPEC_DEVIATIONS N20.
  - R `c84ba64`: rapor.
- **Opus'un sonuçları** (H99 backtest'i, tasarıma maruz; yakın dönem = ilk işlem ≥ 2024-01-01; 82 kırılma akşamı, 69 FIT_OK, 13 `INSUFFICIENT_TRAINING_HISTORY`):

  | Hücre (F1 Brier) | Fark | %95 aralık | n (ay) |
  |---|---|---|---|
  | model − `PRODUCT_BREAK_FLOOR` (birincil) | −0.1904 | [−0.2520, −0.1247] | 69 (21) |
  | model − `@ZERO` | −0.0281 | [−0.0453, −0.0074] | 69 (21) |

  §6'nın 13 satırından 9'u tuttu.
- **Orkestratör kontrolü** (Opus'un ledger'ından; bağımsız yeniden üretimin yerini **TUTMAZ**):
  - İki fark ve aralık C7 bootstrap'iyle aynı çıktı. Model Brier 0.1878, ürün 0.3781, `@ZERO` 0.2158.
  - Taban kırılmaları 28 akşam, 15 olay: model ort. p 0.45, ürün 0.115.
  - Taban üstü kırılmalar 41 akşam, 5 olay: model 0.251, ürün 0.568.
- **N20 (Opus'un bulgusu):**
  - Taban kırılmalarında ürünün "çift tabana yakın" atom payı ort. 0.273.
  - §5.1'in kesin eşiği (iki alt limit adımı, 1e-12 tolerans) adım yuvarlaması yüzünden bunun yalnız 0.115'ini sayıyor.
  - Kod şartnameyi aynen uyguluyor.
  - Orkestratörün kaba tahmini: eşik bir adım toleranslı olsaydı ürün Brier'i ~0.335'e iner, birincil fark ~−0.15 olurdu. Bu tahmin doğrulanmalı.
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** Birincil hücrenin tanımı sonuç görüldükten sonra değiştirilmez.
- **Hijyen:**
  - eski kohort, kasa ve OOT dosyaları açılmaz;
  - `data/outcomes/` (canlı) bu modelin backtest'inde okunmamalı (denetle);
  - metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yok.

## ÖNCE OKU
- CLAUDE.md (kural 1'in yeni POST_BREAK cümlesi dahil)
- `docs/specs_faz8/SPEC_BREAK_V0.md` (tamamı), `KARARLAR.md`, `ekler/profil_kirilma.txt`
- `docs/specs_faz4/SPEC_CEILING_PATH_V0.md` §3, §4, §7 (ürün karşılaştırıcısının kaynağı)
- `docs/specs/SPEC_V1_6.md` (Logit yolu), `docs/specs/SPEC_SCORING.md` §2, §3, §7, §8
- `docs/SPEC_DEVIATIONS.md` N1–N20
- `docs/faz8/IMPL_RAPOR.md`, `docs/faz8/BANT_DOGRULAMA.md`, `docs/MODELS.md` "Faz 8" bölümü
- Kendi önceki betiklerin (kalıp; Opus'un kodu değil): `docs/fable_faz4_audit/ekler/` (özellikle `repro_ceiling_path.py`; ürün karşılaştırıcısı için), `docs/fable_faz7c_audit/ekler/`
- Denetlenecek kod (yeniden üretimde KULLANILMAZ):
  - `borsai/post_break.py`, `predict_break.py`, `report_faz8.py`;
  - `specs.py` (Faz 8 ekleri), `report.py` (kanca);
  - `tests/test_faz8_*.py`, `tests/faz8_support.py` ve A/B'de değişen var olan testler.

## Adım 0
- `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -6`: HEAD `c84ba64` ya da torunu.
- `GIT_OPTIONAL_LOCKS=0 git status --porcelain --untracked-files=all`: yalnız bu görev dosyası. Başka bir şey varsa DUR.
- Koruma ölçümü → `ekler/koruma_once.txt`.

## Adımlar

**1. Sıfırdan yeniden üretim** (`ekler/repro_break.py`)
- **Kurallar:** `borsai` import edilmez. Kanıt: import satırı yok ve alt süreçte `sys.modules` denetimi.
- **Çözücü:** scikit-learn L2 `LogisticRegression` doğrudan çağrılır. Hiperparametreler şartname ve SPEC_V1_6'dan alınır. Birkaç fold'da kendi Newton çözümünle |Δp| ≤ 1e-6 göster.
- **1a · Kırılma tablosu** (§13-1): 82 akşam; b dağılımı 18/11/4/13/12/8/6/6/4; `b_floor` 35; L = 10: 14; b = 10: 3; yapısal sıfır 16 (b = 7: 6, 8: 6, 9: 4). Etiketler `Decimal(kapanış) == Decimal(alt limit)`.
- **1b · Özellikler:** `b_floor`, `b_turnover` = ln(hacim_b / shares_offered); fold içi p05/p95 kırpma (Type-7, ln ölçeğinde) ve z (ddof = 0).
- **1c · Fold planı** (§7.2):
  - Kesim T = D_b tarihi. F1 eğitim satırı `date(D_{b+1}) < T`, F2 `date(D_{b+2}) < T`.
  - En az 10 satır / 5 olay / 5 olay-dışı.
  - Beklenen: 82 fold; 69 FIT_OK; F2 fold'ları b ≤ 8.
  - Aynı gün kuralı N19'daki yoruma göre (formül aynen).
- **1d · Ledger:** `docs/faz8/backtest/break_floor_v0_fold_ledger.csv` ile karşılaştır.
  - Durum, seçilen C, sınıf sayıları, `training_*` ve kimlik sha'ları birebir.
  - p_F1, p_F2, katsayılar, sabitler, ön işleme |Δ| ≤ 1e-9.
  - `zero_F1/F2` Fraction ile bit-eşit.
  - `by_type_F1` birebir.
- **1e · Ürün karşılaştırıcısı (`PRODUCT_BREAK_FLOOR`), bağımsız:** `ceiling_path_v0` durum-2 karışımını SPEC_CEILING_PATH_V0'dan kendin kur (Faz 4 denetimindeki kendi betiklerin kalıp olabilir).
  - Hücreler kesim D_1(k) ile; limit yolu fiyat adımı tablosuyla; eşik §5.1 aynen.
  - `product_F1/F2` |Δ| ≤ 1e-9; `cells_max_session_date < D_1(k)`.
  - Faz 4 ledger'ıyla kesişen 87 fold'da hücre sayıları birebir.
- **1f · Hücreler:** MODELS.md Faz 8 bölümünün bütün hücreleri (F1 ve F2; ürün, `@ZERO`, `base_floor_by_type`; yakın dönem ve 2023 ayrımı).
  - Fark, %95 aralık (C7: ay blokları, 4000 tekrar, `random.Random(20260921)`, indeks 100/3899), n, blok, kazanç/kayıp/eşit |Δ| ≤ 1e-9.
  - §6 satırlarının tuttu/tutmadı değerlendirmesi ve "çok iyi" tetikleri.
- **1g · Nihai fit önizlemeleri** (`docs/faz8/backtest/*_final_fit_preview.json`): C birebir; katsayılar ve ön işleme |Δ| ≤ 1e-9.
- **1h · Duyarlılıklar:** üç duyarlılık ledger'ı aynı kurallarla.

Tutmayan her şeyin kök nedenini ölç: senin kodun mu, Opus'unki mi, şartname belirsizliği mi. Tahmin etme.

**2. N20 ve birincil hükmün sağlamlığı** (bilgi; birincil tanım değişmez)
- **(a)** Kodun §5.1 eşiğini aynen uyguladığını doğrula. Ürünün taban kırılmalarındaki eşik-altı payının yuvarlama yüzünden düştüğünü atom düzeyinde 3 örnekle göster.
- **(b)** Duyarlılık: eşik bir fiyat adımı toleranslı, yani "Lo(Lo(cb)) ya da bir adım üstü". Ürün Brier'i ve model − ürün farkı aralığıyla hesaplanır. Ayrıca "ürünün türetilmiş cevabı" için başka makul bir tanım varsa onu da hesapla.
- **(c)** Hüküm: birincil "aralık 0'ın altında" sonucu bu tanımlara karşı sağlam mı? "Çok iyi" tetiği tanım artefaktından mı geliyor?
- **(d)** Öneri: kartta ürün satırı nasıl gösterilmeli; `@ZERO` hücresi tek başına k1'i taşıyor mu?

**3. Sızıntı, sıra ve uygunluk** (her madde komut ve çıktıyla)
- **(i) Test arzı:** test arzının alanları hiçbir fold'da ön işlemeye ya da eğitime girmiyor. 3 fold'da test arzını değiştirip fit'in bit-eşit kaldığını göster.
- **(ii) Kesimler:** her eğitim satırında etiket tarihi < T; her fold'da hücre `max_session_date < D_1(k)`.
- **(iii) Yükleyici beyaz listesi:** D_b sonrası satırlarda yalnız {ticker, session_number, target_session_date, thb_raw_close, thm_raw_lower_limit} okunuyor. Çalışma zamanı izi; canlı `data/outcomes/` ve `scores/` okunmuyor.
- **(iv) Sıra:**
  - `7d78d43` → `5d84e88` → `fa623df` → `df338c2` atalık zinciri;
  - A ağacında `docs/faz8/backtest/`, MODELS.md Faz 8 bölümü ve günlükte Faz 8 satırı yok;
  - `git diff 7d78d43 c84ba64 -- docs/specs_faz8/SPEC_BREAK_V0.md` boş;
  - KARARLAR yalnız §C'de ve yalnız K'de değişti;
  - §6 kuralları (`OPERATIONAL_RULES_FAZ8`) A'da sabit, B'de değişmedi;
  - `git diff fa623df df338c2 -- borsai` boş ya da yalnız raporlama. Değilse ayrıntı ve hüküm.
- **(v) CLAUDE.md eki:** §9.4 cümlesiyle birebir.
- **(vi) N1–N20:** her biri davranış değiştiriyor mu, lafza aykırı mı, kabul edilebilir mi. Özellikle N19'un üç test değişikliği:
  - hiçbir bekçi onaylanandan fazla gevşetildi mi;
  - kasa testinin mutasyon testi gerçekten yakalıyor mu;
  - sayaç istisnası tam Faz 8 varyant sayısıyla sınırlı mı ve `scores/` bayt-eşitken mi geçerli.
- **(vii) Kasa ve hijyen:** SEALED kod sayısı 0 (bellekte küme, yalnız sayı). Bakılacak yerler: `docs/faz8/`, `docs/specs_faz8/`, `docs/MODELS.md` Faz 8 bölümü, `experiments/log.jsonl` Faz 8 satırları, yeni testler.
- **Tam test:** `.venv/bin/pytest -q` ve `bash app/scripts/test.sh` → `ekler/test_out.txt`.

**4. Mutasyon denetimi**
- Klonda çalış (`git clone --local` → `/tmp/borsai_faz8_audit/clone`, `.venv` bağla).
- Her mutasyon ayrı uygulanır, ilgili test koşar, KIRMIZI olduğu gösterilir, geri alınır.
- Sürücü `ekler/mutate.sh`, çıktı `ekler/mutasyon_ciktilari.txt`.

En az şunlar:
- (a) `b_floor` float eşitliğiyle;
- (b) etiket "en düşük == alt limit" (dokunma) ile;
- (c) eğitim kesimi `<=`;
- (d) hücre kesimi D_1 yerine T;
- (e) beyaz liste dışı sütun okuma;
- (f) yapısal sıfırda 10 − b yerine 9 − b;
- (g) ürün eşiği bir adım kaydırılmış;
- (h) yakın dönem sınırı 2023-12-01;
- (i) `@ZERO` test satırını içerir;
- (j) el değiştirmede pay yerine sermaye;
- (k) kırpma sınırları test arzını içerir;
- (l) §6 "çok iyi" eşiği −0.16 yerine −0.20.

## Teslim
`docs/fable_faz8_audit/AUDIT.md`:
- Özet; ilk satır **`REPRO_OK`** ya da **`REPRO_FAIL`**.
- Bölümler:
  - yeniden üretim tabloları (her ledger sütunu için maks |Δ|);
  - hücreler;
  - N20 ve sağlamlık hükmü;
  - sızıntı ve sıra kanıtları;
  - N1–N20 değerlendirmesi;
  - mutasyonlar;
  - testler;
  - koruma.
- **Dondurma önerisi:** `break_floor_v0` ve `@ZERO` bu şartnameyle dondurulabilir mi? Dondurulursa kartın öne çıkan durumu (§8, k1) ve gösterilecek uyarılar.
- Açık sorular (proje sahibine, en çok 3).

Commit:
```
git add docs/fable_faz8_audit docs/prompts/FAZ8_FABLE_REPRO_AUDIT.md
git commit -m "BORSAI_FAZ8_FABLE_AUDIT: independent reproduction of break_floor_v0 backtest, N20 robustness, leakage/order checks, mutations" -- docs/fable_faz8_audit docs/prompts/FAZ8_FABLE_REPRO_AUDIT.md
```
`index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.

## Kabul kapısı
- **K1** Ledger, önizleme ve hücreler |Δ| ≤ 1e-9; uyuşmazlıkların kökü ölçülmüş.
- **K2** N20 sağlamlık hükmü sayılarla.
- **K3** Sızıntı ve sıra maddeleri komut çıktısıyla; mutasyonların hepsi kırmızı.
- **K4** Koruma eşit; commit yalnız izinli yollarda.

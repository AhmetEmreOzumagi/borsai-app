# TASK_ID: BORSAI_FAZ4_FABLE_REPRO_AUDIT_20260922

Model: Fable · yüksek. Klasör: ~/Desktop/BorsAi. Ağ gerekmez.
- Git: YALNIZ okuma komutları ve her zaman `GIT_OPTIONAL_LOCKS=0` öneki (`log`, `show`, `diff`, `status --porcelain`, `merge-base --is-ancestor`). Paralel bir oturum `app/` altına commit atıyor.
- Yazma: YALNIZ `docs/fable_faz4_audit/` altına. Commit, push, tag, amend yok.

## Bağlam
- Senin şartnamen `docs/specs_faz4/SPEC_CEILING_PATH_V0.md` commit 52e1567'de; push kanıtı `registry/push_proofs/52e1567….json`. Uygulaması Opus'a ait, commit 2d0c98e.
- Üç model uygulandı ve backtest edildi, ama DONDURULMADI. Nedeni: §6'daki "beklentiden çok iyi" denetimi 10 koşulda tetiklendi.
  - Birincil hücre, D5 MAE, `base_train_median`'a karşı: fark −0.1158 [−0.1611, −0.0738], n = 85.
  - Beklentin −0.090…−0.020 idi.
  - Ayrıntı `docs/MODELS.md`'nin "Faz 4" bölümünde.
- Proje kuralı: beklentiden çok iyi çıkan sonuç, dondurmadan önce farklı elle sıfırdan yeniden üretilir.
  - Yazan el Opus'tu, denetleyen el sensin.
  - Faz 1B'de `ceiling_hazard_v0` için aynı işi yaptın: `docs/fable_conformity_20260922/`.
- Orkestratör birincil hücreyi ledger'lardan yeniden hesapladı; nokta tahmini birebir tuttu. Bu, bağımsız yeniden üretimin yerini TUTMAZ.

ÖNCE OKU:
- CLAUDE.md
- docs/specs_faz4/SPEC_CEILING_PATH_V0.md ve `ekler/`
- docs/specs/SPEC_SCORING.md §7–§8
- docs/SPEC_DEVIATIONS.md: C7 ve "F. Faz 4" bölümü
- docs/MODELS.md Faz 4 bölümü
- docs/fable_conformity_20260922/AUDIT.md (1B denetimin, kalıp olarak)
- Denetlenecek kod (yeniden üretimde KULLANILMAZ): borsai/ceiling_path.py, predict_path.py, report_faz4.py, backtest.py (Faz 4 kısmı), tests/test_faz4_ceiling_path.py

## Adımlar

**1. Sıfırdan yeniden üretim**
- Betik: `docs/fable_faz4_audit/ekler/repro_ceiling_path.py`.
  - `borsai` paketini IMPORT ETMEZ; yalnız stdlib (gerekirse numpy).
  - Yalnız şartnameden kodlanır.
- Girdiler (yalnız H99, hepsi ≤ 2026-08-19):
  - `data/training_table.csv`
  - `data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv`
  - H99 takvimi
  - `data/raw/…PREBOOKBUILD…` (PB B(k) için)
- S_k: şartname gereği Faz 1B altın ledger'larından okunur: `tests/reference/macos_golden_faz1b/` altında `ceiling_hazard_v0`, `@INF` ve `pb_ceiling_v0`. `ceiling_hazard_v0` ledger'ını 1B'de sen bağımsız ürettin.
- Bağımsız hesaplanacaklar:
  - fiyat adımı ve limit yolu C_h
  - kırılma sonrası hücreler (Z/B, m)
  - havuzlama merdiveni, N_MIN
  - karışım: medyan, p_up, q10/q90, mean
  - fold başına walk-forward kesim
- Karşılaştırmalar:
  - (a) Üç modelin fold ledger'ları `tests/reference/macos_golden_faz4/` ile. Her h için return, p_up, q10, q90 ve mean: |Δ| ≤ 1e-9. `cells_n_*`, `C_h`, `rho_h` birebir.
  - (b) §6'daki 36 beklenti satırının hepsi: fark, %95 aralık (C7: `random.Random(20260921)`, 4000, aylık blok), n. MODELS.md ile karşılaştır: fark |Δ| ≤ 1e-9, aralık uçları ≤ 1e-9. Karşılaştırılan ledger'lar Faz 1A/1B altınları.
  - (c) Birincil hücre ve "çok iyi" denetiminin 10 koşulu.
- Tutmayan her şeyin kök nedenini bul: senin kodun mu, Opus'unki mi, şartname belirsizliği mi. Tahmin etme; ölç.

**2. Sızıntı ve uygunluk denetimi**
- Her fold'da hücrelerde yalnız seans tarihi < T olan gözlemler var; PB için < B(k). Test arzının kendi seansı hücrede yok.
- Faz 4 kodu `data/outcomes/`, `data/raw/bist/`, `scores/` ve 2026-08-19 sonrası hiçbir veriyi okumuyor: kod taraması ve çalışma zamanı kanıtı.
- Sıra:
  - 52e1567'nin push kanıtı `created_at`'i 2d0c98e'nin commit zamanından önce.
  - `git diff 52e1567 HEAD -- docs/specs_faz4` boş.
- S_k gerçekten yeniden fit edilmemiş: kaynak ledger ile bit-eşit.
- Kod ↔ şartname uygunluğu:
  - §2 limit yolu ve D1 HALF_UP (proje sahibi kararı)
  - §3 hücreler
  - §4 eşleme; medyan birincil nokta
  - §7 koşullu fonksiyonlar
  - §12 sözde kod
- `docs/SPEC_DEVIATIONS.md` F bölümündeki her sapma: davranış değiştiriyor mu?
- Testler: `.venv/bin/pytest -q` tam koşu; çıktı `ekler/pytest_out.txt`'ye.

**3. "Neden bu kadar iyi?" (tanı; model seçimine GİRMEZ)**
- D5 ve D10 kazancı nereden geliyor? En az şunları ölç:
  - S_5 < 0.5 ve S_5 ≥ 0.5 arzlarda ayrı katkı.
  - Kazancın yıllara göre dağılımı.
  - En çok katkı veren 10 arz.
  - `ceiling_path_v0@INF`'e karşı fark: özellik bilgisinin payı.
  - V1.5'e karşı D5 hata dağılımı.
- Mekanizmayı bir paragrafta açıkla. Senin §6 beklentin neden düşük kaldı? Faz 1B'deki tavan modelinde de beklenti düşük kalmıştı; ortak bir neden var mı?

**4. Duyarlılık (bilgi amaçlı)**
- Yalnız birincil hücre için şu varyantlar:
  - (i) N_MIN = 5
  - (ii) N_MIN = 20
  - (iii) Z/B ayrımı yok, tek grup
  - (iv) havuzlama yok; küçük hücre → ret yerine en yakın m
- Amaç: sonucun tasarıma maruz seçimlere (grup, N_MIN, havuzlama) ne kadar bağlı olduğunu görmek.
- Bu varyantlar model DEĞİLDİR. Dondurulacak model şartnamedeki v0'dır; sonucu ne olursa olsun şartname değişmez.
- Her koşuyu `docs/fable_faz4_audit/ekler/sensitivity_runs.jsonl`'a `experiments/log.jsonl` biçiminde yaz: model_id `…__sens_<ad>`, kind `sensitivity`. Dondurma görevi bunları deney günlüğüne ekleyecek.

**5. Hüküm:** `docs/fable_faz4_audit/AUDIT.md`
- Her model için `FREEZE_OK` ya da `FREEZE_BLOCKED` + neden.
- Yeniden üretim tablosu: her karşılaştırma için maks |Δ|.
- Sızıntı bulguları.
- Tanı paragrafı ve duyarlılık tablosu.
- Uygulama için bir cümle: bu backtest sonucu "tasarıma maruz" etiketiyle nasıl gösterilmeli.
- Engelleyici değil ama düzeltilmesi gereken bulgular: listele ve öneri yaz.

## Kurallar
- Mevcut hiçbir dosyayı değiştirme. `borsai/`, `tests/`, `models/`, `docs/specs*/`, `experiments/`, `registry/`, `data/`, `scores/` ve `app/` salt okunur.
- Yeniden üretim betiği `borsai`'yi import etmez (test: betikte `borsai` import satırı yok).
- `data/outcomes/`, `data/raw/bist/`, `scores/` ve `docs/SCORES.md` OKUNMAZ; bu denetime gerekmez.
- Metinde tarihli THB/THM dosya adı kalıbı (thb/thm + 8 hane tarih) yazma.
- Rapor Türkçe.

## Teslim (rapor)
- `docs/fable_faz4_audit/` dosyaları ve sha256'ları.
- Hükümler.
- Yeniden üretim maks |Δ| tablosu.
- Sızıntı bulguları.
- Tanı özeti (5 satır).
- Duyarlılık tablosu.
- Açık konular.

## Kabul kapısı
- K1 Üç ledger ve 36 satır bağımsız betikle |Δ| ≤ 1e-9 eşleşti; ya da eşleşmeyen her şeyin kök nedeni yazılı ve hüküm FREEZE_BLOCKED.
- K2 Sızıntı denetiminin her maddesi kanıtla (komut ve çıktı) yazılı.
- K3 Yalnız `docs/fable_faz4_audit/` altında yeni dosyalar var.

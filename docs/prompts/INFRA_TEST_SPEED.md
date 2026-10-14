# TASK_ID: BORSAI_INFRA_TEST_SPEED_20260929

Model: Sonnet 5 · yüksek. Klasör: ~/Desktop/BorsAi. **Ağ: yalnız PyPI** (`pypi.org`, `files.pythonhosted.org`), yalnız `pytest-xdist` ve zorunlu bağımlılıkları için. push/tag/amend yok.

## Rol
Tam `pytest` koşusu 20–30 dakika sürüyor ve her oturum bunu 3–5 kez koşuyor. Bu görev test paketini Mac'in çekirdeklerine paralel dağıtır (`pytest-xdist`).

**Kalite kuralı (proje sahibi): hız için hiçbir kontrol zayıflatılmaz.**
- Hiçbir test silinmez, atlanmaz, deselect edilmez, `skip`/`xfail` edilmez.
- Hiçbir `assert` satırı ve hiçbir test iddiası değişmez.
- Paralel koşu, sıralı koşuyla **aynı testleri aynı sonuçla** vermedikçe geçiş yapılmaz.

## Bağlam
- `pyproject.toml`: `[project.optional-dependencies] dev = ["pytest==9.1.1"]`; `[tool.pytest.ini_options]` `addopts = "-p no:cacheprovider"`. `requirements.lock` sürüm pinli düz liste (hash yok).
- Son tam koşular: 864 test geçti, sıralı süre 19–31 dk (`docs/faz7_vault/ekler/*test_runs.txt`).
- Bazı testler `git status` ile çalışma ağacının temizliğini denetler (temizlik bekçileri), bazıları geçici git depoları kurar, bazıları repo içindeki dosyaları okur. Paralelde çakışabilecek türler bunlardır.
- Uygulama testleri (`bash app/scripts/test.sh`: cargo, vitest) zaten paraleldir; bu görevin dışında.
- Uygulama hem macOS hem Windows için geliştiriliyor. Yeni kod ya da ayar platforma özel yol ya da komut içermez.

## Orkestratör kararları
- **K1: Varsayılan değişmez.** `addopts`'a `-n` eklenmez; düz `.venv/bin/pytest -q` bugünkü gibi sıralı koşar. Paralel koşu açık bayrakla çağrılır: `.venv/bin/pytest -q -n auto --dist loadgroup` (ya da ölçüme göre sabit bir `-n`).
- **K2: Kullanım kuralı** (sonraki görev dosyalarına orkestratör yazacak):
  - ara koşular paralel;
  - her görevin **son kabul koşusu sıralı** (bugünkü komut).
- **K3: Paralelde çakışan testler** yalnız şu yollarla düzeltilir:
  - (a) aynı gruba alma: `@pytest.mark.xdist_group(...)` + `--dist loadgroup`; aynı gruptaki testler tek işçide sırayla koşar;
  - (b) test altyapısında yalıtım: fixture, `tmp_path`, `conftest.py`. İddia değişmez.
  
  Hangisi seçilirse seçilsin `assert` satırlarına ve test mantığına dokunulmaz. Emin değilsen (a)'yı seç.
- **K4: Sayısal ortam değişmez.** BLAS/OpenMP iş parçacığı ortam değişkenlerine (`OMP_NUM_THREADS` vb.) dokunma; bit-eşit altın testleri etkileyebilir. Yalnız ölç ve raporla.

## İzinli izlenmeyen
Yalnız bu görev dosyası. Başka bir şey varsa DUR.

## ÖNCE OKU
CLAUDE.md; `pyproject.toml`; `requirements.lock`; `docs/ENV.md`; `tests/conftest.py`; `tests/test_guardrails.py`; `tests/test_outcome_guard.py` (baş kısmı).

## Adımlar
0. **Taban (sıralı).**
   - `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -1` ve `origin/main` aynı; `git status --porcelain` → yalnız bu görev dosyası.
   - Tam sıralı koşu, düğüm başına sonuçla: `.venv/bin/pytest -q -rA` (ya da `--junitxml` repo dışına, `/tmp`'ye). Süreyi yaz.
   - Düğüm kimliği → sonuç listesini `/tmp/borsai_speed/serial.txt`'ye kaydet. Beklenen: 864 geçti, 0 kırmızı.
1. **Kurulum.**
   - `.venv/bin/pip install pytest-xdist==<güncel kararlı sürüm>`.
   - Sürümü ve kurulan bağımlılıkları (ör. `execnet`) `requirements.lock`'a biçimine uygun ekle. `pyproject.toml` `dev` listesine `pytest-xdist==<sürüm>` ekle.
   - Bu dosyaların sha'sını pinleyen bir test varsa yalnız o pin satırı güncellenir; başka bir değişiklik gerekirse DUR.
2. **Paralel ölçüm.** `.venv/bin/pytest -q -rA -n auto --dist loadgroup` → düğüm başına sonuç listesi `/tmp/borsai_speed/par1.txt`.
   - `serial.txt` ile karşılaştır: aynı düğüm kümesi, her düğümde aynı sonuç, 0 kırmızı.
   - Fark varsa K3 ile düzelt ve bu adımı baştan koş.
3. **Kararlılık.** Paralel koşuyu toplam **3 kez** tekrarla (`par1`–`par3`). Üçü de sıralı listeyle birebir aynı olmalı. Tek bir düğüm bile bir koşuda farklıysa: o testi K3-(a) ile grupla ve 3 koşuyu yeniden yap.
4. **İşçi sayısı.** `-n auto` ile bir de `-n 4` ve `-n 6` sürelerini ölç (her biri bir kez; sonuçlar yine sıralıyla eşit olmalı). En hızlısını öner.
5. **Belge.** `docs/ENV.md`'ye kısa bir bölüm ekle:
   - paralel komut;
   - "ara koşular paralel, son kabul koşusu sıralı" kuralı (K2);
   - gruplanan testlerin listesi ve nedeni.
   
   CLAUDE.md'ye dokunma.
6. **Son kabul (sıralı).** Tam sıralı `.venv/bin/pytest -q` (864 geçti) + `bash app/scripts/test.sh` + `.venv/bin/python app/parity/gen_golden.py --check`.
7. **Commit C.** Ardından rapor `docs/infra/TEST_SPEED_RAPOR.md` (commit R). Rapor içeriği:
   - sıralı süre;
   - üç paralel süre;
   - `-n` karşılaştırması;
   - üç koşuda düğüm kümesi ve sonuç eşitliği (sayılar);
   - gruplanan ya da yalıtılan testler (ad, neden, hangi yol);
   - `assert` satırlarının değişmediğinin kanıtı (`git diff` üzerinde `assert` içeren eklenen/silinen satır sayısı: 0);
   - bağımlılık değişiklikleri.

## Beklenen sayılar
| Denetim | Beklenen |
|---|---|
| sıralı taban | 864 geçti, 0 kırmızı |
| paralel × 3 | her biri 864 geçti; düğüm kümesi ve sonuçlar sıralıyla birebir |
| `git diff` içinde değişen `assert` satırı | 0 |
| silinen/atlanan test | 0 |

Tutmazsa commit etme, DUR ve raporla.

## Kurallar
- **Yazılabilir:** `pyproject.toml` (yalnız `dev` listesi), `requirements.lock`, `tests/conftest.py`, `tests/` (yalnız `xdist_group` işaretleri ve fixture yalıtımı; iddia değişmez), `docs/ENV.md`, `docs/infra/`, bu görev dosyası.
- **Salt okunur:** `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `app/`, `docs/specs*`, `CLAUDE.md`, `legacy/`.
- Oturum içinde proje sahibine karar sorman gerekirse soruyu ve seçenekleri açıkça yaz. Proje sahibi orkestratöre danışarak cevaplayacak.
- `git add -A` yok. Commit'ler:
  ```
  git add pyproject.toml requirements.lock tests docs/ENV.md docs/prompts/INFRA_TEST_SPEED.md
  git commit -m "BORSAI_INFRA_TEST_SPEED: optional parallel pytest (pytest-xdist, loadgroup); serial default unchanged; no assertion changed" -- pyproject.toml requirements.lock tests docs/ENV.md docs/prompts/INFRA_TEST_SPEED.md
  git add docs/infra
  git commit -m "BORSAI_INFRA_TEST_SPEED_REPORT: serial vs parallel timings and outcome equality" -- docs/infra
  ```
  Değişmeyen bir yol pathspec'te hata verirse o yolu çıkar. `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Push yok. Rapor Türkçe.

## Kabul kapısı
- **K1** Üç paralel koşu sıralı koşuyla düğüm düğüm aynı; 0 kırmızı.
- **K2** Hiçbir test silinmedi, atlanmadı, gevşetilmedi; `assert` farkı 0.
- **K3** Varsayılan `pytest -q` hâlâ sıralı. Son sıralı kabul koşusu + test.sh + `gen_golden --check` yeşil.
- **K4** Commit'ler yalnız izinli yollarda; push yok.

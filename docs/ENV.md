# Ortam

## Python (Faz 0–3)

| Öğe | Değer |
|---|---|
| Yorumlayıcı | CPython 3.12.14, macOS arm64 (uv'nin yönettiği kurulum: `~/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none`, `~/.local/bin/python3.12` bağlantısıyla) |
| Sanal ortam | Repo içinde `.venv/` (git'e girmez) |
| Çalışma zamanı bağımlılıkları | numpy 2.5.2, scikit-learn 1.9.0, scipy 1.18.0, joblib 1.5.3, threadpoolctl 3.6.0, narwhals 2.26.0 (scikit-learn 1.9.0'ın zorunlu bağımlılığı) |
| Geliştirme bağımlılığı | pytest 9.1.1, pytest-xdist 3.8.0 (execnet 2.1.2) |
| Tanım | `pyproject.toml`: sürümler birebir sabit. `requirements.lock`: kurulumdan sonraki `pip freeze` çıktısı |
| Referans ortam | `~/.borsai-venvs/v1_5-model-macos`: aynı yorumlayıcı ve aynı altı çalışma zamanı paketi. Fark yalnız pytest, pytest-xdist ve bağımlılıkları (iniconfig, packaging, pluggy, Pygments, execnet) |

Kurulum. 2026-09-21'de bu makinede `uv` ikili dosyası yoktu. Bu yüzden `.venv`, aynı uv yorumlayıcısıyla stdlib `venv` ve pip kullanılarak kuruldu:

```bash
~/.local/bin/python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
```

uv varsa eşdeğeri:

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.lock
```

Testler: `.venv/bin/pytest -q`

### Testleri paralel koşmak (pytest-xdist)

Varsayılan değişmedi: `.venv/bin/pytest -q` sıralı koşar (`addopts`'ta `-n` yok). Paralel koşu açık bayrakla çağrılır:

```bash
.venv/bin/pytest -q -n 6 --dist loadgroup
```

Kural:
- ara koşular paralel;
- her görevin **son kabul koşusu sıralı** (`.venv/bin/pytest -q`).

Paralel koşu sıralıyla aynı testleri aynı sonuçla verir (864 test, düğüm düğüm eşit); hiçbir test silinmez, atlanmaz ya da gevşetilmez. `--dist loadgroup` zorunludur: gruplama işaretleri yalnız o kipte etkilidir. `-n` değeri makineye göre seçilir (bu Mac: M5, 4 hızlı + 6 verimli çekirdek, 16 GB). Ölçüm: `docs/infra/TEST_SPEED_RAPOR.md`.

Kazanç sınırlıdır (sıralı ≈ 15 dk, paralel ≈ 11 dk), çünkü backtest testleri kendi içinde zaten `default_workers()` = 9 süreçlik havuz açar. Havuzlar aynı anda koşarsa çekirdek ve bellek aşırı yüklenir: gruplamasız 10 işçide 37–44 dk. Bu yüzden aynı anda en çok bir havuz çalışır.

Gruplar (`tests/conftest.py`, `pytest_collection_modifyitems`; aynı gruptaki testler tek işçide, sıralı koşudaki sırayla koşar):

| Grup | Testler | Neden |
|---|---|---|
| `backtest_pool` (146 test) | `backtest_results` fixture'ını kullanan testler (`test_acceptance_backtest`, `test_ceiling`, `test_experiment_log`, `test_faz1b_backtest`, `test_faz4_ceiling_path`, `test_market20`, `test_pb`, `test_port_vs_legacy`, `test_v1_6` içinde) ve `POOL_MODULES`: `test_acceptance_backtest`, `test_faz5_golden`, `test_faz5_post_d1`, `test_faz7_golden`, `test_faz7c_golden`, `test_market20` | 9 süreçlik havuz açarlar; `backtest_results` bütün modellerin backtest'idir ve her işçide baştan kurulurdu |
| modül başına bir grup (43 grup) | her test modülünün kalan testleri | modül ve oturum kapsamlı pahalı fixture'lar işçi başına yeniden kurulmasın; modül fixture'ını değiştirip geri yükleyen testler aynı işçide sırayla koşsun |

Yeni bir test modülü havuz açıyorsa `POOL_MODULES`'e eklenir; eklenmezse yalnız paralel koşu yavaşlar, sonuç değişmez.

Yalıtım: `tests/faz6_support.py::init_repo` geçici git deposunda `gc.auto=0` ve `maintenance.auto=false` ayarlar. Modül fixture'ı depoyu `shutil.copytree` ile klonlarken arka plan bakımı (repack) nesneleri taşıyabiliyordu (`No such file or directory`); bu, aynı testte sıralı koşuda da ≈ %8 oranında görüldü.

Düğüm kimliği: `-rA` çıktısında paralel koşuda kimliğe `@grup` eki eklenir (xdist yapar); sıralı koşuda yoktur. Sonuçları sıralıyla karşılaştırırken ek atılır.

BLAS/OpenMP iş parçacığı ortam değişkenlerine (`OMP_NUM_THREADS` vb.) dokunulmadı; bit-eşit altın testleri etkilenmesin.

### Sayısal tekrar üretilebilirlik notu

Eski V1.5 çekirdeği (`legacy/scripts/modeling/candidate_models.py`, `verify_runtime`) Python 3.12 ve yukarıdaki beş paketin tam sürümlerini ister.

H99 V1.5 benchmark'ı Windows'ta, Python 3.12.13 ile üretildi. macOS'ta yeniden koşunca:
- Ridge tahminleri en çok 2.7e-15, Logit olasılıkları en çok 3.1e-9 farklı çıkıyor.
- `D3|BETAE` fold'u macOS'ta yakınsamıyor.

Kaynaklar:
- `tests/reference/q3a_macos_yeniden_kosu_cikti.json`
- `tests/reference/v1_5_macos_runtime_replay_20260911/REPLAY_REPORT.md`
- AUDIT §1.2-b ve §3a

Bu yüzden Faz 1 kabul testi toleranslı ve fold düzeyli olmalı; "birebir" olamaz.

## Faz 4 için gerekecek araçlar (henüz KURULMADI)

Masaüstü uygulaması Tauri ile kurulacaksa şu araçlar gerekir:

| Araç | Neden | 2026-09-21 durumu |
|---|---|---|
| Rust araç zinciri (`rustup`, kararlı `rustc` ve `cargo`) | Tauri arka ucu. predict'in tek uygulaması burada yazılıp `cargo test` ile sınanacak (AUDIT §3e) | Yok |
| Node.js LTS ve npm | Tauri ön ucu ve `@tauri-apps/cli` | Yok |
| Xcode Command Line Tools | macOS derleyicisi, bağlayıcı ve SDK | Kurulu (`/Library/Developer/CommandLineTools`) |
| Tauri CLI (`npm i -D @tauri-apps/cli` ya da `cargo install tauri-cli`) | Proje iskeleti ve derleme | Yok |

Uygulama başkalarına dağıtılacaksa ayrıca Apple Developer imzası ve notarization gerekir. Önce BIST verisinin lisans sorusu cevaplanmalı (AUDIT §2.10). Kişisel kullanımda bu adım ertelenebilir.

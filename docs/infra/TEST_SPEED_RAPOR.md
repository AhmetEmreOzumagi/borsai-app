# Test hızı raporu: paralel pytest (pytest-xdist)

TASK_ID: BORSAI_INFRA_TEST_SPEED_20260929 · Tarih: 2026-09-30 · Commit C: `f23df7a` · Push yok.

## Sonuç (özet)

- Paralel koşu sıralıyla **düğüm düğüm aynı** sonucu veriyor: 864 test, her koşuda 864 geçti, fark 0 (aşağıda sayılar).
- **Kazanç sınırlı:** en hızlı ayar `-n 6 --dist loadgroup` ≈ 10:55 (655 s); sıralı ≈ 15:09–16:57 (909–1017 s). Oran ≈ 1,4–1,55×. Görevin başındaki "20–30 dakika" beklentisi bu makinede karşılanmıyor (sıralı koşu 15–17 dk).
- Neden küçük: backtest testleri kendi içinde zaten `default_workers()` = 9 süreçlik havuz açıyor, yani sıralı koşu ağır kısımlarda bütün çekirdekleri kullanıyor. xdist yalnız tek süreçli testleri havuzla üst üste bindirebiliyor.
- Havuzlar gruplamadan üst üste binerse paralel koşu sıralıdan **çok daha yavaş**: 10 işçide 37–44 dk. Bu yüzden gruplama zorunlu (aşağıda).
- Bir paralel-yük kararsızlığı bulundu ve düzeltildi (vault testi, sıralıda da ≈ %8 oranında kırılıyordu).
- Varsayılan `.venv/bin/pytest -q` hâlâ sıralı. Son sıralı kabul koşusu, `app/scripts/test.sh` ve `gen_golden --check` yeşil.

Öneri: ara koşularda `.venv/bin/pytest -q -n 6 --dist loadgroup`; son kabul koşusu sıralı `.venv/bin/pytest -q` (K2, `docs/ENV.md`).

## Ortam

Apple M5 (4 hızlı + 6 verimli çekirdek, `hw.ncpu` = 10), 16 GB, fansız MacBook Air; CPython 3.12.14. numpy Accelerate kullanıyor. Ölçüm sırasında pil durumu değişti (%66 pilde → sonra şarjda), bu yüzden süreler ±%5–10 oynayabilir (aşağıda kanıt).

## Süreler

pytest'in kendi bildirdiği süreler (saniye).

### Sıralı

| Koşu | Süre |
|---|---|
| Adım 0 taban (`pytest -q -rA`) | 909,0 s (15:09), 864 geçti |
| Havuz ölçüm eklentisiyle (aynı testler) | 920,6 s (15:20), 864 geçti |
| Adım 6 son kabul (`pytest -q`) | 1016,8 s (16:57), 864 geçti |

Üç sıralı koşu arasında %12 fark var: bu, hız karşılaştırmalarının belirsizlik payıdır.

### Paralel, nihai kodla (`--dist loadgroup`, gruplama açık)

| Koşu | `-n` | Süre | Sonuç |
|---|---|---|---|
| par1 | 3 | 687,6 s (11:27) | 864 geçti |
| par2 | 3 | 700,1 s (11:40) | 864 geçti |
| par3 | 3 | 709,8 s (11:49) | 864 geçti |
| n4 | 4 | 672,1 s (11:12) | 864 geçti |
| n6 | 6 | **655,4 s (10:55)** | 864 geçti |
| nauto | auto (= 10) | 661,7 s (11:01) | 864 geçti |

`-n 3`'ün üç koşusu arasında 22 s (%3) fark var. `-n 3`, 4, 6 ve auto arasındaki fark bu gürültünün biraz üstünde; en hızlısı `-n 6`, ama ayarlar birbirine yakın. `-n auto` aynı sonucu verir. Bellek kaygısı için `-n 6` daha düşük tavandır.

### Keşif koşuları (nihai kod öncesi; karşılaştırma için)

| Koşu | Süre | Not |
|---|---|---|
| `-n auto`, gruplama yok | 2668 s (44:28) | 864 geçti; sıralıdan 3× yavaş |
| `-n auto`, "gruplama" (etkisiz kanca) | 2240 s (37:19) | kanca çok geç çalışıyordu (aşağıya bak); fiilen gruplamasız |
| `-n auto`, aynı etkisiz kanca | 2591 s (43:11) | aynı |
| `-n auto`, gruplama etkili | 982 s (16:22) | ilk etkili koşu; pilde |
| `-n 2` | 807 s | gruplama etkili; havuz dışı ≈ 514 s'lik iş tek işçide |
| `-n 3` | 680 s | |
| `-n 4` | 687 s | **1 kırmızı** (vault testi, aşağıya bak), 863 geçti |
| `-n 6` | 696 s | |

Zaman çizelgeli tanı koşusu (`-n 3`, 698 s): havuz grubu ilk testini 226 s'de bitirip (fixture; sıralıda ≈ 100 s) 624 s'de bitti (sıralıda toplam ≈ 403 s), vault grubu 266 s'de başlayıp 698 s'de bitti (sıralıda ≈ 204 s). Yük ortalaması ilk 4 dakikada 43–50; takas kullanımı sabit (2483 MB), bellek dönmesi yok. Yani havuzla yan işçiler hızlı çekirdekler için yarışıyor.

## Düğüm kümesi ve sonuç eşitliği

Sıralı liste: `/tmp/borsai_speed/serial.txt` (düğüm kimliği → sonuç). Paralel çıktıdaki xdist `@grup` eki atılarak karşılaştırıldı.

| Koşu | Düğüm | Geçti | Sıralıda olup eksik | Fazla | Sonucu farklı |
|---|---|---|---|---|---|
| sıralı (taban) | 864 | 864 | – | – | – |
| par1 (`-n 3`) | 864 | 864 | 0 | 0 | 0 |
| par2 (`-n 3`) | 864 | 864 | 0 | 0 | 0 |
| par3 (`-n 3`) | 864 | 864 | 0 | 0 | 0 |
| n4 | 864 | 864 | 0 | 0 | 0 |
| n6 | 864 | 864 | 0 | 0 | 0 |
| nauto | 864 | 864 | 0 | 0 | 0 |

(Ek olarak gruplamasız koşu ve ikinci sıralı koşu da aynı: 864/864/0/0/0.) Sıralı toplama kimlikleri (`pytest --collect-only`) değişiklikten önce ve sonra aynı.

## Gruplanan ya da yalıtılan testler

Yol K3-(a) (`xdist_group` + `--dist loadgroup`), kanca `tests/conftest.py` içinde tek yerde; K3-(b) yalıtım `tests/faz6_support.py` içinde. Hiçbir `assert` satırına ve test mantığına dokunulmadı.

| Ad | Neden | Yol |
|---|---|---|
| `backtest_pool`: 146 test = `backtest_results` fixture'ını kullananlar + `POOL_MODULES` (`test_acceptance_backtest` 16, `test_ceiling` 7, `test_experiment_log` 1, `test_faz1b_backtest` 19, `test_faz4_ceiling_path` 1, `test_faz5_golden` 8, `test_faz5_post_d1` 32, `test_faz7_golden` 18, `test_faz7c_golden` 15, `test_market20` 12, `test_pb` 2, `test_port_vs_legacy` 12, `test_v1_6` 3) | 9 süreçlik havuz açarlar; aynı anda birden çok havuz koşarsa çekirdek/bellek aşırı yüklenir (44 dk). `backtest_results` (27 modelin backtest'i) her işçide baştan kurulurdu | (a) |
| Modül başına grup: kalan 43 grup (718 test) | oturum/modül kapsamlı pahalı fixture'lar işçi başına tekrar kurulmasın; modül fixture'ını değiştirip geri yükleyen testler tek işçide sırayla koşsun | (a) |
| `faz6_support.init_repo`: `gc.auto=0`, `maintenance.auto=false` | `test_faz7_vault::test_vault_gate_requires_four_committed_unchanged_pushed_documents_and_download_gate` (ve aynı yolla klonlayan `test_faz7_oot`) modül fixture'ı depoyu `shutil.copytree` ile kopyalarken arka plan bakımı (repack) nesneleri taşıyıp `No such file or directory` üretiyordu. Kırık koşularda depoda 3 paket + `multi-pack-index` vardı. Tek başına sıralı koşuda 26 denemede 2 kez kırıldı; düzeltmeden sonra 40 denemede 0 kırılma, 0 paket | (b) |

`POOL_MODULES` listesi ölçümle belirlendi: sıralı koşuda `ProcessPoolExecutor` açılışları test kimliğiyle kaydedildi (repo dışı eklenti). Yeni bir modül havuz açarsa listeye eklenmezse yalnız paralel koşu yavaşlar, sonuç değişmez.

## `assert` farkı ve silinen/atlanan test

Kanıt (commit C, `pyproject.toml`, `requirements.lock`, `tests/`):

```
git show HEAD --format= -U0 -- pyproject.toml requirements.lock tests | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' | grep -c assert   -> 0
git show HEAD --format= -U0 -- pyproject.toml requirements.lock tests | grep -E '^[+-]' | grep -ciE 'skip|xfail|deselect'          -> 0
git show HEAD --numstat --format= -- pyproject.toml requirements.lock tests   -> silinen satır: 0 (yalnız ekleme: 1 + 2 + 31 + 4)
```

- Değişen `assert` satırı: **0**. Silinen, atlanan, `xfail`/`skip`/deselect edilen test: **0** (864 test, aynı kimlikler).
- `pyproject.toml`: yalnız `dev` listesine `pytest-xdist==3.8.0`; `addopts` değişmedi.

## Bağımlılık değişiklikleri

| Paket | Sürüm | Not |
|---|---|---|
| pytest-xdist | 3.8.0 | PyPI'deki güncel kararlı sürüm (`pip index versions`) |
| execnet | 2.1.2 | pytest-xdist'in zorunlu bağımlılığı |

`requirements.lock` = kurulumdan sonraki `pip freeze` (iki satır eklendi, başka satır değişmedi). Ağ yalnız PyPI'ye gitti. Bu dosyaların sha'sını pinleyen test yok; pin güncellemesi gerekmedi.

## Süreçte yapılan hatalar (kayıt için)

- İlk gruplama kancası xdist'in kancasından sonra çalıştığı için işaretler etkisizdi; bu, `-rA` çıktısında `@grup` ekinin görünmemesinden ve aynı modülün testlerinin iki işçiye dağılmasından anlaşıldı. `tryfirst=True` ile düzeltildi. "Etkisiz kanca" satırındaki iki keşif koşusu bu yüzden gruplamasızdı.
- Bir ölçüm betiğinde `wait` çalışmadığı için 13 pytest eşzamanlı başladı; o ölçüm (553 s) geçersiz sayıldı ve kullanılmadı. Kalan artık süreçler bu oturumun başlattıkları olarak temizlendi.
- İlk sıralı ve ilk paralel koşular pilde alınmış olabilir; bu yüzden sıralı ve paralel süreleri karşılaştırırken yukarıdaki %12'lik sıralı oynaklığı hesaba katın.

## Açık nokta (proje sahibi kararı gerekebilir)

- Ağır grupları önce başlatmak (en uzun grup önce) kuyruk gecikmesini kısaltabilir (`-n 3` çizelgesinde vault grubu 266 s'de başladı, yaklaşık 60 s kazanç olası). Bu, paralel koşuda toplama sırasını değiştirmeyi gerektirir; K3 kapsamı dışında sayıp yapılmadı.
- `borsai/backtest.py::default_workers()` (salt okunur) paralel koşuda düşürülebilirse havuz gecikmesi azalırdı; K4 ve salt okunur kuralı gereği dokunulmadı.

## Kabul kapısı

| Kapı | Sonuç |
|---|---|
| K1: üç paralel koşu sıralıyla düğüm düğüm aynı, 0 kırmızı | **Geçti** (par1–par3 + n4, n6, nauto) |
| K2: silinen/atlanan/gevşetilen test yok, `assert` farkı 0 | **Geçti** (0 / 0) |
| K3: varsayılan `pytest -q` sıralı; son sıralı koşu + `test.sh` + `gen_golden --check` yeşil | **Geçti** (864 geçti, 1017 s; `test.sh` rc=0; `gen_golden --check`: 25 dosya, fark 0) |
| K4: commit'ler yalnız izinli yollarda, push yok | **Geçti** (C: `pyproject.toml`, `requirements.lock`, `tests/`, `docs/ENV.md`, görev dosyası; R: `docs/infra/`) |

Not: görevin tablosundaki "sıralı 19–31 dk" eski koşulardır; bu makinede bugünkü sıralı süre 15–17 dk.

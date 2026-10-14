# TASK_ID: BORSAI_FAZ3_APP_STAGE01_20260922

Model: Opus 5 · Extra. Çalışma klasörü ~/Desktop/BorsAi.
Ağ: yalnız araç kurulumu (rustup, nvm/Node, crates.io, npm). push/tag/amend yok.

## Bağlam
- Masaüstü uygulamasının şartnamesi `docs/app/SPEC_APP.md` (Fable; EK 1 dahil). Bağlayıcıdır.
- Bu görev şartnamedeki §7'nin aşama 0 (kurulum ve iskelet) ve aşama 1 (Rust `borsai_predict` + Python paritesi) kısmıdır.
- Proje sahibinin açık sorulara kararları: beş öneri de KABUL.
  1. f3 tanımı SPEC_APP §3a.1'deki gibi.
  2. Uygulama XU100 indirmez.
  3. Girdi belgeleri `<T>.PB.json` ve `<T>.json` ayrı dosyalar.
  4. Bağımsız mod korunur.
  5. Uygulamanın kendi `.gitignore`'u yeterli; kök dosyaya dokunulmaz.
- Paralel oturum: Faz 4 (`docs/prompts/FAZ4_CEILING_PATH_IMPL.md`). `borsai/`, `tests/`, `models/`, `docs/` ve `scores/` yollarına yazıp kendi commit'ini atıyor. Sen YALNIZ `app/` altına yazarsın.
- **Model kümesi.** Bu görevde yalnız f1f9d44'teki 16 model kullanılır: `models/INDEX.json`'un ilk 16 kaydı ve `borsai/predict*.py` türleri. Faz 4 çalışırken INDEX'e yeni `ceiling_path` modelleri eklenebilir. `gen_golden.py` ve `build.rs` o kayıtları bu görevde YOK SAYAR: ilk 16 kaydın model_id listesi açıkça sabitlenir. Yeni tür sonraki bir görevde eklenecek.

ÖNCE OKU:
- CLAUDE.md
- docs/app/SPEC_APP.md (tamamı; özellikle §1, §2.1, §5.1–§5.2, §5.6-U37, §6, §7)
- borsai/predict.py, predict_hazard.py, predict_pb.py, predict_market20.py, features.py, horizons.py, survival.py
- borsai/freeze.py (`model_kind`)
- docs/ENV.md

## Adımlar

### Aşama 0: kurulum ve iskelet
1. İLK iş olarak `app/.gitignore` yaz: `node_modules/`, `src-tauri/target/`, `dist/`. Ağır dizinler bundan sonra oluşur.
2. Araçları kur, sudo yok, şartname §6'daki gibi:
   - rustup kararlı araç zinciri: `~/.cargo`
   - nvm + Node LTS: `~/.nvm`
   - Tauri CLI
   - Sürümleri `docs/ENV.md`'ye DEĞİL raporuna ve `app/README.md`'ye yaz. `docs/`'a dokunma.
   - Kurulum Mac şifresi (sudo) isterse DUR ve proje sahibine tek komutla sor.
3. `app/` altında şartnamedeki dizin düzeniyle Tauri 2 + Vite + TypeScript iskeleti kur. `npm run tauri dev` bir pencere açmalı. Açıldığını proje sahibi görecek; raporda talimatını ver.
4. `build.rs`:
   - Modelleri gömer (§1.4).
   - Çalıştırdığı her git komutu `GIT_OPTIONAL_LOCKS=0` ortam değişkeniyle ve yalnız okuma komutlarıyla (`rev-parse`, `status --porcelain`). Nedeni: paralel commit sırasında `index.lock` bırakmamak.
5. `cargo test` ve `npm test` boş da olsa geçmeli.
6. Commit A. Mesaj: `BORSAI_FAZ3_S0: Tauri app skeleton and toolchain (SPEC_APP stage 0)`

### Aşama 1: predict + parite
7. `app/src-tauri/crates/borsai_predict`: saf Rust portu (§1.2–§1.3). Sayısal kararlar tablosu ve CPython `sum()` algoritması birebir.
8. `app/parity/gen_golden.py` (repo `.venv`'iyle koşar, `borsai`'yi import eder, yalnız okur): 16 model × en az 200 satır, seed 20260922, `app/parity/golden/<model_id>.jsonl`.
   - Girdi planı §1.3'teki gibi.
   - 7 sicil girdisi `registry/inputs/*.json`'dan okunur. Sonuç dosyaları (`data/outcomes/`) OKUNMAZ; bu aşamada gerekmez.
9. `cargo test -p borsai_predict --test golden`:
   - 16/16 model; maks |Δ| ≤ 1e-9 (beklenti < 1e-12).
   - Ret ve uyarı kodları birebir.
   - `target/parity_report.json` üretilir.
10. U37 koşullu parite testi:
    - j = 0..9 için S_k/S_j, P_L[k]/S_j ve 1 − S_{j+1}/S_j.
    - |Δ| ≤ 1e-12. j = 0'da bit-eşit.
11. Aşama 1'in U-testleri (§7 tablosu: U1–U6, U12, U33, U34, U37) yeşil.
12. Commit B. Mesaj: `BORSAI_FAZ3_S1: Rust borsai_predict with Python golden-vector parity (SPEC_APP stage 1)`

Aşama 1 tek oturumda bitmezse:
- Yeşil olan kısmı commit etme.
- Aşama 0 commit'iyle dur.
- Raporda kalan işi listele.

## Kurallar
- YALNIZ `app/` altına yaz. Tek istisna bu görev dosyası. `borsai/`, `tests/`, `models/`, `registry/`, `data/`, `scores/`, `docs/` ve kök `.gitignore` DEĞİŞMEZ.
- Commit YALNIZ kendi yollarınla:
  ```
  git add app docs/prompts/FAZ3_APP_STAGE01.md
  git commit -m "<mesaj>" -- app docs/prompts/FAZ3_APP_STAGE01.md
  ```
- Commit öncesi `git status --porcelain -- app` kontrolü: `node_modules`/`target`/`dist` görünmemeli.
- `git add -A` YOK.
- `index.lock` hatasında 10 saniye bekle ve yeniden dene; kilidi SİLME.
- Python tarafı yalnız okunur. `predict` tanımı Python'dakidir. Parite tutmuyorsa Rust'u düzelt; toleransı gevşetme.
- Rapor Türkçe.

## Teslim (rapor)
- Commit hash'leri ve `git show --stat` özetleri.
- Araç sürümleri.
- `npm run tauri dev` için proje sahibine tıklama/komut talimatı.
- `parity_report.json` özeti: model başına maks |Δ| ve bit-eşit oranı.
- U-testleri tablosu.
- Kalan işler.
- Sapmalar ve kararlar.

## Kabul kapısı
- K1 Commit'ler yalnız `app/` ve bu görev dosyası.
- K2 16/16 model paritesi ≤ 1e-9; ret ve uyarı kodları birebir.
- K3 build.rs'deki git çağrıları kilitsiz ve salt okuma.
- K4 push yok.

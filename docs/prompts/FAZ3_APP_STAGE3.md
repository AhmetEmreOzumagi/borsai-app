# TASK_ID: BORSAI_FAZ3_APP_STAGE3_20260922

Model: Opus 5 · Extra. Klasör: ~/Desktop/BorsAi. Ağ: yalnız npm/crates (gerekirse). push/tag/amend yok.

## Bağlam
- Aşama 0 (50c62da), 1 (0b67f5d) ve 2 (5606772) tamam.
- Faz 4 dondu (a0df5b7). `models/INDEX.json` artık **19 model**.
  - Uygulama ilk 16'yı gömüyor (`PINNED_MODEL_IDS`), son 3'ü `ignored_model_ids` olarak atlıyor.
  - Bu 3 modelin (`ceiling_path_v0`, `ceiling_path_v0@INF`, `pb_ceiling_path_v0`) Rust portu AYRI bir görev. Önce Fable uygulama eki yazıyor (paralel oturum, aşağıda).
- Bu görev `docs/app/SPEC_APP.md` §7'deki **aşama 3: Dondur akışı**. Kapsam:
  - §3e resmi "dondur" sihirbazı (6 adım), "Şimdi yapılacaklar" komut bloğu, iptal akışı
  - Sicil ekranı ve arz sayfası (§3g resmi görünüm: koşullu değerler yalnız dondurulmuş kayıttaki S'ten)
  - U27–U32, U38, U39

### Şartname yazıldıktan sonra değişenler (bağlayıcı; SPEC_APP metniyle çelişirse bunlar geçerli)
1. **Model sayısı.** `borsai.freeze` INDEX'teki bütün modelleri yazar (bugün 19).
   - Parite adımı yalnız uygulamanın desteklediği modelleri karşılaştırır. Diğerleri "uygulamada henüz yok" diye adıyla listelenir. Bu bir uyuşmazlık değildir, `incidents/`'a yazılmaz.
   - Desteklenen küme gömülü veriden okunur; kodda 16 sabiti YOK. Port gelince aynı kod 19/19 demeli.
   - Ekran metni: `parite: 16/16 desteklenen model, |Δ|max = …; uygulamada henüz olmayan: 3 (<adlar>)`.
   - U30'daki "kayıt 16 model içerir" yerine: "kayıt INDEX'teki bütün modelleri içerir (bugün 19)".
2. **Aynı arza ikinci kayıt serbest** (Faz 2B düzeltmesi yapıldı). §3e'deki "iptal edilmemiş kayıt var" dalı eskidi.
   - `borsai/freeze.py`'nin bugünkü davranışını oku. Aynı girdi + aynı INDEX ile ikinci kayıt `DUPLICATE_RECORD` ile reddedilir; bunu Türkçe açıkla.
3. **Girdi dosyası adı** (FAZ3_APP_STAGE01 kararı): `stage = PRE_BOOKBUILD` → `registry/inputs/<T>.PB.json`; `POST_BOOKBUILD_PRE_LISTING` → `registry/inputs/<T>.json`. "Şimdi yapılacaklar" bloğundaki `git add` doğru dosyayı gösterir.
4. **Komut bloğundaki commit** `--` ile yollara sınırlanır:
   `git commit -m "<mesaj>" -- <git add'deki aynı yollar>`. Blokta yorum satırı olmaz.
5. **Sicil ekranında desteklenmeyen modeller:** kayıttaki 3 Faz 4 modeli adıyla listelenir, yanında "bu modelin gösterimi Faz 4 portuyla gelecek" yazar. Çıktıları render edilmez.
6. **Python yolu:** `config.python_path` (varsayılan `<repo_root>/.venv/bin/python`); cwd her zaman hedef repo kökü.

### Paralel oturum
Fable, `docs/app/SPEC_APP_EK2.md` yazıyor ve kendi yollarını commit edecek. `docs/app/` altına dokunma, o dosyayı okuma, commit'ine alma.

ÖNCE OKU:
- CLAUDE.md
- docs/app/SPEC_APP.md: §1.1, §2 (özellikle 2.2 ve 2.5), §3e, §3g, §5.4, §5.5, §7
- docs/prompts/FAZ3_APP_STAGE01.md (kararlar), FAZ3_APP_STAGE2.md
- borsai/freeze.py, borsai/registry.py (`INPUT_FIELDS`, `load_inputs`, `validate_inputs`, `inputs_pit_problems`, `pretty_json_bytes`), borsai/push_proof.py
- registry/inputs/NETGL.json, registry/source_docs/NETGL/MANIFEST.json, registry/records/NETGL/ altındaki bir kayıt
- app/README.md ve app/ kodu

## Adımlar
0. `git log --oneline -3`, `git status --porcelain`.
   - İzinli izlenmeyen dosyalar: bu görev dosyası, `docs/prompts/FAZ3_FABLE_APP_SPEC_EK2.md`, `docs/app/` altındaki yeni dosyalar. Başka değişiklik varsa DUR.
   - Taban çizgisi: `bash app/scripts/test.sh` yeşil.
   - Asıl repo `registry/` ağacının sha listesini al (sıralı `shasum -a 256`), `/tmp/reg_before.txt`'ye yaz.
1. **Rust komutları** (§3e adım 1–6 ve iptal):
   - kaynak belge kopyalama ve `MANIFEST.json` ekleme (var olan giriş değişmez; aynı ad farklı sha → DUR)
   - girdi belgesi yazıcı. `pretty_json_bytes` ile bayt-eşit olmalı. Test: NETGL.json'u ayrıştırıp yeniden yaz, bayt-eşit çıksın.
   - Rust `validate_inputs` portu
   - Python yetkili denetimi, `freeze` ve `--cancel` çağrıları
   - kayıt okuma ve parite (değişen 1)
   - git beyaz listesi: `rev-parse`, `status`, `log`, `ls-files` (U32)
2. **Sihirbaz ekranı:** 6 adım, her adımın çıktısı ekranda kalır, sonra "Şimdi yapılacaklar". T ≤ bugün (İstanbul) ise kırmızı uyarı; T boşsa sarı.
3. **Sicil ekranı ve arz sayfası:**
   - `<repo>/registry/records/**` her açılışta okunur
   - iptal edilen kayıt üstü çizili, neden ve zamanla
   - push kanıtı göstergesi (`registry/push_proofs/`; sınıf hesaplanmaz)
   - bir arzın birden çok kaydı ayrı sekmelerde
   - koşullu görünüm yalnız kayıttaki `models[].output.S`'ten (U38)
4. **U39:** kullanıcı beyanı ve senaryo hiçbir yoldan `data/outcomes`, `registry`, `scores`'a yazılmaz.
5. **Betikler:** `app/tests/e2e_freeze_tmp_repo.sh` (U28–U31) ve `app/tests/e2e_personal_isolation.sh` (U39).
   - Geçici klon: `git clone --local`. Her Python çağrısında cwd = `$TMP`.
   - İlk `freeze`'den önce `borsai.__file__`'in `$TMP` altında olduğunu doğrula. Değilse DUR (PYTHONPATH sızıntısı asıl repoya kayıt yazdırır).
   - Senaryolar: PB kaydı (`SNTA1.PB.json`), ardından talep katlı ikinci kayıt (`SNTA1.json`); aynı girdiyle tekrar → `DUPLICATE_RECORD`; iptal; T = dün (U31).
   - Betik sonunda asıl repo `registry/` sha listesi `/tmp/reg_before.txt` ile birebir aynı olmalı ve `GIT_OPTIONAL_LOCKS=0 git status --porcelain -- registry` boş olmalı. Betik bunu kendisi denetler ve yazdırır.
6. **Testler:** geliştirirken hedefli test. Commit öncesi tam koşu: `bash app/scripts/test.sh`, iki betik ve `.venv/bin/pytest -q` (bekçi testleri bütün repoyu tarar).
7. **Ekran görüntüleri** `app/docs/screens/` altına: sihirbaz adımları (YALNIZ geçici klonda) ve NETGL'li Sicil ekranı. Asıl repoda sihirbaz çalıştırılmaz.
8. Commit.

Bu aşama tek oturumda bitmezse:
- Yeşil ve tutarlı bir ara noktada commit at. Mesaja `(partial)` ekle.
- Kalanları raporda listele.

## Kurallar
- YALNIZ `app/` altına yaz. Tek istisna bu görev dosyası.
- Asıl repoda `registry/`, `data/`, `scores/`, `models/`, `borsai/`, `docs/`, `tests/` salt okunur. Dondur/iptal komutları yalnız geçici klona karşı koşar.
- Uygulama `git commit`/`push`/`add` çalıştırmaz (U32 testi).
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma; `tests/test_outcome_guard.py` bunu sızıntı sayar.
- Model davranışı Python'daki gibidir.
- Commit:
  ```
  git add app docs/prompts/FAZ3_APP_STAGE3.md
  git commit -m "<mesaj>" -- app docs/prompts/FAZ3_APP_STAGE3.md
  ```
  - `git add -A` yok.
  - `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Mesaj: `BORSAI_FAZ3_S3: official freeze wizard, registry screen and frozen-record conditional view (SPEC_APP stage 3)`
- Rapor Türkçe.

## Teslim (rapor)
- Commit hash'i ve `git show --stat` özeti.
- U-testleri tablosu (U27–U32, U38, U39).
- e2e betik çıktısından: kaydın model sayısı (19), parite satırı (16/16 + 3 desteklenmeyen), DUPLICATE_RECORD ve iptal satırları, asıl repo `registry/` eşitlik satırı.
- Test sayıları ve süreleri: cargo, npm, pytest.
- Ekran görüntülerinin yolları.
- Kalan işler ve sapmalar.

## Kabul kapısı
- K1 U27–U32, U38, U39 yeşil; aşama 0–2 testleri yeşil kalıyor.
- K2 İki e2e betiği yeşil. Asıl repo `registry/` sha listesi öncesiyle aynı, `git status --porcelain -- registry` boş.
- K3 Parite kodunda 16 sabiti yok; desteklenen küme gömülü veriden.
- K4 Uygulama git'e yazmıyor (U32).
- K5 Commit yalnız `app/` ve bu görev dosyası. Tam pytest yeşil.

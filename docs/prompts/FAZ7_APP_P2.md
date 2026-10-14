# TASK_ID: BORSAI_FAZ7_APP_P2_20261001

Model: Opus 5.5 · Extra. Klasör: ~/Desktop/BorsAi. Ağ gerekmez. push/tag/amend yok.

## Rol
Uygulama EK3'ün ikinci aşaması **P2**: D1 sonrası güncelleme (`post_d1_hazard_v0`). Kullanıcı açısından soru şu: **"tavan serisi yarın bozulur mu?"** Şartname `docs/app/SPEC_APP_EK3.md` §6, §9 (P2 satırları), §10.2, §11 (Fable, `7be8394`). Bu görev onu uygular:
- `predict_post_d1` Rust portu ve ikinci dizinin (`INDEX_POST_D1.json`) gömülmesi;
- koşullu sekmede ve "Tavan serisi" kartında **"D1 sonrası" satırı** (yalnız resmi kayıttan);
- Sicil ekranında **"D1 sonrası kayıt" sihirbazı**;
- Doğruluk sekmesinde `scores_post_d1.json` bölümü.

Sonunda uygulama derlenir; proje sahibi kurar.

## Bağlam: EK3 yazıldığından beri değişenler (orkestratör ölçtü, 2026-10-01)
0. **Taban:** `origin/main` = `d1193fa` (NETGL D4–D10 sonuçları, skorlar ve push kanıtı dahil; ağaç temiz).
1. **P1 bitti** (`b29486e`, push'lu). `hazard::linear` (v0 doğrusal öngörücü, `LinOut.eta`) ve `Warning.bool_fields` hazır (P1 RAPOR §11). `PINNED_MODEL_IDS` 23; `ignored_model_ids` dört (C) kimliği. P2 bunları değiştirmez.
2. **İkinci dizin:**
   - `models/INDEX_POST_D1.json` tek giriş `post_d1_hazard_v0`: sha `3f7640267cd0…`, `parent_sha256` `caa4dc867a9f…` (= `ceiling_hazard_v0`).
   - Dosya sha256 `94ac36faffac…`; `models/INDEX.json` sha256 `7e636e8bf64b…` (27 giriş).
3. **Canlı POST_D1 kaydı yok:** `registry/post_d1/` dizini yok.
   - `scores/scores_post_d1.json` (`as_of_session` 2026-09-30): `n_retro 7`, hücre 0, `n_live 0`.
   - Gerçek veriyle koşullu satır görünmez. Ekran görüntüleri sentetik kayıtla alınır (adım 6).
4. **Kasa açık** (`registry/oot/VAULT_OPEN.json`). `registry/oot/post_d1/<T>/` altında 135 eski kohort POST_D1 kaydı (`borsai.oot_post_d1_record/1`) var; 64'ü kasa (SEALED) üyesi.
   - Uygulamanın kayıt okuyucusu **yalnız `registry/post_d1/`'i** okur; OOT dizinine bakmaz.
   - Yalnız K-P2-4 testi OOT kayıtlarını okur; o da kasa dışındakileri.
5. **`scores/scores_oot.json` D1 sonrası blokları** (birincil hücre, karşılaştırıcı `ceiling_hazard_v0`, RPS):
   - `post_d1` (açık küme): n 59, −0.042 [−0.066, −0.020], **geçiyor**;
   - `post_d1_sealed` (kasa): n 45, −0.035 [−0.071, +0.004], **ayırt edilemiyor**;
   - `post_d1_all`: n 104, −0.039 [−0.060, −0.017], geçiyor.

   P1'in `commands/scores_oot.rs` okuyucusu bu blokları satırsız önbellekte tutuyor.
6. **Python CLI** (EK3 §6.6 ve Ö6 düzeltmesi):
   - kayıt `python -m borsai.freeze --post-d1 <TICKER>`;
   - **iptal `python -m borsai.freeze --cancel <dosya> --reason "…"`** (EK3'teki `--cancel-post-d1` yok);
   - `borsai.registry.t_open(d1, calendar)` var; `borsai.push_proof` commit sha'larını argüman alır.
7. **Komut blokları** mevcut `commands/freeze.rs: todo_commands` kalıbıyla üretilir: satır başına bir komut, `&&` yok, Python yolu yapılandırmadan (`repo.python`, `python_display`). EK3 §6.6'daki `&&`'li bloklar bu kuralla okunur.
8. **Test komutları** (`docs/ENV.md`):
   - ara koşular `.venv/bin/pytest -q -n 6 --dist loadgroup`;
   - her commit'ten önceki son kabul koşusu sıralı `.venv/bin/pytest -q`.

   Taban sayıları adım 0'da ölçülür.

## Proje sahibi ve orkestratör kararları (bağlayıcı)
- **K-P2-1 (EK3 §13 kalan sorular):**
  - S4: Uygulama `freeze --post-d1`'i kendisi çalıştırır (§6.6 adım 3; parite anında görünür). Bülten indirme ve commit/push yalnız komut bloğudur.
  - S5: Senaryo modunda D1 alanı elle girilmez.
- **K-P2-2: komut metni tek fonksiyonda.**
  - Sihirbazın komut blokları tek fonksiyondan üretilir (`freeze.rs: todo_commands` kalıbı, ortak yardımcıya taşınabilir).
  - İptal komutu `--cancel <dosya> --reason "…"`.
- **K-P2-3: karttaki "D1 sonrası" satırının terazi sütunları.** Satır yalnız etkin POST_D1 kaydı ve j ≥ 1 varken görünür (EK3 §6.5).
  - **Zaman-dışı:** `post_d1_sealed` bloğunun `label == "birincil"` hücresinin `verdict`'i + " (zaman-dışı terazide)".
    - Bugün "ayırt edilemiyor (zaman-dışı terazide)".
    - Karşılaştırıcı hücrenin `rule_ids`'inden **görünür biçimde** yazılır: "karşılaştırıcı: ceiling_hazard_v0". Bu birincil hücre basit kurala değil ebeveyn modele karşıdır.
  - **Yakın dönem:** "—".
  - **Canlı:** `scores_post_d1.json` `n_live` (n < 10 → "n = {n}: hüküm yok").
  - Değerler toplanmaz ve ortalanmaz; açık küme ya da `_all` bloğu bu sütuna yazılmaz (P3 panelinin işi).
- **K-P2-4: gerçek D1 verisiyle ek parite testi (EK3'e ek).**
  - Rust `predict_post_d1`, `registry/oot/post_d1/` altındaki **kasa dışı** kayıtlarla koşulur. Süzgeç: `registry/oot/cohort_pre_h99.csv` `vault != SEALED`; SEALED dizinleri **açılmaz**.
  - Girdiler kaydın `base_record` ve `d1` bloğundan alınır; çıktı kaydın `models[post_d1_hazard_v0]` hücresiyle §6.3 kurallarına göre karşılaştırılır.
  - Beklenti (önceden yazılı, orkestratör ölçümü): **71 kayıt; 59 PREDICTED, 9 NOT_APPLICABLE (`D1_NOT_CEILING`), 3 REFUSED (`F3_MISSING`); parite 71/71.**
  - Çıktıda yalnız sayılar yer alır. Uyuşmazlık olursa Rust düzeltilir; Python'a dokunulmaz.
  - Kayıt şeması testi kurmaya izin vermiyorsa test içi okuyucu uyarlanır. Yine olmuyorsa raporla ve diğer adımlara devam et.
- **K-P2-5: Windows uyumu** (K-P1-5 aynen).
  - Yeni kodda sabit Mac yolu ya da zsh/bash'e özel sözdizimi yok.
  - Yollar `PathBuf`/`Path.join` ile kurulur.
  - Platform farkı tek fonksiyonda toplanır.
  - Mevcut `config.rs: default_python` (`.venv/bin/python`) bu görevde değişmez; Windows aşamasında ele alınır.
- **K-P2-6: önceden onaylı pin güncellemeleri** (K-P1-6 aynen).
  - `app/` altında model sayısı, MANIFEST sha'ları, altın dosya sayısı ve fikstür sayan satırlar asgari yeniden pinlenebilir.
  - `tests/` (Python) altında yalnız `app/` dosyasını ya da `gen_golden --check` dosya sayısını pinleyen satırlar değişebilir (ör. 30 → 31). Bunlar ayrı commit APPPIN olur.
  - Bekçi (sıra, kasa, hijyen, temizlik) testine dokunmak gerekirse **DUR**.
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** Parite tutmuyorsa Rust düzeltilir; tolerans gevşetilmez.
- **Soru sorman gerekirse** seçenekleri açık yaz. Proje sahibi orkestratöre danışarak cevaplayacak.

## İzinli izlenmeyen
Yalnız bu görev dosyası. Başka bir şey varsa DUR.

## Paralel
Bu görev koşarken başka oturum yok. Proje sahibi bu sırada git komutu çalıştırmaz.

## ÖNCE OKU
- CLAUDE.md
- `docs/app/SPEC_APP_EK3.md`: §0, §1, §4.1 (P2 satırı), §6 tamamı, §9 (P2 satırları), §10.2, §11 (P2), §12 Ö6
- `docs/app/p1/RAPOR.md` (§7 sapmalar, §11 P2 notları)
- `docs/specs_faz5/SPEC_POST_D1_V0.md` (§4, §7, §8; errata H23–H47 `docs/SPEC_DEVIATIONS.md`)
- `docs/faz7_vault/SKOR_RAPOR.md` (D1 sonrası satırları)
- `docs/ENV.md`
- `borsai/predict_post_d1.py`, `borsai/freeze.py` (post_d1 fonksiyonları, CLI), `borsai/registry.py` (`t_open`, `POST_D1_DIR`)
- `app/src-tauri/build_embed.rs`, `crates/borsai_predict/src/*`, `src/commands/{ceiling,path,parity,registry,freeze,scores,scores_oot,git}.rs`, `src/render/{ceiling,summary,registry,accuracy}.ts`, `src/i18n/tr.ts`, `app/parity/gen_golden.py`, `app/scripts/{test.sh,screens.sh,env.sh}`, `tests/faz5_live_support.py` (U69 sentetik bülten kalıbı)

## Adımlar
Her adım kendi commit'iyle biter ve tek başına yeşildir (`bash app/scripts/test.sh`).

0. **Taban.**
   - `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -1` = `origin/main`; ağaçta yalnız bu görev dosyası.
   - `bash app/scripts/test.sh`, `.venv/bin/python app/parity/gen_golden.py --check`, paralel pytest. Sayıları `docs/app/p2/test_runs.txt`'ye yaz.
1. **B1: crate (commit B1; bu görev dosyası da girer).**
   - `Kind::PostD1`, `params::parse_post_d1` (§6.1 sırası), `post_d1.rs` (`evaluate_d1`, `predict_post_d1` §6.2), çıktı ve kodlar (§6.3).
   - U65 ve crate birim testleri (`INPUT_SHARES_OFFERED` birim testi dahil).
2. **B2: altın vektörler (commit B2).**
   - §6.4: `gen_golden.py` `PINNED_POST_D1_MODEL_IDS`, `synth_d1` (seed 20260922); `golden/post_d1_hazard_v0.jsonl` ≥ 220 satır; `_patched_params.jsonl` +8; MANIFEST (`post_d1_rows`, `models_index_post_d1_sha256`); `bit_equal_floor.json` +1.
   - Girdi tabanlarında kasa süzgeci P1'deki gibi.
   - U64, U66. `golden_unchanged.sh`: eski 23 dosya bayt-eşit; `_patched_params.jsonl` mevcut satırları bayt-eşit.
3. **B3: gömme, bütünlük, komutlar (commit B3).**
   - `build_embed.rs` ikinci dizin (§4.1 P2), `models::verify_post_d1`, `POST_D1_PARENT_MISMATCH` (U67).
   - Komutlar: `commands/post_d1.rs` (kayıt okuyucu `post_d1_records`, `post_d1_preflight`, freeze çağrısı, parite), `ceiling`/`path`/`parity`/`registry` ekleri.
   - `predict_all` bu türü çalıştırmaz. `git` beyaz listesi değişmez (U32 genişler).
   - K-P2-4 gerçek D1 parite testi (ör. `BORSAI_REPO=… cargo test --test records_parity post_d1_oot_open`).
4. **B4: arayüz (commit B4).**
   - Koşullu sekmede "D1 sonrası" satırı ve kaynak satırı (§6.5).
   - Kartta POST_D1 satırı (§6.5 + K-P2-3).
   - "Getiri (koşullu)" ek kartı (`path_conditional`).
   - Doğruluk sekmesinde `scores_post_d1.json` bölümü (U70).
   - Metinler §9 P2 satırları.
   - U68, U70; kart için K-P2-3 testi: sentetik kayıt + gerçek `scores_oot.json` → "ayırt edilemiyor (zaman-dışı terazide)" ve "karşılaştırıcı: ceiling_hazard_v0" DOM'da.
   - Ön uçta hesap yok (`no_frontend_math` genişler).
5. **B5: sihirbaz (commit B5).**
   - §6.6 dört adım + K-P2-1/K-P2-2; iptal `--cancel`.
   - U69: geçici klon, kurgusal `SNTA1`, sentetik zip + MANIFEST satırı (`tests/faz5_live_support.py` kalıbı; Python koduna dokunma).
   - U69 bir Python bekçisine takılırsa diğer adımları bitir; U69'u son adım olarak bırak ve engeli raporla.
6. **Ekran görüntüleri** (`docs/app/p2/ekran/*.png`). Geçici klonda sentetik SNTA1 kaydıyla:
   - koşullu sekme j = 0 (satır yok + not) ve j = 2;
   - kart (POST_D1 satırı ve terazi sütunları);
   - sihirbazın dört adımı;
   - Doğruluk sekmesindeki post_d1 bölümü (gerçek dosya).

   Her görüntü raporda "sentetik kayıt" diye etiketlenir. Gerçek repoya kayıt yazılmaz.
7. **Derleme** (commit yok):
   ```
   source app/scripts/env.sh
   cd app
   npm run tauri build -- --bundles app
   ```
   `/Applications`'a kopyalama. `.app` sha256'sı rapora.
8. **Son kabul:** sıralı `.venv/bin/pytest -q`, `bash app/scripts/test.sh`, `gen_golden --check`. Gerekirse önceden onaylı APPPIN commit'i.
9. **Rapor** `docs/app/p2/RAPOR.md` (commit R). İçerik:
   - hash'ler;
   - U64–U70 + K-P2-4 sonuçları (tablo) ve EK3 §11 P2 beklentisiyle karşılaştırma;
   - K-P2-3 kart metni (sentetik kayıtla, metin olarak);
   - ekran görüntüleri; test sayıları; `.app` sha;
   - kurulum bloğu (aşağıda);
   - **proje sahibi için D1 akşamı akışı:** bir sonraki arzda D1 bülteni yayımlandıktan sonra sihirbazla kayıt ve T_open (D2 09:40) öncesi push. Tıklama düzeyinde, 6–8 satır.
   - P3/P4/Windows için notlar.

## Proje sahibi için kurulum bloğu (rapora aynen koy)
Önce çalışan uygulamayı kapat (Cmd+Q), sonra:
```
cd ~/Desktop/BorsAi
ditto app/src-tauri/target/release/bundle/macos/BorsAi.app /Applications/BorsAi.app
open /Applications/BorsAi.app
```

## Tek oturumda bitmezse
- Her adım commit'le biter. Yeniden başlarken `git log`'dan son commit'i bul ve sonraki adımdan devam et. Yarım adımın commit'lenmemiş değişiklikleri ağaçta kalır: önce ölç, sonra sürdür.
- Bağlam dolarsa bir adım sonunda dur ve rapora "kalan adımlar" yaz. Proje sahibi aynı cümleyle yeni oturum açar.

## Kurallar
- **Yazılabilir:**
  - `app/` (EK3 §1 P2 satırındaki dosyalar ve K-P2-2 ortak yardımcısı);
  - `docs/app/p2/`, bu görev dosyası;
  - K-P2-6 kapsamında `tests/` pin satırları (ayrı commit).
- **Salt okunur:** `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `docs/specs*`, `docs/app/SPEC_APP*.md`, `CLAUDE.md`, `legacy/`.
- Python'da eksik bulunursa Ö-görevi olarak raporla; düzeltme.
- Kasa (SEALED) üyelerinin kodları `app/` altındaki hiçbir dosyaya, fikstüre, rapora ya da test çıktısına yazılmaz.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- `git add -A` yok. Her commit yalnız kendi yollarıyla:
  ```
  git add <yollar>
  git commit -m "BORSAI_APP_P2_<B1|B2|B3|B4|B5|APPPIN|REPORT>: <özet>" -- <yollar>
  ```
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Push yok. Rapor Türkçe.

## Kabul kapısı
- **K1** post_d1 paritesi (U64) geçer; eski 23 altın dosya bayt-eşit; gerçek D1 paritesi 71/71 (59/9/3) ya da engel raporlandı.
- **K2** İkinci dizin bütünlüğü (U67) ve `predict_all` 23 sütun; uygulama OOT kayıt dizinini göstermiyor.
- **K3** "D1 sonrası" satırı yalnız kayıttan ve yalnız j ≥ 1'de; kart satırının terazi sütunları K-P2-3'e uygun; ön uçta hesap yok. Ekran görüntüleri raporda.
- **K4** Sihirbaz U69 yeşil (ya da engel raporlandı); uygulama git commit/push çalıştırmıyor.
- **K5** Son kabul: sıralı pytest + test.sh + `gen_golden --check` yeşil; `.app` derlendi. Commit'ler yalnız izinli yollarda; push yok.

PUBLIC_INVENTORY: GİRER 1 340 dosya, 66,3 MB · GİRMEZ 909, 225,7 MB · KARAR 1 512, 157,5 MB · ham veri isteyen test 97 · sır 0 · kişisel veri 0

# Herkese açık ayna için envanter (yalnız ölçüm ve öneri)

- **Görev:** `BORSAI_FAZ9_PUBLIC_INVENTORY_20261013` (`docs/prompts/FAZ9_PUBLIC_INVENTORY.md`). Model: Claude Code / Fable, yüksek.
- **Taban:** HEAD = `origin/main` = `e5a4d0f`, ağaç temiz; izlenen 3 761 dosya, 449,5 MB (MB = 10⁶ bayt); `.git` paketi 231,7 MiB; 187 commit.
- **Ekler:** `ekler/envanter.csv` (3 761 satır; yollar maskeli), `ekler/envanter.py` (üretici), `ekler/kirmizi_testler.txt`, `ekler/hijyen.py`, `ekler/koruma_once.txt`, `ekler/koruma_sonra.txt`. Ayna yol listesi: `MIRROR_MANIFEST.txt`.
- **İşaretler:** [ÖLÇTÜM] kendi ölçümüm; [ÇIKARIM] yorum. Hiçbir dosya değiştirilmedi, taşınmadı, silinmedi.
- **Bu raporda ne yok:** kasa kodu, bülten dosya adı (`th?` + 8 hane), PDF/zip içeriği alıntısı, zaman-dışı arz kodu (kasa harcanmış olsa da ORTAK hijyen kuralı uygulandı). Zaman-dışı dosyalar yalnız sayıyla anılır.

## 1. Özet (proje sahibi için)

1. [ÖLÇTÜM] Repo üç parçaya ayrılıyor: **GİRER** 1 340 dosya / 66,3 MB (kod, belgeler, modeller, testler, ekran görüntüleri), **GİRMEZ** 909 / 225,7 MB (555 KAP/SPK PDF'i, 73 BIST bülten zip'i ve yanlarındaki 281 manifest dosyası), **KARAR** 1 512 / 157,5 MB. KARAR'ın %90'ı iki şey: BIST bültenlerinden türetilmiş veri (skorlar, altın vektörler, sonuç CSV'leri, eğitim tabloları: ~120 MB) ve sicil (`registry/` kayıt ve girdileri: ~28 MB).
2. [ÖLÇTÜM] Türev veri dosyaları bültenden **aynen** değer taşıyor, ama bültenin tamamını değil: bir THB günde ~12 000 satır × 57 sütun; biz arz başına **tek satırın 11–14 alanını** kopyalıyoruz (`close_raw`, `upper_limit_raw`, hacim vb.). Repodaki 73 zip ile karşılaştırılabilen 98 satırın 98'i bayt düzeyinde bültenle aynı (§2.2). "Türev mi, alıntı mı" sorusu bu yüzden hukuki bir sorudur; ölçüm hüküm vermez (soru 1).
3. [ÖLÇTÜM] GİRMEZ dosyalar silinmiş bir klonda **uygulama kişisel modda çalışır**: `borsai_predict` ve Tauri komutları bu yollara çalışma anında dokunmaz; `registry/source_docs` yalnız repo modundaki dondurma sihirbazı (yazma + manifest okuma) tarafından kullanılır. Python tarafında `data/raw/bist` ve `source_docs`'u okuyan 5 modül vardır (`outcomes`, `outcomes_oot`, `scoring`, `registry`, `freeze`): sonuç alma, skorlama ve PIT belge denetimi. Bunlar aynada **koşmaz** (§3.1).
4. [ÖLÇTÜM] Test takımı aynada tam koşmaz: pytest 960 testin **79'u kırmızı, 16'sı hata** (866 yeşil; bir toplama hatası: `tests/test_registry_ipos.py`). Cargo 167 testin **2'si kırmızı** (`stage3.rs`: `inputs_doc_bytes_roundtrip`, `inputs_doc_bytes_match_python`; ikisi de `registry/source_docs/NETGL/MANIFEST.json` okur). Vitest 377/377, parite 8/8, `golden_unchanged.sh` yeşil. Kırmızıların 69'u doğrudan bir GİRMEZ yolunun yokluğundan, 24'ü aynı yolları isteyen akışların (kaydı yeniden dondurma, skoru yeniden hesaplama) dolaylı sonucudur (§3.2, `ekler/kirmizi_testler.txt`).
5. [ÖLÇTÜM] Aynadaki CI: `build.yml` yalnız `cargo test --workspace` (ignore'lar dahil değil) + `npm test` koşar. `inputs_doc_bytes_roundtrip` **ignore değildir** ve `registry/source_docs/NETGL/MANIFEST.json` ister: ayna CI'ı o dosya olmadan **bir testle kırmızı** olur. Diğer test (`…_match_python`) `#[ignore]`'dır, CI'da zaten koşmaz (§3.3, §6.4).
6. [ÖLÇTÜM] Sır: izlenen dosyalarda ve 187 commit'in tamamında anahtar/belirteç kalıbı **0**; `.env`, `.pem`, `.key`, `credentials` adlı dosya **0** (geçmişte de yok). Kişisel veri: dosya içinde e-posta **0** (tek `git@github.com` metni), telefon/TC kalıbı vuruşlarının hepsi sayısal yanlış pozitif (pay adedi, arz büyüklüğü, ondalık). Git geçmişinde 187 commit'in yazarı ve committer'ı tek kişisel Gmail adresi; `registry/push_proofs/` 31 dosyada GitHub kullanıcı adı ve profil URL'leri var (§4).
7. [ÖLÇTÜM] Kasa: 64 kasa kodu, GİRMEZ dışı **646 metin dosyasında** geçiyor (532'si KARAR, 114'ü GİRER: çoğu `docs/faz6`, `docs/faz7`, `docs/specs_faz6`); ayrıca 1 015 dosyanın **yolunda** kasa kodu var (hepsi `registry/oot`, `data/outcomes_oot`, `docs/faz6/dogrulama`). Kasa harcandı; ayna için karar yine de proje sahibinin (soru 6).
8. [ÖLÇTÜM] Yazılım lisansları temiz: npm ağacı 82 paket (MIT 58, Apache-2.0 4, ISC 3, OFL-1.1 3 yazı tipi, MPL-2.0 2, BSD 4, diğer izinli 8; GPL/AGPL/LGPL **0**). Cargo macOS çözümü 258 paket (MIT/Apache çoğunluk; MPL-2.0 **5**: `cssparser`, `cssparser-macros`, `dtoa-short`, `option-ext`, `selectors`; GPL/AGPL 0; tüm platformlarda `r-efi` "MIT OR Apache-2.0 OR LGPL-2.1-or-later" seçimli). Python 14 paket, hepsi MIT/BSD/Apache. **Kökte ve `app/`'ta `LICENSE` yok** (soru 12).
9. [ÖLÇTÜM] Ayna boyutu: GİRER 66,3 MB; GİRER + bütün KARAR 223,8 MB. 100 MB üstü dosya **yok**; en büyük `scores/scores_oot.json` 41,3 MB (GitHub'ın 50 MB uyarısının altında). Git geçmişinde GİRMEZ yollara dokunan commit 10/187; hiçbiri yalnız GİRMEZ dosya içermiyor, yani `filter-repo` o 10 commit'i ve onlardan sonraki tüm sha'ları yeniden yazar (§6.2).
10. [ÇIKARIM] Önerim: tek commit'lik yeni geçmiş + README'de özel repodaki sha ve push kanıtlarına atıf; kod için Apache-2.0 veya MIT; veri için ayrı `DATA_LICENSE`/beyan paragrafı; `registry/source_docs/*/MANIFEST.json` ile `data/raw/bist/MANIFEST*.csv`'nin aynaya alınması (PDF/zip içermezler, 1 CI testini ve 13 pytest'i yeşile çevirirler). Karar proje sahibinin (§5, §6, §7).

## 2. Envanter (adım 1)

### 2.1 Tür × durum × MB [ÖLÇTÜM]

Üretici: `ekler/envanter.py` (git ls-files → sınıf; kurallar betikte yazılı). CSV sütunları: yol (maskeli), boyut (bayt), tür, kaynak sahibi, durum, not. Satır sayısı 3 761 = HEAD'deki izlenen dosya sayısı.

| Tür | Durum | Dosya | MB |
|---|---|---:|---:|
| görsel | GİRER | 117 | 34,3 |
| kanıt (denetim ekleri, günlükler) | GİRER | 566 | 18,4 |
| belge | GİRER | 128 | 4,5 |
| test | GİRER | 232 | 4,5 |
| kod | GİRER | 180 | 3,2 |
| görev dosyası | GİRER | 83 | 0,9 |
| model | GİRER | 34 | 0,5 |
| resmi belge (KAP/SPK PDF) | GİRMEZ | 555 | 208,3 |
| ham veri (BIST zip) | GİRMEZ | 73 | 15,4 |
| kanıt (manifestler, GİRMEZ dizinlerinde) | GİRMEZ | 281 | 2,0 |
| türev veri | KARAR | 818 | 85,8 |
| skor | KARAR | 4 | 42,7 |
| kanıt (sicil kayıtları, deney günlüğü, push kanıtı) | KARAR | 497 | 25,6 |
| ham veri (bülten satır kopyaları, XU100) | KARAR | 137 | 2,2 |
| kod (`legacy/`) | KARAR | 34 | 0,9 |
| görsel (ikonlar) | KARAR | 16 | 0,2 |
| resmi belge (SPK xlsx, TÜİK xls) | KARAR | 6 | 0,2 |
| **Toplam** | | **3 761** | **449,5** |

| Durum | Dosya | MB |
|---|---:|---:|
| GİRER | 1 340 | 66,3 |
| GİRMEZ | 909 | 225,7 |
| KARAR | 1 512 | 157,5 |

Kaynak sahibine göre: proje 2 079 dosya (GİRER 1 340 + GİRMEZ manifest 281 + KARAR 458), KAP-şirket 417 (413 PDF GİRMEZ, 4 kohort CSV KARAR), SPK 147 (142 PDF GİRMEZ, 5 xlsx KARAR), BIST 420 türev KARAR + 73 zip GİRMEZ + 4 "BIST + KAP-şirket" eğitim tablosu, KAP-şirket + SPK (sicil girdi dosyaları) 414 KARAR, proje/H99 türevi (`tests/reference`) 75, proje/KAP girdisi (`app/parity/golden`) 34, XU100 kaynağı 2, TÜİK 4, GitHub yanıtı 31, belirsiz (ikon) 16.

GİRMEZ dizinlerinin ayrıntısı (karar verildi; yalnız sayı):

| Yol | Dosya | MB | İçerik |
|---|---:|---:|---|
| `registry/oot/source_docs/` | 658 | 204,1 | 523 PDF (135 arz × ~4; KAP bildirim/ek, SPK bülten) + 135 `MANIFEST.json` |
| `registry/oot/source_docs_faz7/` | 135 | 1,3 | yalnız JSON manifest; PDF yok |
| `registry/source_docs/` | 41 | 4,6 | 32 PDF (7 canlı arz) + 7 `MANIFEST.json` + `_ENUMERATION/` (1 PDF + `ENUMERATION.json`) |
| `data/raw/bist/` | 75 | 15,7 | 73 THB/THM zip (2026-08-06…2026-09-30; 40 THB + 33 THM) + `MANIFEST.csv` (73 satır) + `MANIFEST_OOT.csv` (1 168 satır: 2020-02-06…2023-10-04 bültenlerinin URL/sha'sı; **zip'leri repoda yok**) |

### 2.2 Ham mı, türev mi: ölçümler [ÖLÇTÜM]

Bir THB zip'inin içi: tek CSV, 57 sütun (`TARIH`, `ISLEM KODU`, … `KAPANIS FIYATI`, `REFERANS FIYAT`, `TOPLAM ISLEM HACMI` …), örneklenen günlerde ~11 700 satır; pay (`.E`) satırı 625–631. THM: 19 sütun (`ALT LIMIT FIYATI`, `UST LIMIT FIYATI`, `REFERANS FIYATI`, …).

| Dosya kümesi | Dosya / MB | Ne taşıyor | Bültenden aynen kopya var mı | Ölçüm |
|---|---|---|---|---|
| `data/raw/…_bist_session_outcomes.csv` (SESSIONS) | 1 / 0,75 | 990 arz-seans satırı, 40 sütun | **Evet:** 11 sütun `thb_raw_*`/`thm_raw_*` (açılış, yüksek, düşük, kapanış, hacim, ciro, AOF, işlem sayısı; referans, üst, alt limit) bülten hücresinin metni; 11 sütun normalleştirilmiş kopyası; kalan 18 sütun kaynak URL/sha/durum (proje) | Repodaki zip'lerle kesişen 28 satırın 28'inde `thb_raw_close` = bültenin `KAPANIS FIYATI` |
| `…_d1_d3_d5_d10_targets.csv` | 1 / 0,16 | 396 satır | `official_close` bültenden; `target_return` ve kesin kesir türev | — |
| `…_field_provenance.csv` | 1 / 4,40 | 11 880 satır | **Evet:** `raw_value` (12 alan × 990 seans; 8 910 THB + 2 970 THM hücresi) + `normalized_value` | sütun adları ve sayılar |
| `…_bist_pay_session_calendar.csv`, `pay_calendar_*.csv`, `v2_market20_…_calendar_evidence_r4.csv` | 4 / 1,27 | seans takvimleri (gün, yarım gün, kapanış) | Hayır; BIST tatil tablosu/bültenlerden çıkarılan durum alanları + kaynak PDF sha'ları | — |
| `…_pretrade_master.csv`, `…_provenance.csv`, `…_membership.csv`, `…_feature_readiness.csv` | 4 / 0,23 | 99 arz kohortu: fiyat, pay, talep katı, aracı kurum, **şirket adı** | KAP sonuç bildirimlerinden derlenen alanlar; bülten yok | — |
| `PREBOOKBUILD_…_R2_99.csv` | 1 / 0,08 | planlanan arz yapısı, SPK bülten no/URL | izahname/SPK bülteninden derlenen sayılar | — |
| `data/raw/*xu100*.json` (2) | 2 / 1,16 | XU100 kapanış serisi (9 682 + güncel kayıt) | BIST grafik uç noktasının JSON'u, pinli; 2 kayıt çıkarılmış türev (PROVENANCE §1) | — |
| `data/raw/tuik/` | 5 / 0,12 | TÜFE (2025=100) serisi, TÜİK xls, kaynak pini, üretici | TÜİK tablosunun kopyası + türev CSV | — |
| `data/outcomes/*.csv` (7 arz) | 8 / 0,63 | h, tarih, `close_raw`, `upper_limit_raw`, `reference_raw`, `trade_count_raw`, bayraklar, R/Y, iki sha | **Evet:** 4 `*_raw` sütun bülten hücresi | 70 satırın 70'inde `close_raw` = THB `KAPANIS FIYATI`, 70/70 `upper_limit_raw` = THM `UST LIMIT FIYATI` |
| `data/outcomes_oot/*.csv` (135) | 135 / 0,32 | aynı şema + `outcome_basis` | **Evet** (aynı 4 sütun) | zip'leri repoda yok, karşılaştırılamadı |
| `data/outcomes_oot/raw/*.json` (135) | 135 / 1,04 | 1 352 seans × `thb_row` (14 alan: aof, close, group, halt, high, low, market, **name**, open, special_*, trade_count, turnover, volume) + `thm_row` (lower, reference, upper) | **Evet, en geniş kopya:** arzın kendi bülten satırının alan alan kopyası | şema |
| `data/outcomes/COMPLETENESS.csv` | 1 / — | 6 413 satır: bültenlerde görülen bütün pay kodları ve adları (tamlık denetimi) | pay kodu + ad listesi bültenden | — |
| `data/training_table*.csv`, `data_version*.json` | 4 / 0,10 | 99 ve 170 arz × 31/39 sütun: KAP girdileri + R_Dh, Y_Dh, tavan etiketleri | `R_Dh` kapanış/fiyat − 1 (türev), etiketler türev; ham hücre yok | — |
| `app/parity/golden/*.jsonl` (34) | 34 / 58,7 | vaka başına KAP kaynaklı girdiler (fiyat, pay adetleri, talep katı, planlanan yapı) + model çıktıları; şirket adı yok | Bülten hücresi yok; girdiler KAP'tan | şema (`inputs` 17 alan) |
| `scores/scores.json`, `scores_break.json`, `scores_post_d1.json` | 3 / 1,4 | model × arz satırları: gerçekleşen R, tavan etiketi, L; `outcomes` bloğu | gerçekleşen değerler bültenden türev (R = kapanış/fiyat − 1); ham hücre olarak kapanış da geçer | — |
| `scores/scores_oot.json` | 1 / 41,3 | `oot_pre_h99*`, `post_d1*` blokları: 13–14 model × 135 arz × hücre; `retro_info` 568 satır | aynı | boyutun %90'ı `models` listeleri |
| `experiments/log.jsonl` | 1 / 2,1 | 2 146 backtest koşusu: model_id, spec/veri/ledger sha, metrikler, zaman | hayır (yalnız metrik ve hash) | — |
| `registry/records/`, `registry/oot/records/`, `registry/post_break/`, `registry/oot/post_d1/`, `registry/legacy_frozen/` | 419 / 21,2 | dondurulmuş tahmin kayıtları: girdiler (KAP), model çıktıları, karşılaştırıcılar, zaman | `post_d1`/`post_break`/`d1_rows` D1 bülten alanlarını (kapanış, limit) taşır | şema (`models[]`, `inputs`, `comparators`) |
| `registry/inputs/`, `registry/oot/inputs/`, `registry/oot/candidate_features*` | 413 / 6,1 | KAP/SPK belgelerinden alan değerleri, **alıntılar**, şirket adı, belge URL/sha | KAP belge metni alıntıları (`quote`); bülten yok | 116 dosyada "Yönetim Kurulu" geçer |
| `registry/push_proofs/*.json` (31) | 31 / 0,07 | GitHub status API yanıtı | — | `creator` bloğu: `login`, `avatar_url`, `html_url`, … (§4.2) |
| `tests/reference/**` | 75 / 13,4 | fold ledger'ları, benchmark çıktıları, SHA256SUMS | H99 R değerleri (türev) | 13 test dosyası okur |
| `legacy/**` | 34 / 0,9 | eski repodan birebir kod ve 2 şartname belgesi | — | `borsai/` import etmez (yalnız yorumda anılır); `tests/test_port_vs_legacy.py` (17 test), `test_pb.py` (10), `test_market20.py` (12), `test_guardrails.py` (3) import eder ya da sha'sını pinler |

[ÇIKARIM] BIST'in lisans koşullarının bu "tek satırın birkaç hücresi" türevini kapsayıp kapsamadığını ölçemem; metin okunmadı (ağ yok). Okunması gereken yerler soru 1'de.

### 2.3 Belge ve görsel kaynakları [ÖLÇTÜM]

- `docs/` 839 dosya / 40,5 MB: 207 md, 131 png (13'ü `docs/design/ui_v2/png`), 12 tasarım panosu `.dc.html` (Claude Design kanvasından; `docs/design/ui_v2/README.md`), 5 SPK xlsx (`docs/specs_faz6/ekler/spk_tablolar/`, resmi belge, KARAR), 177 doğrulama aracı dosyası (`docs/faz6/dogrulama/_tools/`; 11 günlük KARAR: `spk_rows.json` 135 SPK bülten satır metni + şirket adresi, `requests.jsonl` 0,6 MB istek günlüğü), geri kalanı denetim ekleri (py, json, txt, csv).
- `app/docs/` 67 png ekran görüntüsü (19,0 MB): gerçek arz kodları ve değerleri görünür (canlı 7 arz); kasa kodu içeren görüntü ölçülmedi (görsel).
- `app/src-tauri/icons/` 16 dosya: Aşama 0 iskelet commit'inde geldi (`50c62da`); kaynağı repoda yazılı değil. `node_modules` içinde karşılaştırılacak şablon ikon bulunamadı. Owner: belirsiz (soru 11).
- Yazı tipleri: IBM Plex (OFL-1.1) `@fontsource/*` devDependency; repoda font dosyası yok (Vite pakete gömer).

## 3. Bağımlılık haritası (adım 2)

### 3.1 Çalışma anı [ÖLÇTÜM]

`grep` kalıpları: `data/raw/bist`, `source_docs`, `.zip`/`zipfile`, `outcomes_oot/raw`.

| Katman | Dosya | Ne yapıyor | Aynada |
|---|---|---|---|
| `app/src-tauri/crates/borsai_predict/src/**`, `app/src/**` | 0 gerçek vuruş (Rust `.zip()` yineleyici yanlış pozitifleri hariç) | — | kişisel mod etkilenmez |
| `app/src-tauri/src/commands/source_docs.rs`, `inputs_doc.rs`, `freeze.rs`, `lib.rs`, `app/src/api.ts` | 5 | repo modunda dondurma sihirbazı: `registry/source_docs/<T>/` altına PDF kopyalar, `MANIFEST.json` okur/yazar | repo modunda çalışır (dizin yoksa oluşturur); okunacak eski manifest yoksa `read_source_manifest` boş döner — ölçülmedi, [ÇIKARIM] |
| `borsai/outcomes.py`, `outcomes_oot.py` | 2 | bülten indirir, `data/raw/bist/**.zip` yazar/okur, `MANIFEST*.csv` | aynada koşmaz (zip yok) |
| `borsai/scoring.py` | 1 | skorlama: sonuç alma commit'i için `data/raw/bist/` git geçmişi, bülten adı kalıbı | aynada koşmaz |
| `borsai/registry.py` | 1 | kayıt denetimi: `MANIFEST.csv` ve bülten dosya adı eşleşmesi; `registry/oot/source_docs` yolu | aynada koşmaz |
| `borsai/freeze.py` | 1 | PIT belge denetimi: girdi belgesinin `registry/source_docs/<T>/…pdf` dosyası var mı | **dondurma aynada koşmaz** (belge yok → `FreezeError`) |

Sonuç: uygulamanın kişisel modu için cevap **hayır** (dokunmuyor). Repo modu ve Python akışları (sonuç, skor, dondurma, sicil denetimi) GİRMEZ dosyaları ister.

### 3.2 Testler: klon deneyi [ÖLÇTÜM]

Klon `/tmp/borsai_mirror_probe_20261013/clone` (`git clone --local`, HEAD `e5a4d0f`; `.venv` ve `app/node_modules` sembolik bağ, `.git/info/exclude`'da). Dört GİRMEZ yolu `git rm` + commit ile silindi (2 852 dosya kaldı, ağaç temiz). Sonda klon ve derleme dizini silindi.

| Takım | Komut | Tam repo | Klon (GİRMEZ yok) |
|---|---|---|---|
| pytest toplama | `pytest --collect-only -q -p no:cacheprovider tests app/parity` | 960 test | 955 test + 1 toplama hatası (`tests/test_registry_ipos.py`: `registry/source_docs/_ENUMERATION/ENUMERATION.json` import anında okunur) |
| pytest koşu | `pytest -q -p no:cacheprovider -n 6 --dist loadgroup -rfEs tests app/parity` | (yeşil, `docs/app/windows_test_runs`: 952) | **79 failed, 866 passed, 16 errors**, 9 dk 51 s |
| cargo | test.sh seçimi: `BORSAI_REPO=<klon> cargo test --workspace --no-fail-fast -- --include-ignored --exact --skip …` (5 geçici-klon e2e'si atlandı) | 167 (yeşil) | **165 passed, 2 failed** (`stage3.rs`: `inputs_doc_bytes_roundtrip`, `inputs_doc_bytes_match_python`; ikisi de `registry/source_docs/NETGL/MANIFEST.json` → `NotFound`) |
| vitest | `npm test` | 377 | 377/377 yeşil |
| parite | `pytest app/parity/test_gen_golden.py` | 8 | 8/8 yeşil |
| altın değişmezlik | `bash app/tests/golden_unchanged.sh` | yeşil | yeşil |

Kırmızı pytest'lerin dağılımı (dosya: sayı): `test_registry_inputs.py` 15, `test_freeze_records.py` 14, `test_outcome_guard.py` 7, `test_faz5_live.py` 7 + 7 hata, `test_registry_ipos.py` 6 hata, `test_outcomes.py` 5, `test_faz7_freeze.py` 5, `test_faz8_live.py` 4 + 3 hata, `test_faz7_prospectus.py` 4, `test_scoring.py` 3, `test_faz7c_freeze.py` 3, `test_faz6_oot.py` 3, `test_scoring_conditional.py` 2, ve birer: `test_faz8_frozen`, `test_faz7c_frozen`, `test_faz7_vault`, `test_faz7_table_v2`, `test_faz7_frozen`, `test_faz5_post_d1`, `test_faz4_ceiling_path`. Tam liste (test kimliği + neden sınıfı, kasa kodları maskeli): `ekler/kirmizi_testler.txt`.

Neden sınıfları (93 hata bloğu): doğrudan `registry/source_docs` 47, `data/raw/bist` 14, `registry/oot/source_docs` 5, `source_docs_faz7` 3; yolun adı geçmeyen 24 (kaydı yeniden dondurup karşılaştıran, skoru yeniden hesaplayan, manifest satırlarını dosyalarla eşleyen testler). İstisna türleri: `FreezeError` 21 ("girdi belgesi geçmedi: … belge dosyası yok"), `FileNotFoundError` 18, `AssertionError` 25 (çoğu PIT denetiminin boş olmayan hata listesi), `KeyError` 5 (manifestte tarih/tür anahtarı yok), `TypeError` 3, `DataIntegrityError` 1, `AttributeError` 1.

[ÇIKARIM] 24 dolaylı kırmızının hepsi aynı iki kökten gelir (belge PIT denetimi ve bülten manifesti); GİRMEZ dışı başka bir eksik yoktur, çünkü klonda GİRMEZ dışında hiçbir şey silinmedi.

Cevap: aynada **"tam test takımı koşar" denemez**; "95 pytest + 2 cargo testi ham veri/resmi belge ister ve aynada atlanır ya da işaretlenir" denir. `registry/source_docs/*/MANIFEST.json`, `_ENUMERATION/ENUMERATION.json` ve `data/raw/bist/MANIFEST*.csv` aynaya girerse (soru 7) kırmızı sayısı düşer; kaç test yeşile döner ölçülmedi (yalnız manifest adı geçen 13 pytest + 2 cargo bloğu için beklenir) — [ÇIKARIM].

### 3.3 Aynada CI [ÖLÇTÜM]

`build.yml`: `workflow_dispatch` ve `v*` etiketi; `test-windows` işi `cargo test --workspace --no-fail-fast` (ignore'lar **dahil değil**) + `npm test`; sonra `build-windows`/`build-macos` `npm run tauri build`. Secret kullanmaz, release oluşturmaz. GİRMEZ'e bağlı adım:
- `inputs_doc_bytes_roundtrip` (`stage3.rs:128`, ignore değil) `pretty_written_files()` ile `registry/source_docs/NETGL/MANIFEST.json` okur → aynada **1 kırmızı test, iş kırmızı**, paket adımı çalışmaz (`needs: test-windows`). `build-macos` bağımsızdır, yine koşar.
- `inputs_doc_bytes_match_python` `#[ignore]` (BORSAI_REPO ister); CI'da koşmaz.
- `sade.rs`, `oot_panel.rs`, `stage4.rs` gerçek repo dosyalarını (`scores/`, `registry/records`, `registry/oot/records`, `data/outcomes`) okur: bunlar KARAR dosyalarıdır; **KARAR dışlanırsa bu testler de kırmızı olur** (ölçülmedi, [ÇIKARIM]; klon deneyinde KARAR dosyaları yerindeydi ve yeşildi).
- `build.rs` `models/INDEX.json` ve `scores/scores.json`'ı gömer: `scores.json` aynada yoksa derleme "skor dosyası yok" dalına düşer (`app/README.md`: "varsa gömülür"); ölçülmedi.

## 4. Hassas içerik (adım 3)

### 4.1 Sırlar [ÖLÇTÜM]

- Çalışma ağacı (izlenen 3 761 dosyadan ikili olmayan hepsi): AWS, GitHub (`gh?_`, `github_pat_`), OpenAI/Anthropic (`sk-…`), Slack, Google API, JWT, `BEGIN … PRIVATE KEY`, `api_key|secret|token|password = "…"` kalıpları: **0** vuruş.
- Git geçmişi: 187 commit'in her ağacında `git grep` ile aynı kalıplar: **0**. Geçmişte eklenmiş `.env`, `.pem`, `.key`, `credentials`, `id_rsa`, `token` adlı dosya: **0**. Geçmişte silinmiş dosya yalnız 3 (`app/.gitkeep`, bir ekran görüntüsü, bir fixture).
- Betik: `ekler/`'e konmadı (yalnız sayı istenmişti); kalıplar yukarıda yazılı.

### 4.2 Kişisel veri [ÖLÇTÜM]

- E-posta kalıbı: dosya içinde kişisel adres **0**. Vuruşların hepsi model dosya adları (`…@inf.json`, `…@zero.json`, `128x128@2x.png`) ve bir `git@github.com` metni (`tests/`).
- Telefon (TR mobil) kalıbı 5 794 vuruş / TC kimlik (sağlama geçerli 11 hane) 107 vuruş: bağlam sınıflaması — TC vuruşlarının 72'si ondalık kesir içinde, 35'i `ipo_size_tl`/pay adedi gibi JSON sayı alanı; telefon vuruşlarının 4 969'u daha uzun sayı ya da ondalık içinde, 825'i `ipo_size_tl` gibi alanlar. **Kişisel veri olarak 0** [ÇIKARIM: örneklenen bağlamların hepsi finansal büyüklük].
- Adres anahtar kelimeleri (mahalle, sokak, cadde, no:): 9 dosya / 303 vuruş; 294'ü `docs/faz6/dogrulama/_tools/logs/spk_rows.json` (SPK bülteninden şirket adresleri: tüzel kişi, kamuya açık), kalanı belge metni.
- Git yazarı: 187 commit'in `author` ve `committer` alanı aynı kişi, kişisel Gmail adresi. Ayna tek commit'le kurulursa ayna geçmişinde yalnız o commit'in yazarı görünür; `filter-repo` ile süzülürse 187 commit'in e-postası aynaya taşınır (`--mailmap` ile değiştirilebilir). Soru 5.
- `registry/push_proofs/*.json` (31): GitHub status API yanıtının tamamı: `creator.login`, `avatar_url`, `html_url`, `followers_url` vb. (kamuya açık GitHub profili) ve `repo_slug`. Soru 5.

### 4.3 Üçüncü şahıslar [ÖLÇTÜM]

- Şirket adları (`company`/`company_name` alanı): `registry/oot/records` 270, `oot/inputs` 135, `oot/candidate_features` 135, `oot/candidate_features_faz7` 135, `oot/source_docs_faz7` 135 (GİRMEZ), `registry/legacy_frozen` 16, `app/tests/fixtures` 11, `docs/specs_faz6/ekler` 2; `registry/ipos.csv`, `registry/oot/cohort_pre_h99.csv`, `…_pretrade_master.csv`, `PREBOOKBUILD…csv`, `data/outcomes/COMPLETENESS.csv` (6 413 pay kodu + ad).
- Kişi adları (yönetim kurulu vb.): "Yönetim Kurulu" ifadesi `registry/oot/candidate_features_faz7` 116 dosyada (KAP alıntıları), `oot/source_docs_faz7` 3, `docs/specs_faz6/ekler` 2, `docs/faz8/BANT_DOGRULAMA.md` 1. Aracı kurum adları `lead_broker` sütununda (99 satır). Hepsi KAP/SPK'da yayımlanmış kamuya açık bilgidir; yine de ayna için soru 9.

### 4.4 Kasa kodları [ÖLÇTÜM]

- `registry/oot/cohort_pre_h99.csv`: 136 satır; `vault` = SEALED 64, OPEN 66, EXPOSED_ARCHIVE 4, EXPOSED_CODEX 1, boş 1. Kodlar yalnız bellekte tutuldu.
- İçinde kasa kodu geçen metin dosyası: GİRMEZ dışı **646** (KARAR 532, GİRER 114). GİRER 114'ün dağılımı: `docs/faz6` 74, `docs/faz7` 12, `docs/specs_faz6` 9, `docs/prompts` 8, `docs/fable_faz6_audit` 7, `docs/PROVENANCE.md`, `docs/SCORES.md`, `docs/fable_faz7_vault` ve `tests/test_outcome_guard.py` birer. GİRMEZ dizinlerinde 135 dosya daha.
- **Yolunda** kasa kodu geçen dosya: 1 015 (`registry/oot/source_docs` 311, `registry/oot/records` 128, `data/outcomes_oot` ve `raw/` 128, `docs/faz6/dogrulama` 64, `oot/inputs`, `candidate_features*`, `d1_rows`, `post_d1`, `source_docs_faz7` 64'er). Bu yüzden `ekler/envanter.csv`'de yol sütunu maskelidir (`<KASA>`); dosya sayısı korunur.
- Kasa 2026-09-25'te açıldı ve skorlandı (`VAULT_OPEN.json`, HANDOFF); gizlilik tarihseldir. Soru 6.

### 4.5 Yazılım lisansları [ÖLÇTÜM]

Araç: `license-checker` ve `cargo-license` yok; npm için `node_modules/*/package.json` `license` alanı, cargo için `cargo metadata --offline --locked` `license` alanı, Python için `.venv` `METADATA`.

| Ekosistem | Kapsam | Dağılım | Copyleft |
|---|---|---|---|
| npm (`app/package.json`) | kurulu ağaç 82 paket | MIT 58, Apache-2.0 4, Apache-2.0 OR MIT 3 (+1 MIT OR Apache-2.0), ISC 3, OFL-1.1 3 (IBM Plex), MPL-2.0 2, BSD-2 2, BSD-3 2, MIT-0 2, BlueOak-1.0.0 1, CC0-1.0 1 | GPL/AGPL/LGPL **0**; MPL-2.0 2 (zayıf copyleft, dosya düzeyi) |
| cargo (`Cargo.lock`) | tüm platformlar 445 paket; macOS çözümü 258 | MIT/Apache ikili lisans ~370, MIT 100, Unicode-3.0 18, Zlib-içeren 20, Unlicense OR MIT 11, BSD-3 2–5, Apache-2.0 2, ISC 1, CC0/MIT-0 1; `unicode-ident` "(MIT OR Apache-2.0) AND Unicode-3.0" | GPL/AGPL **0**; **MPL-2.0 5** (macOS'ta da): `cssparser` 0.36.0, `cssparser-macros` 0.6.1, `dtoa-short` 0.3.5, `option-ext` 0.2.0, `selectors` 0.36.1 (Tauri/wry zinciri); `r-efi` 5.3.0/6.0.0 "MIT OR Apache-2.0 OR LGPL-2.1-or-later" (seçimli; yalnız UEFI hedefinde) |
| Python (`requirements.lock`, 13 + pip) | 14 paket | MIT 7, BSD-3 3 (joblib, scikit-learn, threadpoolctl), numpy çoklu izinli, packaging Apache-2.0 OR BSD-2, Pygments BSD-2, scipy BSD (METADATA metin) | **0** |

[ÇIKARIM] MPL-2.0 bağımlılıkları değiştirilmemiş kütüphane olarak kullanıldığında yalnız o dosyaların kaynağının erişilebilir kalmasını ister; proje kodunun lisansını belirlemez. Dağıtılan paket için üçüncü taraf lisans bildirimi (`THIRD_PARTY_LICENSES`) üretmek ayrı bir iştir; Tauri paketi bunu otomatik üretmez (ölçülmedi).

Tasarım varlıkları: yazı tipleri OFL-1.1 (`docs/app/UI_V2_RAPOR.md` K-UI-9); tasarım panoları ve png'ler proje sahibinin onayladığı Claude Design çıktısı (`docs/design/ui_v2/README.md`); ikonlar belirsiz (soru 11).

## 5. Lisans ve beyan önerisi (adım 4; hepsi [ÇIKARIM], karar proje sahibinin)

### 5.1 Kod lisansı adayları

| Lisans | Projeye etkisi |
|---|---|
| **MIT** | En kısa; atıf + lisans metni korunur. Patent hükmü yok; Rust/npm zincirinin çoğunluğuyla (MIT OR Apache-2.0) uyumlu. |
| **Apache-2.0** | Açık patent lisansı ve katkı hükümleri; `NOTICE` dosyasıyla veri beyanını taşımaya uygun. MPL-2.0 ve MIT bağımlılıklarla uyumlu. Türev çalışmalarda değişiklik bildirimi ister. |
| **BSD-3-Clause** | MIT gibi izinli; ek olarak proje/yazar adının tanıtımda izinsiz kullanımını yasaklar. Patent hükmü yok. |

Öneri: Apache-2.0 (patent + NOTICE) ya da MIT (sadelik). Lisans metni web'den alınmalı (ağ yok; `choosealicense.com` veya `opensource.org/licenses`). `LICENSE` köke; `app/` ayrı paketlenirse `app/LICENSE` kopyası. İkisi de "kod" içindir; veriye uygulanmaz.

### 5.2 Veri beyanı (ayrı dosya: `DATA_LICENSE.md` ya da README bölümü)

Model JSON'ları, skorlar, türev CSV/JSON'lar için önerilen cümle (taslak, hukuki metin değil):

> Bu depodaki model parametreleri, skor dosyaları ve türetilmiş tablolar Borsa İstanbul Pay Piyasası günlük bültenlerinden (THB/THM), KAP bildirimlerinden, SPK bültenlerinden ve TÜİK TÜFE serisinden türetilmiştir. Ham bültenler, KAP/SPK belgeleri ve bülten zip dosyaları bu depoda **yoktur**; her türev dosya kaynak URL kalıbını ve sha256'sını taşır. Kaynak verinin yeniden dağıtım koşulları ilgili kurumun koşullarına tabidir; bu depo o verileri yeniden yayımlama amacı taşımaz, yalnız kendi hesaplamalarının izlenebilirliği için gerekli alanları kaydeder.

README paragrafı (taslak): "Ham bültenler ve resmi belgeler bu repoda yoktur. Yeniden üretim için kaynak URL kalıpları `docs/DATA.md` ve `docs/PROVENANCE.md`'de: bültenler `https://www.borsaistanbul.com/data/{thb,thm}/YYYY/MM/…zip`, KAP `https://www.kap.org.tr/tr/Bildirim/<id>` ve `/tr/api/BildirimPdf/<id>`, TÜİK `https://veriportali.tuik.gov.tr/…`; her dosyanın sha256'sı `data/raw/bist/MANIFEST*.csv` ve `registry/**/MANIFEST.json`'dadır."

Okunması gereken lisans metinleri (ağ gerekir; indirme değil, okuma): Borsa İstanbul veri yayın/kullanım koşulları (bülten sayfalarının "yasal uyarı"/"veri yayın" bölümü ve `datastore.borsaistanbul.com` koşulları; özellikle "yeniden dağıtım", "türev veri", "gerçek zamanlı olmayan/gecikmeli veri" maddeleri), KAP kullanım koşulları/yasal uyarı (`kap.org.tr`), SPK sitesi yasal uyarı, TÜİK veri kullanım koşulları (`data.tuik.gov.tr`; genelde kaynak göstererek kullanım serbesttir — doğrulanmadı).

### 5.3 Uyarı metni

Mevcut: README "yatırım tavsiyesi ya da al-sat sinyali değildir"; uygulamada `disclaimer.test.ts` ile zorlanan metin. SPEC_APP §8.1 (açık konu) "ücretli ürün … yatırım danışmanlığı düzenlemelerine dokunabilir; tek satırlık yer tutucu hukuki metin değildir; dağıtım kararı öncesi hukuki görüş alınır" der. Araştırma raporunun hukuk atıfları dağıtım esaslarına ilişkindir, yatırım danışmanlığına değil. [ÇIKARIM] Ek bir cümle gerekirse adayı: "Bu yazılım ve içerdiği istatistikler SPK mevzuatı kapsamında yatırım danışmanlığı faaliyeti değildir; herhangi bir sermaye piyasası aracının alım-satımına yönelik kişiye özel öneri içermez; geçmiş performans geleceğin göstergesi değildir." Gerekliliğine hüküm vermiyorum; SPEC_APP §8.1'in "hukuki görüş" notu geçerlidir (soru 15).

## 6. Ayna kurulum planı (adım 5; öneri)

### 6.1 Yol listesi

`MIRROR_MANIFEST.txt`: GİRER / GİRMEZ / KARAR glob'ları, dosya sayısı, MB ve gerekçe (soru numarasıyla). Ayna görevi (Opus) bu dosyadan ve proje sahibinin soru cevaplarından yürür.

### 6.2 Geçmiş: tek commit mi, süzülmüş mü [ÖLÇTÜM + ÇIKARIM]

| | Tek commit'lik yeni geçmiş | `git filter-repo` ile süzülmüş geçmiş |
|---|---|---|
| Ne taşır | HEAD ağacının GİRER (+ seçilen KARAR) kısmı | 187 commit; GİRMEZ yollar her ağaçtan çıkarılır; 10 commit (hiçbiri yalnız GİRMEZ içermez) ve onlardan sonraki her commit yeni sha alır |
| Zaman kanıtı | aynada **yok**; README'de özel repo sha'larına ve push kanıtı dosyalarına (`registry/push_proofs/<sha>.json`, GitHub status API) atıf. Kanıt özel repoda kalır; dışarıdan doğrulanamaz. | aynada commit zamanları var ama sha'lar değişmiş; push kanıtları eski sha'ya işaret eder, aynadaki commit'le eşleşmez. Zaman kanıtı yine özel repodadır. |
| Yazar e-postası | yalnız yeni commit'in yazarı (seçilebilir, ör. GitHub `noreply`) | 187 commit'in e-postası (mailmap ile değiştirilebilir) |
| KARAR dosyalarının geçmişi | yok | kalır (ör. eski `scores.json` sürümleri; kasa kodlu eski yollar) |
| Sızıntı riski | düşük (yalnız HEAD içeriği denetlenir) | her commit'in ağacı denetlenmeli; GİRMEZ dışı ama şimdi silinmiş içerik (3 silinmiş dosya) da taşınır |
| Güncelleme | her kilometre taşında yeni "snapshot" commit'i; mesajda özel repo sha'sı | her seferde yeniden süzme ve force-push ya da artımlı filter |
| Boyut | ~66–224 MB ağaç; paket küçük | paket ≤ 231 MiB − GİRMEZ blob'ları (yaklaşık 225 MB çıkar) ≈ az; ölçülmedi |

Öneri: **tek commit'lik yeni geçmiş**, her snapshot commit'inin mesajında `kaynak: AhmetEmreOzumagi/borsai@<sha>` ve README'de "zaman kanıtı özel repodaki push kanıtlarındadır; sha'lar `registry/push_proofs/`'ta listelenir" cümlesi. Gerekçe: CLAUDE.md kural 1 zaman kanıtını push'a bağlar; ayna bu kanıtı üretmez, yalnız atıf yapar; süzülmüş geçmiş sha'ları değiştirerek atıfları kırar. Karar proje sahibinin (soru 13).

### 6.3 Güncel tutma (yalnız seçenekler)

- **Elle, kilometre taşında:** proje sahibi `MIRROR_MANIFEST.txt`'e göre dışa aktarır (ör. `git archive` + rsync + `git commit`), snapshot mesajında özel sha. Kontrol: dışa aktarılan ağaçta GİRMEZ glob'u 0 dosya, hijyen taraması 0.
- **CI ile (özel repoda workflow):** her push'ta ya da etiket'te aynı dışa aktarma; ayna reposuna yazma yetkisi olan bir token gerekir (bugün `build.yml` secret kullanmıyor; CLAUDE.md "push yalnız proje sahibi" kuralıyla çelişir, çünkü robot push eder). 
- **Karma:** CI yalnız ayna ağacını artefakt olarak üretir ve denetler (GİRMEZ 0, hijyen 0); push'u proje sahibi yapar.

### 6.4 Aynada CI

`build.yml` olduğu gibi kopyalanırsa: `inputs_doc_bytes_roundtrip` kırmızı (§3.3) → `test-windows` kırmızı → Windows paketi üretilmez; `build-macos` yine üretir. Çözümler (seçenek): (a) `registry/source_docs/*/MANIFEST.json`'ı aynaya almak (soru 7); (b) testi `BORSAI_REPO` ister biçimde `#[ignore]`'a çevirmek (kod değişikliği; bu görevin dışında, yeni commit); (c) aynada CI'ı yalnız `build` işleriyle sınırlamak. KARAR dosyaları (özellikle `scores/`, `registry/records`, `registry/oot/records`, `data/outcomes`) dışlanırsa `sade.rs`, `oot_panel.rs`, `stage4.rs` ve gömme adımı etkilenir (§3.3).

### 6.5 Boyut [ÖLÇTÜM]

- GİRER toplamı 66,3 MB (1 340 dosya); en büyük GİRER dosyaları `docs/faz6/dogrulama/verification_log.jsonl` 2,8 MB ve `docs/fable_faz7_vault/BAGIMSIZ.json` 1,6 MB; en büyük png 0,7 MB (`app/docs/` kümesi 67 dosya / 19,0 MB).
- GİRER + bütün KARAR: 2 852 dosya, 223,8 MB. 100 MB üstü tek dosya **yok**. 50 MB üstü **yok**; en büyükler: `scores/scores_oot.json` 41,3 MB, 8 altın `.jsonl` 3,4–4,4 MB, `field_provenance.csv` 4,4 MB, `verification_log.jsonl` 2,8 MB.
- `scores_oot.json` notu: 41 MB JSON, GitHub web görüntüleyicisinde açılmaz, diff'lenemez; her yeniden üretim ~41 MB yeni blob ekler. Seçenekler: olduğu gibi (sınırların altında), Git LFS, ya da aynada yalnız `docs/SCORES.md` + sha. Boyutun %90'ı 135 arz × 13–14 modelin hücre listeleridir (§2.2).

## 7. Proje sahibine sorular

1. **Türev veri (BIST):** `data/raw/*.csv`, `data/outcomes*/`, `data/outcomes_oot/raw/*.json`, `scores/*.json`, `app/parity/golden/`, `tests/reference/`, `data/training_table*.csv`, `experiments/log.jsonl`, XU100 JSON'ları aynaya girsin mi? Ölçüm: bülten hücreleri aynen taşınıyor ama yalnız arzın kendi satırı (bir günün ~12 000 satırından 1'i, 57 sütundan 11–14'ü). Borsa İstanbul veri koşullarının bunu kapsayıp kapsamadığı okunmalı (§5.2'deki sayfalar). Girmezse: pytest'te ek kırmızılar (ölçülmedi), `sade.rs`/`oot_panel.rs`/`stage4.rs` kırmızı, `scores.json` gömülemez.
2. **Resmi belge ama PDF değil:** `docs/specs_faz6/ekler/spk_tablolar/*.xlsx` (5 SPK tablosu), `data/raw/tuik/*.xls` + `.source.json` (TÜİK) aynaya girsin mi? Karar "KAP/SPK PDF'leri girmez" diyor; bunlar PDF değil.
3. **Skorlar:** karar "skorlar girer" diyor; ölçüm skorların arz başına gerçekleşen kapanış/getiri/tavan etiketi taşıdığını gösteriyor (soru 1 ile aynı veri). Uygulamanın gömülü `scores.json`'u zaten deneme grubuna dağıtılacak. Ayna için aynı karar mı?
4. **Sicil:** `registry/records`, `registry/oot/records` (270 dosya, 17 MB), `registry/oot/{inputs,candidate_features*,post_d1,d1_rows}`, `registry/post_break`, `registry/legacy_frozen`, `registry/ipos.csv` aynaya girsin mi? Kural 1'in "dondurulmuş kayıt silinmez" ilkesi aynada da "silinmez" demek midir, yoksa ayna yalnız özel repoya atıf mı yapar?
5. **Commit yazarı ve GitHub kimliği:** aynanın commit yazarı hangi ad/e-posta olacak (kişisel Gmail mi, GitHub `noreply` mi)? `registry/push_proofs/*.json` GitHub kullanıcı adı ve profil URL'lerini içeriyor: olduğu gibi mi, `creator` bloğu kırpılmış mı, yoksa girmez mi?
6. **Kasa kodlu dosyalar:** içinde kasa kodu geçen 646 (+ yolunda 1 015) GİRMEZ dışı dosya aynaya olduğu gibi mi? Kasa harcandı; ama ORTAK hijyen kuralı rapor düzeyinde sürüyor. Aynada bu kural kalkar mı?
7. **GİRMEZ dizinlerindeki manifestler:** `registry/source_docs/*/MANIFEST.json` (7), `_ENUMERATION/ENUMERATION.json`, `registry/oot/source_docs/*/MANIFEST.json` (135), `registry/oot/source_docs_faz7/*.json` (135), `data/raw/bist/MANIFEST.csv` ve `MANIFEST_OOT.csv` PDF/zip içermez (URL, sha256, bayt, tarih). Girerse `inputs_doc_bytes_roundtrip` (CI) ve `test_registry_ipos.py` toplama hatası dahil en az 13 pytest yeşile döner. Girsin mi?
8. **Doğrulama günlükleri:** `docs/faz6/dogrulama/_tools/logs/` (11 dosya, 1,4 MB) SPK bülten tablo satır metinleri ve şirket adresleri içerir. Girsin mi, yoksa `docs/faz6/dogrulama/REPORT.md` yeter mi?
9. **Üçüncü şahıs adları:** şirket adları (yüzlerce dosya), yönetim kurulu adları (116 KAP alıntısı dosyası), aracı kurum adları kamuya açık belgelerden; aynada aynen mi?
10. **`legacy/`:** `borsai/` import etmiyor; 4 test dosyası (42 test) import ediyor ya da sha pinliyor. Girsin mi (eski reponun kodu, aynı sahip), yoksa o testler aynada atlansın mı?
11. **İkonlar:** `app/src-tauri/icons/` 16 dosyanın kaynağı (Tauri şablonu mu, özel çizim mi) nedir? Şablonsa Tauri'nin lisansı (MIT/Apache) geçerli; özel çizimse kod lisansı kapsar.
12. **Kod lisansı:** MIT, Apache-2.0 ya da BSD-3 (§5.1)? `LICENSE` köke; `app/` için kopya gerekli mi?
13. **Ayna geçmişi:** tek commit'lik yeni geçmiş mi (önerim), `filter-repo` ile süzülmüş geçmiş mi (§6.2)?
14. **Güncelleme biçimi:** elle kilometre taşında mı, CI ile mi, karma mı (§6.3)?
15. **SPK ek cümlesi:** mevcut "yatırım tavsiyesi değildir" cümlesine §5.3'teki aday eklensin mi; hukuki görüş alınacak mı (SPEC_APP §8.1)?

## 8. Koruma ve hijyen sayımları

- Koruma: `ekler/koruma_once.txt` ve `ekler/koruma_sonra.txt`: dokuz ağaç sha'sı iki ölçümde aynı; korunan yollarda `git status --porcelain --untracked-files=all` iki ölçümde boş (`ekler/hijyen.py` karşılaştırır).
- Hijyen (`ekler/hijyen.py`, `docs/public_mirror/**`): kasa kodu geçişi **0**; `th[bm]` + 8 hane bülten adı **0**. Envanter CSV'sinde yollar maskeli (`<KASA>`, `YYYYMMDD`); satır sayısı 3 761.
- Geçici klon `/tmp/borsai_mirror_probe_20261013/` (klon + cargo hedef dizini) silindi.
- Yazılan yerler: yalnız `docs/public_mirror/` ve bu görev dosyası. Push, tag, amend yok.

## 9. Bakılmayanlar

- Lisans metinleri (BIST, KAP, SPK, TÜİK): ağ yok; yalnız okunacak yerler yazıldı.
- KARAR dosyaları da silinmiş bir klonla test koşusu (yalnız GİRMEZ silindi).
- PDF ve zip içerikleri (yalnız zip başlık/sütun adları ve satır sayısı ölçüldü; PDF hiç açılmadı).
- `app/docs/*.png` ekran görüntülerinde hangi kodların göründüğü (görsel).
- Tauri paketinin üçüncü taraf lisans bildirimi üretip üretmediği; MPL-2.0 kaynak erişim yükümlülüğünün paket düzeyinde nasıl karşılanacağı.
- `filter-repo` sonrası paket boyutu (hesaplanmadı).

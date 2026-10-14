# FAZ9_PUBLIC_INVENTORY — Herkese açık ayna repo için envanter ve öneri (yalnız okuma)

**Model: Claude Code / Fable · yüksek**

- **TASK_ID:** `BORSAI_FAZ9_PUBLIC_INVENTORY_20261013`
- **Klasör:** repo kökü `~/Desktop/BorsAi`
- **Ağ:** yok. (Lisans metinleri için web gerekiyorsa sorular bölümüne yaz; indirme yok.)
- **Commit konusu:** `BORSAI_FAZ9_PUBLIC_INVENTORY: …` (tek commit; yalnız bu görev dosyası ve `docs/public_mirror/`).
- **Yazan el ≠ denetleyen el:** bu görev yalnız ölçer ve önerir. Aynayı kuracak görev ayrıdır (Opus) ve bu raporu girdi alır.

## Rol

Proje sahibi, BorsAi'yi kapalı deneme grubuna verecek ve GitHub'da herkese açık bir repo göstermek istiyor. Bugünkü repo (`AhmetEmreOzumagi/borsai`) özeldir ve **özel kalacaktır**: git geçmişi push kanıtlarının ve zaman damgalarının taşıyıcısıdır, yeniden yazılamaz. Karar (13 Ekim): **kod + belgeler + modeller + skorlar için ayrı bir herkese açık ayna repo** kurulacak; ham BIST bültenleri ve KAP/SPK PDF'leri aynaya girmeyecek. Senin işin, bu kararı uygulanabilir ve dürüst kılacak envanteri çıkarmak: repoda ne var, kime ait, aynaya ne girer, ne giremez, girenlerle testler ve belgeler tutarlı kalır mı, hangi lisans ve hangi açıklama gerekir.

Hiçbir dosyayı değiştirme, taşıma ya da silme. Yalnız oku ve `docs/public_mirror/` altına yaz.

## Orkestratörün ölçtükleri (2026-10-13, HEAD = origin/main = `e5a4d0f`, ağaç temiz; izlenmeyen yalnız iki bekleyen görev dosyası)

- İzlenen dosya **3 761**, toplam **449,5 MB**; `.git` 236 MB; 187 commit.
- Üst dizine göre: `registry` 1 865 dosya / 237,8 MB; `app` 418 / 83,0; `scores` 4 / 42,7; `docs` 839 / 40,5; `data` 379 / 26,0; `tests` 140 / 14,5; `experiments` 2 / 2,1; `borsai` 39 / 1,5; `legacy` 34 / 0,9; `models` 34 / 0,5.
- **PDF:** 555 dosya, 208,3 MB; çoğu `registry/oot/source_docs/` (658 dosya, 196 MB) ve `registry/source_docs/` (41 dosya, 5 MB). KAP ve SPK belgeleri.
- **BIST bülten zip'leri:** `data/raw/bist/` 73 zip, 15,4 MB. Lisanslı veri; aynaya girmez (proje sahibi kararı).
- `scores/scores_oot.json` 41,3 MB (tek dosya). `app/parity/golden/*.jsonl` 3–4,4 MB'lık 8 dosya.
- `data/raw/*.csv`: bültenlerden türetilmiş kanonik tablolar (etiketler, seans takvimi, özellik hazırlığı). Bunların "türev veri" olarak aynaya girip giremeyeceği bu görevin ana sorularından biri.
- `LICENSE` dosyası yok (kökte ve `app/`'ta). `README.md` kökte var (FAZ9_WINDOWS ile yazıldı).
- Hızlı sır taraması (AWS/GitHub/OpenAI anahtar kalıpları, özel anahtar başlığı): 0. Kişisel e-posta geçişi (`legacy` hariç): 0. Bunlar tam tarama değildir; sen tam taramayı yap.
- Kasa: `registry/oot/cohort_pre_h99.csv`'de 64 SEALED kod. Kasa bir kez açıldı ve harcandı (HANDOFF); gizlilik tarihseldir. Yine de rapor hijyen kuralına uyar (aşağıda).

## ÖNCE OKU
- `CLAUDE.md`, `README.md`, `app/README.md`
- `docs/prompts/FAZ9_KITAP_AUDIT_ORTAK.md` (koruma, hijyen ve rapor biçimi kuralları; buradaki "yalnız okuma" ve "hijyen" kuralları aynen geçerli)
- `docs/DATA.md`, `docs/PROVENANCE.md` (veri kaynakları ve pinler)
- `docs/arastirma/TR_HALKA_ARZ_PIYASASI_20261001.md` §lisans/hukuk kısımları (BIST veri lisansı, KAP, SPK)
- `docs/fable_kitap_audit/AUDIT_1_VERI.md` §3.2 (kaynakların URL kalıpları ve koşulları)
- `.gitattributes`, `.gitignore`, `app/.gitignore`

## Adımlar

**0. Taban ve koruma.** `GIT_OPTIONAL_LOCKS=0`. HEAD `e5a4d0f`; `git status --porcelain --untracked-files=all` yalnız `docs/prompts/FAZ10_FABLE_STREAK_SPEC.md`, `docs/prompts/TUFE_2026_09.md` ve bu dosya. ORTAK.md'deki koruma ölçümünü (dokuz ağaç sha'sı) `docs/public_mirror/ekler/koruma_once.txt`'ye yaz; sonda `koruma_sonra.txt`.

**1. Dosya envanteri (ölçüm).** `git ls-files` üzerinden her izlenen dosyayı şu alanlarla sınıfla ve `ekler/envanter.csv`'ye yaz: yol, boyut, tür (kod / test / model / skor / türev veri / ham veri / resmi belge / görsel / belge / görev dosyası / kanıt / diğer), **kaynak sahibi** (proje / BIST / KAP-şirket / SPK / TÜİK / XU100 kaynağı / üçüncü taraf kütüphane / belirsiz), **aynaya önerilen durum** (GİRER / GİRMEZ / KARAR). Özet tabloyu rapora koy (tür × durum × MB).
   - `registry/oot/source_docs*`, `registry/source_docs`, `data/raw/bist`: GİRMEZ (karar verildi). Yine de sayılarını ve boyutlarını yaz.
   - `data/raw/*.csv`, `data/outcomes/*.csv`, `app/parity/golden/*`, `scores/*.json`, `experiments/log.jsonl`, `registry/oot/records`, `registry/records`, `registry/push_proofs`: her biri için "ham mı, türev mi; içinde bültenden aynen kopyalanmış satır var mı; BIST'in lisans koşulları türevi kapsar mı" sorusunu **ölçerek** cevapla (örnek: `data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv` bültenin hangi sütunlarını aynen taşıyor?). Hüküm verme; KARAR olarak işaretle ve proje sahibine soruyu yaz. Lisans metnini web'den okuman gerekiyorsa URL'yi ve okunacak maddeyi yaz, indirme.
   - `legacy/`: eski repodan gelen kod; aynaya girmesi gerekiyor mu (import ediliyor mu, test bağımlılığı var mı)?

**2. Bağımlılık haritası (ölçüm).** Ayna "GİRMEZ" dosyalar olmadan ne kadar çalışır?
   - `borsai/` ve `app/` kodu GİRMEZ dosyalara **çalışma anında** dokunuyor mu? (`grep` ile yol kalıpları: `data/raw/bist`, `source_docs`, `.zip`.) Uygulamanın kişisel modu için cevap "hayır" bekleniyor; ölç.
   - `tests/` ve `app/src-tauri/tests`, `app/tests`: GİRMEZ dosyaları okuyan testlerin listesi (dosya:test adı). Geçici klonda GİRMEZ yolları silip `pytest --collect-only` ve kısa bir koşuyla kırmızı listesini çıkar (`.venv/bin/pytest -q -n 6 --dist loadgroup -x` değil; tam liste için `-p no:cacheprovider --maxfail=0` eşdeğeri). Klon `/tmp/borsai_mirror_probe_<tarih>/`, sonunda silinir.
   - Sonuç: aynada "tam test takımı koşar" mı, yoksa "N test ham veri ister ve aynada atlanır" mı? Sayıyı yaz.

**3. Hassas içerik taraması (ölçüm).**
   - Sırlar: anahtar/belirteç kalıpları, `.env`, `*.pem`, `*.key`, `credentials`; git geçmişinde de (`git log -p -S` ya da `git rev-list --all | xargs git grep`) tara. Yalnız sayı ve dosya yolu; değer yazma.
   - Kişisel veri: e-posta, telefon, TC kimlik kalıbı, ev adresi; `docs/`, `legacy/`, `experiments/` dahil. Commit yazarı e-postası git geçmişinde olacaktır; aynada yazar bilgisinin ne olacağı proje sahibine soru.
   - Üçüncü şahıs: KAP belgelerindeki şirket adları ve kişi adları (yönetim kurulu vb.) aynaya girecek dosyalarda (CSV'ler, JSON'lar, raporlar) geçiyor mu? Kamuya açık bilgidir; yine de say ve yaz.
   - Kasa kodları: aynaya GİRER dosyalarda SEALED kodlarının geçtiği dosya sayısı (kodları yazma). Kasa harcandı; proje sahibine "aynada bu dosyalar olduğu gibi mi" sorusu.
   - Yazılım lisansları: `app/package.json`, `Cargo.lock`, `requirements.lock` bağımlılıklarının lisans dağılımı (ölçebildiğin kadar; `cargo license` / `license-checker` yoksa ad listesi ve bilinen lisans). GPL/AGPL varsa işaretle. `app/` içindeki fontlar, ikonlar, tasarım varlıkları (`docs/design/`) kime ait?

**4. Lisans ve beyan önerisi (yorum, [ÇIKARIM] işaretli).**
   - Kod için aday lisanslar (MIT / Apache-2.0 / BSD-3) ve her birinin projeye etkisi iki satırda. Karar proje sahibinin.
   - Veri için ayrı beyan gereksinimi: model JSON'ları, skorlar, türev CSV'ler için "kaynak BIST/KAP/SPK/TÜİK; yeniden dağıtım koşulları …" cümlesi. `README`'de "ham bültenler ve resmi belgeler bu repoda yoktur; yeniden üretim için kaynak URL kalıpları `docs/DATA.md`'de" paragrafı.
   - Uyarı metni: "yatırım tavsiyesi değildir" cümlesi zaten var; SPK bağlamında ek bir cümle gerekir mi (araştırma raporu §hukuk'a dayanarak, hüküm vermeden)?

**5. Ayna kurulum planı (öneri).** Opus görevine girdi olacak:
   - `docs/public_mirror/MIRROR_MANIFEST.txt`: aynaya girecek ve girmeyecek yollar (glob), gerekçe sütunuyla.
   - Aynanın **tek commit'lik yeni geçmiş** mi, yoksa `git filter-repo` ile süzülmüş geçmiş mi olacağı: ikisinin artı/eksisi (zaman kanıtı aynada yoktur; özel repodaki push kanıtlarına ve sha'lara nasıl atıf yapılır?). Öneri ver, karar proje sahibinin.
   - Aynanın güncel tutulma biçimi: elle (her kilometre taşında) mı, CI ile mi? Yalnız seçenekleri yaz.
   - Aynada CI: `build.yml` aynada da çalışır mı (GİRMEZ dosyalara bağımlı test var mı)? Ölçümden (adım 2) gelir.
   - Boyut: GİRER dosyaların toplamı; 100 MB üstü tek dosya var mı (GitHub sınırı); `scores_oot.json` 41 MB için not.

**6. Rapor ve commit.** `docs/public_mirror/INVENTORY.md`; ilk satır:
   `PUBLIC_INVENTORY: GİRER <n dosya, MB> · GİRMEZ <n, MB> · KARAR <n, MB> · ham veri isteyen test <n> · sır <n> · kişisel veri <n>`
   Bölümler: özet (proje sahibi için 8–10 madde), envanter tablosu, bağımlılık haritası, hassas içerik, lisans önerisi, ayna planı, proje sahibine sorular (numaralı), koruma ve hijyen sayımları. Betikler ve ham çıktılar `docs/public_mirror/ekler/`. Tek commit, `git add` yalnız `docs/public_mirror/` ve `docs/prompts/FAZ9_PUBLIC_INVENTORY.md`.

## Kurallar
- **Yalnız okuma.** `borsai/`, `app/`, `data/`, `models/`, `scores/`, `registry/`, `tests/`, `legacy/`, `experiments/`, `CLAUDE.md`, `README.md` değişmez. Koruma ölçümü iki kez.
- **Hijyen:** rapor ve eklerde kasa kodu 0, `th[bm]`+8 hane bülten adı 0 (ORTAK.md kuralı). Envanter CSV'sinde yol adı olarak bülten dosya adları geçecekse yalnız sayıyla özetle, tek tek listeleme (`data/raw/bist/<73 zip>` gibi).
- PDF ve zip içeriklerini raporda alıntılama; yalnız sayı, boyut ve tür.
- Push, tag, amend yok. Geçici klon silinir.
- Hüküm değil ölçüm: "girer/girmez" yalnız proje sahibinin verdiği iki karar için (ham bültenler ve resmi belgeler GİRMEZ; kod, belgeler, modeller, skorlar GİRER). Gerisi KARAR ve soru.

## Kabul kapısı
- İlk satır biçimi doğru; envanter CSV'si 3 761 satır (HEAD'deki izlenen dosya sayısı; ölç).
- Koruma sha'ları iki ölçümde aynı; `git status` korunan yollarda boş.
- Adım 2'nin kırmızı test listesi ve sayısı raporda; klon silindi.
- Hijyen 0/0.
- Sorular bölümünde en az şu beşi: türev CSV'lerin yeniden dağıtımı; kod lisansı; commit yazarı/e-posta; kasa kodlu dosyalar; ayna geçmişi (tek commit mi süzülmüş mü).

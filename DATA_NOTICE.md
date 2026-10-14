# Veri beyanı

**English summary.** The model parameters, scores, registry records and derived tables in this repository are computed from
Borsa İstanbul daily equity market bulletins (THB/THM), the XU100 index series, KAP (Public Disclosure Platform) filings, SPK
(Capital Markets Board) bulletins and the TÜİK consumer price index. Official bulletins and documents are not redistributed:
the public mirror contains no bulletin zip files and no KAP/SPK PDFs; their URLs and sha256 hashes are kept in manifest files.
Some derived files copy a few fields of an IPO's own bulletin row (e.g. closing price, upper limit) and short quotations from
KAP filings, because the forecasts and scores cannot be traced without them. The terms of use of the source institutions apply
to that content. No legal opinion has been obtained. The Apache-2.0 license (LICENSE) applies to the source code only.

## Kaynaklar ve depodaki karşılıkları

| Kaynak | Ne alınır | Depoda |
|---|---|---|
| Borsa İstanbul Pay Piyasası günlük bültenleri: THB (işlem) ve THM (fiyat limitleri), `https://www.borsaistanbul.com/data/{thb,thm}/YYYY/MM/…zip` | arzın kendi pay satırından kapanış, açılış, yüksek, düşük, hacim, işlem sayısı; referans fiyat, üst ve alt limit | arz başına tek bülten satırının 11–14 alanı ve bunlardan türetilen getiri ve tavan etiketleri: `data/raw/` kanonik tabloları, `data/outcomes/`, `data/outcomes_oot/`, `registry/oot/d1_rows/`, `scores/`. Bültenlerin kendisi yok; adresleri, bayt sayıları ve sha256'ları `data/raw/bist/MANIFEST.csv` ve `MANIFEST_OOT.csv`'de |
| Borsa İstanbul XU100 endeks grafiği (`https://www.borsaistanbul.com/graphic.php?veriTuru=endeks-graphic&indexCode=XU100`) | günlük kapanış serisi | `data/raw/*xu100*.json`, `data/raw/xu100/` |
| Borsa İstanbul tatil tabloları (PDF) | seans takvimi | PDF'ler yok; döküm `borsai/market20.py` ve takvim CSV'leri |
| KAP bildirimleri ve ekleri (`https://www.kap.org.tr/tr/Bildirim/<id>`, `https://www.kap.org.tr/tr/api/BildirimPdf/<id>`) | arz fiyatı, pay adetleri, talep katı, planlanan arz yapısı; kısa alıntılar; şirket ve aracı kurum adları | `registry/inputs/`, `registry/oot/inputs/`, `registry/oot/candidate_features*/`, `data/raw/` kohort tabloları, `app/parity/golden/`. PDF'ler yok; adresleri ve sha256'ları `registry/source_docs/*/MANIFEST.json` ve `registry/oot/source_docs*/`'deki manifestlerde |
| SPK bültenleri (`https://spk.gov.tr/data/…/<yıl-sayı>.pdf`) | onay tarihi ve planlanan arz yapısı alanları | aynı dosyalar; PDF'ler ve SPK yıllık tabloları (xlsx) yok |
| TÜİK TÜFE (2025=100), `https://veriportali.tuik.gov.tr/` | aylık endeks | `data/raw/tuik/` (TÜİK tablosunun kopyası, türetilmiş CSV ve kaynak pini) |
| GitHub status API | push kanıtı (commit'in uzak depoya ulaştığı an) | `registry/push_proofs/`: yanıtın tamamı; proje sahibinin GitHub kullanıcı adı ve profil adresleri |

Her türetilmiş dosyanın kaynak dosyası ve dönüşümü `docs/PROVENANCE.md` ve `docs/DATA.md`'de yazılıdır.

## Yeniden dağıtılmayanlar

Resmi bültenler ve belgeler yeniden dağıtılmaz. Herkese açık aynada (`AhmetEmreOzumagi/borsai-app`) şunlar yoktur: Borsa
İstanbul bülten zip'leri, KAP ve SPK PDF'leri, KAP bildirim listesi API yanıtı, SPK yıllık tabloları (xlsx) ve şirket
adresleri içeren doğrulama günlükleri. Özel kaynak repo bunları yalnız hesapların izlenebilirliği için saklar; dağıtmaz.
Yeniden üretmek isteyen, dosyaları manifestlerdeki adreslerden kendisi indirir ve sha256 ile doğrular.

## Koşullar

- LICENSE'taki Apache-2.0 depodaki kaynak koda uygulanır. Veri dosyalarına (`data/`, `scores/`, `registry/`,
  `app/parity/golden/`, `tests/reference/`, `experiments/log.jsonl`) ayrı bir lisans verilmez. Projenin kendi hesapladığı
  değerler (model parametreleri, tahminler, skorlar) projenin çıktısıdır; içerdikleri ya da dayandıkları kaynak değerler
  (bülten alanları, KAP ve SPK alıntıları, TÜİK serisi) kaynak kurumun kullanım koşullarına tabidir.
- Bu depo kaynak verileri yeniden yayımlama amacı taşımaz; yalnız kendi hesaplarının izlenebilirliği için gereken alanları
  kaydeder. Resmi değerler için kaynağın kendisine başvurun.
- Hukuki görüş alınmamıştır. Türev verinin dağıtımının kaynak kurumların koşullarına uygunluğu bir hukukçu tarafından
  değerlendirilmedi. Bir kurumun itirazı olursa aynanın kapsamı yeniden değerlendirilir (iletişim: README).
- Veri olduğu gibi sunulur; doğruluğu için garanti verilmez. Bu depodaki hiçbir sayı yatırım tavsiyesi değildir (README,
  "Uyarı").

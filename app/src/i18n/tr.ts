// Bütün arayüz metinleri (SPEC_APP §4). Kod içinde serbest metin yok.
// Yasak sözcükler (§4) bu dosyada geçmez; "tahmin", "olasılık", "tavan serisi", "basit kural" kullanılır.

export const DISCLAIMER =
  "Bu uygulama yatırım tavsiyesi değildir; çıktılar istatistiksel tahmin ve olasılıklardır.";

export const NAV = [
  { id: "inputs", label: "Girdi" },
  { id: "results", label: "Sonuç" },
  { id: "accuracy", label: "Doğruluk" },
  { id: "registry", label: "Sicil" },
  { id: "scenarios", label: "Kişisel kayıtlar" },
  { id: "settings", label: "Ayarlar" },
  { id: "about", label: "Hakkında" },
] as const;

export type ScreenId = (typeof NAV)[number]["id"];

// ---------------------------------------------------------------- T-2: ret ve uyarı kodları (§3b.1)

/** Modelin döndürebileceği ret, uyarı ve hata kodları. Anahtar kümesi = kod kümesi (U8; eksik anahtar tsc hatası). */
export type ModelCode =
  | "INPUT_MISSING"
  | "INPUT_NOT_NUMERIC"
  | "INPUT_NOT_POSITIVE"
  | "INPUT_NEGATIVE"
  | "DIVISION_BY_ZERO"
  | "INPUT_INCONSISTENT"
  | "F3_MISSING"
  | "F3_FILTER_STATUS_CONFLICT"
  | "FEATURE_NOT_PROVIDED"
  | "MARKET20_NOT_PROVIDED"
  | "MARKET20_NOT_NUMERIC"
  | "MARKET20_CALENDAR_NOT_COVERING"
  | "MARKET20_INSUFFICIENT_HISTORY"
  | "MARKET20_XU100_CLOSE_MISSING"
  | "MARKET20_STALE_S0"
  | "MARKET20_PREDICTION_TOO_EARLY"
  | "MARKET20_XU100_INTEGRITY"
  | "PB_FIELD_MISSING"
  | "PB_IDENTITY"
  | "PB_PRICE_RANGE"
  | "OUT_OF_TRAINING_RANGE"
  | "F4_ZERO_NO_TRAINING_EXAMPLE"
  | "F3_WINSORIZED"
  | "F3_CLIPPED_TO_TRAINING_P05_P95"
  | "RETURN_CLIPPED_TO_PHYSICAL_BOUND"
  | "IPO_PRICE_NOT_ON_TICK_GRID"
  | "PB4_ADDITIONAL_SALE_CEILING"
  | "DOMAIN_ERROR"
  | "PARAMS_INVALID"
  | "SCHEMA_UNSUPPORTED"
  | "TUFE_MISSING"
  | "TUFE_NOT_PIT"
  | "TUFE_FILE_MISMATCH"
  | "REGIME_UNKNOWN"
  | "FEATURE_CLIPPED_TO_TRAINING_P05_P95"
  | "D1_NOT_TRADED"
  | "D1_LIMIT_NA"
  | "D1_NOT_CEILING"
  | "D1_VOLUME_INVALID"
  | "D1_FIELD_INVALID"
  | "INPUT_SHARES_OFFERED"
  | "WARN_D1_HALF_DAY"
  | "WARN_D1_INTRADAY_HALT"
  | "WARN_D1_SPECIAL_TRADES"
  | "WARN_D1_LOCK_INCONSISTENT"
  | "D1_TURNOVER_CLIPPED_TO_TRAINING_P05_P95"
  | "ADDITIONAL_SALE_MISSING";

/** Metin şablonundaki yer tutucular: alan/özellik adı ve biçimlendirilmiş sayılar. */
export interface CodeParams {
  field: string;
  fieldRaw: string;
  feature: string;
  value: string;
  min: string;
  max: string;
  used: string;
  horizon: string;
  /** Tavan yolu uyarısı (`IPO_PRICE_NOT_ON_TICK_GRID`) metin alanları. */
  snapped: string;
  tick: string;
  /** D1 özel işlem uyarısı (`WARN_D1_SPECIAL_TRADES`) metin alanları. */
  specialVolume: string;
  volume: string;
}

const MARKET20_PREFIX_TEXT = (why: string) =>
  `f6 (20 seanslık XU100 getirisi) yok: ${why}; bu model f6'sız tahmin vermez`;

export const PB_IDENTITY_NAMES: Record<string, string> = {
  "ID-A": "ID-A: yeni sermaye = mevcut sermaye + bedelli",
  "ID-B": "ID-B: taban arz = bedelli + mevcut pay satışı",
  "ID-C": "ID-C: azami arz = taban arz + ek satış tavanı",
  BASE_POSITIVE: "taban arz pozitif olmalı",
  POST_POSITIVE: "yeni sermaye pozitif olmalı",
  VALUE_POSITIVE: "planlanan fiyat × taban arz pozitif olmalı",
  PB2_RANGE: "pb2 (taban arz / yeni sermaye) (0, 100] dışında",
  PB3_RANGE: "pb3 (bedelli / taban arz) (0, 100] dışında",
  PB4_RANGE: "pb4 (ek satış tavanı / taban arz) negatif",
  precision: "200 haneli bağlamda tam hesaplanamıyor",
};

export const MARKET20_REASON_TEXT: Record<string, string> = {
  NOT_PROVIDED: "f6 verilmedi (elle boş bırakıldı ya da repo modunda hesaplanmadı)",
  NOT_NUMERIC: "f6 sayı değil",
  CALENDAR_NOT_COVERING: "takvim uzatması bitti",
  INSUFFICIENT_HISTORY: "20 seanslık pencere için takvim geçmişi yetersiz",
  XU100_CLOSE_MISSING: "pencerede XU100 kapanışı eksik",
  STALE_S0: "pinli XU100 dosyası bayat; SPEC_MARKET20_V0 §4 prosedürüyle Python tarafında güncellenmeli",
  PREDICTION_TOO_EARLY: "ilk işlem günü tahmin tarihinden 12 günden fazla sonra (kural 5)",
  XU100_INTEGRITY: "XU100 dosyası bütünlük denetimini geçmedi",
};

export const CODE_TEXT: Record<ModelCode, (p: CodeParams) => string> = {
  INPUT_MISSING: (p) => `${p.field} boş; bu model bu alansız tahmin vermez`,
  INPUT_NOT_NUMERIC: (p) => `${p.field} sayı değil`,
  INPUT_NOT_POSITIVE: (p) => `${p.field} pozitif olmalı`,
  INPUT_NEGATIVE: (p) =>
    p.fieldRaw === "additional_sale_shares" ? "ek satış payı negatif olamaz" : "sermaye artırımı payı negatif olamaz",
  DIVISION_BY_ZERO: (p) => `payda sıfır (${p.field})`,
  INPUT_INCONSISTENT: (p) =>
    p.fieldRaw === "shares_offered"
      ? "satılan pay arz sonrası sermayeden büyük"
      : "sermaye artırımı payı satılan paydan büyük",
  F3_MISSING: () =>
    "Toplam talep katı (f3) yok; bu model f3'süz tahmin vermez. f3'süz tahmin PB sütunlarındadır.",
  F3_FILTER_STATUS_CONFLICT: () => "f3 filtre durumu eğitimdekiyle çelişiyor",
  FEATURE_NOT_PROVIDED: (p) => `${p.feature} verilmedi; impute edilmez`,
  MARKET20_NOT_PROVIDED: () => MARKET20_PREFIX_TEXT(MARKET20_REASON_TEXT.NOT_PROVIDED),
  MARKET20_NOT_NUMERIC: () => MARKET20_PREFIX_TEXT(MARKET20_REASON_TEXT.NOT_NUMERIC),
  MARKET20_CALENDAR_NOT_COVERING: () => MARKET20_PREFIX_TEXT(MARKET20_REASON_TEXT.CALENDAR_NOT_COVERING),
  MARKET20_INSUFFICIENT_HISTORY: () => MARKET20_PREFIX_TEXT(MARKET20_REASON_TEXT.INSUFFICIENT_HISTORY),
  MARKET20_XU100_CLOSE_MISSING: () => MARKET20_PREFIX_TEXT(MARKET20_REASON_TEXT.XU100_CLOSE_MISSING),
  MARKET20_STALE_S0: () => MARKET20_PREFIX_TEXT(MARKET20_REASON_TEXT.STALE_S0),
  MARKET20_PREDICTION_TOO_EARLY: () => MARKET20_PREFIX_TEXT(MARKET20_REASON_TEXT.PREDICTION_TOO_EARLY),
  MARKET20_XU100_INTEGRITY: () => MARKET20_PREFIX_TEXT(MARKET20_REASON_TEXT.XU100_INTEGRITY),
  PB_FIELD_MISSING: (p) => `${p.field} boş ya da ayrıştırılamıyor (PB)`,
  PB_IDENTITY: (p) => `planlanan yapı özdeşliği tutmuyor: ${PB_IDENTITY_NAMES[p.fieldRaw] ?? p.fieldRaw}`,
  PB_PRICE_RANGE: () => "fiyat tek değer değil (aralık); PB modeli aralıkla tahmin vermez",
  OUT_OF_TRAINING_RANGE: (p) =>
    `${p.feature} = ${p.value} eğitim aralığı [${p.min}, ${p.max}] dışında; tahmin dışdeğerlemedir`,
  F4_ZERO_NO_TRAINING_EXAMPLE: () => "sermaye artırımı yok (f4 = 0): eğitimde örneği yok",
  F3_WINSORIZED: (p) => `f3 eğitim p05/p95 sınırına kırpıldı: kullanılan ${p.used}`,
  F3_CLIPPED_TO_TRAINING_P05_P95: (p) => `f3 eğitim p05/p95 sınırına kırpıldı: kullanılan ${p.used}`,
  RETURN_CLIPPED_TO_PHYSICAL_BOUND: (p) => `${p.horizon} getirisi fiziksel sınıra kırpıldı`,
  PB4_ADDITIONAL_SALE_CEILING: (p) => `ek satış tavanı var (pb4 = ${p.value}); eğitimde 7 örnek`,
  IPO_PRICE_NOT_ON_TICK_GRID: (p) =>
    `arz fiyatı ${p.value} fiyat adımı ızgarasında değil (adım ${p.tick}); D1 baz fiyatı ${p.snapped} alındı`,
  DOMAIN_ERROR: () => "girdi tanım dışı (Python'da etiketsiz istisna); bu girdiyle tahmin yok",
  PARAMS_INVALID: () => "parametre dosyası geçersiz (bütünlük hatası)",
  SCHEMA_UNSUPPORTED: () => "parametre dosyası sürümü desteklenmiyor (bütünlük hatası)",
  // Faz 7 ceiling_hazard_v1 (SPEC_APP EK 3 §2.5); ayın adı, yayım günü ve neden TÜFE satırındadır (TUFE.line)
  TUFE_MISSING: () => "TÜFE endeksi (T'nin ayı − 2) yok; bu model deflatörsüz tahmin vermez, imputasyon yok.",
  TUFE_NOT_PIT: () => "TÜFE ayının yayımı ilk işlem gününden önce değil (bekçi; kural gereği olamaz)",
  TUFE_FILE_MISMATCH: () =>
    "TÜFE tablosunun önek pini modelin pinine uymuyor (eski satır, temel yıl ya da zincirleme değişmiş): yeni veri sürümü gerekir",
  REGIME_UNKNOWN: () =>
    "tahsis rejimi etiketi bilinmiyor; eski kohort kaydı kohort satırındaki ALLOC_REGIME'i verir (canlı kayıtta bu anahtar olmaz)",
  FEATURE_CLIPPED_TO_TRAINING_P05_P95: (p) => `${p.feature} eğitim p05/p95 sınırına kırpıldı: kullanılan ${p.used}`,
  // D1 sonrası güncelleme post_d1_hazard_v0 (SPEC_APP EK 3 §6.3; öneksiz kodlar, H23)
  D1_NOT_TRADED: () =>
    "D_1 işlem görmemiş (sözleşme sayısı ya da kapanış yok / ≤ 0): D_1 henüz oluşmadı; POST_D1 kaydı yazılamaz",
  D1_LIMIT_NA: () => "D_1 THM üst limiti yok ya da ≤ 0 (tavan etiketi NA)",
  D1_NOT_CEILING: () =>
    "D1 tavanda kapanmadı: D1 sonrası model bu arzda tanımlı değil (ret değil; kırılma sonrası görünüm için tavan yolu sekmesi)",
  D1_VOLUME_INVALID: () =>
    "TOPLAM ISLEM ADEDI boş/≤ 0 iken sözleşme sayısı > 0 (veri tutarsızlığı; bülten satırı elle incelenir)",
  D1_FIELD_INVALID: (p) => `D_1 THB ${p.fieldRaw} alanı yok ya da ≤ 0 (veri tutarsızlığı)`,
  INPUT_SHARES_OFFERED: () => "arz edilen pay yok / sayı değil / ≤ 0 (el değiştirme paydası)",
  WARN_D1_HALF_DAY: () => "D1 yarım gün: el değiştirme kısa seansta ölçüldü (eğitimde örnek yok)",
  WARN_D1_INTRADAY_HALT: () => "D1'de gün içi geçici durdurma (eğitimde örnek yok)",
  WARN_D1_SPECIAL_TRADES: (p) =>
    `özel işlem bildirimi hacmi ${p.specialVolume} > 0; hacim düzeltilmedi (resmi toplam ${p.volume})`,
  WARN_D1_LOCK_INCONSISTENT: () =>
    "en düşük = üst limit ama açılış/en yüksek/kapanış üst limite eşit değil; bülten satırı elle incelenmeli",
  D1_TURNOVER_CLIPPED_TO_TRAINING_P05_P95: (p) =>
    `el değiştirme ln(hacim/pay) eğitim p05/p95 sınırına kırpıldı: kullanılan ${p.used}`,
  // Faz 7C düşen arz fall_d10_v0 (SPEC_APP EK 3 §8.2; KARARLAR_C C4)
  ADDITIONAL_SALE_MISSING: () => "ek satış alanı boş → bu model tahmin vermez (0 varsayılmaz; KARARLAR_C C4)",
};

export const UNKNOWN_CODE_TEXT = (code: string) => `tanımsız kod: ${code}`;

/** Tavan yolu durumları ve kodları (EK 2 §2.9). Gösterimi Aşama P2'de kullanılır. */
export const PATH_TEXT: Record<string, string> = {
  POST_BREAK_INSUFFICIENT:
    "kırılma sonrası hücrelerde yeterli gözlem yok (n < 10): S ve P(L) var, getiri/p_up/kuantil yok",
  REALIZED: "gerçekleşti",
  CONDITIONAL_INVALID: "koşullu güncelleme bu kayıttan yapılamaz",
  SURVIVAL_MODEL_MISMATCH: "gömülü seri modeli kopyası INDEX ile uyuşmuyor",
};

// ---------------------------------------------------------------- uygulama hataları (AppError.code)

export const ERROR_TEXT: Record<string, string> = {
  INTEGRITY_FAILED: "Gömülü model dosyası INDEX ile uyuşmuyor; tahmin kapalı",
  REPO_MODE_REQUIRED: "Bu işlem repo modu ister (Ayarlar'da repo kökünü doğrulayın)",
  PYTHON_FAILED: "Python komutu başarısız oldu",
  PYTHON_NOT_FOUND: "Python çalıştırılamadı",
  IO_ERROR: "Dosya işlemi başarısız",
  INVALID_ARGUMENT: "Geçersiz girdi",
  GIT_NOT_ALLOWED: "Bu git komutu uygulamada yasak (yalnız salt okuma)",
  GIT_FAILED: "git komutu başarısız",
  SCENARIO_PATH_INSIDE_REPO: "Kişisel kayıt repo altına yazılamaz",
  SCENARIO_PATH_INSIDE_SNAPSHOT: "Kişisel kayıt gömülü sicil anlık görüntüsünün altına yazılamaz",
  SNAPSHOT_INTEGRITY_FAILED: "Gömülü sicil anlık görüntüsü doğrulanamadı; Monitör, Analiz ve Sicil kapalı",
  SCENARIO_NOT_FOUND: "Kişisel kayıt bulunamadı",
  SCENARIO_SCHEMA_UNSUPPORTED: "Bu kişisel kayıt eski sürüm; açılmaz (silinebilir)",
  INPUTS_SCHEMA_UNSUPPORTED: "Desteklenmeyen girdi belgesi sürümü",
  OUTCOMES_INVALID: "Gözlenen seri dosyası okunamadı",
  MARKET20_OUTPUT_INVALID: "Python f6 çıktısı beklenen biçimde değil",
  DATA_DIR_INSIDE_REPO: "Uygulama verisi repo altında olamaz; ayar reddedildi",
  CONFIG_RESET: "Eski ya da bozuk ayar dosyası config.json.bak olarak saklandı; varsayılanlara dönüldü",
  SOURCE_DOC_CONFLICT: "DUR: aynı adlı kaynak belge farklı içerikte (var olan dosya ve MANIFEST girişi değiştirilmez)",
  MANIFEST_INVALID: "Kaynak belge MANIFEST.json okunamadı",
  INPUTS_DOC_INVALID: "Girdi belgesi kurulamadı",
  INPUTS_DOC_EXISTS: "Girdi belgesi zaten var; farkı görüp onaylayın",
  FREEZE_DUPLICATE_RECORD:
    "DUPLICATE_RECORD: bu arz için aynı girdi belgesi ve aynı models/INDEX.json ile etkin bir kayıt zaten var. " +
    "Aynı arza ikinci kayıt serbesttir (Faz 2B düzeltmesi), ama girdi ya da model dizini değişmeden ikinci kayıt yazılmaz: " +
    "girdi belgesini güncelleyin ya da var olan kaydı iptal edin.",
  FREEZE_CANCEL_AFTER_T: "İptal ilk işlem gününden itibaren yapılamaz (SPEC_SCORING §6); son söz Python'undur",
  FREEZE_FAILED: "Dondurma başarısız",
  FREEZE_PREFLIGHT_BLOCKED:
    "DUR: ön koşullar sağlanmıyor (adım 1: INDEX sha, borsai konumu ya da git HEAD); Python çağrılmadı, kayıt yazılmadı",
  RECORD_INVALID: "Kayıt dosyası okunamadı ya da sürümü desteklenmiyor",
  RECORD_NOT_ACTIVE: "Bu kayıt etkin bir tahmin kaydı değil (iptal edilmiş ya da iptal kaydı)",
  RECORD_NO_CEILING: "Bu kayıtta tavan serisi (S) yok",
  BORSAI_OUTSIDE_REPO: "borsai paketi hedef repo altından yüklenmiyor",
  PATH_MODEL_UNKNOWN: "Bu model gömülü tavan yolu kümesinde yok",
  PATH_MODEL_NOT_IN_RECORD: "Bu kayıt Faz 4 modellerini içermiyor (kayıt INDEX'ten eski)",
  PATH_PARAMS_SHA_MISMATCH: "Kayıt farklı parametreyle yazılmış; koşullu getiri hesaplanamaz (model yeniden çalıştırılmaz)",
  PATH_CLOSE_MISSING: "Kırılma günü kapanışı dosyada yok; kırılma sonrası dağılım için resmi kapanış gerekir",
  PATH_CONDITIONAL_FAILED: "Koşullu getiri bu kayıttan hesaplanamadı",
  // D1 sonrası kayıt (EK 3 §6.6; Python hataları stderr'den sınıflanır, ham metin "Ham çıktı"da)
  POST_D1_RECORD_INVALID: "D1 sonrası kayıt dosyası okunamadı ya da sürümü desteklenmiyor",
  POST_D1_RECORD_NOT_ACTIVE: "Bu dosya etkin bir D1 sonrası kaydı değil (iptal edilmiş ya da iptal kaydı)",
  POST_D1_PREFLIGHT_BLOCKED: "DUR: D1 sonrası ön koşulları sağlanmıyor; Python çağrılmadı, kayıt yazılmadı",
  POST_D1_FREEZE_FAILED: "D1 sonrası kayıt yazılamadı",
  POST_D1_NOT_TRADED: "D_1 henüz oluşmadı ya da D_1 bülteni yerelde yok (D1_NOT_TRADED): POST_D1 kaydı yazılamaz; önce adım 2",
  POST_D1_CALENDAR_NOT_AVAILABLE: "takvim D_1'i kapsamıyor (CALENDAR_NOT_AVAILABLE): T_open hesaplanamaz, kayıt yazılamaz",
  POST_D1_NO_BASE_RECORD: "listeleme öncesi kayıt yok → SKIPPED_POST_D1: NO_PRE_LISTING_RECORD; POST_D1 kaydı yazılmaz",
  POST_D1_DUPLICATE_RECORD:
    "DUPLICATE_RECORD: aynı listeleme öncesi kayıt, aynı D_1 bültenleri ve aynı ikinci dizinle etkin bir D1 sonrası kaydı zaten var",
  POST_D1_CANCEL_AFTER_T_OPEN: "D1 sonrası iptali T_open'dan (D2 09:40) itibaren yapılamaz; son söz Python'undur",
};

export const ERROR_UNKNOWN = "Beklenmeyen hata";
export const ERROR_DETAIL = "Ham çıktı";

// ---------------------------------------------------------------- girdi formu (§3a)

export const STAGES = [
  { id: "PRE_BOOKBUILD", label: "Talep toplama ÖNCESİ (PB)" },
  { id: "POST_BOOKBUILD_PRE_LISTING", label: "Talep toplama SONRASI, listeleme öncesi" },
] as const;

export type StageId = (typeof STAGES)[number]["id"];

export const REQUIREMENT_TEXT: Record<string, string> = {
  REQUIRED: "zorunlu",
  OPTIONAL: "isteğe bağlı",
  EMPTY: "boş (bu aşamada beklenmez)",
  REQUIRED_IF_F3: "f3 doluysa zorunlu",
};

export interface FieldText {
  name: string;
  label: string;
  def: string;
  hint: string;
  users: string;
  /** PB aşamasında boş bırakılırken önerilen missing_reason ön metni. */
  pbEmpty?: string;
}

export const FIELDS: FieldText[] = [
  {
    name: "ipo_price_tl",
    label: "Halka arz fiyatı (TL)",
    def: "Resmi nihai halka arz fiyatı, TL",
    hint: "KAP 'Halka Arz Sonuçları' (aracı kurum bildirimi) 'HALKA ARZ FİYATI'; çapraz: BIST 'Payların İşlem Görmeye Başlaması' baz fiyat",
    users: "V1.5 ailesi, basit kurallar (fiyat çıktısı), tavan modeli",
  },
  {
    name: "shares_offered",
    label: "Satışa sunulan pay adedi",
    def: "Dağıtılan toplam pay adedi; ek satış kullanıldıysa dahil (ek satış ayrıca 6. alanda yazılır)",
    hint: "KAP 'Halka Arz Sonuçları' 'SATIŞA SUNULAN PAY ADEDİ'",
    users: "f1 (büyüklük verilmezse), f2, f4",
    pbEmpty: "nihai dağıtım yok",
  },
  {
    name: "post_ipo_share_capital",
    label: "Arz sonrası ödenmiş sermaye (pay adedi)",
    def: "Arz sonrası ödenmiş sermaye, pay adedi (nominal 1 TL pay)",
    hint: "BIST 'Payların İşlem Görmeye Başlaması'; çapraz SPK bülteni 'Yeni Sermaye'",
    users: "f2",
  },
  {
    name: "capital_increase_shares",
    label: "Sermaye artırımı yoluyla satılan pay",
    def: "Sermaye artırımı (bedelli) yoluyla satılan pay adedi",
    hint: "Sonuç bildirimi ayrımı basmıyorsa SPK bülteni 'Bedelli' sütunu (DATA_NOTES §2'nin üç koşuluyla)",
    users: "f4",
  },
  {
    name: "existing_share_sale_shares",
    label: "Ortak satışı yoluyla dağıtılan pay",
    def: "Mevcut ortakların sattığı pay adedi",
    hint: "KAP sonuç eki",
    users: "yalnız tutarlılık denetimi (2 = 4 + 5 + 6)",
    pbEmpty: "nihai dağıtım yok",
  },
  {
    name: "additional_sale_shares",
    label: "Kullanılan ek satış pay adedi",
    def: "Kullanılan ek satış (0 olabilir)",
    hint: "KAP sonuç eki; SPK bülteni 'Ek Pay Satışı' '-' ise 0",
    users: "tutarlılık denetimi",
    pbEmpty: "nihai dağıtım yok",
  },
  {
    name: "total_demand_multiple",
    label: "Toplam talep katı (f3)",
    def: "f3 = toplam talep / taban arz (tam tanım aşağıda)",
    hint: "KAP 'Halka Arz Sonuçları' eki ('toplamda X katı talep')",
    users: "f3; boşsa f3 isteyen 4 model RET eder",
    pbEmpty: "talep toplama yapılmadı",
  },
  {
    name: "total_demand_filter_status",
    label: "f3 filtre durumu",
    def: "Belge mükerrer taleplerin ayıklandığını söylüyorsa FILTERED, filtrelenmediğini söylüyorsa UNFILTERED, ifade yoksa NOT_SPECIFIED",
    hint: "f3 ile aynı belge",
    users: "f3 filtre çakışması denetimi",
    pbEmpty: "f3 yok",
  },
  {
    name: "ipo_size_tl",
    label: "Halka arz büyüklüğü (TL)",
    def: "Kaynakta bildirilen büyüklük, TL; verilmezse f1 = fiyat × pay",
    hint: "KAP sonuç bildirimi 'HALKA ARZ BÜYÜKLÜĞÜ (TL)'",
    users: "f1",
    pbEmpty: "nihai dağıtım yok",
  },
  {
    name: "ipo_price_try",
    label: "Planlanan fiyat (SPK)",
    def: "SPK onaylı planlanan fiyat, tek değer; aralık ('10-12') yazılırsa PB modelleri PB_PRICE_RANGE ile RET eder",
    hint: "SPK haftalık bülteni A.1 'İlk Halka Arzlar' tablosu 'Satış Fiyatı'",
    users: "pb1",
  },
  {
    name: "planned_pre_ipo_capital",
    label: "Mevcut sermaye",
    def: "Arz öncesi sermaye (pay adedi)",
    hint: "SPK bülteni tablosu 'Mevcut Sermaye'",
    users: "ID-A",
  },
  {
    name: "planned_post_ipo_capital",
    label: "Yeni sermaye",
    def: "Planlanan arz sonrası sermaye (pay adedi)",
    hint: "SPK bülteni tablosu 'Yeni Sermaye'",
    users: "pb2, ID-A",
  },
  {
    name: "planned_capital_increase_shares",
    label: "Bedelli (sermaye artırımı)",
    def: "Planlanan sermaye artırımı pay adedi",
    hint: "SPK bülteni tablosu 'Bedelli'",
    users: "pb3, ID-A/B",
  },
  {
    name: "planned_existing_share_sale",
    label: "Mevcut pay satışı",
    def: "Planlanan ortak satışı ('-' = 0)",
    hint: "SPK bülteni tablosu 'Mevcut Pay Satışı'",
    users: "ID-B",
  },
  {
    name: "planned_base_offer_shares",
    label: "Taban arz",
    def: "Taban arz = bedelli + mevcut pay satışı (H99 PB tanımı); belgede açıkça yazan toplamla çapraz denetlenir",
    hint: "SPK bülteni tablosu + KAP sonuç eki toplamı",
    users: "pb1, pb2, pb3, ID-B/C",
  },
  {
    name: "planned_additional_sale_ceiling",
    label: "Ek pay satışı tavanı",
    def: "Planlanan ek satış tavanı ('-' = 0)",
    hint: "SPK bülteni tablosu 'Ek Pay Satışı'",
    users: "pb4 (uyarı), ID-C",
  },
  {
    name: "planned_max_offer_shares",
    label: "Azami arz",
    def: "Azami arz = taban arz + ek satış tavanı; form önerir, kullanıcı onaylar",
    hint: "türetilmiş ama tabloya yazılır",
    users: "ID-C",
  },
  {
    name: "first_trading_date",
    label: "İlk işlem günü T",
    def: "ISO tarih (YYYY-AA-GG)",
    hint: "BIST 'Payların İşlem Görmeye Başlaması' bildirimi",
    users: "f6 kural 5; dondur akışında 'ilk işlem gününden önce' uyarısı",
    pbEmpty: "ilk işlem günü henüz ilan edilmedi",
  },
  {
    name: "bookbuilding_start",
    label: "İlk talep toplama günü B",
    def: "ISO tarih",
    hint: "BIST bildirimi 'Halka Arz Tarihi'; SPK bülteni",
    users: "pb_after_bookbuild_start (SPEC_SCORING §6)",
  },
  {
    name: "bookbuilding_end",
    label: "Son talep toplama günü",
    def: "ISO tarih",
    hint: "BIST bildirimi; SPK bülteni",
    users: "bilgi",
  },
];

export const F3_DEFINITION = [
  "f3 = toplam talep / taban arz.",
  "Pay: resmi sonuç belgesinde bildirilen toplam talep (tüm yatırımcı grupları); belge mükerrer/filtrelenmiş demiyorsa filtre durumu NOT_SPECIFIED.",
  "Payda: satışa sunulan taban pay adedi (ek satış tavanı HARİÇ; planned_base_offer_shares ile aynı büyüklük). Belge ek satış dahil paydayla kat veriyorsa değer yine belgedeki gibi alınır, dönüştürülmez.",
  "Köken sırası: belge katı açıkça yazıyorsa SOURCE_REPORTED ('yaklaşık' diyorsa SOURCE_REPORTED_APPROX); katı yazmıyor ama toplam talebi ve taban arzı açıkça veriyorsa talep / taban (CALCULATED_FROM_SOURCE_TOTALS); talep dağıtıma eşit basılmışsa, planlanandan az satılmışsa ya da yalnız grup bazlı talep varsa f3 BOŞ bırakılır.",
  "Uygulama f3'ü başka bir alandan türetmez, ortalama almaz, yuvarlamaz.",
];

export const FORM_NOTE_TEXT: Record<string, (n: { value?: string; name?: string }) => string> = {
  COMMA_CONVERTED: (n) => `virgül noktaya çevrildi: ${n.value ?? ""}`,
  DATE_NOT_ISO: () => "ISO tarih değil (YYYY-AA-GG)",
  FILTER_STATUS_INVALID: () => "NOT_SPECIFIED, UNFILTERED ya da FILTERED olmalı",
  PB_PRICE_RANGE: () => "fiyat aralığı: PB modelleri PB_PRICE_RANGE ile RET edecek",
  INPUT_NOT_NUMERIC: () => "sayı değil: bu alanı kullanan modeller RET edecek",
  INPUT_NOT_POSITIVE: () => "pozitif olmalı: bu alanı kullanan modeller RET edecek",
  INPUT_NEGATIVE: () => "negatif olamaz: V1.5 ailesi RET edecek",
  INPUT_INCONSISTENT: () => "tutarsız (2 ≥ 4 ve 2 ≤ 3 olmalı): V1.5 ailesi RET edecek",
  SHARES_SUM_MISMATCH: (n) => `2 ≠ 4 + 5 + 6 (toplam ${n.value ?? "—"}); RET değil, DATA_NOTES §4`,
  FILTER_STATUS_REQUIRED: () => "f3 dolu: filtre durumu zorunlu",
  PB_IDENTITY: (n) =>
    `${PB_IDENTITY_NAMES[n.name ?? ""] ?? n.name ?? ""} tutmuyor (beklenen ${n.value ?? "—"}): PB modelleri RET edecek; görünür kalır`,
  REQUIRED_EMPTY: () => "bu aşamada zorunlu; boş",
};

export const INPUTS = {
  title: "Girdi",
  stageLegend: "Aşama",
  stageNone: "Önce aşamayı seçin; alanlar aşama seçilince açılır.",
  stageNote: "Aşama yalnız hangi alanların zorunlu olduğunu belirler; hiçbir model davranışını değiştirmez (f3 boşsa f3 isteyen modeller her aşamada RET eder).",
  units: "Birim: pay adetleri nominal 1 TL pay; fiyatlar TL; oranlar sayı. Binlik ayırıcı yok, ondalık nokta (virgül noktaya çevrilir ve gösterilir).",
  prefillTitle: "Sicil girdi belgesinden kopyala (salt okuma)",
  prefillButton: "Senaryoya kopyala",
  prefillNote: "registry/inputs/<T>.json okunur, değiştirilmez; kopyalanan değerler senaryodur ve düzenlenebilir.",
  prefillNeedsRepo: "Sicil belgesinden kopyalama repo modu ister.",
  prefillDone: (t: string, company: string) => `${t} girdileri kopyalandı (${company}).`,
  tickerLabel: "Arz etiketi (isteğe bağlı; gözlenen seri data/outcomes/<T>.csv bu koddan aranır)",
  colNo: "#",
  colField: "Alan",
  colHint: "Kaynak ipucu",
  colRequirement: "Bu aşamada",
  colValue: "Değer",
  colNotes: "Denetim",
  sourceScenario: "senaryo: kaynak gerekmez",
  suggestion: (v: string) => `öneri: ${v}`,
  applySuggestion: "uygula",
  missingReasonFromDoc: (r: string) => `belgede boş: ${r}`,
  pbEmptyPlaceholder: (r: string) => `boş: ${r}`,
  filterStatusEmpty: "(boş)",
  f3Title: "f3'ün tam tanımı (SPEC_APP §3a.1)",
  predict: "Tahmin et",
  predictNote: "Senaryo tahmini: sicile ve doğruluk hesabına girmez. RET'ler sonuç ekranında görünür.",
  prepareOfficial: "Resmi kayıt için hazırla",
  prepareOfficialNote: "Önce 'Tahmin et'e basın: dondur sihirbazı sonuç ekranındaki girdileri kullanır (kayda giren değerler tahmin edilen değerlerdir).",
  prepareOfficialClosed: "kapalı: resmi kayıt akışı repo modu ister (Ayarlar)",
  predicting: "Tahmin ediliyor…",
};

export const F6 = {
  title: "f6: XU100 20 seans getirisi (yalnız v1_5_market20_v0)",
  modeRepo: "Repo modunda Python ile hesapla (borsai.market20, pinli dosyalar)",
  modeManual: "Elle gir (senaryo)",
  modeNone: "Boş bırak (MARKET20_NOT_PROVIDED ile RET)",
  repoClosed: "repo modu yok",
  compute: "f6'yı hesapla",
  computing: "hesaplanıyor…",
  manualLabel: "elle girildi (senaryo)",
  value: "f6",
  refDate: "Referans tarihi (bugün, Istanbul)",
  s0: "S0 tarihi",
  s20: "S20 tarihi",
  xu100: "XU100 dosyası sha256 (ilk 12)",
  refusal: "RET nedeni",
  tUnknown: "T bilinmiyor; kural 5 denetlenemedi",
  stale: "T değişti; f6 yeniden hesaplanacak",
  officialNote: "Resmi kayıtta f6'yı borsai.freeze kendisi hesaplar; bu değer girdi belgesine yazılmaz ve kayda etkisi yoktur.",
  noNetwork: "Uygulama ağa çıkmaz; XU100 indirmez, güncellemez.",
};

// ---------------------------------------------------------------- mod bandı ve genel

export const TR = {
  appName: "BorsAi",
  modeScenario: "SENARYO",
  modeScenarioNote: "Bu tahmin sicile girmez",
  modeOfficial: "RESMİ KAYIT",
  modeOfficialList: "sicil (salt okuma)",
  modeOfficialNoRecord: "kayıt yok",
  modeOfficialWizard: "hazırlanıyor · Dondur gerçek repoya yazar",
  modeOfficialPostD1: (t: string) => `${t} · D1 sonrası kayıt sihirbazı (kayıt yazıcı Python; commit/push uygulamada yok)`,
  modeAccuracy: "DOĞRULUK",
  modeAccuracyNote: "scores.json'dan salt okuma; uygulama skor hesaplamaz",
  standaloneMode: "Bağımsız mod (dondur ve doğruluk paneli repo ister)",
  repoMode: (p: string) => `Repo modu: ${p}`,
  loading: "Yükleniyor…",
  dash: "—",
  closedRegistry: "Kapalı: sicil ekranı ve resmi dondur akışı repo modu ister (Ayarlar'da repo kökünü doğrulayın).",
  yes: "evet",
  no: "hayır",
};

// ---------------------------------------------------------------- sonuç ekranı (§3b, §3c)

export const RESULTS = {
  title: "Sonuç",
  empty: "Henüz tahmin yok. Girdi formuna gidin ve 'Tahmin et'e basın.",
  goInputs: "Girdi formuna git",
  integrityBand: "Gömülü model dosyası INDEX ile uyuşmuyor; tahmin kapalı.",
  scenarioTooltip: "senaryo tahmini; sicile ve doğruluk hesabına girmez",
  watermark: "SENARYO",
  modelSelector: "Gösterilen modeller (gizleme yalnız görünümü etkiler; kayıtta bütün modeller vardır)",
  regime:
    "Modeller 2023-09-22…2026-08-06 arasında listelenen 99 arzla eğitildi (kesim 2026-08-19). D1 tavan oranı yıllara göre %95 (18/19; 2023 Eyl–Ara) → %82 (27/33) → %67 (12/18) → %83 (24/29) değişti (kaynak: data/training_table.csv); bugünkü rejim eğitim dönemine benzemeyebilir. Girdi eğitim aralığı dışındaysa sütun uyarı taşır.",
  groupA: "Grup A: getiri ve olasılık",
  groupB: "Grup B: tavan serisi",
  horizon: "Ufuk",
  clipMark: "⌐",
  clipTooltip: (raw: string) => `fiziksel sınıra kırpıldı; ham değer ${raw}`,
  approx: "yaklaşık",
  approxTooltip: "fiyat adımı yuvarlaması yok (AUDIT §3e)",
  pUpLabel: "P(kapanış > arz)",
  up: "↑",
  down: "↓",
  maeLine: (n: string, v: string) => `backtest tipik hata (n = ${n}): MAE ${v}`,
  refused: "RET",
  error: "HATA",
  warningsBadge: (n: number) => `⚠ ${n}`,
  warningsTitle: (m: string) => `${m}: uyarılar (hiçbir hücreyi gizlemez)`,
  noWarnings: "uyarı yok",
  close: "kapat",
  cardButton: "kart",
  raw: "ham",
  savedAs: (id: string) => `Kişisel kayıt olarak saklandı: ${id}`,
  saveTitle: "Kişisel kayıt başlığı",
  saveButton: "Kişisel kayıt olarak sakla",
  saveNote: "Kişisel kayıtlar yalnız uygulama verisine yazılır; sicile ve doğruluk hesabına girmez.",
  officialFlow: "Dondur akışına geç",
  officialFlowClosed: "kapalı: dondur akışı repo modu ister (Ayarlar)",
  scenarioLoaded: (title: string, at: string) => `Yüklenen kişisel kayıt: ${title} (${at})`,
  otherIndex: "bu senaryo farklı bir model kümesiyle üretildi; yeniden hesaplamak için Tahmin et",
  toInputs: "Girdileri forma kopyala",
  f6Summary: (origin: string, value: string) => `f6 kaynağı: ${origin} · değer: ${value}`,
};

export const F6_ORIGIN_TEXT: Record<string, string> = {
  REPO_PYTHON: "repo modu, Python (borsai.market20)",
  MANUAL: "elle girildi (senaryo)",
  NONE: "verilmedi",
};

/** Bulunma eki (ünlü/ünsüz uyumu): D1'de, D3'te, D6'da … */
const LOCATIVE: Record<number, string> = { 1: "'de", 2: "'de", 3: "'te", 4: "'te", 5: "'te", 6: "'da", 7: "'de", 8: "'de", 9: "'da", 10: "'da", 11: "'de" };

// ---------------------------------------------------------------- tavan yolu (EK 2 §4.1–§4.2)

export const PATH = {
  groupC: "Grup C: tavan yolu — getiri dağılımı (h = 1..10)",
  medianBadge: "medyan",
  limitBadge: "limit yolu",
  approxTooltip: "görüntüleme türevi: arz fiyatı × (1 + medyan); kayıtta yoktur",
  bandLabel: (lo: string, hi: string) => `%10–%90: ${lo} … ${hi}`,
  sTooltip: (h: number) => `P(limit yolu D${h}'e kadar)`,
  survivalNote: (id: string) => `S: ${id} ile aynı`,
  survivalModel: (id: string, sha: string) => `seri modeli: ${id} (sha ${sha})`,
  insufficient: "kırılma sonrası hücrelerde yeterli gözlem yok (n < 10): getiri/p_up/kuantil üretilmedi",
  colH: "h",
  hRow: (h: number) => `h = ${h}`,
  colMedian: "medyan",
  colBand: "%10–%90",
  colPUp: "P(kapanış > arz)",
  colS: "S_h",
  colPrice: "fiyat",
  colAtoms: "atom",
  chartY: "getiri",
  chartX: "h (gün)",
  q50Label: (id: string) => `${id}: medyan`,
  bandSeries: (id: string) => `${id}: %10–%90`,
  rhoLabel: (id: string) => `${id}: limit yolu (rho_h)`,
  limitTitle: "Limit yolu (fiyat adımı kuralıyla hesaplanan C_h)",
  limitPrice: (p: string) => `arz fiyatı: ${p}`,
  limitSnapped: (p: string) => `D1 baz fiyatı: ${p}`,
  limitTick: (t: string) => `fiyat adımı: ${t}`,
  limitCompare: "Grup B'deki satır yaklaşıktır (arz × 1.1^k); buradaki C_h fiyat adımı kuralıyla hesaplanmıştır.",
  cellsTitle: "Kırılma sonrası hücreler (katlanır)",
  cellsNote: (nIpo: string, cutoff: string, nMin: number) =>
    `kırılma sonrası hücre: H99'un ${nIpo} arzından, kesim ${cutoff}, N_MIN = ${nMin}`,
  cellLine: (group: string, m: number, n: number, pooled: string, sources: string) =>
    `${group}${m}: n = ${n}, havuzlandı: ${pooled}, merdiven: ${sources}`,
  cellPooled: "evet",
  cellOwn: "hayır",
};

/** Koşullu getiri sekmesi (EK 2 §4.3). */
export const PATH_COND = {
  title: "Getiri (koşullu)",
  stateOngoing: (j: number) => `durum 1: seri ${j} gün sürüyor (L ≥ ${j})`,
  stateBreak: (t: number) => `durum 2: seri D${t + 1}${LOCATIVE[t + 1] ?? "'de"} bozuldu (L = ${t})`,
  hypothetical: "varsayımsal j",
  hypotheticalBroken: (t: number) => `seri D${t + 1}${LOCATIVE[t + 1] ?? "'de"} bozuldu; varsayımsal j için durum 1 hesaplandı`,
  closesTitle: "Kullanılan kapanışlar",
  closeFile: (h: number, close: string, date: string) => `D${h}: ${close} (resmi kapanış, ${date})`,
  closeAssumed: (h: number, close: string) => `D${h}: ${close} — kapanış varsayımı: limit yolu (varsayımsal j)`,
  sourceRecord: (file: string, sha: string) => `kaynak: kayıt ${file}, params sha ${sha}`,
  sourceOutput: "kaynak: bu ekrandaki çıktı (kayıt değil)",
  noRecordModels: "bu kayıt Faz 4 modellerini içermiyor (kayıt INDEX'ten eski)",
  sJ: (j: number) => `S_${j}`,
  pLCond: (j: number) => `P(L = t | L ≥ ${j})`,
  realized: "gerçekleşti",
  realizedReturn: "gerçekleşen getiri",
  mismatch: (t: number, close: string, c: string) =>
    `gözlenen kapanış limit yolundan sapıyor: D${t} gözlenen ${close} / C_${t} ${c}`,
  mismatchNote: "hesap yine gösterilir (SPEC_CEILING_PATH_V0 §2 açık soru 1).",
  afterBreakNote: "kırılma sonrası, D_t'ye koşullu; D_{t+2}… gözlemleri koşullanmaz",
  colH: "h",
  sourceRecordPostD1: (file: string, sha: string) =>
    `kaynak: D1 sonrası kayıt ${file}, params sha ${sha}; değerler kayıttaki path_conditional'dan (hesap yok)`,
};

export const CEILING = {
  sTitle: "S_k tablosu ve eğrisi",
  axisY: "P(seri ≥ k gün)",
  axisX: "k (gün)",
  always: "her zaman tavan",
  alwaysNote: "S_k ≡ 1 (tanım gereği; SPEC_DEVIATIONS C4); model çıktısı değil, sabit satır",
  expectedL: "Beklenen L",
  expectedLTip: "Beklenen L = Σ_l l·P(L = l), l = 0..10 (görüntüleme türevi; kayda yazılmaz)",
  medianL: "Medyan L",
  medianLTip: "Medyan L = en küçük l ile Σ_{i≤l} P(L = i) ≥ 0.5 (görüntüleme türevi; kayda yazılmaz)",
  days: (s: string) => `${s} gün`,
  plTitle: "Tavan k'ıncı günden sonra bozulur: P(L = k)",
  plTip: "l = 0: hiç tavan yok; l = 10: 10 gün boyunca tavan (sağdan sansürlü); P(L = 0) + … + P(L = 10) = 1",
  pCloseTitle: "P(Dk'de tavan kapanışı)",
  pCloseNote: "ikincil, türetilmiş (SPEC_CEILING_V0 §8)",
  priceHint: "seri k gün sürerse kapanış ≈ arz fiyatı × 1.1^k (fiyat adımı yuvarlaması nedeniyle yaklaşık)",
  priceHintItem: (k: number, p: string) => `k = ${k}: ≈ ${p}`,
  hazards: "Günlük bozulma olasılıkları hazard[d] (katlanır)",
  kRow: (k: number) => `k = ${k}`,
  lLabel: (l: number) => `${l}`,
  noCeilingModels: "Tavan modeli tahmin vermedi.",
};

export const COND = {
  title: "Koşullu tavan güncellemesi (EK 1): seri j gün sürdüyse",
  definition: "P(L ≥ k | L ≥ j) = S_k / S_j; yarın bozulur = 1 − S_{j+1} / S_j; S_j = 0 ya da j ≥ 10 → tanımsız (—). Model yeniden çalıştırılmaz; j yalnız resmi veriden gelir.",
  tabCeiling: "Tavan serisi (koşullu)",
  tabReturn: "Getiri (koşullu)",
  returnNone: "Henüz yok: INDEX'te tavan-yolu (Faz 4) modeli yok; koşullu getiri dağılımı o modeller dondurulunca gelir.",
  returnRefused: "bu model bu girdiyle tahmin vermedi (RET); koşullu getiri de yok",
  strip: "Gün gün şerit (D1..D10)",
  stripHelp: "Bir güne tıklayarak tek beyanı girin ya da kaldırın: seri sürüyor.",
  declareOption: "seri sürüyor",
  state: {
    CEILING: "tavan",
    NOT_CEILING: "tavan değil",
    PENDING: "bekliyor",
    NO_LABEL: "etiket yok",
    NONE: "bilgi yok",
  } as Record<string, string>,
  userBadge: "seri sürüyor (kullanıcı beyanı)",
  sourceFile: (p: string, asOf: string) => `kaynak: ${p} (as-of ${asOf})`,
  declaredNotCounted: (k: number) => `D${k}: kullanıcı beyanı, hesaba katılmadı`,
  fileMissing: (p: string) => `gözlenen seri yok (Faz 2B henüz üretmedi): ${p}`,
  noRepo: "gözlenen seri dosyası repo modu ister; resmi j yalnız o dosyadan gelir",
  noTicker: "arz etiketi yok; gözlenen seri dosyası aranmadı",
  declarationConflict: "beyan resmi veriyle çelişiyor; resmi değer esas",
  declarationDropped: "kişisel kayıttaki eski beyan türleri (tavan değil / bekliyor) yok sayıldı; tek beyan türü 'seri sürüyor'",
  officialPending: "resmi kapanış bekleniyor",
  clearUser: "Beyanları temizle",
  userNote: "Beyan yalnız etikettir: hiçbir olasılık ya da getiri hesabına girmez, resmi j'yi değiştirmez. Yalnız uygulama belleğinde ve (saklarsanız) kişisel kayıtta tutulur; hiçbir skora ve sicile girmez.",
  broken: (day: number, l: number) => `seri D${day}${LOCATIVE[day] ?? "'de"} bozuldu; gerçekleşen L = ${l}`,
  unlabeled: "etiketsiz gün var: sayım o günde durdu; koşullu eğri bu j ile hesaplandı",
  jLabel: "j (gözlenen ardışık tavan günü)",
  jObserved: (j: number) => `gözlenen j = ${j}`,
  jNone: "gözlenen j yok (j = 0: koşulsuz)",
  hypothetical: "varsayımsal j",
  undefinedAll: "Tanımsız: j ≥ 10 ya da S_j = 0 (—).",
  curveTitle: (j: number) => `P(L ≥ k | L ≥ ${j})`,
  kRow: (k: number) => `k = ${k}`,
  tableK: "k",
  breakNext: "Yarın bozulma olasılığı",
  condExpected: "Koşullu beklenen L",
  condRemaining: "Beklenen kalan gün",
  condMedian: "Koşullu medyan L",
  // D1 sonrası (SPEC_APP EK 3 §6.5, §9 P2)
  postD1Row: "D1 sonrası (post_d1_hazard_v0)",
  postD1None: "D1 sonrası kayıt yok",
  postD1Scenario: "senaryoda D1 bülteni yok; D1 sonrası tahmin yalnız resmi kayıttan",
  postD1J0: "D1 sonrası model j ≥ 1'de tanımlı",
  postD1Source: (f: string, sha: string, d1: string, thb: string, thm: string) =>
    `kaynak: ${f}, params sha ${sha}; D_1 ${d1}; bültenler sha ${thb} / ${thm}`,
  postD1Primary: "birincil POST_D1 kaydı seçimi skorlamada yapılır (T_open ve push kanıtı)",
  postD1NotApplicable: "D1 tavanda kapanmadı: model tanımlı değil",
  postD1PathCard: "D1 sonrası S ile tavan yolu (ikincil)",
  postD1Refused: (code: string) => `D1 sonrası (post_d1_hazard_v0): RET · ${code}`,
  postD1NoCell: "kayıtta post_d1_hazard_v0 hücresi yok",
  postD1Tab: (i: number, at: string) => `POST_D1 kaydı ${i} · ${at}`,
  postD1Undefined: "D1 sonrası: bu j'de koşullu değerler tanımsız (j ≥ 10 ya da S_j = 0; —)",
};

// ---------------------------------------------------------------- model kartı (§3b)

const CARD_CAPTION = "Model kartı";

export const CARD = {
  caption: CARD_CAPTION,
  title: (m: string) => `${CARD_CAPTION}: ${m}`,
  what: "Ne yapar",
  kind: "Tür",
  training: "Eğitim n / kesim",
  sha: "params sha256 (ilk 8)",
  variants: "Aynı veri sürümünde denenen varyant sayısı",
  survival: "Seri modeli",
  primary: "Önceden ilan edilmiş birincil hücre",
  primaryNone: "bu model için birincil hücre scores.json'da yok (SPEC_CEILING_PATH_V0 §5); değer uydurulmaz",
  prospective: "Prospektif hüküm durumu",
  liveNoVerdict: (n: string) => `canlı n = ${n}: hüküm yok`,
  scoresSource: (src: string, gen: string, asOf: string, sha: string) =>
    `scores.json: ${src} · üretim ${gen} · as-of ${asOf} · sha ${sha}`,
  scoresIndexMismatch: "skorlar farklı bir model dizini için üretilmiş",
  shaMismatch: "skorlar bu parametrelerle üretilmemiş",
  noScores: "scores.json yok: kart alanları ve backtest tipik hata satırı gösterilmiyor",
};

export const KIND_TEXT: Record<string, string> = {
  hazard: "tavan serisi (kesikli zaman hazard)",
  ceiling_path: "tavan yolu (S_k + limit yolu + kırılma sonrası hücreler)",
  km: "basit kural: Kaplan–Meier tavan serisi",
  market20: "V1.5 + f6 (XU100 20 seans)",
  pb: "talep toplama öncesi (PB)",
  linear: "V1.5 ailesi (Ridge + lojistik)",
  rule: "basit kural",
  fall: "düşen arz (D5/D10 arz altı kapanış olasılığı)",
  post_d1: "D1 sonrası güncelleme (ofset + D1 kilit ve el değiştirme)",
};

// ---------------------------------------------------------------- kişisel kayıtlar (§3f)

export const SCENARIOS = {
  title: "Kişisel kayıtlar",
  banner: "Kişisel kayıtlar sicile ve doğruluk hesabına girmez.",
  empty: "Henüz kişisel kayıt yok; sonuç ekranında 'Kişisel kayıt olarak sakla'.",
  colTitle: "Başlık",
  colCreated: "Oluşturma",
  colStage: "Aşama",
  colVersion: "Uygulama sürümü",
  colIndex: "Model kümesi sha (ilk 8)",
  colSame: "Gömülü kümeyle aynı mı",
  open: "Aç",
  remove: "Sil",
  confirmDelete: (t: string) => `"${t}" silinsin mi? Geri alınamaz; dosya silinir.`,
  oldVersion: "eski sürüm",
  unreadable: "okunamıyor",
  export: "Dışa aktar",
  exportTitle: "Kişisel kaydı dosyaya aktar",
  exportDone: (p: string) => `Dışa aktarıldı: ${p}`,
  exportAll: "Tümünü dışa aktar",
  exportAllTitle: "Bütün kişisel kayıtları tek JSON dizisine aktar",
  exportAllDone: (p: string, n: number, bad: number) =>
    `Tümü dışa aktarıldı: ${p} · ${n} kayıt` + (bad === 0 ? "" : ` · okunamayan ${bad} dosya diziye girmedi`),
  exportNote: "Dışa aktarma repo altına yapılamaz (kişisel kayıt sicile giremez).",
};

// ---------------------------------------------------------------- ayarlar ve hakkında

export const SETTINGS = {
  title: "Ayarlar",
  repoRoot: "Repo kökü (repo_root)",
  pick: "Klasör seç",
  useSuggested: (p: string) => `Öneri (derleme anındaki repo): ${p}`,
  useSuggestedButton: "öneriyi kullan",
  python: "Python yolu (boşsa <repo_root> içindeki .venv Python'u)",
  scoresSource: "scores.json kaynağı",
  scoresRepo: "REPO: <repo_root>/scores/scores.json",
  scoresEmbedded: "EMBEDDED: derlemeye gömülü anlık kopya",
  validate: "Doğrula",
  save: "Kaydet",
  saved: "Ayar kaydedildi.",
  clearRepo: "Repo'yu kaldır (bağımsız mod)",
  checks: "Doğrulama",
  ok: "tamam",
  fail: "başarısız",
  info: "bilgi",
  checkText: {
    REPO_DIR: "Repo dizini var",
    DATA_DIR_OUTSIDE_REPO: "Uygulama verisi repo dışında",
    INDEX_SHA: "models/INDEX.json sha256 gömülü INDEX ile eşit",
    GIT_HEAD: "git rev-parse HEAD",
    PYTHON_IMPORT: "python -c \"import borsai\" (repo içinden)",
    OUTCOMES_DIR: "data/outcomes dizini (bilgi)",
    MARKET20_SOURCES: "pinli XU100 son günü ve takvim son günü (bilgi)",
    TUFE_TABLE: "TÜFE tablosu (data/raw/tuik): son ay ve pin (bilgi; her tahminde yeniden okunur)",
  } as Record<string, string>,
  dataDir: "Uygulama verisi",
  modeOn: "Repo modu açık",
  modeOff: "Repo modu kapalı",
  xu100Last: "XU100 son gün",
  calendarLast: "Takvim son gün",
};

export const ABOUT = {
  title: "Hakkında",
  appVersion: "Uygulama sürümü",
  buildGitHead: "Derleme anındaki git HEAD",
  buildGitStatus: "Derleme anında models/ ve scores/ git durumu",
  buildGitStatusClean: "temiz",
  indexSha: "Gömülü models/INDEX.json sha256",
  embeddedModels: "Gömülü modeller",
  ignoredModels: "INDEX'te olup bu sürümde gömülmeyen modeller",
  none: "yok",
  scoresEmbedded: "Gömülü scores.json anlık kopyası",
  yes: "var",
  no: "yok",
  loadFailed: "Uygulama bilgisi alınamadı",
  integrity: "Gömülü model bütünlüğü",
  integrityOk: "tamam (sha256 INDEX ile eşit; parametre denetimi geçti)",
  integrityFailed: "BOZUK: tahmin kapalı",
  modelTable: "Model · tür · params sha256 (ilk 8)",
  dataDir: "Uygulama verisi dizini",
  repo: "Repo modu",
  tufeEmbedded: "Gömülü TÜFE tablosu (bağımsız mod)",
  postD1Index: (sha: string) => `INDEX_POST_D1 sha256 ${sha}`,
  postD1Models: "Gömülü D1 sonrası modeller (ikinci dizin; listeleme öncesi tahminde çalışmaz)",
};

// ---------------------------------------------------------------- Tavan serisi kartı (SPEC_APP EK 3 §5, §9)

export const SUMMARY = {
  ceilingTitle: "Tavan serisi — kaç gün tavan?",
  featured: (m: string, why: string) => `öne çıkan: ${m} (${why})`,
  featuredWhy: {
    VAULT_CLOSED_V0_DEFAULT: "kasa kapalı; SPEC_HAZARD_V1 §5.5 uyarınca v0",
    RULE_5_5: "kasa sonucu, §5.5",
    RULE_5_5_NONE_ELIGIBLE_V0: "kasa sonrası kural: uygun v1 adayı yok",
  } as Record<string, string>,
  featuredTip: "Öne çıkarma kuralı (SPEC_HAZARD_V1 §5.5, KARARLAR K4) dosyadaki hükümlerden uygulanır; hiçbir model listeden kalkmaz.",
  candidateCheck: (m: string, k1: string, k2: string, k3: string) => `${m}: k1 (kasa birincil) ${k1} · k2 (v0'a karşı üst uç < 0) ${k2} · k3 (yakın dönem) ${k3}`,
  officialSource: (file: string, sha: string) => `kaynak: kayıt ${file}, params sha ${sha}`,
  expected: (d: string) => `Beklenen seri ${d} gün`,
  medianDays: (d: string) => `medyan ${d} gün`,
  pGe: (k: number, p: string) => `P(en az ${k} gün) ${p}`,
  p10: (p: string) => `P(10 gün) ${p}`,
  modeLabel: "En olası bozulma günü",
  modeNone: (p: string) => `D1'de tavan kapanışı yok (P = ${p})`,
  modeDay: (d: number, l: number, p: string) => `D${d} (seri ${l} gün; P = ${p})`,
  modeCensored: (p: string) => `10 gün boyunca tavan (sağdan sansürlü; P = ${p})`,
  condLine: (j: number, src: string, pb: string, rem: string, s5: string, s10: string) =>
    `Seri ${j} gün sürdü (${src}) → yarın bozulma ${pb} · beklenen kalan ${rem} gün · P(≥ 5 | ≥ ${j}) ${s5} · P(10 | ≥ ${j}) ${s10}`,
  condUndefined: (j: number) => `Seri ${j} gün sürdü: koşullu değerler tanımsız (j ≥ 10 ya da S_j = 0; —)`,
  jObserved: "gözlenen",
  jHypothetical: "varsayımsal",
  headRefused: (m: string) => `${m} bu girdiyle tahmin vermedi; aşağıdaki satırlar diğer modellerindir`,
  colModel: "model",
  colExpected: "beklenen",
  colMedian: "medyan",
  colPGe3: "P≥3",
  colPGe5: "P≥5",
  colP10: "P10",
  colBreak: "yarın",
  colNearEra: "yakın dönem (geçmiş veri testi)",
  colVault: "zaman-dışı (kasa)",
  colLive: "canlı sicil",
  refused: (code: string) => `RET · ${code}`,
  vaultClosed: "kasa: bekliyor",
  vaultOpen: "kasa: açıldı",
  vaultUnavailable: "scores_oot.json yok",
  vaultSuffix: " (zaman-dışı terazide)",
  nearEraTip: (cmp: string, d: string, ci: string, n: string, nb: string) =>
    `${cmp}'a karşı fark ${d} [${ci}], n = ${n} (${nb} ay); backtest, tasarıma maruz`,
  nearEraMissing: "scores.json'da yakın dönem bloğu yok",
  nearEraUnsupported: (v: string) => `desteklenmeyen yakın dönem bloğu (sürüm ${v})`,
  liveNoVerdict: (n: string) => `n = ${n}: hüküm yok`,
  scalesLine: "üç terazi ayrıdır; toplanmaz",
  nearEraFoot: (n: string, nb: string) => `yakın dönem: H99, ilk işlem ≥ 2024-01-01, n = ${n} (${nb} ay), tasarıma maruz`,
  sources: (sc: string, oot: string) => `skor kaynakları: ${sc} · ${oot}`,
  scoresSource: (src: string, sha: string) => `scores.json ${src} (sha ${sha})`,
  ootSource: (src: string, sha: string, rows: string) => `scores_oot.json ${src} (sha ${sha}${rows})`,
  ootRowsNotEmbedded: "; satırlar gömülmedi",
  noScores: "skor dosyası yok",
  detailGroupB: "Ayrıntı: Grup B — S_k tablosu ve eğrisi, P(L = k), P_close, hazard",
  pbMirror: "PB aynası (f3'süz tahmin)",
  roleRule: "kural",
  featuredMark: "★",
  recordWithoutModel: "kayıt bu modeli içermiyor (kayıt INDEX'ten eski)",
  integrity: (src: string, rule: string, detail: string) => `${src} şartname kuralına aykırı: ${rule} (${detail}); kart gösterilmiyor`,
  // D1 sonrası satırı (K-P2-3): yakın dönem yok; zaman-dışı karşılaştırıcısı görünür; canlı n_live
  postD1NearEraTip: "D1 sonrası modelin yakın dönem bloğu yok",
  comparator: (m: string) => `karşılaştırıcı: ${m}`,
  // "Düşüş (D10)" kartı (EK 3 §8.4, §9 P4; SPEC_C_V0 §9; K-P4-1, K-P4-2)
  fallTitle: "Düşüş (D10) — arz fiyatının altına düşme olasılığı",
  fallFeatured: (m: string) => `öne çıkan: ${m} (kasa sonrası kural, §5.5)`,
  fallNone: "öne çıkan yok — kasa sonrası kural (§5.5): uygun aday yok",
  fallVaultClosed: "öne çıkan yok — kasa: bekliyor",
  fallOfficialSource: (file: string) => `kaynak: kayıt ${file}`,
  fallFeaturedTip:
    "Öne çıkarma kuralı (SPEC_C_V0 §5.5, KARARLAR K4) dosyadaki hüküm, aralık ve yakın dönem bloklarından uygulanır; hiçbir model listeden kalkmaz.",
  pFall: (h: string, k: string) => `P(${h} kapanışı ≤ arz fiyatı) = ${k}`,
  pUpLine: (k: string) => `P(kapanış > arz) = ${k}`,
  fallRule: "basit kural: havuz oranı",
  comparatorBadge: "karşılaştırıcı",
  colFallD10: "P(D10 ≤ arz)",
  colFallD5: "P(D5 ≤ arz)",
  colRule55: "öne çıkarma (§5.5)",
  fallWhy: {
    k1: "kasada taban orandan ayırt edilemiyor",
    k2: "kasada V1.5'ten ayırt edilemiyor",
    k3: "yakın dönemde taban orandan kötü / bozuyor",
  } as Record<string, string>,
  fallEligible: "uygun (öne çıkan)",
  fallRefused: {
    ADDITIONAL_SALE_MISSING: "ek satış alanı boş → bu model tahmin vermez",
    F3_MISSING: "talep katı yok → bu model tahmin vermez (f3'süz düşüş tahmini fall_d10_v0_addsale'den)",
  } as Record<string, string>,
  fallWhat: "ek satış, reel büyüklük ve talep katından D10'da arz altı kapanış olasılığı",
  fallPrimary: "D10 Brier − taban oran",
  fallCardLine: (m: string, what: string, n: string, cut: string, sha: string, nv: string, prim: string) =>
    `${m} · ${what} · eğitim n = ${n}, kesim ${cut} · sha ${sha} · varyant ${nv} · birincil hücre: ${prim}`,
  fallCardsTitle: "Model kartları",
  fallComparatorTip: "karşılaştırıcı satırı (Grup A'daki p_up'tan); terazi hücreleri (C) satırlarındadır",
  fallV15Note: "V1.5'in p_up sütunu Grup A'da olduğu gibi kalır.",
  fallRawTip: (pUp: string, pFall: string) => `p_up = ${pUp} · 1 − p_up = ${pFall}`,
};

// ---------------------------------------------------------------- TÜFE (SPEC_APP EK 3 §3, §9)

export const TUFE = {
  line: (m: string, idx: string, rel: string, src: string, pin: string) => `TÜFE: ${m} = ${idx} (yayım ${rel}; kaynak ${src}; pin ${pin})`,
  sourceText: { REPO: "repo dosyası", EMBEDDED: "gömülü tablo" } as Record<string, string>,
  pinOk: "✓",
  pinBad: "✗ (TUFE_FILE_MISMATCH)",
  missingMonth: (m: string) => `TÜFE ${m} tabloda yok. Bülten yayımlanınca (m + 1'in 3'ü 10:00) Python tarafında eklenir:`,
  embeddedThrough: (m: string, head: string) =>
    `TÜFE tablosu ${m}'a kadar gömülü (derleme ${head}); yeni ay için yeniden derleme ya da repo modu`,
  invalid: (why: string) => `TÜFE tablosu ayrıştırılamadı: ${why}`,
  tUnknown: "ilk işlem günü girilmedi; TÜFE ayı belirlenemez",
  notPit: (m: string, rel: string) => `TÜFE ${m} yayımı (${rel}) ilk işlem gününden önce değil (bekçi; kural gereği olamaz)`,
  pinMismatch: "TÜFE tablosunun önek pini modelin pinine uymuyor (eski satır, temel yıl ya da zincirleme değişmiş): yeni veri sürümü gerekir",
  noManual: "TÜFE elle girilmez (imputasyon yok); ay ilk işlem gününden türetilir",
  commandNote: "Komutu uygulama çalıştırmaz; kopyalayıp repo kökünde çalıştırın.",
};

// ---------------------------------------------------------------- sicil ekranı ve arz sayfası (§3e, §3g)

export const REGISTRY = {
  title: "Sicil",
  subtitle: "Resmi sicil repoda kalır: bu ekran her açılışta <repo>/registry/records/** okur. Uygulama sicile yazmaz.",
  repoLine: (p: string) => `Repo: ${p}`,
  gitStatus: "git status --porcelain -- registry",
  gitClean: "temiz",
  empty: "Sicilde kayıt yok. 'Yeni resmi kayıt' ile dondur akışını başlatın.",
  newRecord: "Yeni resmi kayıt (dondur)",
  back: "Sicile dön",
  colTicker: "Arz",
  colCompany: "Şirket",
  colT: "İlk işlem günü (T)",
  colRecords: "Kayıt",
  colActive: "Etkin",
  colStatus: "Payda durumu",
  open: "Aç",
  recordTab: (i: number, at: string) => `Kayıt ${i} · ${at}`,
  cancelTab: (at: string) => `İptal kaydı · ${at}`,
  cancelled: "İPTAL EDİLDİ",
  cancelledBy: (reason: string, at: string) => `iptal nedeni: ${reason} (${at})`,
  cancels: (f: string) => `iptal edilen kayıt: ${f}`,
  recordHead: (f: string) => `kayıt dosyası: ${f}`,
  recordedAt: "Kayıt zamanı (Istanbul)",
  recordedAtBasis: "Yerel saat beyandır; zaman kanıtı push'tur (CLAUDE.md kural 1).",
  gitHead: "Kayıt anındaki git HEAD",
  inputSha: "Girdi belgesi sha256 (ilk 12)",
  indexSha: "models/INDEX.json sha256 (ilk 12)",
  inputsPath: "Girdi belgesi",
  nModels: "Kayıttaki model sayısı",
  nActive: "Etkin tahmin kaydı",
  tracked: "git'te izleniyor",
  untracked: "git'te izlenmiyor (commit uygulama tarafından atılmaz)",
  addedCommit: (c: string) => `kaydı ekleyen commit: ${c}`,
  proofFound: (sha: string, at: string) => `kanıt dosyası var: ${sha} ${at}`,
  // Gösterge yalnız kaydı EKLEYEN commit'in kanıtına bakar; torun commit kanıtını skorlama sayar
  // (SPEC_SCORING §5). Bant da bu dizeyi taşır (A5-3). Git beyaz listesi genişletilmez (B12).
  proofMissing: "bu kaydı ekleyen commit için kanıt dosyası yok; torun commit kanıtı skorlamada değerlendirilir",
  proofNote:
    "Gösterge sınıf hesaplamaz: LIVE / LATE_RECORD / RETRO ayrımı SPEC_SCORING §5'e göre Faz 2B'de tarihlerden çıkar.",
  proofsTitle: (n: number) => `registry/push_proofs/: ${n} kanıt dosyası`,
  primaryNote: "Aynı arzın birden çok kaydı ayrı sekmelerdedir; birincil kayıt seçimi skorlamada yapılır (SPEC_SCORING §6).",
  unsupportedTitle: "Kayıtta olup uygulamada henüz olmayan modeller",
  unsupportedNote: "bu model gömülü model kümesinde yok; kayıttaki çıktısı gösterilmez",
  pathTitle: "Kayıttaki tavan yolu modelleri (Grup A / Grup C ile aynı render)",
  pathMissing: "bu kayıt Faz 4 modellerini içermiyor (kayıt INDEX'ten eski)",
  pathShaMismatch: (id: string) => `${id}: kayıttaki params sha gömülüyle eşit değil; koşullu getiri hesaplanmaz`,
  recordSource: (f: string) => `kaynak: kayıt ${f}`,
  recordShaLine: (ids: string) => `params sha (ilk 8): ${ids}`,
  recordOnly: "Koşullu değerler yalnız bu kayıttaki models[].output.S'ten okunur; model yeniden çalıştırılmaz.",
  unreadable: "okunamıyor",
  unsupportedVersion: (v: string) => `okunamıyor (sürüm ${v})`,
  rawRecord: "Ham kayıt (JSON)",
  cancelButton: "İptal kaydı düş",
  cancelReason: "İptal nedeni (boş olamaz)",
  cancelConfirm: (f: string) => `${f} için iptal kaydı düşülsün mü? İptal edilen dosya silinmez.`,
  cancelDone: (f: string) => `İptal kaydı yazıldı: ${f}`,
  cancelRuleNote: "Python T'den itibaren iptali reddeder (SPEC_SCORING §6); uygulama kuralı önceden gösterir, son söz Python'undur.",
  cancelBlocked: (t: string) => `İlk işlem günü ${t} geçti: Python bu iptali reddedecek.`,
  ipos: (n: number) => `Payda (registry/ipos.csv): ${n} satır`,
  colPostD1: "D1 sonrası kayıt",
};

// ---------------------------------------------------------------- D1 sonrası kayıt sihirbazı (EK 3 §6.6, §9 P2)

export const POST_D1 = {
  title: "D1 sonrası kayıt sihirbazı",
  intro:
    "Kayıt yazıcı repo içindeki Python'dur (borsai.freeze --post-d1); bülten indirme de Python'dadır (borsai.outcomes update). " +
    "Uygulama ağa çıkmaz, bülten okumaz, etiket üretmez; git commit / push / tag uygulama tarafından YAPILMAZ.",
  steps: ["Ön koşullar", "Bülten ve sonuç güncellemesi (Python; komut)", "Kayıt (Python freeze --post-d1)", "Şimdi yapılacaklar"],
  step: (n: number, title: string) => `Adım ${n}: ${title}`,
  open: "D1 sonrası kayıt sihirbazı",
  back: "Arz sayfasına dön",
  ticker: "Arz kodu",
  check: "Ön koşulları denetle",
  recheck: "Çalıştırdım, yeniden denetle",
  freeze: "Kaydı yaz (Python freeze --post-d1)",
  ok: "Ön koşullar tamam.",
  blocked: "DUR: ön koşullar sağlanmadı.",
  blockerText: {
    GIT_HEAD: "git HEAD okunamadı",
    INDEX_SHA: "models/INDEX.json gömülü dizinle aynı değil (uygulamayı yeniden derleyin)",
    INDEX_POST_D1_SHA: "models/INDEX_POST_D1.json gömülü ikinci dizinle aynı değil (uygulamayı yeniden derleyin)",
    BORSAI_IMPORT: "borsai paketi repo altından yüklenmiyor",
    NO_PRE_LISTING_RECORD: "listeleme öncesi kayıt yok → SKIPPED_POST_D1: NO_PRE_LISTING_RECORD",
    D1_PENDING: "D_1 henüz repoda değil: adım 2'yi çalıştırın",
    CALENDAR_NOT_AVAILABLE: "takvim D_1'i kapsamıyor (CALENDAR_NOT_AVAILABLE); kayıt yazılamaz",
  } as Record<string, string>,
  warningText: {
    UNCOMMITTED: "commit bekliyor: freeze durabilir (sequence_guard)",
    T_OPEN_PASSED: "yerel saate göre T_open geçti: kayıt en iyi ihtimalle LATE_RECORD olur",
  } as Record<string, string>,
  gitHead: "git HEAD",
  indexSha: "models/INDEX.json = gömülü",
  indexPostD1Sha: "models/INDEX_POST_D1.json = gömülü",
  borsaiImport: "borsai repo altından",
  baseRecords: "Listeleme öncesi etkin kayıt (ceiling_hazard_v0 tahmin)",
  d1: "D_1 (data/outcomes h = 1)",
  d1Found: (d: string, status: string) => `${d} (${status})`,
  d1Pending: "D_1 henüz repoda değil: adım 2'yi çalıştırın",
  tOpen: (t: string) => `T_open = ${t} (D2_cal 09:40 Europe/Istanbul)`,
  tOpenNote: "yerel saat kanıt değildir; sınır push kanıtının created_at'idir",
  minutesLeft: (m: string) => `yerel saate göre T_open'a kalan: ${m} dakika (yalnız bilgi)`,
  committed: "data/ ve registry/post_d1/ commit'li (git status boş)",
  uncommitted: "commit bekliyor: freeze durabilir (sequence_guard)",
  activePostD1: (n: number) => `etkin D1 sonrası kaydı: ${n}`,
  yes: "✓",
  no: "✗",
  outcomesNote: "Komutları uygulama çalıştırmaz (ağ ve git). Repo kökünde sırayla çalıştırın; sonra \"Çalıştırdım, yeniden denetle\".",
  outcomesThrough: (d: string) => `--through ${d}: D_1 repoda yoksa girdi belgesindeki ilk işlem günü`,
  recordPath: "Kayıt dosyası",
  recordD1: "D_1",
  ceilingClose: "D1 tavan kapanışı (1/0)",
  summary: (p: string, r: string, na: string) => `tahmin ${p} · RET ${r} · kapsam dışı ${na}`,
  summaryLabel: "Model sonuçları",
  baseRecord: "Listeleme öncesi kayıt (base_record)",
  parity: (ok: boolean, n: number, d: string) =>
    ok ? `parite: ${n}/${n} (maks |Δ| ${d})` : `parite UYUŞMAZLIĞI: ${n} hücreden uyuşmayan var (maks |Δ| ${d})`,
  comparators: (n: number, d: string) => `comparators_conditional kopyaları: ${n} karşılaştırıcı, maks |Δ| ${d} (sınır 1e-12; bilgi)`,
  incident: (p: string) => `olay dosyası: ${p}`,
  pythonNote: (t: string, note: string) => `Python: T_open ${t} · ${note}`,
  todoTitle: "Şimdi yapılacaklar (uygulama ÇALIŞTIRMAZ)",
  timeProof: "Zaman kanıtı push'tur (CLAUDE.md kural 1).",
  liveNote: (t: string) =>
    `Kanıtın created_at'i ${t}'dan önceyse kayıt LIVE adayıdır; sonra LATE_RECORD. Sınıf skorlamada tarihlerden hesaplanır.`,
  copy: "Kopyala",
  cancelTitle: "İptal kaydı düş (D1 sonrası)",
  cancelRule: "T_open'dan (D2 09:40) itibaren iptal yapılamaz; Python reddeder (son söz Python'undur).",
  cancelPick: "İptal edilecek kayıt",
  cancelReason: "İptal nedeni (boş olamaz)",
  cancelButton: "İptal kaydı düş",
  cancelDone: (f: string) => `İptal kaydı yazıldı: ${f}`,
  noActive: "etkin D1 sonrası kaydı yok",
};

// ---------------------------------------------------------------- dondur sihirbazı (§3e)

export const FREEZE = {
  title: "Resmi kayıt sihirbazı",
  intro:
    "Kayıt yazıcı repo içindeki Python'dur (borsai.freeze). Uygulama girdi belgesini üretir, süreci toplar ve " +
    "çıkan kaydı kendi tahminiyle karşılaştırır. git commit / push / tag uygulama tarafından YAPILMAZ.",
  needResults: "Dondur akışı sonuç ekranındaki girdileri kullanır. Önce Girdi ekranında 'Tahmin et'e basın.",
  goInputs: "Girdi ekranına git",
  closed: "Kapalı: dondur akışı repo modu ister (Ayarlar'da repo kökünü doğrulayın).",
  step: (n: number, title: string) => `Adım ${n}: ${title}`,
  steps: [
    "Ön koşullar",
    "Kaynak belgeler",
    "Girdi belgesi",
    "Denetim (yetkili, Python)",
    "İlk işlem günü uyarısı",
    "Dondur",
  ],
  run: "Çalıştır",
  ticker: "Arz kodu (büyük harf ve rakam)",
  company: "Şirket",
  stage: "Aşama",
  // adım 1
  preflightOk: "Ön koşullar tamam.",
  preflightBlocked: "DUR: ön koşullar sağlanmadı.",
  blockerText: {
    REPO_DIR: "Repo dizini yok",
    GIT_HEAD: "git çalışmıyor ya da repo değil",
    INDEX_SHA: "Uygulama farklı bir model kümesiyle derlenmiş; yeniden derleyin",
    BORSAI_IMPORT: "borsai paketi bu repo altından yüklenmiyor (Python yolu ya da PYTHONPATH)",
    TUFE_MONTH: "TÜFE (T'nin ayı − 2) dosyada yok; kayıt yazılamaz. Önce ayı ekleyin (komut aşağıda).",
  } as Record<string, string>,
  gitHead: "git HEAD",
  indexSha: "models/INDEX.json sha256",
  indexEmbedded: "gömülü INDEX sha256",
  borsaiFile: "borsai.__file__",
  pythonPath: "Python",
  statusInfo: "git status --porcelain -- registry (kirli olabilir; yalnız bilgi)",
  // adım 2
  pickDocs: "Belge seç (PDF)",
  docSourceId: "Kaynak kimliği",
  docKind: "Tür",
  docDocumentId: "Belge kimliği",
  docPublishedAt: "Yayın zamanı (ISO + saat dilimi)",
  docBasis: "Yayın zamanı nereden ölçüldü",
  docTitle: "Başlık",
  docFile: "Dosya",
  docRemove: "çıkar",
  copyDocs: "Kopyala ve MANIFEST'e ekle",
  readManifest: "Var olan MANIFEST'i oku",
  copyDone: (n: number, dir: string) => `${n} belge: ${dir}`,
  docStateText: { NEW: "kopyalandı", SAME: "zaten vardı (sha eşit)", KEPT: "MANIFEST girişi korundu" } as Record<string, string>,
  manifestDocs: (n: number) => `MANIFEST'teki belge sayısı: ${n}`,
  noDocs: "Henüz belge yok; en az bir kaynak belge gerekir.",
  // adım 3
  fieldsTitle: "Alanlar: değerler sonuç ekranından gelir (kayda giren değer = tahmin edilen değer)",
  colField: "Alan",
  colValue: "Değer",
  colSource: "Kaynak belge",
  colQuote: "Belgeden alıntı",
  colMissing: "Boşsa gerekçe (missing_reason)",
  colOrigin: "f3 kökeni",
  pickSource: "(seçin)",
  collectionRules: "Toplama kuralları (her satır bir kural)",
  ftdSource: "İlk işlem günü kaynağı",
  preview: "Önizle",
  writeDoc: "Girdi belgesini yaz",
  writeConfirm: "Farkı onayla ve üzerine yaz",
  docPath: (p: string) => `girdi belgesi: ${p}`,
  docIdentical: "Var olan dosyayla bayt-eşit; değişiklik yok.",
  docExists: "Bu dosya zaten var. Fark aşağıda; onaylarsanız üzerine yazılır.",
  docWritten: (p: string, sha: string) => `Yazıldı: ${p} (sha ${sha})`,
  docProblems: "Yapısal denetim (Rust validate_inputs):",
  docPreviewTitle: "Belgenin baytları (pretty_json_bytes biçimi)",
  diffTitle: "Var olan dosyaya göre fark",
  // adım 4
  pitRun: "Yetkili denetimi çalıştır (Python)",
  pitOk: "inputs_pit_problems: boş liste (geçti).",
  pitFail: "DUR: yetkili denetim sorun buldu.",
  pitNote: "Bu denetim Python'un kendisidir; Rust denetimi yalnız ön kontroldür.",
  // adım 5
  tRed: (t: string, today: string) =>
    `Bu kayıt ilk işlem gününden sonra yazılıyor (T = ${t}, bugün = ${today}); SPEC_SCORING §5'e göre en iyi hâlde LATE_RECORD olur, LIVE olamaz.`,
  tYellow: "T bilinmiyor; kayıt yine yazılır, f6 kural 5 denetlenemez.",
  tNone: (t: string) => `İlk işlem günü ${t} henüz gelmedi.`,
  acknowledge: "Yine de dondur",
  // adım 6
  freezeButton: "Dondur (python -m borsai.freeze)",
  freezing: "Dondur çalışıyor…",
  recordWritten: (p: string) => `Kayıt yazıldı: ${p}`,
  recordModels: (n: number) => `Kayıt models/INDEX.json'daki bütün modelleri içerir: ${n}`,
  parityLine: (matched: number, supported: number, max: string, n: number, names: string) =>
    `parite: ${matched}/${supported} desteklenen model, |Δ|max = ${max}` +
    (n > 0 ? `; uygulamada henüz olmayan: ${n} (${names})` : ""),
  parityMissing: (n: number, names: string) => `kayıt INDEX'ten eski: ${n} model kayıtta yok (${names})`,
  parityNote:
    "Uygulamada henüz olmayan modeller ve kayıtta olmayan modeller uyuşmazlık değildir; karşılaştırma desteklenen ve kayıtta bulunan modellerdedir.",
  parityMismatch: (m: string) => `PARİTE UYUŞMAZLIĞI: ${m}`,
  parityRecordWins: "Kayıt yine geçerlidir: uygulamanın sayısı değil kayıt esastır.",
  parityIncident: (p: string) => `uyuşmazlık dosyası: ${p}`,
  todoTitle: "Şimdi yapılacaklar",
  todoNote:
    "Zaman kanıtı push'tur, yerel saat değil (CLAUDE.md kural 1). Kanıt created_at tarihi T'den önceyse kayıt LIVE adayıdır.",
  todoNotRun: "Uygulama bu komutları çalıştırmaz; kopyalayıp kendiniz koşarsınız.",
  copy: "Kopyala",
  copied: "kopyalandı",
  done: "Sicile dön",
  /** Girdi belgesinin `collection_rules` alanı için varsayılan metin (sicildeki belgelerle aynı). */
  defaultRules: [
    "Yalnız resmi belgeler: KAP bildirimleri (Borsa İstanbul ve aracı kurum) ve SPK bülteni; hepsi ilk işlem gününden önce yayımlanmış.",
    "Değerler belgedeki yazımdan: binlik noktalar atıldı, ondalık virgül noktaya çevrildi; başka dönüşüm yok.",
    "Belgede olmayan alan boş (null) ve missing_reason ile; tahmin, türetme, ikincil kaynak yok.",
  ].join("\n"),
};

export const SOURCE_KIND_TEXT: Record<string, string> = {
  KAP_NOTIFICATION_PDF: "KAP bildirimi (PDF)",
  KAP_ATTACHMENT_PDF: "KAP bildirim eki (PDF)",
  SPK_BULLETIN: "SPK bülteni (PDF)",
};

// ---------------------------------------------------------------- doğruluk paneli (§3d, SPEC_SCORING §8)

/**
 * `scores.json`'daki `verdict` değerlerinin TEK arayüz eşlemesi (U19). Panelde basılan metin
 * dosyadaki `verdict` alanının kendisidir; buradaki dizeler yalnız renk sınıfı seçmek ve küçük-n
 * rozetini yazmak için karşılaştırılır. "geçiyor" sözcüğü kaynak ağacında başka hiçbir arayüz
 * metninde geçmez (SPEC_SCORING §8 kural 6).
 */
export const VERDICT = {
  pass: "geçiyor",
  fail: "geçemiyor",
  undecided: "ayırt edilemiyor",
  insufficient: "yetersiz örnek",
  noInterval: "aralık için yetersiz",
};

/** Canlı sayı parçası: başlıkta ve model özetinde aynı dize (boş başlıkla çift ayraç çıkmaz). */
const LIVE_COUNT = (n: number, skipped: number) => `n = ${n}; atlanan = ${skipped}`;

/** Zaman-dışı terazinin hüküm eki (EK 3 §7.2, §9): yalnız geçiyor / geçemiyor / ayırt edilemiyor'a eklenir. */
export const VERDICT_OOT_SUFFIX = " (zaman-dışı terazide)";

export const ACCURACY = {
  title: "Doğruluk",
  noFile: "scores.json bulunamadı (Faz 2B henüz koşmadı ya da yol yanlış)",
  unsupportedVersion: (v: string) => `scores.json sürümü ${v}; uygulama 1'i destekler. Uygulamayı güncelleyin.`,
  source: (src: string, gen: string, asOf: string, sha: string) =>
    `Kaynak: ${src} · üretim ${gen} · as-of ${asOf} · sha ${sha}`,
  sourceText: { REPO: "repo dosyası", EMBEDDED: "derlemeye gömülü anlık kopya", FIXTURE: "sentetik fixture (yalnız ekran görüntüsü koşusu)" } as Record<string, string>,
  indexMismatch: "skorlar farklı bir model dizini için üretilmiş",
  syntheticNote: "Bu dosya kendini kurgusal ilan ediyor (synthetic: true): arzlar gerçek değildir.",
  integrityTitle: (rule: string) => `scores.json şartname kuralına aykırı: ${rule}`,
  integrityNote: "Panel kapalı (§2.3 fail-closed). Uygulama hiçbir hücreyi hesaplamaz, düzeltmez, doldurmaz.",
  integrityRule: {
    LIVE_CELLS_BELOW_MIN_N: "n_scored < 10 iken canlı hücre üretilmiş (§8: yalnız satır tablosu)",
    LIVE_DESCRIPTIVE_BELOW_MIN_N: "n_scored < 10 iken betimleyici ölçü üretilmiş (§8 ile aynı eşik; görev kararı)",
    SELF_REPORTED_CELLS_BELOW_MIN_N: "n_self_reported_scored < 10 iken self-reported hücre üretilmiş (görev kararı)",
    LIVE_N_SPLIT: "n_live + n_late ≠ n_scored",
    VERDICT_WITHOUT_INTERVAL: "hüküm verilmiş ama n < 30 ya da aralık yok ya da aralık 0'ı içeriyor",
    UNDECIDED_WITH_INTERVAL: "aralık 0'ı dışlarken hüküm 'ayırt edilemiyor'",
    CONDITIONAL_CELLS_BELOW_MIN_N: "koşullu blokta n_scored < 10 iken hücre üretilmiş",
    CONDITIONAL_N_SPLIT: "koşullu blokta n_live + n_late ≠ n_scored",
  } as Record<string, string>,
  // EK 3 §7.2 (P3): üç terazi
  scalesNote:
    "Üç terazi bağımsızdır: geçmiş veri testi (retrospektif, tasarıma maruz), zaman-dışı test (eski kohort) ve canlı sicil (prospektif) hiçbir yerde toplanmaz, ortalanmaz, tek hükümde birleşmez.",
  modelSelector: "Gösterilen modeller (gizleme yalnız görünümü etkiler; dosyada bütün modeller vardır)",
  noBacktestCells: "bu model için backtest hücresi yok (scores.json üretmedi)",
  liveCount: LIVE_COUNT,
  liveHead: (title: string, n: number, skipped: number) => `${title} · ${LIVE_COUNT(n, skipped)}`,
  liveBreakdown: (live: number, late: number, refused: number, unavailable: number, pending: number) =>
    `n_live = ${live} (LIVE), n_late = ${late} (LATE_RECORD); ret = ${refused}; hedef oluşmadı = ${unavailable}; bekleyen = ${pending}`,
  liveNone: "canlı kayıt henüz skorlanmadı",
  rowsOnly: "n < 10: metrik hesaplanmaz, yalnız satırlar (SPEC_SCORING §8)",
  insufficientNote: "10 ≤ n < 30: her hücre 'yetersiz örnek'; kazanan vurgusu ve renk yok",
  colOutput: "Çıktı",
  colHorizon: "Ufuk/k",
  colMetric: "Metrik",
  colModel: "Model",
  colRule: "Kural",
  colDiff: "Fark",
  colCi: "%95 aralık",
  colN: "n",
  colWlt: "kazanç / kayıp / eşit",
  pointsUnit: "puan",
  colVerdict: "Hüküm",
  colTicker: "Arz",
  colD1: "D1",
  colClass: "Sınıf",
  colRecord: "Kayıt",
  colProof: "Zaman kanıtı",
  colPrediction: "Tahmin",
  colRealized: "Gerçekleşen",
  colStatus: "Durum",
  colObserved: "Gözlenen",
  proofYes: (t: string) => `git+push ${t}`,
  proofNo: "zaman kanıtı yok",
  primaryBadge: "birincil (önceden ilan)",
  exploratoryBadge: "keşif",
  accuracyHidden: "isabet oranı tek başına gösterilmez (kuralın isabeti yok)",
  descriptiveTitle: "Betimleyici (aralıksız, hükümsüz)",
  invalidUseTitle: "Geçersiz kullanım (model bugün RET eder; hiçbir metriğe ve n'e girmez)",
  cancelledTitle: "İptal edilen kayıtlar",
  cancelledLine: (rec: string, at: string, reason: string) => `${rec} · ${at} · ${reason}`,
  selfReportedTitle: "Legacy, yalnız beyanla zamanlanmış (LEGACY_SELF_REPORTED) — ikincil",
  selfReportedNote: (n: string) => `Birincil canlı sayılara girmez; kendi n'i: ${n}`,
  retroTitle: "RETRO (bilgi amaçlı; hiçbir teraziye girmez)",
  retroLine: (model: string, tickers: string, n: number) => `${model} — ${tickers} (${n})`,
  denomTitle: (n: number) => `FROZEN olmayan payda satırları (${n})`,
  denomSkipped: (n: number) => `SKIPPED (${n})`,
  denomOutOfScope: (n: number) => `OUT_OF_SCOPE (${n})`,
  denomOther: (n: number) => `başka durum (${n})`,
  denomNote:
    "Canlı 'atlanan' yalnız SKIPPED satırlarını sayar (değer scores.json'daki n_skipped). " +
    "OUT_OF_SCOPE satırlar kapsam dışıdır; hiçbir n'e girmez.",
  skippedReason: "Atlama nedeni",
  separateTitle: "Ayrı modeller (INDEX dışı; metrik yok)",
  condTitle: "Koşullu skorlar (canlı, j başına)",
  condNone: "henüz koşullu skor yok",
  condUnsupported: (v: string) => `desteklenmeyen koşullu skor bloğu (sürüm ${v})`,
  condJ: (j: number, n: number) => `j = ${j} · n = ${n}`,
  condNote: "Koşullu blok koşulsuz tabloyla ve başka j'lerle hiçbir satırda toplanmaz.",
  refusedPrediction: (code: string) => `RET · ${code}`,
  none: "yok",
  // D1 sonrası skorlar (scores/scores_post_d1.json; EK 3 §6.5, U70). Ölçek live_post_d1: ayrı bölüm, toplanmaz.
  // "Zaman-dışı test (eski kohort)" paneli (EK 3 §7, §9 P3; K-P3-1..3). Başlıklar dosyadan aynen; burada yalnız etiketler.
  oot: {
    sectionTitle: "Zaman-dışı test (eski kohort)",
    source: (src: string, gen: string, head: string, cohort: string, sha: string) =>
      `Kaynak: ${src} · üretim ${gen} · kod ${head} · kohort ${cohort} · dosya sha ${sha}`,
    sourceText: { REPO: "repo dosyası", EMBEDDED: "derlemeye gömülü satırsız kopya" } as Record<string, string>,
    counters: (member: string, open: string, sealed: string, out: string, arch: string, codex: string, inTable: string) =>
      `MEMBER ${member} · açık küme ${open} · kasa (SEALED) ${sealed} · kapsam dışı ${out} · EXPOSED ${arch} + ${codex} · tabloya giren ${inTable}`,
    vaultClosed: "kasa: kapalı — SEALED üyelerin sonucu repoda yok; skor yok ((C) şartnamesiyle birlikte açılır)",
    vaultOpen: (t: string) => `kasa: açıldı — ${t}`,
    classDef: "Sınıf tanımı",
    classNote: "sınıf tarihlerden hesaplanır, elle etiket yok; OOT_RETRO çift hiçbir n'e girmez",
    openTitle: "Açık küme",
    sealedTitle: "Kasa (SEALED; tek seferlik, H99 öncesi kohort)",
    allTitle: "Açık ∪ kasa (yalnız açık kümede OOT_BLIND olan modeller)",
    postD1Group: "D1 sonrası zaman-dışı",
    postD1Note: "ayrı ölçek; birincil tabloya girmez",
    subsetLabel: (s: string) => `alt küme: ${s}`,
    primaryTitle: "Birincil hücreler (önceden ilan edilmiş)",
    noPrimary: (ids: string) => `birincil hücresi olmayan modeller (basit kural, OOT_RETRO ya da n < 10): ${ids}`,
    excluded: "Birleştirilmeyen modeller",
    excludedLine: (m: string, why: string) => `${m}: ${why}`,
    modelSelector: "Model",
    cellsTitle: "Hücreler",
    byYear: "İlk işlem yılı — ikincil",
    byRegime: "Tahsis rejimi — keşif",
    colSubset: "Alt küme",
    noMetric: "metrik yok (n < 10)",
    modelCounters: (sc: string, ref: string, reg: string, tu: string, pend: string, skip: string, retro: string) =>
      `skorlanan ${sc} · ret ${ref} · rejimle uygulanamaz ${reg} · hedef oluşmadı ${tu} · bekleyen ${pend} · atlanan ${skip} · OOT_RETRO ${retro} (yalnız bilgi)`,
    postD1Counters: (rows: string, sc: string, ref: string, na: string, lna: string, norec: string, retro: string) =>
      `satır ${rows} · skorlanan ${sc} · ret ${ref} · D1 tavan değil ${na} · D1 etiketi NA ${lna} · kayıt yok ${norec} · OOT_RETRO ${retro}`,
    exposure: (c: string) => `maruziyet: ${c}`,
    rowsTitle: "Satırlar (yalnız açık küme)",
    rowsRepoOnly: "satır tablosu repo modu ister (gömülü kopyada satır yok)",
    colYear: "Yıl",
    colRegime: "Rejim",
    predS: (s1: string, s5: string, s10: string) => `S_1 ${s1} · S_5 ${s5} · S_10 ${s10}`,
    predReturn: (r: string, p: string) => `D5 ${r} · p_up ${p}`,
    realized: (l: string, r5: string) => `L = ${l} · D5 ${r5}`,
    retroTitle: "OOT_RETRO (yalnız bilgi; hiçbir n'e girmez)",
    retroLine: (m: string, n: number, tickers: string) => `${m} — ${n} çift; ${tickers}`,
    retroNotDrawn: (n: number) => `${n} kod çizilmedi (açık satırda geçmiyor; SEALED gösterilmez)`,
    retroRepoOnly: "OOT_RETRO listesi repo modu ister",
    noFile: "scores_oot.json bulunamadı (Faz 6 S6 henüz koşmadı ya da yol yanlış)",
    repoOnly: "zaman-dışı skorlar repo modu ister",
    unsupported: (v: string) => `scores_oot.json sürümü ${v}; uygulama 1'i destekler. Uygulamayı güncelleyin.`,
    integrityTitle: (rule: string) => `scores_oot.json şartname kuralına aykırı: ${rule}`,
    integrityRule: {
      OOT_CELLS_BELOW_MIN_N: "n_scored < 10 iken hücre üretilmiş",
      OOT_LIVE_COUNTS_NONZERO: "zaman-dışı satırlarda canlı sınıf sayacı sıfır değil",
      OOT_ROW_NOT_OPEN: "açık küme bloğunda açık küme olmayan satır (SEALED gösterilmez)",
      VERDICT_WITHOUT_INTERVAL: "hüküm verilmiş ama n < 30 ya da aralık yok ya da aralık 0'ı içeriyor",
      UNDECIDED_WITH_INTERVAL: "aralık 0'ı dışlarken hüküm 'ayırt edilemiyor'",
    } as Record<string, string>,
    noShaNote: "dosya params sha taşımıyor",
    noModels: "zaman-dışı skor yok",
  },
  postD1: {
    title: "D1 sonrası güncelleme (canlı POST_D1, j = 1)",
    note: "Koşullu skorlar, ayrı ölçek (live_post_d1): koşulsuz tablo, öteki j'ler ve öteki terazilerle hiçbir satırda toplanmaz.",
    noFile: "scores_post_d1.json bulunamadı (D1 sonrası skorlama henüz koşmadı ya da yol yanlış)",
    repoOnly: "D1 sonrası skorlar repo modu ister (dosya derlemeye gömülmez)",
    unsupported: (v: string) => `scores_post_d1.json sürümü ${v}; uygulama 1'i destekler`,
    integrity: (rule: string, detail: string) => `scores_post_d1.json şartname kuralına aykırı: ${rule} (${detail}); bölüm kapalı`,
    source: (path: string, gen: string, asOf: string, sha: string) => `Kaynak: ${path} · üretim ${gen} · as-of ${asOf} · sha ${sha}`,
    counts: (n: number, live: number, late: number, refused: number, na: number, skipped: number, pending: number) =>
      `n = ${n} (n_live = ${live}, n_late = ${late}); ret = ${refused}; kapsam dışı (D1 tavan değil) = ${na}; atlanan = ${skipped}; bekleyen = ${pending}`,
    retro: (n: number) => `RETRO: ${n} arz (yalnız bilgi; hiçbir n'e girmez)`,
    retroLine: (t: string, d1: string) => `${t} · D_1 ${d1}`,
    noCells: "hücre yok (n < 10: metrik hesaplanmaz)",
    cardTitle: "Model kartı: post_d1_hazard_v0",
    trainingN: "δ eğitim arz sayısı",
    lastSession: "δ eğitiminin son seans tarihi",
    lastSessionMeaning: "δ eğitim arzlarının 10 seansının en geç tarihi (SPEC_DEVIATIONS H43)",
    specCutoff: "şartnamedeki eğitim sınırı (SPEC_POST_D1_V0 §3.5)",
    parent: "Ebeveyn (ofset) modeli",
    sha: "params sha256 (ilk 8)",
    variants: "Aynı veri sürümünde denenen varyant sayısı",
    primary: "Önceden ilan edilmiş birincil hücre",
    rowsTitle: "Satırlar (LIVE / LATE_RECORD)",
  },
};

// ---------------------------------------------------------------- sade görünüm (UI v2; FAZ9_APP_UI K-UI-1…15)
// Yalnız yeni dışa aktarımlar; yukarıdaki dizeler değişmez. Hüküm metni dosyadaki `verdict`'tir (U19); buradaki açıklamalar
// verdict'e bağlı ayrı satırlardır (K-UI-5). Sayılar biçimlendiriciden gelir; burada yalnız kalıplar var.

/** Sade görünüm sekmeleri (üst bar). Ayarlar dişli düğmesidir; "Yeni arz gir" birincil düğmedir. */
export const SADE_NAV = [
  { id: "monitor", label: "Monitör" },
  { id: "analiz", label: "Analiz" },
  { id: "perf", label: "Model performansı" },
  { id: "sicil", label: "Sicil" },
  { id: "kayitlarim", label: "Kayıtlarım" },
] as const;

export type SadeScreenId = (typeof SADE_NAV)[number]["id"] | "giris" | "sonuc" | "ayarlar" | "sihirbaz";

/** Hüküm hücresinin yanındaki sade açıklama: anahtar dosyadaki `verdict`'in kendisi (VERDICT eşlemesi). */
export const VERDICT_PLAIN: Record<string, string> = {
  [VERDICT.pass]: "Model daha iyi: aralığın tamamı sıfırın altında, model ortalamada daha az hata yaptı.",
  [VERDICT.fail]: "Basit kural daha iyi: aralığın tamamı sıfırın üstünde.",
  [VERDICT.undecided]: "Fark net değil: aralık sıfırı kesiyor, fark tesadüf olabilir.",
  [VERDICT.insufficient]: "Örnek az (n < 30): hüküm verilmez.",
  [VERDICT.noInterval]: "Aralık için örnek yetersiz.",
};

/** Hüküm işaretleri (renk tek başına bilgi taşımaz). */
export const VERDICT_MARK: Record<string, string> = {
  [VERDICT.pass]: "✓",
  [VERDICT.fail]: "×",
  [VERDICT.undecided]: "≈",
};

export const SADE = {
  // ---------------------------------------------------------------- kabuk
  brand: "BorsAi",
  search: "Kod ara",
  searchNone: (q: string) => `${q}: takipteki arzlarda yok`,
  newIpo: "Yeni arz gir",
  settings: "Ayarlar",
  dataDate: (d: string) => `Veri ${d}`,
  version: (v: string) => `BorsAi ${v}`,
  about: "Hakkında",
  detailed: "Ayrıntılı görünüm",
  detailedLink: "Ayrıntılı görünüm: bütün modeller ve basit kurallar",
  detailedGo: "Ayrıntılı görünüme geç",
  backToSade: "Sade görünüme dön",
  // gömülü sicil anlık görüntüsü (FAZ9_SNAPSHOT K-SNAP-3): kişisel modda Monitör, Analiz, Sicil ve Performans bundan okunur
  snapshot: {
    strip: (sha7: string, last: string, dirty: boolean) =>
      `Veri: gömülü anlık görüntü · derleme ${sha7} · son sonuç ${last}` + (dirty ? " · derlemede commit bekleyen değişiklik vardı" : ""),
    source: "Veri kaynağı",
    sourceVal: "gömülü anlık görüntü",
    sourceSub: (sha7: string) => `derleme ${sha7}`,
    cardSource: (sha7: string) => `Kaynak: gömülü anlık görüntü · derleme ${sha7}`,
  },
  repoRequired: "Bu ekran repo modu ister",
  repoRequiredNote: "Sicil, sonuç ve skor dosyaları repodan okunur. Repo klasörünü Ayarlar'da bağlayın; bağımsız modda yalnız yeni arz girişi, tahmin sonucu ve kayıtlarım çalışır.",
  goSettings: "Ayarlara git",
  loading: "Yükleniyor…",
  regimeBadge: "Fon krizi rejimi",
  regimeStripe: (d: string) =>
    `${d} ve sonrasında listelenen arzların ilk seansları eğitim döneminde görülmemiş bir stres penceresine düşüyor. Modeller bu rejimi eğitimde görmedi; çıktılar bu arzlarda dikkatle okunmalı.`,
  months: ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"],
  units: { thousand: "bin", million: "milyon", billion: "milyar" },
  modelGold: "model çıktısı",
  approxMark: "≈",
  approxText: "fark net değil",
  // FAZ9_WINDOWS K-TXT-1: öne çıkmayan ufkun "Geçmiş test" hücresi; dosyadaki keşif hükmü burada gösterilmez
  notPrimaryMark: "·",
  notPrimaryText: "birincil değil",
  approxTip: "Önceden ilan edilmiş birincil hücresi dosyada geçmediği için öne çıkmaz (ana ekran kapısı).",
  featuredTip: "Önceden ilan edilmiş birincil hücresinin dosyadaki hükmüyle öne çıkar.",
  dash: "—",

  // ---------------------------------------------------------------- model ve soru adları
  question: {
    CEILING_DAYS: "Kaç gün tavan",
    RETURN: "Getiri",
    ABOVE_IPO: "Arz üstünde mi",
    POST_D1_BREAK: "Yarın tavan bozulur mu",
    BREAK_FLOOR: "Yarın da taban mı",
  } as Record<string, string>,
  questionShort: {
    CEILING_DAYS: "Tavan",
    RETURN: "Getiri",
    ABOVE_IPO: "Arz üstü",
    POST_D1_BREAK: "D1 sonrası",
    BREAK_FLOOR: "Kırılma",
  } as Record<string, string>,
  perfQuestion: {
    CEILING_DAYS: "Kaç gün tavan",
    RETURN: "5. gün getirisi",
    ABOVE_IPO: "10. gün arz üstünde mi",
    POST_D1_BREAK: "Yarın tavan bozulur mu",
    BREAK_FLOOR: "Yarın da taban mı",
  } as Record<string, string>,
  rule: {
    base_km_last10: "son 10 arzın tablosu",
    base_km_expanding: "bütün geçmişin tablosu",
    base_train_median: "eğitim medyanı",
    base_rate: "taban oranı",
    PRODUCT_BREAK_FLOOR: "ürünün eski cevabı",
    "break_floor_v0@ZERO": "bütün kırılmaların oranı",
    ceiling_hazard_v0: "listeleme öncesi model",
  } as Record<string, string>,

  // ---------------------------------------------------------------- sınıflar (dosyadan; burada yalnız okunur metin)
  classText: {
    LIVE: "canlı",
    LATE_RECORD: "geç kayıt",
    RETRO: "geçmişe dönük",
    MACHINE_SEQUENCED: "makine sıralı",
    REFUSED: "ret",
    SKIPPED: "atlandı",
    PENDING: "bekliyor",
  } as Record<string, string>,
  classLine: (q: string, c: string) => `${q}: ${c}`,
  classNone: "kayıt yok",
  refusedShort: (code: string) => `girdi eksik (${code})`,

  // ---------------------------------------------------------------- Monitör
  monitor: {
    title: "Monitör",
    summary: (n: number, inStreak: number) =>
      `${n} arz takipte. ` + (inStreak === 0 ? "Şu an tavan serisinde olan yok." : `Tavan serisinde ${inStreak} arz var.`),
    belowList: (names: string) => ` ${names} 10. günde arz fiyatının altında kapattı.`,
    stripIpos: "Takipteki arz",
    stripIposSub: (a: string, b: string) => `${a} – ${b}`,
    stripStreak: "Tavan serisinde",
    stripStreakSub: "bugünkü bültene göre",
    stripBelow: "D10'da arz altında",
    stripBelowSub: (names: string) => names,
    stripFloor: "Tabanda kırılma",
    stripFloorSub: "seri taban kapanışıyla bozuldu",
    stripModels: "Üretimdeki model",
    stripModelsSub: "kendi sorusunda ölçülen",
    of: (a: number, b: number) => `${a} / ${b}`,
    tableTitle: "Arz takip tablosu",
    tableSub: "Kayıtlı arzlar, ilk on işlem günü",
    filterAll: (n: number) => `Tümü ${n}`,
    filterStreak: (n: number) => `Seride ${n}`,
    colIpo: "Arz",
    colD1: "İlk işlem",
    colPrice: "Arz fiyatı",
    colD10: "D10",
    colVsIpo: "Arza göre",
    colSpark: "10 seans",
    colStreak: "Seri",
    groupPre: "Listeleme öncesi tahmin",
    colExpected: "Beklenen / medyan",
    colGe5: "5+ gün",
    colBreak: "Kırılma",
    groupBreak: "Kırılma akşamı",
    colNextFloor: "Ertesi gün taban",
    colRecord: "Kayıt",
    recordReturn: (c: string) => `getiri ${c}`,
    breakFloor: (b: number) => `${b}. gün taban`,
    breakAbove: (b: number) => `${b}. gün taban üstü`,
    noBreak: "kırılma yok",
    impossibleBadge: "D10'da arz altına inemez",
    impossibleTip: "Kırılma günündeki kapanıştan altı ardışık taban bile arz fiyatının üstünde kalıyor (yapısal sıfır).",
    tableNote:
      "Geç kayıt: tahmin ilk işlem gününden sonra yazıldı, canlı sicilde sayılmaz. Sınıf her model için ayrı yazılır; tarihlerden hesaplanır. Kırılma sütunu serinin bozulduğu günü ve o günkü kapanış türünü gösterir.",
    selected: "Seçili arz",
    openAnalysis: "Analizi aç",
    vsIpo: "arza göre",
    selStreak: "Seri, model medyanı ve gerçek",
    selStreakVal: (m: string, l: string) => `${m} / ${l} gün`,
    selBreak: (b: number) => `D${b} akşamı, yarın taban olasılığı`,
    selD5: "D5 getiri, tahmin ve gerçek",
    selPair: (a: string, b: string) => `${a} / ${b}`,
    prodTitle: "Üretimdeki modeller",
    prodPerf: "Performans",
    colModel: "Model",
    colBacktest: "Geçmiş test",
    colOld: "Eski dönem",
    colLive: "Canlı",
    prodNote: "Üç sınav ayrı tutulur, toplanmaz. Canlı: listeleme öncesi push kanıtlı, sayılan arz.",
    noTest: "test yok",
    eventsTitle: "Olay akışı",
    emptyRows: "Sicilde kayıtlı arz yok.",
  },
  event: {
    RECORD: (n: number, cls: string) => `${n} arz için listeleme öncesi resmi kayıt yazıldı${cls === "" ? "" : ` (${cls})`}.`,
    RECORD_ONE: (cls: string) => `Listeleme öncesi resmi kayıt yazıldı${cls === "" ? "" : ` (${cls})`}.`,
    LEGACY_RECORD: (m: string, cls: string) => `${m} tahmini eski repoda donduruldu ve push'landı${cls === "" ? "" : ` (${cls})`}.`,
    STREAK: (a: number, b: number, closes: string) => (a === b ? `D${a}: tavan (${closes}).` : `D${a}–D${b}: ardışık tavan (${closes}).`),
    BREAK: (b: number, close: string, floor: boolean) => `${b}. gün kırılma: ${floor ? "tabanda" : "taban üstünde"} ${close} kapanış.`,
    D10: (close: string, r: string) => `D10 kapanışı ${close}; arza göre ${r}.`,
    MACHINE: (n: number, cls: string) => `${n} arz için kırılma akşamı makine kaydı yazıldı${cls === "" ? "" : ` (${cls})`}.`,
    MACHINE_ONE: (cls: string) => `Kırılma akşamı makine kaydı yazıldı${cls === "" ? "" : ` (${cls})`}.`,
    MODEL_FROZEN: (m: string, proof: string) => `${m} donduruldu${proof === "" ? "" : `; zaman kanıtı push ${proof}`}.`,
    REGIME: "Fon krizi rejimi başladı (rejim uyarısı açık).",
  },
  eventSource: {
    RECORD: "Kayıt",
    LEGACY_RECORD: "Kayıt",
    STREAK: "Seri",
    BREAK: "Kırılma",
    D10: "D10",
    MACHINE: "Kayıt",
    MODEL_FROZEN: "Model",
    REGIME: "Rejim",
  } as Record<string, string>,

  // ---------------------------------------------------------------- Yeni arz girişi
  giris: {
    title: "Yeni arz girişi",
    intro: "Alanlar belgelerin yayımlandığı sırayla gruplanmıştır. Her değer yazılırken Rust'ta denetlenir; büyük sayılar altında okunur biçimde tekrar edilir.",
    stage: "Aşama",
    stagePre: "Talep toplama öncesi",
    stagePost: "Talep toplama sonrası",
    ticker: "Arz kodu",
    prefill: "Sicildeki girdi belgesinden doldur",
    prefillButton: "Doldur",
    prefillNeedsRepo: "Sicilden doldurma repo modu ister.",
    stageFirst: "Önce aşamayı seçin; alanlar aşama seçilince açılır.",
    groups: {
      spk: { title: "SPK bülteni", sub: "İlk halka arzlar tablosu. Talep toplamadan önce yayımlanır; iki aşamada da gerekir." },
      kap: { title: "KAP halka arz sonuçları", sub: "Aracı kurumun dağıtım bildirimi ve eki. Talep toplama bittikten sonra yayımlanır." },
      bist: { title: "BIST duyuruları", sub: "Payların işlem görmeye başlaması ve halka arz tarihleri." },
    },
    kapPreNote: "Talep toplama bitmeden dağıtım sonucu yayımlanmaz; bu aşamada boş kalan alanlar beklenir.",
    optional: "isteğe bağlı",
    emptyExpected: "bu aşamada boş",
    suggestion: (v: string) => `öneri: ${v}`,
    apply: "uygula",
    fromDoc: (r: string) => `belgede boş: ${r}`,
    unit: { TL: "TL", pay: "pay", kat: "kat" } as Record<string, string>,
    readableShares: (v: string) => `${v} pay`,
    readableTl: (v: string) => `${v} TL`,
    checkTitle: "Denetim",
    checkSub: "Yazdıkça güncellenir (Rust check_form)",
    missingNone: "Eksik zorunlu alan yok.",
    missingSome: "Eksik zorunlu alanlar:",
    identities: "Özdeşlikler",
    identityOk: "tutuyor",
    identityBad: "tutmuyor",
    identityWarn: "tutmuyor (uyarı)",
    identityWarnMark: "⚠",
    identityNote: "ID-A, ID-B, ID-C tutmazsa PB modelleri durur; SUM tutmazsa yalnız uyarıdır, model durmaz.",
    identity: {
      "ID-A": "Yeni sermaye = mevcut + bedelli",
      "ID-B": "Taban arz = bedelli + mevcut pay satışı",
      "ID-C": "Azami arz = taban + ek satış tavanı",
      SUM: "Satışa sunulan = artırım + ortak + ek satış",
    } as Record<string, string>,
    market: "Piyasa",
    marketSub: "XU100'ün ilk işlem gününden önceki 20 seanslık getirisi. Yalnız v1_5_market20_v0 kullanır.",
    marketCompute: "Hesapla",
    marketManual: "Elle gir",
    marketNone: "Boş bırak",
    market20: "20 seans getirisi",
    marketClose: (d: string) => `${d} kapanış`,
    marketNote: "Repodaki sabitlenmiş XU100 dosyasından Python hesaplar; uygulama ağa çıkmaz. Resmi kayıtta bu değeri dondurma adımı kendisi hesaplar.",
    marketRepoOnly: "Hesaplama repo modu ister.",
    f3How: "Toplam talep katı nasıl yazılır?",
    predict: "Tahmin et",
    predicting: "Tahmin ediliyor…",
    official: "Resmi kayıt için hazırla",
    officialClosed: "Resmi kayıt repo modu ister (Ayarlar).",
    footNote: "Tahmin senaryodur; sicile ve doğruluk hesabına girmez. Resmi kayıt, tahmin ekranındaki değerlerle dondurma adımını açar.",
  },
  fieldLabel: {
    ipo_price_try: "Planlanan fiyat",
    planned_pre_ipo_capital: "Mevcut sermaye",
    planned_post_ipo_capital: "Yeni sermaye",
    planned_capital_increase_shares: "Bedelli (sermaye artırımı)",
    planned_existing_share_sale: "Mevcut pay satışı",
    planned_additional_sale_ceiling: "Ek pay satışı tavanı",
    planned_base_offer_shares: "Taban arz",
    planned_max_offer_shares: "Azami arz",
    ipo_price_tl: "Halka arz fiyatı",
    capital_increase_shares: "Sermaye artırımıyla satılan",
    shares_offered: "Satışa sunulan pay",
    existing_share_sale_shares: "Ortak satışıyla dağıtılan",
    additional_sale_shares: "Kullanılan ek satış",
    ipo_size_tl: "Halka arz büyüklüğü",
    total_demand_multiple: "Toplam talep katı",
    total_demand_filter_status: "Talepte mükerrer ayıklama",
    first_trading_date: "İlk işlem günü",
    bookbuilding_start: "Talep toplama başlangıcı",
    bookbuilding_end: "Talep toplama bitişi",
    post_ipo_share_capital: "Arz sonrası ödenmiş sermaye",
  } as Record<string, string>,
  filterStatus: {
    NOT_SPECIFIED: "Belgede belirtilmemiş",
    UNFILTERED: "Ayıklanmamış",
    FILTERED: "Ayıklanmış",
  } as Record<string, string>,

  // ---------------------------------------------------------------- Tahmin sonucu
  sonuc: {
    crumb: "Yeni arz girişi",
    crumbHere: "Tahmin sonucu",
    title: (t: string) => (t === "" ? "Senaryo tahmini" : `${t} için tahmin`),
    sub: (stage: string, src: string) => `${stage}, ${src}. Bu bir senaryodur: sicile ve doğruluk hesabına girmez.`,
    srcForm: "formdaki değerlerle",
    srcScenario: (title: string) => `kişisel kayıttan (${title})`,
    editInputs: "Girdileri düzenle",
    empty: "Henüz tahmin yok. Yeni arz girişinde 'Tahmin et'e basın.",
    headCeiling: (e: string, l: number, d: number) =>
      `Model bu arz için ortalama ${e} gün tavan bekliyor. En olası yol ${l} gün tavan, ${d}. gün bozulma.`,
    headCeilingNone: (e: string) => `Model bu arz için ortalama ${e} gün tavan bekliyor.`,
    headReturn: (r: string) => ` 5. gün getirisi tahmini ${r}.`,
    kacTitle: "Kaç gün tavan?",
    kacSub: "Seri uzunluğunun dağılımı, listeleme öncesi",
    expectedDays: (m: string) => `gün bekleniyor, medyan ${m}`,
    barsNote: "Çubuk k: serinin tam k gün sürme olasılığı. 0: ilk gün tavan yok; 10: on gün boyunca tavan.",
    colExpected: "Beklenen",
    colMedian: "Medyan",
    colGe3: "3+ gün",
    colGe5: "5+ gün",
    col10: "10 gün",
    rowModel: "Model",
    rowRule: "Basit kural, son 10 arz",
    backtestLine: (m: string, r: string, n: string) => `Geçmiş testte hata puanı (RPS): model ${m}, basit kural ${r} (n = ${n}). Hüküm: `,
    refused: (m: string, code: string) => `${m} bu girdiyle tahmin vermedi (${code}).`,
    returnTitle: "Getiri tahmini",
    returnSub: "Arz fiyatına göre; fiyat modelin çıktısıdır",
    colDay: "Gün",
    colForecast: "Tahmin",
    colPrice: "Fiyat",
    colPUp: "Arz üstü olasılığı",
    colBacktest: "Geçmiş test",
    featuredMark: "birincil:",
    maeLine: (v: string, n: string) => `Geçmiş testte 5. gün tahmininin tipik hatası ${v} (ortalama mutlak, n = ${n}).`,
    regimeTitle: "Rejim uyarısı",
    basisTitle: "Bu tahminin dayanakları",
    basisWarnings: "Uyarı",
    basisNoWarnings: "uyarı yok",
    basisWarningsN: (n: number) => `${n} uyarı (ayrıntılı görünümde)`,
    basisTufe: "TÜFE (reel büyüklük için)",
    basisXu100: "XU100 20 seans",
    basisSource: "Girdi kaynağı",
    basisSourceForm: "form",
    saveTitle: "Kişisel kayıt olarak sakla",
    saveLabel: "Başlık",
    save: "Sakla",
    saved: (id: string) => `Saklandı: ${id}`,
    saveNote: "Yalnız bu bilgisayarda, uygulama verisine yazılır.",
    myRecords: "Kayıtlarım",
  },

  // ---------------------------------------------------------------- Seri hesaplayıcı (K-UI-8)
  calc: {
    title: "Seri j gün sürdüyse yarın ne olur?",
    subScenario: "Gün sayısını seç; yarının tavan ve bozulma olasılığı Rust'tan gelir.",
    subOfficial: "Bültendeki seriyle ya da kendi seçtiğin günle",
    question: "Kaç gün üst üste tavan oldu?",
    help: "Seçtiğin gün varsayımsaldır; model yeniden çalıştırılmaz.",
    helpOfficial: "Seçtiğin gün varsayımsaldır; resmi j bültenden gelir ve değişmez.",
    tomorrow: "yarın",
    past: "tavan",
    observedTitle: (j: number) => `Bültende gözlenen: ${j} gün`,
    observedOngoing: "seri sürüyor",
    observedNone: "bültende gözlenen seri yok",
    backToObserved: "Gözlenene dön",
    day0: (p: string) => `Listeleme günü: D1'de tavan olasılığı ${p}.`,
    dayJ: (j: number, d: number, p: string) => `Seri ${j} gün sürdüyse yarın (D${d}) da tavan olasılığı ${p}.`,
    stillCeiling: "Yarın da tavan",
    breakProb: (p: string) => `bozulma ${p}`,
    remaining: "Beklenen kalan gün",
    condMedian: (m: string) => `koşullu medyan seri ${m} gün`,
    ge5: "En az 5 gün sürme",
    all10: "10 gün boyunca tavan",
    undefinedAll: "Bu j'de koşullu değerler tanımsız (j ≥ 10 ya da S_j = 0).",
    legendCond: "seçilen güne koşullu",
    legendUncond: "koşulsuz (listeleme öncesi)",
    legendPast: "gölgeli alan: geçmiş günler",
    formula: "Hesap modelin listeleme öncesi eğrisinden yapılır: P(L ≥ k | L ≥ j) = S_k / S_j. Model yeniden çalıştırılmaz.",
    // FAZ9_UI_FIX K-FIX-3: geçmiş karşılaştırması (kural, gri) ve modelin gün grupları notu (model dosyasından)
    historyLabel: "Geçmiş arzlarda",
    historySub: "basit kural, eğitimdeki tüm arzlar",
    historyCount: (j: number, nAt: string, nNext: string, d: number) =>
      j === 0 ? `Eğitimdeki ${nAt} arzdan ${nNext} tanesi ilk gün tavan oldu.` : `${j} gün tavan yapan ${nAt} arzdan ${nNext} tanesi ${d}. gün de tavan oldu.`,
    groupWord: ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz", "on"],
    groupOne: (d: number) => `${d}. gün`,
    groupRange: (a: number, b: number) => `${a}–${b}. gün`,
    groupsNote: (n: string, groups: string, last: number) =>
      `Model günleri ${n} grupta ele alır: ${groups}. Aynı gruptaki her gün için aynı devam olasılığını kullanır; bu yüzden ${last}. günden sonra 'yarın da tavan' değişmez. 'Geçmiş arzlarda' oranı her gün için ayrı hesaplanır.`,
    legendRule: "basit kural, seçilen güne koşullu",
    postD1Scenario: "Senaryoda D1 bülteni yok; D1 sonrası güncelleme yalnız resmi kayıtta çalışır.",
    postD1None: "D1 sonrası model (post_d1_hazard_v0) bu arz için kayıtlı değil.",
    postD1Row: (p: string) => `D1 sonrası model (post_d1_hazard_v0) yarın bozulma: ${p}`,
    official: "resmi",
    hypothetical: "varsayımsal",
  },

  // ---------------------------------------------------------------- Analiz
  analiz: {
    title: "Analiz",
    pick: "Arz seç",
    pickNote: "Takipteki arzlar, en yeni ilk işlem günü üstte. Bir satıra tıkla ya da üst bardan kod ara.",
    // FAZ9_UI_FIX K-FIX-1: yol, dönüş ve arz değiştirici; K-FIX-4: işlem sayısı
    allIpos: "Tüm arzlar",
    switchIpo: "Başka arz",
    colIpo: "Arz",
    colD1: "İlk işlem günü",
    open: "Aç",
    tradeTitle: "İşlem sayısı",
    tradeSub: "Bültendeki toplam sözleşme sayısı; çubuk arzın on günündeki en büyük güne göre.",
    company: "Şirket",
    ipoPrice: "Arz fiyatı",
    d10: "D10 kapanış",
    vsIpo: "Arza göre",
    d1: "İlk işlem",
    streak: "Tavan serisi",
    streakDays: (l: string) => `${l} gün`,
    shares: "Arz adedi",
    tlPre: "Listelemeden önce",
    tlPreRec: (d: string, cls: string) => `kayıt ${d}${cls === "" ? "" : `, ${cls}`}`,
    tlPreNone: "listeleme öncesi kayıt yok",
    tlPreVal: (e: string, r: string) => `Beklenen seri ${e} gün${r === "" ? "" : `, D5 getiri ${r}`}`,
    tlD1: (d: string) => `${d}, ilk gün akşamı`,
    tlD1Rec: (n: number) => `${n} D1 sonrası kayıt`,
    tlD1None: "Kayıt yazılmadı",
    tlBreak: (d: string) => `${d}, kırılma akşamı`,
    tlBreakSub: (b: number, floor: boolean) => `${b}. gün ${floor ? "tabanda" : "taban üstünde"} kapandı`,
    tlBreakVal: (p: string) => `Yarın da taban olasılığı ${p}`,
    tlBreakNone: "kırılma kaydı yok",
    tlD10: (d: string) => `${d}, D10`,
    tlD10Sub: "sonuç",
    tlD10Val: (l: string, r: string) => `${l} gün tavan; arza göre ${r}`,
    corridorTitle: "Fiyat koridoru",
    corridorSub: "On seans: kapanış, günün üst limiti ve arz fiyatı",
    legendCeiling: "tavan kapanış",
    legendNotCeiling: "tavan değil",
    legendUpper: "üst limit",
    legendModel: "getiri modelinin beklentisi",
    ipoLine: (p: string) => `arz ${p}`,
    xIpo: "arz",
    eq: (a: string, b: string, same: boolean) => `${a} ${same ? "=" : "≠"} ${b}`,
    lnOf: (x: string) => `ln ${x}`,
    promoted: "✓",
    pickList: "Takipteki arzlar",
    breakMark: (b: number) => `${b}. gün kırılma`,
    rowModel: "Model: o gün tavan kapanış olasılığı (listeleme öncesi)",
    rowRealized: "Gerçekleşen kapanış",
    ceiling: "tavan",
    notCeiling: "tavan değil",
    noOutcome: "bekliyor",
    kacTitle: "Kaç gün tavan?",
    kacSub: "Kayıttaki dağılım (listeleme öncesi)",
    realizedMark: "Gerçekleşen seri işaretli",
    breakTitle: "Kırılma akşamı: yarın da taban mı?",
    breakSub: (b: number) => `${b}. gün akşamı, makine kaydı`,
    breakF1: (d: number) => `${d}. gün taban olasılığı`,
    breakF2: (a: number, b: number) => `${a}. ve ${b}. gün taban`,
    breakModel: "Model",
    breakByTypeFloor: "Tabanda kırılanların oranı",
    breakByTypeAbove: "Taban üstü kırılanların oranı",
    breakZero: "Bütün kırılmaların oranı",
    breakProduct: "Ürünün eski cevabı",
    breakProductNone: "yok",
    featTitle: "Özellik",
    featRaw: "Ham değer",
    featInput: "Girdi",
    featZ: "z",
    featCoef: "Katsayı",
    featFloor: "Kapanış alt limitte",
    featTurnover: "ln(işlem adedi / arz adedi)",
    featConst: (c: string) => `Sabit (C = ${c})`,
    clippedNote: (raw: string, n: string, ev: string) =>
      `* ham ${raw}, eğitimin %5'lik sınırına kırpıldı. Eğitim: ${n} kırılma akşamı; ertesi gün taban olan: ${ev}.`,
    trainingNote: (n: string, ev: string) => `Eğitim: ${n} kırılma akşamı; ertesi gün taban olan: ${ev}.`,
    structural: (min10: string, p: string) => `10. günün en düşük mümkün kapanışı ${min10} (altı ardışık taban), arz fiyatı ${p}.`,
    impossible: "Bu arz D10'da arz fiyatının altına inemez (yapısal sıfır).",
    promotion: (label: string, n: string) => `${label}. Geçmiş test: ${n} kırılma akşamı.`,
    breakClass: (cls: string) => `Bu arz için sınıf: ${cls}.`,
    breakClosed: "Kırılma kartı kapalı: katsayı dosyasının sha'sı makine kaydındakiyle tutmuyor.",
    breakNoModel: "Kırılma kartı kapalı: models/break_floor_v0.json okunamadı.",
    breakNone: "Bu arz için kırılma akşamı makine kaydı yok.",
    returnTitle: "Getiri: tahmin ve gerçekleşen",
    returnSub: "Arz fiyatına göre",
    colDay: "Gün",
    colForecast: "Tahmin",
    colPUp: "Arz üstü olasılığı",
    colRealized: "Gerçek",
    colBacktest: "Geçmiş test",
    returnNote: (cls: string) => `Halkalı nokta tahmin, dolu nokta gerçekleşen. Sınıf: ${cls}.`,
    logTitle: "Kayıt ve kanıt günlüğü",
    goSicil: "Sicilde gör",
    recordShort: "Kayıt",
  },

  // ---------------------------------------------------------------- Model performansı
  perf: {
    title: "Model performansı",
    intro: "Her model kendi sorusunda, o soruya basit bir kuralla verilen cevaba karşı ölçülür. Önceden ilan edilmiş birincil hücresi dosyada geçmeyen çıktı ana ekrana çıkmaz.",
    stripProd: "Üretimde",
    stripProdSub: "kendi sorusunda ölçülen",
    stripRows: "Karşılaştırma",
    // FAZ9_UI_FIX K-FIX-5: sayımlar dosyadaki verdict'e göre ayrı; sıfır olan parça yazılmaz
    stripRowsSub: (c: { n_pass: number; n_undecided: number; n_fail: number; n_other: number; n_no_verdict: number }) =>
      [
        c.n_pass ? `${c.n_pass} satırda model daha iyi` : "",
        c.n_undecided ? `${c.n_undecided} satırda fark net değil` : "",
        c.n_fail ? `${c.n_fail} satırda kural daha iyi` : "",
        c.n_no_verdict ? `${c.n_no_verdict} satır hükümsüz` : "",
        c.n_other ? `${c.n_other} satır yetersiz örnek` : "",
      ]
        .filter((s) => s !== "")
        .join(" · "),
    stripMinN: "Hüküm eşiği",
    stripMinNSub: (m: string, v: string) => `n ≥ ${v} hüküm, n < ${m} yalnız satır`,
    diffTitle: "Model, basit kuraldan daha iyi mi?",
    diffSub: "Geçmiş test. Hata puanında küçük olan iyidir; fark = model − kural.",
    guide0: "0 = fark yok",
    guideLeft: "← model daha az hata yaptı",
    guideRight: "kural daha iyi →",
    guideDot: "Nokta ortalama farktır: model hatası eksi kural hatası. Sıfırın solundaysa model ortalamada daha az hata yapmış.",
    guideLine: "Çizgi %95 aralıktır: arzlar ilk işlem ayına göre bloklar hâlinde yeniden örneklendi; farkların %95'i bu çizginin üstüne düştü.",
    guideZero: "Çizginin tamamı sıfırın solunda ise fark tesadüf sayılmaz: model geçer. Çizgi sıfırı kesiyorsa fark tesadüf olabilir: \"fark net değil\". Bu sayılar ana ekrana çıkmaz.",
    colQuestion: "Soru ve karşılaştırma",
    colScore: "Hata puanı",
    colInterval: "Fark ve %95 aralık",
    colWins: "Model daha iyi olan arz",
    colVerdict: "Hüküm",
    vsRule: (m: string, r: string, metric: string) => `${m} ile ${r}, ${metric}`,
    model: "model",
    rule: "kural",
    wins: (w: string, n: string) => `${w} / ${n}`,
    nOnly: (n: string, months: string) => `n = ${n} (${months} ay)`,
    wlt: (w: string, l: string, t: string) => `kazanç ${w} · kayıp ${l} · eşit ${t}`,
    noVerdict: "hüküm alanı yok",
    breakLabel: (l: string) => `dosya: ${l}`,
    exploratory: "keşif",
    primary: "birincil",
    legend: "RPS: kaç gün sorusundaki olasılık dağılımının hatası. MAE: getiri tahmininin ortalama mutlak sapması. Brier: evet/hayır olasılığının karesel hatası. Geçmiş test tasarıma maruzdur, yalnız ön elemedir; asıl sınav canlı sicildir.",
    scalesTitle: "Üç ayrı sınav",
    scalesSub: "Geçmiş test, eski dönem ve canlı sicil ayrı tutulur, asla toplanmaz.",
    scalesMain: "Asıl sınav canlı sicil",
    colModel: "Model",
    colBacktest: "Geçmiş test",
    colOld: "Eski dönem (zaman-dışı)",
    colLive: "Canlı sicil",
    oldN: (n: string) => `${n} arz`,
    liveLine: (live: string, late: string) => `${live} sayılan, ${late} geç kayıt`,
    liveRetro: (n: string) => `${n} geçmişe dönük`,
    liveTitle: "Canlı sicil",
    liveSub: (v: string) => `Her aşama ${v} sayılan arzda değerlendirilir; geç ve geçmişe dönük kayıt sayılmaz.`,
    liveStage: {
      PRE: "Listeleme öncesi",
      PRE_SUB: "kaç gün tavan",
      PRE_RET: "Listeleme öncesi",
      PRE_RET_SUB: "D5 getiri",
      POST_D1: "İlk gün akşamı",
      POST_D1_SUB: "yarın tavan bozulur mu",
      BREAK: "Kırılma akşamı",
      BREAK_SUB: "yarın da taban mı",
    } as Record<string, string>,
    rowsTitle: "Canlı sicil satırları",
    rowsSub: "Her arz için kaydın sınıfı, tahmin ve gerçekleşen. Yalnız canlı sınıf sicil sayısına girer.",
    colIpo: "Arz",
    colD1: "İlk işlem",
    colClass: "Sınıf",
    colPredicted: "Beklenen",
    colRealized: "Gerçek",
    colForecast: "Tahmin",
    groupCeiling: "Kaç gün tavan",
    groupD5: "5. gün getirisi",
    groupPostD1: "İlk gün akşamı",
    groupBreak: "Kırılma akşamı",
    rowsNote: "Sınıf push kanıtının tarihinden hesaplanır: ilk işlem gününden önce push'lanan kayıt canlıdır. D1 sonrası ve kırılma akşamı modelleri bu arzlardan sonra donduruldu; onlarda sayılan arz yok.",
    detailedLink: "Ayrıntılı görünüm: bütün modeller, hücreler ve zaman-dışı panel",
    integrity: (rule: string) => `scores.json şartname kuralına aykırı (${rule}); panel kapalı.`,
    noScores: "scores.json yok: geçmiş test satırları gösterilemiyor.",
    repoOnlyPart: "D1 sonrası, kırılma akşamı ve zaman-dışı bölümler repo modu ister.",
  },

  // ---------------------------------------------------------------- Sicil
  sicil: {
    title: "Sicil",
    intro: "Resmi kayıtlar repoda kalır. Bu ekran her açılışta repodan okur; uygulama sicile yazmaz, commit ve push atmaz.",
    introSnapshot:
      "Resmi kayıtlar repoda kalır. Kişisel modda bu ekran paketin derlendiği andaki sicilin gömülü, salt okunur kopyasından okur; uygulama sicile yazmaz, commit ve push atmaz.",
    newRecord: "Yeni resmi kayıt",
    payda: "Payda",
    paydaSub: (a: number, b: number) => `${a} kayıtlı, ${b} kapsam dışı`,
    rows: "satır",
    pre: "Listeleme öncesi kayıt",
    preSub: "etkin tahmin kaydı",
    postD1: "D1 sonrası kayıt",
    postD1Sub: "etkin",
    machine: "Kırılma akşamı kaydı",
    machineSub: "makine kaydı",
    proofs: "Zaman kanıtı dosyası",
    proofsSub: "registry/push_proofs",
    repo: "Repo durumu",
    repoClean: "temiz",
    repoDirty: "commit bekleyen değişiklik var",
    repoSub: "registry/ ve data/",
    tableTitle: "Kayıtlı arzlar",
    tableSub: "Payda dosyasında dondurulmuş satırlar, en yeni ilk işlem günü üstte",
    colIpo: "Arz",
    colD1: "İlk işlem günü",
    colPre: "Listeleme öncesi",
    colPost: "D1 sonrası",
    colBreak: "Kırılma akşamı",
    nRecords: (n: number) => `${n} kayıt`,
    none: "yok",
    machineRecord: "makine kaydı",
    open: "Aç",
    outOfScope: (n: number) => `Kapsam dışı ${n} satır`,
    outOfScopeSub: "hiçbir sayıma girmez",
    card: "Kayıt künyesi",
    tabPre: (d: string) => `Listeleme öncesi, ${d}`,
    tabBreak: (d: string) => `Kırılma akşamı, ${d}`,
    tabPost: "D1 sonrası",
    tabPostNone: "D1 sonrası, yok",
    file: "Kayıt dosyası",
    at: "Kayıt zamanı",
    atBasis: "Yerel saat beyandır; zaman kanıtı push'tur.",
    proof: "Zaman kanıtı",
    proofYes: (at: string) => `push kanıtı var ${at}`,
    proofNo: "kaydı ekleyen commit için kanıt dosyası yok",
    addedBy: (c: string) => `kaydı ekleyen commit ${c}`,
    classRow: "Sınıf",
    inputs: "Girdi belgesi",
    modelSet: "Model kümesi",
    modelSetVal: (n: number) => `${n} model`,
    indexSha: (s: string) => `kayıt anındaki INDEX sha256 ${s}`,
    head: "Kayıt anındaki git HEAD",
    produced: "Üretim zamanı (UTC)",
    machineClass: "Kırılma akşamı sınıfı",
    pBreak: "Yarın da taban olasılığı",
    pd1Wizard: "D1 sonrası kayıt sihirbazı",
    raw: "Ham kayıt (JSON)",
    cancel: "İptal kaydı düş",
    cancelNote: "İptal ve iptal kuralı ayrıntılı kayıt sayfasındadır; son söz Python'undur. Aynı arzın birden çok kaydı ayrı sekmelerdedir; birincil kayıt seçimi skorlamada yapılır.",
    openAnalysis: "Analizi aç",
    postNone: "Bu arz için D1 sonrası kayıt yok.",
  },

  // ---------------------------------------------------------------- Kayıtlarım
  kayitlarim: {
    title: "Kayıtlarım",
    intro: "Sakladığın senaryo tahminleri. Yalnız bu bilgisayarda durur; sicile ve doğruluk hesabına girmez.",
    exportAll: "Tümünü dışa aktar",
    emptyTitle: "Henüz saklanan senaryo yok",
    emptyText: "Bir arzın girdilerini yazıp tahmin ettikten sonra, sonuç ekranındaki \"Kişisel kayıt olarak sakla\" ile buraya eklersin. Açtığın kayıt yeniden hesaplanmaz; o anki çıktılar aynen gösterilir.",
    colTitle: "Başlık",
    colCreated: "Oluşturma",
    colStage: "Aşama",
    colSet: "Model kümesi",
    colActions: "İşlemler",
    sameSet: "güncel kümeyle aynı",
    oldSet: "eski küme",
    open: "Aç",
    export: "Dışa aktar",
    remove: "Sil",
    note: "Farklı bir model kümesiyle üretilmiş kayıtlar \"eski küme\" diye işaretlenir; yeniden hesaplamak için girdileri forma kopyalayıp tahmin edersin. Dışa aktarma repo klasörüne yapılamaz.",
  },

  // ---------------------------------------------------------------- Ayarlar ve Hakkında
  ayarlar: {
    title: "Ayarlar",
    intro: "Repo bağlanınca sicil, resmi kayıt ve doğruluk ekranları açılır. Bağlı değilken uygulama bağımsız modda yalnız senaryo üretir.",
    repo: "Repo klasörü",
    pick: "Klasör seç",
    suggested: (p: string) => `Öneri (derleme anındaki repo): ${p}`,
    useSuggested: "Öneriyi kullan",
    python: "Python yolu",
    pythonPlaceholder: "boşsa repo içindeki .venv Python'u",
    scores: "Skor dosyalarının kaynağı",
    scoresRepo: "Repodaki dosya",
    scoresEmbedded: "Uygulamaya gömülü kopya",
    save: "Kaydet",
    validate: "Doğrula",
    clear: "Repoyu kaldır",
    saved: "Ayar kaydedildi.",
    view: "Görünüm",
    viewSade: "Sade görünüm",
    viewSadeSub: "Monitör, analiz ve hesaplayıcı (varsayılan)",
    viewDetailed: "Ayrıntılı görünüm",
    viewDetailedSub: "Bütün modeller, hücreler ve kurallar (eski arayüz, aynen)",
    checks: "Doğrulama",
    repoMode: "Repo modu",
    standalone: "Bağımsız mod",
    dataDir: "Uygulama verisi",
    about: "Hakkında",
    aboutSub: "Bu sürümün içindeki modeller ve dosyalar.",
    appVersion: "Uygulama sürümü",
    integrity: "Model bütünlüğü",
    integrityOk: "tamam",
    integrityBad: "bozuk: tahmin kapalı",
    preModels: "Listeleme öncesi modeller",
    postModels: "D1 sonrası modeller",
    embeddedScores: "Gömülü skor kopyası",
    embeddedTufe: "Gömülü TÜFE tablosu",
    yes: "var",
    no: "yok",
    appData: "Uygulama verisi",
    appDataVal: "kullanıcı klasöründe, repo dışında",
    fullList: "Gömülü modellerin tam listesi ve parametre özetleri (ayrıntılı görünüm)",
  },

  // ---------------------------------------------------------------- sihirbaz kabuğu (K-UI-11)
  wizard: {
    freezeCrumb: "Sicil / Yeni resmi kayıt",
    postD1Crumb: "Sicil / D1 sonrası kayıt",
    keepInMind: "Akılda tut",
    keep1: "Zaman kanıtı push'tur, yerel saat değil. Push ilk işlem gününden önceyse kayıt canlı adayıdır.",
    keep2: "Kayda giren değerler tahmin ekranındaki değerlerin aynısıdır.",
    keep3: "İptal, ilk işlem gününden önce yapılabilir; sonrasında Python reddeder.",
    back: "Sicile dön",
    recordCrumb: "Sicil / Kayıt sayfası",
  },
};

// Uygulama belleğindeki durum. Kalıcı olan yalnız Rust'ın yazdığı dosyalardır (config, kişisel
// kayıtlar); kullanıcı beyanı (şerit) yalnız burada ve saklanırsa kişisel kayıtta durur (§3g).
import type { StageId } from "./i18n/tr";
import type { DocDraft, FieldDraftUI } from "./render/freeze";
import type { F6VM } from "./render/inputs";
import type { PathCondVM } from "./render/ceiling";
import type { ScenarioHeader } from "./render/results";
import type {
  AppError,
  AppInfo,
  CeilingSummary,
  ConfigView,
  F6Doc,
  FormCheck,
  FreezeResult,
  InputsDocPreview,
  LoadedScenario,
  ManifestDoc,
  ModelRun,
  PathDisplayRow,
  PathParamsInfo,
  PostD1CancelResult,
  PostD1FreezeResult,
  PostD1Preflight,
  PostD1View,
  Preflight,
  RecordCeiling,
  RegistryView,
  ScoreHints,
  OotModelDetail,
  OotPanelView,
  ScoresPostD1View,
  ScoresView,
  SourceDocsView,
  StreakView,
  UserDayState,
} from "./types";

export interface FormState {
  stage: StageId | null;
  fields: Record<string, string>;
  tickerLabel: string;
  check: FormCheck | null;
  tickers: string[];
  prefillTicker: string;
  prefillMsg: string | null;
  missingReasons: Record<string, string>;
  f6: F6VM;
  busy: boolean;
  error: AppError | null;
}

export interface ResultsState {
  runs: ModelRun[];
  inputs: Record<string, string | null>;
  inputDates: Record<string, string | null>;
  stage: StageId;
  tickerLabel: string;
  f6: F6Doc;
  source: "FORM" | "SCENARIO";
  scenario: ScenarioHeader | null;
  savedId: string | null;
}

export interface ViewState {
  hidden: string[];
  openCard: string | null;
  openWarnings: string | null;
  /** D1..D10 "seri sürüyor" beyanı: yalnız şerit etiketi (U52); hiçbir hesaba ve komuta girmez. */
  declared: boolean[];
  /** Yüklenen kişisel kayıtta desteklenmeyen beyan türü vardı ve yok sayıldı (U52-2). */
  declDropped: boolean;
  jSelected: number | null;
  tab: "ceiling" | "return";
}

/** Doğruluk paneli (§3d): dosya Rust'tan gelir, ön uçta yalnız görünüm durumu tutulur. */
export interface AccuracyState {
  scores: ScoresView | null;
  /** Gömülü tavan yolu künyesi: model kartındaki "seri modeli" satırı (G3). */
  pathParams: PathParamsInfo[];
  loaded: boolean;
  hidden: string[];
  /** Açık model blokları (kullanıcı açtıkça büyür). */
  open: string[];
  /** D1 sonrası skorlar (`scores_post_d1_view`; repo modu); yüklenmediyse `undefined`. */
  postD1?: ScoresPostD1View | null;
  /** Zaman-dışı panel (EK 3 §7): görünüm, blok başına seçili model ve ayrıntısı; yüklenmediyse `undefined`. */
  oot?: OotPanelView | null;
  ootSelected?: Record<string, string>;
  ootDetails?: Record<string, OotModelDetail | null>;
  error: AppError | null;
}

/** Sicil ekranı ve arz sayfası (§3e sonu, §3g). Sicilin kopyası tutulmaz: her açılışta repo okunur. */
export interface RegistryState {
  /** post_d1: "D1 sonrası kayıt" sihirbazı (EK 3 §6.6). */
  mode: "list" | "record" | "wizard" | "post_d1";
  view: RegistryView | null;
  ticker: string | null;
  selected: number;
  ceiling: RecordCeiling | null;
  /** Tavan serisi kartı (Rust `record_summary`; yalnız kayıttan). */
  summary: CeilingSummary | null;
  streak: StreakView | null;
  /** Kayıttaki tavan yolu modellerinin gösterim türevleri (Rust: path_display / path_conditional). */
  pathDisplay: PathDisplayRow[];
  pathParams: PathParamsInfo[];
  pathCond: PathCondVM[];
  jSelected: number | null;
  tab: "ceiling" | "return";
  /** D1 sonrası (EK 3 §6.5): `post_d1_view` (S yalnız kayıttan), seçili POST_D1 kaydı sekmesi ve hata. */
  postD1: PostD1View | null;
  postD1File: string | null;
  postD1Error: AppError | null;
  /** Kullanıcı beyanı: yalnız bellekte ve yalnız etiket (U39, U52). */
  declared: boolean[];
  declDropped: boolean;
  raw: string | null;
  cancelReason: string;
  cancelDone: string | null;
  error: AppError | null;
}

/** "D1 sonrası kayıt" sihirbazı (EK 3 §6.6): Python yalnız düğmeyle çağrılır; komut blokları çalıştırılmaz. */
export interface PostD1WizardState {
  ticker: string;
  preflight: PostD1Preflight | null;
  outcomesTodo: string[] | null;
  frozen: PostD1FreezeResult | null;
  cancelFile: string;
  cancelReason: string;
  cancelled: PostD1CancelResult | null;
  busy: string | null;
  error: AppError | null;
}

/** Dondur sihirbazının taslağı (§3e). Hiçbir adımı uygulama kendiliğinden çalıştırmaz. */
export interface FreezeState {
  ticker: string;
  company: string;
  docs: DocDraft[];
  copied: SourceDocsView | null;
  manifest: ManifestDoc | null;
  fields: Record<string, FieldDraftUI>;
  collectionRules: string;
  ftdSource: string;
  preflight: Preflight | null;
  preview: InputsDocPreview | null;
  written: InputsDocPreview | null;
  pit: string[] | null;
  acknowledged: boolean;
  frozen: FreezeResult | null;
  busy: string | null;
  error: AppError | null;
}

export const store = {
  info: null as AppInfo | null,
  config: null as ConfigView | null,
  hints: null as ScoreHints | null,
  form: {
    stage: null,
    fields: {},
    tickerLabel: "",
    check: null,
    tickers: [],
    prefillTicker: "",
    prefillMsg: null,
    missingReasons: {},
    f6: { mode: "NONE", manual: "", market20: null, market20ForT: null, busy: false, error: null },
    busy: false,
    error: null,
  } as FormState,
  results: null as ResultsState | null,
  accuracy: { scores: null, pathParams: [], loaded: false, hidden: [], open: [], error: null } as AccuracyState,
  view: { hidden: [], openCard: null, openWarnings: null, declared: Array(10).fill(false), declDropped: false, jSelected: null, tab: "ceiling" } as ViewState,
  registry: {
    mode: "list",
    view: null,
    ticker: null,
    selected: 0,
    ceiling: null,
    summary: null,
    streak: null,
    pathDisplay: [],
    pathParams: [],
    pathCond: [],
    jSelected: null,
    tab: "ceiling",
    postD1: null,
    postD1File: null,
    postD1Error: null,
    declared: Array(10).fill(false),
    declDropped: false,
    raw: null,
    cancelReason: "",
    cancelDone: null,
    error: null,
  } as RegistryState,
  postD1Wizard: {
    ticker: "",
    preflight: null,
    outcomesTodo: null,
    frozen: null,
    cancelFile: "",
    cancelReason: "",
    cancelled: null,
    busy: null,
    error: null,
  } as PostD1WizardState,
  freeze: {
    ticker: "",
    company: "",
    docs: [],
    copied: null,
    manifest: null,
    fields: {},
    collectionRules: "",
    ftdSource: "",
    preflight: null,
    preview: null,
    written: null,
    pit: null,
    acknowledged: false,
    frozen: null,
    busy: null,
    error: null,
  } as FreezeState,
};

/** Beyan durumunu kişisel kayıt biçimine çevirir: "CEILING" | null (U52: tek tür). */
export function declaredDays(declared: boolean[]): (UserDayState | null)[] {
  return declared.map((d) => (d ? "CEILING" : null));
}

/** Kişisel kayıttan gelen beyan alanı: yalnız "CEILING" kabul edilir, ötekiler yok sayılır (U52-2). */
export function resetView(days: (string | null)[] = []): void {
  const declared: boolean[] = Array(10).fill(false);
  let dropped = false;
  days.slice(0, 10).forEach((d, i) => {
    if (d === null || d === undefined) return;
    if (d === "CEILING") declared[i] = true;
    else dropped = true;
  });
  store.view = { ...store.view, openCard: null, openWarnings: null, declared, declDropped: dropped, jSelected: null, tab: "ceiling" };
}

/** Yüklenen kişisel kaydın çıktıları, dosyadaki gibi (yeniden hesaplanmaz; U36). */
export function resultsFromScenario(l: LoadedScenario): ResultsState {
  const d = l.doc;
  const runs: ModelRun[] = Object.entries(d.outputs).map(([model_id, o]) => ({ model_id, ...o }));
  return {
    runs,
    inputs: d.inputs,
    inputDates: d.input_dates ?? {},
    stage: d.stage as StageId,
    tickerLabel: d.ticker_label ?? "",
    f6: d.f6,
    source: "SCENARIO",
    scenario: { title: d.title, created_at_local: d.created_at_local, same_index: l.same_index },
    savedId: null,
  };
}

// ---------------------------------------------------------------- sade görünüm yardımcıları (FAZ9_APP_UI; yalnız ekleme)
// Sade görünümde kullanıcı beyanı (U52 şeridi) yoktur (K-UI-8): kayıt isteği beyansız kurulur. Beyan alanı adı bu dosyada
// kalır (U52-5 statik taraması: beyan yalnız izinli dosyalarda geçer).

/** Sade sonuç ekranının kişisel kayıt isteği: beyan alanı her zaman boş. */
export function scenarioRequestWithoutDeclaration(r: ResultsState, title: string): import("./api").SaveScenarioReq {
  return {
    title,
    stage: r.stage,
    ticker_label: r.tickerLabel,
    inputs: r.inputs,
    input_dates: r.inputDates,
    f6: r.f6,
    observed_streak_user: null,
  };
}

/** Kişisel kaydı açar (eski Kişisel kayıtlar ekranıyla aynı iki adım): çıktılar aynen, beyan etiketi ayrıntılı görünüm için korunur. */
export function openScenarioIntoStore(l: LoadedScenario): void {
  store.results = resultsFromScenario(l);
  resetView(l.doc.observed_streak_user?.days ?? []);
}

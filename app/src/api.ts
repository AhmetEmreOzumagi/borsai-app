// Rust komutlarının tipli sarmalayıcıları (SPEC_APP §6). Tauri argüman adlarını camelCase'e çevirir.
import { invoke } from "@tauri-apps/api/core";

import type {
  AppConfig,
  AppInfo,
  CancelResult,
  CeilingDisplay,
  CeilingSummary,
  ConfigView,
  ExportAllResult,
  F6Doc,
  FormCheck,
  FreezeResult,
  InputDocument,
  InputsDocPreview,
  InputsDocReq,
  LoadedScenario,
  ManifestDoc,
  Market20View,
  ModelOutput,
  ModelRun,
  OotModelDetail,
  OotPanelView,
  PathConditional,
  PathDisplayRow,
  PathParamsInfo,
  PostD1CancelResult,
  PostD1FreezeResult,
  PostD1Preflight,
  PostD1RecordRow,
  PostD1View,
  Preflight,
  RecordCeiling,
  RegistryView,
  RepoCheck,
  ScenarioSummary,
  ScoreHints,
  ScoresPostD1View,
  ScoresView,
  SourceDocReq,
  SourceDocsView,
  StreakView,
  UserDayState,
} from "./types";

/** `path_conditional` kaynağı: dondurulmuş kayıt (resmi görünüm) ya da eldeki çıktı. */
export interface PathSourceReq {
  kind: "RECORD" | "OUTPUT";
  ticker: string | null;
  file: string | null;
  output: ModelOutput | null;
  params_sha256: string | null;
}

export interface SaveScenarioReq {
  title: string;
  stage: string;
  ticker_label: string | null;
  inputs: Record<string, string | null>;
  input_dates: Record<string, string | null>;
  f6: F6Doc;
  observed_streak_user: { ticker: string | null; days: (UserDayState | null)[] } | null;
}

export const api = {
  appInfo: () => invoke<AppInfo>("app_info"),
  getConfig: () => invoke<ConfigView>("get_config"),
  setConfig: (cfg: AppConfig) => invoke<ConfigView>("set_config", { cfg }),
  validateRepo: (path: string, pythonPath: string | null) => invoke<RepoCheck>("validate_repo", { path, pythonPath }),
  // t: ilk işlem günü; TÜFE ayı (T − 2) Rust'ta ondan türetilir (EK 3 §3.3; elle TÜFE girdisi yok)
  predictAll: (inputs: Record<string, string | null>, f6: { value: string | null; refusal: string | null }, t: string | null) =>
    invoke<ModelRun[]>("predict_all", { inputs, f6, t }),
  market20: (t: string | null) => invoke<Market20View>("market20_via_python", { refDate: null, t }),
  checkForm: (stage: string | null, fields: Record<string, string>) => invoke<FormCheck>("check_form", { stage, fields }),
  listInputDocuments: () => invoke<string[]>("list_input_documents"),
  readInputDocument: (ticker: string) => invoke<InputDocument>("read_input_document", { ticker }),
  ceilingDisplay: (models: { model_id: string; S: number[] }[], j: number, ipoPriceTl: string | null) =>
    invoke<CeilingDisplay>("ceiling_display", { models, j, ipoPriceTl }),
  // Tavan serisi kartı (EK 3 §5): Rust derler (ceiling_display + skor okuyucuları); beyan parametresi YOK (U52-5).
  ceilingSummary: (runs: ModelRun[], j: number, jObserved: number | null, t: string | null) =>
    invoke<CeilingSummary>("ceiling_summary", { runs, j, jObserved, t }),
  // Resmi görünüm: S yalnız dondurulmuş kayıttan (U38, U62); predict_all çağrılmaz.
  recordSummary: (ticker: string, file: string, j: number, jObserved: number | null) =>
    invoke<CeilingSummary>("record_summary", { ticker, file, j, jObserved }),
  // Beyan parametresi YOK (U52-5): şerit ve resmi j yalnız data/outcomes/<T>.csv'den gelir.
  streakView: (ticker: string | null) => invoke<StreakView>("streak_view", { ticker }),
  // Tavan yolu (EK 2 §4): fiyat türevi, gömülü künye ve koşullu getiri. Beyan bu çağrılarda da yok.
  pathDisplay: (models: { model_id: string; output: ModelOutput | null }[]) => invoke<PathDisplayRow[]>("path_display", { models }),
  pathParams: () => invoke<PathParamsInfo[]>("path_params"),
  pathConditional: (modelId: string, source: PathSourceReq, jOrT: number, stateName: string) =>
    invoke<PathConditional>("path_conditional", { modelId, source, jOrT, stateName }),
  saveScenario: (req: SaveScenarioReq) => invoke<ScenarioSummary>("save_scenario", { req }),
  listScenarios: () => invoke<ScenarioSummary[]>("list_scenarios"),
  loadScenario: (id: string) => invoke<LoadedScenario>("load_scenario", { id }),
  deleteScenario: (id: string) => invoke<void>("delete_scenario", { id }),
  scoreHints: () => invoke<ScoreHints | null>("score_hints"),
  scoresView: () => invoke<ScoresView | null>("scores_view"),
  exportScenario: (id: string, target: string) => invoke<string>("export_scenario", { id, target }),
  exportAllScenarios: (target: string) => invoke<ExportAllResult>("export_all_scenarios", { target }),
  // dondur akışı (§3e) ve sicil (§3g)
  freezePreflight: (t: string | null) => invoke<Preflight>("freeze_preflight", { t }),
  copySourceDocs: (ticker: string, docs: SourceDocReq[]) => invoke<SourceDocsView>("copy_source_docs", { ticker, docs }),
  readSourceManifest: (ticker: string) => invoke<ManifestDoc>("read_source_manifest", { ticker }),
  previewInputsDoc: (req: InputsDocReq) => invoke<InputsDocPreview>("preview_inputs_doc", { req }),
  writeInputsDoc: (req: InputsDocReq, confirm: boolean) => invoke<InputsDocPreview>("write_inputs_doc", { req, confirm }),
  inputsPitCheck: (relPath: string) => invoke<string[]>("inputs_pit_check", { relPath }),
  freezeRecord: (relPath: string) => invoke<FreezeResult>("freeze_record", { relPath }),
  cancelRecord: (relPath: string, reason: string) => invoke<CancelResult>("cancel_record", { relPath, reason }),
  registryView: () => invoke<RegistryView>("registry_view"),
  recordCeiling: (ticker: string, file: string, j: number) => invoke<RecordCeiling>("record_ceiling", { ticker, file, j }),
  readRecordJson: (ticker: string, file: string) => invoke<unknown>("read_record_json", { ticker, file }),
  // D1 sonrası (EK 3 §6.5–§6.6): kayıt okuyucu (yalnız registry/post_d1/), sihirbaz, D1 sonrası skorlar (repo modu)
  postD1Records: (ticker: string) => invoke<PostD1RecordRow[]>("post_d1_records", { ticker }),
  postD1View: (ticker: string, j: number, file: string | null) => invoke<PostD1View>("post_d1_view", { ticker, j, file }),
  postD1Preflight: (ticker: string) => invoke<PostD1Preflight>("post_d1_preflight", { ticker }),
  postD1Freeze: (ticker: string) => invoke<PostD1FreezeResult>("post_d1_freeze", { ticker }),
  postD1Cancel: (relPath: string, reason: string) => invoke<PostD1CancelResult>("post_d1_cancel", { relPath, reason }),
  postD1Todo: (kind: "OUTCOMES" | "RECORD", ticker: string, through: string | null) =>
    invoke<string[]>("post_d1_todo", { kind, ticker, through }),
  scoresPostD1View: () => invoke<ScoresPostD1View>("scores_post_d1_view"),
  // Zaman-dışı panel (EK 3 §7): görünüm satırsız; satırlar yalnız açık küme bloğunda ve yalnız `open == true` (K-P3-1)
  scoresOotView: () => invoke<OotPanelView>("scores_oot_view"),
  scoresOotModel: (block: string, modelId: string) => invoke<OotModelDetail | null>("scores_oot_model", { block, modelId }),
};

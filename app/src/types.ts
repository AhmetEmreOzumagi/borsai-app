// Rust komut sözleşmeleri (serde ile aynı alan adları; SPEC_APP §6).

export interface AppError {
  code: string;
  message: string;
  detail?: string;
}

export type Kind = "hazard" | "km" | "ceiling_path" | "market20" | "pb" | "linear" | "rule";

export interface ModelInfo {
  model_id: string;
  kind: Kind;
  params_sha256: string;
  description: string | null;
  algorithm: string | null;
  training_n: number | null;
  training_cutoff_date: string | null;
}

/** TÜFE tablosunun durumu (Rust `commands::predict::TufeStatus`; EK 3 §3.5). */
export interface TufeStatus {
  source: "REPO" | "EMBEDDED";
  path: string | null;
  valid: boolean;
  error: string | null;
  through_month: string | null;
  file_sha256: string | null;
  pins: { model_id: string; through_month: string; ok: boolean }[];
}

/** Bir T için TÜFE girdisinin durumu (Rust `commands::predict::TufeInfo`; EK 3 §3.3). */
export interface TufeInfo {
  source: "REPO" | "EMBEDDED" | "RECORD";
  path: string | null;
  file_sha256: string | null;
  through_month: string | null;
  t: string | null;
  month: string | null;
  index: string | null;
  release_date: string | null;
  bulletin_id: string | null;
  refusal: "TUFE_MISSING" | "TUFE_NOT_PIT" | "TUFE_FILE_MISMATCH" | null;
  reason: "T_UNKNOWN" | "TABLE_INVALID" | "MONTH_MISSING" | "NOT_PIT" | "PIN_MISMATCH" | null;
  detail: string | null;
  append_command: string | null;
  pin_ok: boolean | null;
}

/** Tavan serisi kartı (Rust `commands::ceiling::CeilingSummary`; EK 3 §5.2). Bütün değerler Rust'tan. */
export interface SummaryCond {
  p_break_next: number;
  expected_remaining: number;
  median_l: number;
  mode_l: number;
  p_mode: number | null;
  s_cond_5: number | null;
  s_cond_10: number | null;
}

export interface NearEraView {
  supported: boolean;
  schema_version: string | null;
  label: string | null;
  comparator: string | null;
  metric: string | null;
  subset: string | null;
  diff: Num | null;
  ci95: Num[] | null;
  n: number | null;
  n_blocks: number | null;
}

export interface SummaryRow {
  model_id: string;
  /** POST_D1: resmi görünümde etkin D1 sonrası kaydı ve j ≥ 1 varken (EK 3 §6.5, K-P2-3). */
  role: "FEATURED" | "CANDIDATE" | "RULE" | "PB" | "CONSTANT" | "POST_D1";
  in_record: boolean;
  status: string | null;
  refused: { code: string; field: string | null } | null;
  expected_l: number | null;
  median_l: number | null;
  mode_l: number | null;
  /** D{mode_l + 1} (1 ≤ mode_l ≤ 9); Rust verir. */
  mode_break_day: number | null;
  p_mode: number | null;
  p_ge3: number | null;
  p_ge5: number | null;
  p_10: number | null;
  cond: SummaryCond | null;
  near_era: NearEraView | null;
  vault: { status: "CLOSED" | "OPEN" | "UNAVAILABLE" | "NONE"; verdict: string | null; diff: Num | null; ci95: Num[] | null; n: number | null; rule_id: string | null };
  live: { n_scored: number | null; verdict: string | null };
}

export interface CandidateCheck {
  model_id: string;
  in_index: boolean;
  primary_verdict: string | null;
  model_value: number | null;
  v0_ci95_hi: number | null;
  near_era_label: string | null;
  k1: boolean;
  k2: boolean;
  k3: boolean;
  eligible: boolean;
}

export interface CeilingSummary {
  featured: { model_id: string; reason: "VAULT_CLOSED_V0_DEFAULT" | "RULE_5_5" | "RULE_5_5_NONE_ELIGIBLE_V0"; candidates: CandidateCheck[] };
  featured_params_sha256: string | null;
  j: number;
  j_source: "OFFICIAL" | "HYPOTHETICAL" | "NONE";
  official: boolean;
  record_file: string | null;
  f3_missing: boolean;
  rows: SummaryRow[];
  integrity: { rule: string; model_id: string | null; detail: string } | null;
  scores: { source: string; sha12: string; generated_at_utc: string | null } | null;
  oot: { source: string; generated_at_utc: string | null; sha12: string | null; vault_open: boolean; rows_present: boolean; unsupported_version: string | null; integrity: { rule: string; model_id: string | null; detail: string } | null } | null;
  tufe: TufeInfo | null;
  /** "Düşüş (D10)" kartı (EK 3 §8.4; Rust `commands::fall`); gömülü kümede (C) yoksa null. */
  fall: FallSummary | null;
}

/** (C) adayının k1–k3 durumu (Rust `scores::featured_fall`; dosyadaki alanların karşılaştırması). */
export interface FallCandidateCheck {
  model_id: string;
  in_index: boolean;
  primary_verdict: string | null;
  model_value: number | null;
  v15_ci95_hi: number | null;
  near_era_label: string | null;
  near_era_comparator: string | null;
  near_era_ci95_lo: number | null;
  k1: boolean;
  k2: boolean;
  k3: boolean;
  eligible: boolean;
  first_failed: "k1" | "k2" | "k3" | null;
}

/** Bir ufukta düşüş kartı değerleri: p_fall = 1 − p_up ve yüzdeler Rust'ta (pct_up = 100 − pct_fall). */
export interface FallCell {
  p_up: number | null;
  p_fall: number | null;
  pct_fall: number | null;
  pct_up: number | null;
}

export interface FallCard {
  description: string | null;
  training_n: number | null;
  training_cutoff: string | null;
  params_sha256_8: string | null;
  n_variants_same_data: number | null;
  primary_cell: { output: string; horizon_or_k: string | null; metric: string; rule_ids: string[] } | null;
}

export interface FallRow {
  model_id: string;
  role: "FEATURED" | "CANDIDATE" | "RULE" | "COMPARATOR";
  in_record: boolean;
  status: string | null;
  refused: { code: string; field: string | null } | null;
  d10: FallCell;
  d5: FallCell;
  near_era: NearEraView | null;
  vault: SummaryRow["vault"];
  live: SummaryRow["live"];
  first_failed: "k1" | "k2" | "k3" | null;
  card: FallCard | null;
}

export interface FallSummary {
  featured: { model_id: string | null; reason: "VAULT_CLOSED" | "RULE_5_5" | "RULE_5_5_NONE_ELIGIBLE"; candidates: FallCandidateCheck[] };
  official: boolean;
  record_file: string | null;
  rows: FallRow[];
  integrity: { rule: string; model_id: string | null; detail: string } | null;
  scores: { source: string; sha12: string; generated_at_utc: string | null } | null;
  oot: CeilingSummary["oot"];
  tufe: TufeInfo | null;
}

export interface AppInfo {
  app_version: string;
  build_git_head: string;
  build_git_status_models_scores: string;
  index_sha256: string;
  /** İkinci dizin (models/INDEX_POST_D1.json; EK 3 §4.1 P2). */
  index_post_d1_sha256: string;
  embedded_post_d1_models: string[];
  embedded_models: string[];
  ignored_index_models: string[];
  scores_embedded: boolean;
  /** Gömülü TÜFE tablosu (bağımsız modun kaynağı); tablo gömülü değilse null. */
  tufe_embedded: TufeStatus | null;
  integrity_ok: boolean;
  integrity_error: AppError | null;
  models: ModelInfo[];
}

/** JSON'da sonlu olmayan binary64 metin olarak gelir ("NaN", "Infinity", "-Infinity"). */
export type Num = number | string;

export interface Warning {
  code: string;
  message: string;
  feature?: string;
  horizon?: string;
  /** `IPO_PRICE_NOT_ON_TICK_GRID`: metin (str(Decimal)); ötekilerde sayı. */
  value?: Num | string;
  used?: Num;
  train_min?: Num;
  train_max?: Num;
  /** Yalnız `IPO_PRICE_NOT_ON_TICK_GRID` (tavan yolu): metin alanlar. */
  field?: string;
  snapped?: string;
  tick?: string;
  /** Yalnız `WARN_D1_SPECIAL_TRADES` (D1 sonrası; EK 3 §6.3): metin alanlar (str(Decimal)). */
  special_trade_volume?: string;
  volume?: string;
  /** Yalnız `WARN_D1_LOCK_INCONSISTENT`: mantıksal alanlar. */
  open_at_U?: boolean;
  high_at_U?: boolean;
  close_at_U?: boolean;
}

export interface Refusal {
  code: string;
  field: string | null;
  reason: string;
}

export interface HorizonCell {
  return: Num | null;
  return_unclipped: Num | null;
  return_clipped: "UPPER" | "LOWER" | null;
  price: Num | null;
  p_up: Num | null;
  direction: "UP" | "DOWN" | null;
}

/** `ceiling_path` limit yolu: metin alanlar aynen (Decimal `str()`); `rho` binary64. */
export interface LimitPath {
  ipo_price: string;
  snapped_ipo_price: string;
  tick: string;
  C: string[];
  rho: Num[];
}

/** `post_break.cells` öğesi (SPEC_CEILING_PATH_V0 §3): havuzlanan hücre ve merdiven kaynakları. */
export interface PostBreakCell {
  group: string;
  m: number;
  n: number;
  pooled: boolean;
  sources: [string, number][];
}

/** `ceiling_path` D_h hücresi (koşulsuz ve koşullu çıktıda aynı alanlar; koşulluda `status` de var). */
export interface PathHorizon {
  return: Num | null;
  p_up: Num | null;
  mean: Num | null;
  q10: Num | null;
  q50: Num | null;
  q90: Num | null;
  limit_path_return: Num | null;
  S_h: Num | null;
  p_limit_path: Num | null;
  n_atoms: number;
  post_break: { cells: PostBreakCell[]; status: string };
  /** Yalnız koşullu çıktı: OK | POST_BREAK_INSUFFICIENT | REALIZED. */
  status?: string;
  realized_return?: Num;
}

/** linear / rule / pb / market20 ve hazard / km çıktılarının birleşimi (alan adları Python'daki gibi). */
export interface ModelOutput {
  model_id: string | null;
  D1?: HorizonCell | null;
  D3?: HorizonCell | null;
  D5?: HorizonCell | null;
  D10?: HorizonCell | null;
  hazard?: Num[] | null;
  S?: Num[] | null;
  P_L?: Num[] | null;
  P_close_ceiling?: Num[] | null;
  /** Yalnız `ceiling_path`. D1..D10 hücreleri `PathHorizon`'dur (HorizonCell değil). */
  limit_path?: LimitPath | null;
  clipped?: boolean | null;
  warnings: Warning[];
  refused: Refusal | null;
  features?: Record<string, Num> | null;
  f6_market20?: Num | null;
}

/** `predict_all` sonucu, model başına (borsai.freeze.run_model alanları + model_id, params_sha256). */
export interface ModelRun {
  model_id: string;
  params_sha256: string;
  kind: Kind;
  status: "PREDICTED" | "REFUSED" | "ERROR";
  refusal: Refusal | null;
  output: ModelOutput | null;
}

export interface FormNote {
  field: string;
  code: string;
  level: "error" | "warn" | "info";
  name?: string;
  value?: string;
}

export interface FormCheck {
  stage: string | null;
  normalized: Record<string, string | null>;
  notes: FormNote[];
  suggestions: Record<string, string>;
  requirements: Record<string, string>;
  model_inputs: Record<string, string | null>;
}

export interface Market20Record {
  ref_date: string;
  f6: string | null;
  refusal: string | null;
  S0_date: string | null;
  S20_date: string | null;
  close_S0: string | null;
  close_S20: string | null;
  calendar_sha256: string | null;
  xu100_sha256: string | null;
}

export interface Market20View {
  record: Market20Record;
  t_unknown: boolean;
}

export interface InputDocument {
  ticker: string;
  company: string | null;
  stage: string | null;
  rel_path: string;
  values: Record<string, string | null>;
  missing_reasons: Record<string, string>;
}

export interface CondView {
  S_cond: (number | null)[];
  P_L_cond: (number | null)[];
  p_break_next: number;
  expected_l: number;
  expected_remaining: number;
  median_l: number;
  /** En olası l (l ≥ j; eşitlikte en küçük); Rust görüntüleme türevi. */
  mode_l: number;
}

export interface CeilingRow {
  model_id: string;
  constant: boolean;
  S: number[];
  P_L: number[];
  expected_l: number;
  median_l: number;
  /** En olası l = argmax P(L = l) (eşitlikte en küçük); Rust görüntüleme türevi. */
  mode_l: number;
  cond: CondView | null;
}

export interface CeilingDisplay {
  j: number;
  rows: CeilingRow[];
  price_hint: { k: number; price: number }[] | null;
  /** Hesaplayıcı eki (FAZ9_UI_FIX K-FIX-3): yalnız `ceiling_display` ve `record_ceiling` komut çıktısında. */
  calc?: CalcView | null;
}

/** "Geçmiş arzlarda" (K-FIX-3): kuralın seçilen j'deki koşullu değeri ve sayımları; hepsi Rust'tan (`commands::ceiling::CalcHistory`). */
export interface CalcHistory {
  rule_id: string;
  in_rows: boolean;
  /** P(L ≥ j+1 | L ≥ j) = S_{j+1} / S_j; Rust alanı. */
  p_next: number | null;
  s_cond: (number | null)[];
  n_train: number | null;
  n_at_j: number | null;
  n_next: number | null;
}

/** Model dosyasındaki `day_groups` (Rust okur; metin ön uçta kurulur). */
export interface DayGroups {
  model_id: string;
  groups: number[][];
}

export interface CalcView {
  j: number;
  history: CalcHistory;
  day_groups: DayGroups[];
}

// ---------------------------------------------------------------- tavan yolu gösterimi (EK 2 §4)

/** `path_display` hücresi: fiyat satırı kuralı (limit atomu → `C_h` metni, değilse ≈). */
export interface PathPriceCell {
  h: number;
  on_limit_path: boolean;
  c_text: string | null;
  approx_price: number | null;
}

export interface PathDisplayRow {
  model_id: string;
  ipo_price: string | null;
  snapped_ipo_price: string | null;
  tick: string | null;
  c: string[];
  cells: PathPriceCell[];
}

/** `path_params`: gömülü tavan yolu modellerinin hücre notu ve seri modeli künyesi. */
export interface PathParamsInfo {
  model_id: string;
  survival_model_id: string | null;
  survival_model_sha256: string | null;
  n_min: number;
  n_ipo: number | null;
  n_obs: number | null;
  cutoff_date: string | null;
}

/** Koşullu getiride kullanılan kapanış: dosyadan ya da limit yolu varsayımı (varsayımsal j). */
export interface CloseRow {
  h: number;
  origin: "FILE" | "LIMIT_PATH";
  close: string;
  session_date: string | null;
}

export interface PathMismatch {
  t: number;
  close: string;
  c: string;
}

/** `predict_path.conditional` / `conditional_after_break` çıktısı (D1..D10 anahtarlarıyla). */
export interface PathCondResult {
  state: "STREAK_ONGOING" | "AFTER_BREAK";
  j?: number;
  t?: number;
  note?: string;
  S_j?: Num;
  S_cond?: Record<string, Num>;
  P_L_cond?: Record<string, Num>;
  limit_path_mismatch: number;
}

export interface PathConditional {
  model_id: string;
  state: "STREAK_ONGOING" | "AFTER_BREAK";
  j_or_t: number;
  source_kind: string;
  source_file: string | null;
  params_sha256: string;
  closes: CloseRow[];
  assumed: boolean;
  limit_path_mismatch: number;
  mismatch: PathMismatch | null;
  result: PathCondResult;
}

export type DayState = "CEILING" | "NOT_CEILING" | "PENDING" | "NO_LABEL";
/** Tek beyan türü: "seri sürüyor" (U52). Yalnız etiket; hiçbir hesaba girmez. */
export type UserDayState = "CEILING";

export interface StreakDay {
  h: number;
  session_date: string | null;
  file: DayState | null;
}

export interface StreakView {
  ticker: string | null;
  file_status: "FOUND" | "MISSING" | "NO_REPO" | "NO_TICKER";
  file_rel_path: string | null;
  as_of: string | null;
  days: StreakDay[];
  /** Resmi j (yalnız dosyadan); beyan bu değeri değiştirmez. */
  j_observed: number | null;
  broken: boolean;
  unlabeled: boolean;
}

/** Beyanın resmi veriye göre durumu (yalnız etiket render'ı; SPEC_APP §3g). */
export type DeclarationState = "AHEAD" | "CONFLICT" | "SUPERSEDED";

export interface F6Doc {
  value: string | null;
  refusal: string | null;
  origin: "REPO_PYTHON" | "MANUAL" | "NONE";
  S0_date: string | null;
  S20_date: string | null;
  xu100_sha256: string | null;
  ref_date: string | null;
}

export interface ScenarioOutput {
  params_sha256: string;
  kind: Kind;
  status: ModelRun["status"];
  refusal: Refusal | null;
  output: ModelOutput | null;
}

export interface ScenarioDoc {
  schema_version: string;
  official: false;
  scenario_id: string;
  title: string;
  created_at_local: string;
  app_version: string;
  build_git_head: string;
  stage: string;
  ticker_label: string;
  inputs: Record<string, string | null>;
  input_dates?: Record<string, string | null>;
  f6: F6Doc;
  models_index_sha256: string;
  outputs: Record<string, ScenarioOutput>;
  observed_streak_user?: { ticker: string | null; days: (UserDayState | null)[] };
}

export interface LoadedScenario {
  doc: ScenarioDoc;
  same_index: boolean;
  embedded_index_sha256: string;
}

export interface ScenarioSummary {
  scenario_id: string;
  status: "OK" | "OLD_VERSION" | "UNREADABLE";
  title: string | null;
  created_at_local: string | null;
  stage: string | null;
  ticker_label: string | null;
  app_version: string | null;
  models_index_sha256: string | null;
  same_index: boolean;
  schema_version: string | null;
}

/** Tümünü dışa aktarma sonucu (§3f): tek JSON dizisi + okunamayan dosya sayısı. */
export interface ExportAllResult {
  path: string;
  n_exported: number;
  n_unreadable: number;
}

export interface ScoreHint {
  card: {
    training_n?: number;
    training_cutoff?: string;
    params_sha256_8?: string;
    n_variants_same_data?: number;
  } | null;
  primary_cell: { output?: string; horizon_or_k?: string; metric?: string; rule_ids?: string[] } | null;
  mae: Record<string, { model_value: number | null; n: number | null }>;
  live_n_scored: number | null;
  live_primary_verdict: string | null;
}

export interface ScoreHints {
  source: "REPO" | "EMBEDDED";
  unsupported_version: string | null;
  generated_at_utc: string | null;
  as_of_session: string | null;
  sha12: string;
  index_mismatch: boolean;
  models: Record<string, ScoreHint>;
}

export interface AppConfig {
  schema_version: string;
  repo_root: string | null;
  python_path: string | null;
  scores_source: "REPO" | "EMBEDDED";
  /** Görünüm (FAZ9_APP_UI K-UI-1): yoksa Rust "SADE" sayar (geriye uyumlu ek alan). */
  ui_view?: "SADE" | "AYRINTILI";
}

export interface RepoCheckItem {
  id: string;
  ok: boolean;
  required: boolean;
  detail: string;
}

export interface RepoCheck {
  repo_root: string;
  python_path: string;
  ok: boolean;
  checks: RepoCheckItem[];
  git_head: string | null;
  market20_sources: { xu100_last?: string; calendar_last?: string; xu100_sha256?: string } | null;
}

/** Gömülü sicil anlık görüntüsünün künyesi (FAZ9_SNAPSHOT K-SNAP-2/3; Rust `registry_snapshot::SnapshotInfo`). */
export interface SnapshotInfo {
  /** READY | PENDING (ilk okumada yazılır) | FAILED (SNAPSHOT_INTEGRITY_FAILED) | NONE (derlemede yok) */
  status: "READY" | "PENDING" | "FAILED" | "NONE";
  code: string | null;
  detail: string | null;
  build_sha7: string;
  build_dirty: boolean;
  manifest_sha256: string;
  n_files: number;
  bytes: number;
  last_session: string | null;
}

export interface ConfigView {
  config: AppConfig;
  config_note: string | null;
  repo: RepoCheck | null;
  repo_mode: boolean;
  data_dir: string | null;
  suggested_repo_root: string | null;
  /** Yalnız kişisel modda (repo modunda alan yok). */
  snapshot?: SnapshotInfo | null;
}

// ---------------------------------------------------------------- dondur akışı ve sicil (§3e, §3g)

export interface Preflight {
  repo_root: string;
  python_path: string;
  git_head: string | null;
  git_status_registry: string;
  index_sha_repo: string | null;
  index_sha_embedded: string;
  index_match: boolean;
  borsai_file: string | null;
  borsai_in_repo: boolean;
  today_istanbul: string;
  t: string | null;
  t_level: "RED" | "YELLOW" | "NONE";
  ok: boolean;
  blockers: string[];
  /** Deflatörlü model varsa repo TÜFE tablosunun T için durumu (ay eksikse engel `TUFE_MONTH`). */
  tufe: TufeInfo | null;
}

export interface SourceDocReq {
  source_id: string;
  kind: string;
  document_id: string;
  published_at: string;
  published_at_basis: string;
  path: string;
  file_name: string | null;
  title: string | null;
  url: string | null;
  issuer: string | null;
}

export interface SourceDocResult {
  source_id: string;
  file_name: string;
  rel_path: string;
  sha256: string;
  size_bytes: number;
  file_state: "NEW" | "SAME";
  manifest_state: "NEW" | "KEPT";
}

export interface ManifestDoc {
  schema_version: string;
  ticker: string;
  documents: Record<string, { document_id: string; kind: string; published_at: string; sha256: string; path: string }>;
}

export interface SourceDocsView {
  ticker: string;
  rel_dir: string;
  manifest_rel_path: string;
  documents: SourceDocResult[];
  manifest: ManifestDoc;
}

export interface FieldDraft {
  value: string | null;
  missing_reason: string | null;
  source_id: string | null;
  quote: string | null;
  origin: string | null;
  locator: string | null;
  cross_checks: { source_id: string; quote: string }[];
  checked_sources: string[];
}

export interface InputsDocReq {
  ticker: string;
  company: string;
  stage: string;
  first_trading_date_source: string | null;
  collection_rules: string[];
  fields: Record<string, FieldDraft>;
  collected_at: string | null;
}

export interface InputsDocPreview {
  rel_path: string;
  text: string;
  problems: string[];
  exists: boolean;
  identical: boolean;
  diff: string[];
  written: boolean;
  sha256: string;
}

export interface ParityCell {
  model_id: string;
  ok: boolean;
  bit_equal: boolean;
  max_abs: number;
  n_numbers: number;
  failures: string[];
}

export interface ParityReport {
  n_record_models: number;
  n_supported: number;
  n_matched: number;
  max_abs: number;
  n_bit_equal: number;
  unsupported: string[];
  /** Uygulamada olup kayıtta olmayan modeller: kayıt INDEX'ten eski (uyuşmazlık değil). */
  missing_in_record: string[];
  mismatches: ParityCell[];
  incident_rel_path: string | null;
}

export interface FreezeResult {
  record_rel_path: string;
  record_file: string;
  ticker: string;
  recorded_at_utc: string;
  recorded_at_istanbul: string;
  n_models: number;
  model_ids: string[];
  summary: { n_models?: number; n_predicted?: number; n_refused?: number; refusals?: Record<string, string> } | null;
  input_sha256: string | null;
  models_index_sha256: string | null;
  parity: ParityReport;
  todo: string[];
}

export interface CancelResult {
  cancel_rel_path: string;
  cancels: string;
  ticker: string;
  reason: string;
  recorded_at_istanbul: string;
  todo: string[];
}

export interface PushProof {
  sha: string;
  created_at: string | null;
  rel_path: string;
}

export interface RecordModelRef {
  model_id: string;
  params_sha256: string;
  status: string;
  has_s: boolean;
}

export interface RecordRow {
  file: string;
  rel_path: string;
  status: "OK" | "UNSUPPORTED_VERSION" | "UNREADABLE";
  schema_version: string | null;
  record_type: string | null;
  ticker: string | null;
  recorded_at_utc: string | null;
  recorded_at_istanbul: string | null;
  git_head: string | null;
  input_sha256: string | null;
  models_index_sha256: string | null;
  inputs_path: string | null;
  first_trading_date: string | null;
  n_models: number;
  summary: { n_predicted?: number; n_refused?: number; refusals?: Record<string, string> } | null;
  models: RecordModelRef[];
  unsupported_models: RecordModelRef[];
  n_ceiling_models: number;
  cancels: string | null;
  reason: string | null;
  cancelled_by: { file: string; reason: string; recorded_at_istanbul: string } | null;
  tracked: boolean;
  added_commit: string | null;
  push_proof: PushProof | null;
  error: string | null;
}

export interface TickerRow {
  ticker: string;
  company: string | null;
  first_trading_date: string | null;
  ipo_status: string | null;
  records: RecordRow[];
  n_active: number;
  /** D1 sonrası kayıtlar (`registry/post_d1/<T>/`): dosya ve etkin tahmin kaydı sayısı. */
  n_post_d1_files: number;
  n_post_d1_active: number;
}

export interface RegistryView {
  repo_root: string;
  today_istanbul: string;
  git_status_registry: string;
  tickers: TickerRow[];
  ipos: Record<string, string>[];
  proofs: PushProof[];
  supported_models: string[];
  /** Kişisel modda gömülü anlık görüntünün künyesi; repo modunda alan yok. */
  snapshot?: SnapshotInfo | null;
}

/** Kayıttaki bir tavan yolu modelinin çıktısı (Grup A/C render'ı; U38: yalnız kayıttan). */
export interface RecordPathModel {
  model_id: string;
  params_sha256: string;
  status: string;
  sha_matches_embedded: boolean;
  refusal: Refusal | null;
  output: ModelOutput | null;
}

export interface RecordCeiling {
  ticker: string;
  file: string;
  rel_path: string;
  recorded_at_istanbul: string;
  first_trading_date: string | null;
  ipo_price_tl: string | null;
  models: RecordModelRef[];
  unsupported_models: RecordModelRef[];
  /** Boşsa kayıt INDEX'ten eskidir (Faz 4 modelleri kayıtta yok). */
  path_models: RecordPathModel[];
  display: CeilingDisplay;
}

// ---------------------------------------------------------------- doğruluk paneli (§2.3, §3d)

/** `scores.json` hücresi (backtest, canlı, self-reported ve koşullu bloklar aynı biçimde). */
export interface ScoreCell {
  output: string;
  horizon_or_k: string | number;
  metric: string;
  model_value: Num | null;
  rule_id: string;
  rule_value: Num | null;
  diff: Num | null;
  ci95: [Num, Num] | null;
  n: number;
  wins: number | null;
  losses: number | null;
  ties: number | null;
  /** Dosyadaki hüküm metni; panelde AYNEN basılır (§3d, U19). */
  verdict: string | null;
  label?: string;
  scale?: string;
  n_blocks?: number;
}

// ---------------------------------------------------------------- zaman-dışı panel (EK 3 §7; Rust `commands::scores_oot`)

/** Kırılım satırı (`by_year`, `by_regime`): birincil hücrenin alt kümesi; n < 10'da değerler null. */
export interface OotBreakdown {
  subset: string;
  label?: string;
  n: number;
  n_blocks?: number | null;
  rule_id?: string;
  model_value: Num | null;
  rule_value: Num | null;
  diff: Num | null;
  ci95: [Num, Num] | null;
  verdict: string | null;
  wins?: number | null;
  losses?: number | null;
  ties?: number | null;
}

export interface OotPrimarySpec {
  output: string;
  horizon_or_k: string | number | null;
  metric: string;
  rule_ids?: string[];
}

export interface OotModelSummary {
  model_id: string;
  kind: string | null;
  scale: string | null;
  subset: string | null;
  primary_cell: OotPrimarySpec | null;
  primary: ScoreCell | null;
  counters: Record<string, number>;
  exposure_class: string | null;
}

export interface OotBlockView {
  key: "oot_pre_h99" | "oot_pre_h99_sealed" | "oot_pre_h99_all" | "post_d1" | "post_d1_sealed" | "post_d1_all";
  title: string | null;
  scale: string | null;
  subset: string | null;
  counters: Record<string, number>;
  excluded_models: { model_id: string; reason: string }[];
  models: OotModelSummary[];
}

/** Açık küme satırı (yalnız `oot_pre_h99`, yalnız `open == true`; Rust özetler: S_1/S_5/S_10 ya da D5 getirisi/p_up). */
export interface OotRowView {
  ticker: string;
  d1: string | null;
  year: number | string | null;
  alloc_regime: string | null;
  class: string | null;
  class_evidence: Record<string, unknown> | null;
  status: string | null;
  cell_status: string | null;
  record_id: string | null;
  pred_kind: "S" | "RETURN" | "REFUSED" | "NONE";
  pred_s: [number | null, number | null, number | null] | null;
  pred_d5_return: number | null;
  pred_d5_p_up: number | null;
  refused_code: string | null;
  realized_l: number | string | null;
  realized_d5_r: string | null;
}

export interface OotRetroView {
  groups: { model_id: string; n: number; tickers: string[]; n_not_drawn: number }[];
  n: number;
  n_not_drawn: number;
}

export interface OotPanelView {
  status: "OK" | "NO_FILE" | "REPO_ONLY" | "UNSUPPORTED" | "INTEGRITY";
  source: "REPO" | "EMBEDDED" | null;
  path: string | null;
  sha12: string | null;
  generated_at_utc: string | null;
  git_head12: string | null;
  cohort_sha12: string | null;
  unsupported_version: string | null;
  integrity: { rule: string; model_id: string | null; detail: string } | null;
  rows_present: boolean;
  vault_open: boolean;
  class_definition: string | null;
  blocks: OotBlockView[];
  retro: OotRetroView;
}

export interface OotModelDetail {
  block: string;
  model_id: string;
  kind: string | null;
  primary_cell: OotPrimarySpec | null;
  cells: ScoreCell[];
  by_year: OotBreakdown[];
  by_regime: OotBreakdown[];
  info: Record<string, unknown>[];
  rows: OotRowView[];
  rows_block: boolean;
  rows_available: boolean;
}

/** §7'nin eşleşik fark olmayan ikincil ölçüleri (SPEC_DEVIATIONS E13): aralıksız ve hükümsüz. */
export interface ScoreDescriptive {
  output: string;
  horizon_or_k: string | number;
  metric: string;
  n: number;
  model_value: Num | null;
  observed?: Num | null;
  rules: Record<string, Num | null>;
}

export interface ScoreRow {
  ticker: string;
  d1: string | null;
  d1_basis?: string | null;
  class: string | null;
  record_id: string | null;
  record_source?: string | null;
  selection_rule?: string | null;
  status: string;
  targets?: Record<string, string>;
  prediction: Record<string, unknown> | null;
  realized: Record<string, unknown> | null;
  rules: Record<string, { record_id?: string | null; values?: Record<string, unknown> }>;
  class_evidence?: Record<string, unknown> | null;
  inputs_pit_problems?: string[];
  note?: string;
}

export interface ScoreLive {
  title: string;
  n_scored: number;
  n_live: number;
  n_late: number;
  n_refused: number;
  n_skipped: number;
  n_target_unavailable: number;
  n_pending: number;
  n_rows?: number;
  n_partial_pending?: number;
  rows: ScoreRow[];
  cells: ScoreCell[];
  descriptive?: ScoreDescriptive[];
  self_reported_rows?: ScoreRow[];
  n_self_reported_scored?: number;
  self_reported_cells?: ScoreCell[];
  invalid_use_rows?: { ticker: string; record_id: string | null; note: string; prediction?: unknown }[];
  cancelled_records?: { ticker: string; record_id: string; cancelled_at?: string | null; reason?: string | null }[];
}

/** EK 2 §5: `models[].conditional` (`borsai.scores_conditional/1`); j'ler asla toplanmaz. */
export interface ScoreConditionalByJ {
  j: number;
  n_scored: number;
  n_live: number;
  n_late: number;
  n_refused: number;
  n_skipped: number;
  n_target_unavailable: number;
  rows: Record<string, unknown>[];
  cells: ScoreCell[];
}

export interface ScoreConditional {
  schema_version: string;
  title?: string;
  scale?: string;
  by_j: ScoreConditionalByJ[];
}

export interface ScoreCard {
  training_n?: number;
  training_cutoff?: string;
  params_sha256_8?: string;
  n_variants_same_data?: number;
  n_runs_same_data?: number;
}

export interface ScoreModel {
  model_id: string;
  kind: string;
  card: ScoreCard | null;
  primary_cell: { output: string; horizon_or_k: string | number; metric: string; rule_ids?: string[]; rule_id?: string } | null;
  backtest: { title: string; cells: ScoreCell[]; scale?: string };
  live: ScoreLive;
  conditional?: ScoreConditional;
}

export interface ScoresDoc {
  schema_version: string;
  generated_at_utc?: string;
  as_of_session?: string;
  inputs?: Record<string, string>;
  models: ScoreModel[];
  retro_info?: { model_id: string; ticker: string; record_id: string | null; class_evidence?: Record<string, unknown>; inputs_pit_problems?: string[] }[];
  skipped?: Record<string, string>[];
  separate_models?: { model_id: string; in_models_index?: boolean; rows: ScoreRow[]; cells: ScoreCell[] }[];
  synthetic?: boolean;
  synthetic_note?: string;
}

/** §2.3 bütünlük ihlali: panel yerine bu gösterilir (fail-closed). */
export interface IntegrityProblem {
  rule: string;
  model_id: string | null;
  detail: string;
}

export interface ScoresView {
  source: string;
  unsupported_version: string | null;
  generated_at_utc: string | null;
  as_of_session: string | null;
  sha12: string;
  index_mismatch: boolean;
  synthetic: boolean;
  integrity: IntegrityProblem | null;
  doc: ScoresDoc | null;
}

// ---------------------------------------------------------------- D1 sonrası (SPEC_APP EK 3 §6; Rust `commands::post_d1`)

export interface PostD1Cell {
  model_id: string;
  params_sha256: string;
  /** PREDICTED | REFUSED | NOT_APPLICABLE */
  status: string;
  refusal: { code: string; field?: string | null; reason?: string } | null;
  has_s: boolean;
}

export interface PostD1RecordRow {
  file: string;
  rel_path: string;
  status: "OK" | "UNSUPPORTED_VERSION" | "UNREADABLE";
  record_type: string | null;
  ticker: string | null;
  recorded_at_utc: string | null;
  recorded_at_istanbul: string | null;
  d1_session_date: string | null;
  base_record_file: string | null;
  thb_sha8: string | null;
  thm_sha8: string | null;
  models_index_sha256: string | null;
  cells: PostD1Cell[];
  summary: { n_models?: number; n_predicted?: number; n_refused?: number; n_not_applicable?: number } | null;
  cancels: string | null;
  reason: string | null;
  cancelled_by: { file: string; reason: string; recorded_at_istanbul: string } | null;
  tracked: boolean;
  added_commit: string | null;
  push_proof: PushProof | null;
  error: string | null;
}

export interface PostD1Source {
  file: string;
  rel_path: string;
  params_sha8: string;
  d1_session_date: string | null;
  thb_sha8: string | null;
  thm_sha8: string | null;
}

/** Arz sayfasının "D1 sonrası" satırı: S yalnız kayıttan; j = 0'da satır yok. */
export interface PostD1View {
  ticker: string;
  j: number;
  records: PostD1RecordRow[];
  /** Etkin kayıtlar, en erken önce (varsayılan sekme ilk öğe). */
  active: string[];
  selected: string | null;
  state: "NO_RECORD" | "J0" | "PREDICTED" | "REFUSED" | "NOT_APPLICABLE" | "NO_CELL";
  refusal: { code: string; field?: string | null; reason?: string } | null;
  row: CeilingRow | null;
  source: PostD1Source | null;
  path_card: PathConditional | null;
  d1_close: string | null;
}

export interface PostD1Preflight {
  ticker: string;
  repo_root: string;
  python_path: string;
  git_head: string | null;
  index_sha_repo: string | null;
  index_sha_embedded: string;
  index_match: boolean;
  index_post_d1_sha_repo: string | null;
  index_post_d1_sha_embedded: string;
  index_post_d1_match: boolean;
  borsai_file: string | null;
  borsai_in_repo: boolean;
  base_records: string[];
  first_trading_date: string | null;
  d1_status: string | null;
  d1: string | null;
  t_open: string | null;
  t_open_error: string | null;
  git_status_pending: string;
  committed: boolean;
  now_istanbul: string;
  minutes_to_t_open: number | null;
  active_post_d1: string[];
  blockers: string[];
  warnings: string[];
  ok: boolean;
}

export interface PostD1FreezeResult {
  record_rel_path: string;
  record_file: string;
  ticker: string;
  recorded_at_utc: string;
  recorded_at_istanbul: string;
  d1: string | null;
  ceiling_close_d1: number | null;
  summary: { n_models?: number; n_predicted?: number; n_refused?: number; n_not_applicable?: number } | null;
  t_open: string | null;
  python_note: string | null;
  base_record_file: string | null;
  parity: ParityReport;
  comparators: { n_checked: number; max_abs: number; failures: string[] };
  todo: string[];
}

export interface PostD1CancelResult {
  cancel_rel_path: string;
  cancels: string;
  ticker: string;
  reason: string;
  recorded_at_istanbul: string;
  todo: string[];
}

/** `scores/scores_post_d1.json` (borsai.scores_post_d1/1; ölçek live_post_d1). Gömülmez: yalnız repo modu. */
export interface ScorePostD1Block {
  title?: string;
  scale?: string;
  j: number;
  n_scored: number;
  n_live: number;
  n_late: number;
  n_refused: number;
  n_skipped: number;
  n_not_applicable: number;
  n_retro: number;
  n_pending: number;
  n_target_unavailable: number;
  n_undefined?: number;
  n_undetermined?: number;
  n_d1_label_na?: number;
  n_no_record?: number;
  n_calendar_not_available?: number;
  cells: ScoreCell[];
  rows: Record<string, unknown>[];
  descriptive: Record<string, unknown>[];
  denominator: Record<string, unknown>[];
}

export interface ScorePostD1Model {
  model_id: string;
  kind: string;
  stage: string;
  card: {
    training_n?: number;
    training_last_session_date?: string;
    spec_training_cutoff?: string;
    params_sha256_8?: string;
    parent_model_id?: string;
    n_variants_same_data?: number;
    n_runs_same_data?: number;
  };
  primary_cell: ScoreModel["primary_cell"];
  conditional_j1: ScorePostD1Block;
}

export interface ScoresPostD1Doc {
  schema_version: string;
  as_of_session?: string;
  generated_at_utc?: string;
  synthetic?: boolean;
  models: ScorePostD1Model[];
  retro_info: { model_id: string; ticker: string; d1?: string; class_evidence?: Record<string, unknown> }[];
}

export interface ScoresPostD1View {
  status: "REPO" | "NO_REPO" | "NO_FILE";
  path: string | null;
  sha12: string | null;
  generated_at_utc: string | null;
  as_of_session: string | null;
  unsupported_version: string | null;
  integrity: { rule: string; model_id: string | null; detail: string } | null;
  doc: ScoresPostD1Doc | null;
}

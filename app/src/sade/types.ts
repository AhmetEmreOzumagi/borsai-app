// Sade görünüm komutlarının çıktı tipleri (Rust `commands/sade.rs`, `commands/sade_break.rs`; alan adları aynen).
import type { IntegrityProblem, SnapshotInfo } from "../types";

export interface DayRow {
  h: number;
  session_date: string | null;
  close_raw: string | null;
  upper_limit_raw: string | null;
  reference_raw: string | null;
  ceiling_close: number | null;
  status: string | null;
  r_h: string | null;
  /** Bültendeki toplam sözleşme sayısı metni aynen (K-FIX-4) ve Rust'ın verdiği 0–1 göreli yükseklik. */
  trade_count_raw: string | null;
  trade_count_rel: number | null;
}

export interface StreakInfo {
  file_status: "FOUND" | "MISSING";
  as_of: string | null;
  j_observed: number | null;
  broken: boolean;
  unlabeled: boolean;
  in_streak: boolean;
  realized_l: number | null;
}

export interface CeilingInfo {
  model_id: string;
  record_file: string;
  status: string | null;
  refusal_code: string | null;
  params_sha256: string | null;
  expected_l: number | null;
  median_l: number | null;
  mode_l: number | null;
  p_ge5: number | null;
  p_10: number | null;
}

export interface ReturnRow {
  horizon: "D1" | "D3" | "D5" | "D10";
  h: number;
  ret: number | null;
  p_up: number | null;
  price: number | null;
  return_clipped: unknown;
  realized: string | null;
}

export interface ReturnInfo {
  model_id: string;
  record_file: string;
  status: string | null;
  refusal_code: string | null;
  rows: ReturnRow[];
}

export interface ClassRow {
  model_id: string;
  class: string | null;
  status: string | null;
  record_source: string | null;
  record_push_proof_created_at: string | null;
}

export interface BreakInfo {
  record_file: string;
  produced_at_utc: string | null;
  b: number | null;
  l: number | null;
  break_date: string | null;
  b_floor: number | null;
  close_raw: string | null;
  status: string | null;
  p_floor_f1: number | null;
  p_floor_f2: number | null;
  impossible_d10: boolean | null;
  warnings: string[];
  t_open: string | null;
}

export interface MonitorRow {
  ticker: string;
  company: string | null;
  first_trading_date: string | null;
  ipo_status: string | null;
  ipo_price: string | null;
  shares_offered: string | null;
  days: DayRow[];
  d10_close: string | null;
  d10_date: string | null;
  r10: string | null;
  r10_below: boolean | null;
  streak: StreakInfo;
  record_file: string | null;
  recorded_at_istanbul: string | null;
  ceiling: CeilingInfo | null;
  returns: ReturnInfo | null;
  break_info: BreakInfo | null;
  classes: ClassRow[];
  regime_tags: string[];
  n_pre_listing_records: number;
  n_post_d1_records: number;
  n_machine_records: number;
}

export interface MonitorCounts {
  n_ipos: number;
  first_d1: string | null;
  last_d1: string | null;
  n_in_streak: number;
  n_d10_known: number;
  n_d10_below: number;
  n_break_known: number;
  n_break_floor: number;
  n_impossible_d10: number;
  n_payda: number;
  n_frozen: number;
  n_out_of_scope: number;
  n_skipped: number;
  n_pre_listing_records: number;
  n_post_d1_records: number;
  n_machine_records: number;
  n_push_proofs: number;
}

export interface RegimeInfo {
  tag: string;
  start_d1: string | null;
  end_d1: string | null;
}

export interface EventItem {
  at: string;
  kind: "RECORD" | "LEGACY_RECORD" | "STREAK" | "BREAK" | "D10" | "MACHINE" | "MODEL_FROZEN" | "REGIME" | "POST_D1";
  ticker: string | null;
  tickers: string[];
  model_id: string | null;
  h_from: number | null;
  h_to: number | null;
  b: number | null;
  b_floor: number | null;
  close_raw: string | null;
  closes: string[];
  r: string | null;
  class: string | null;
  proof_at: string | null;
  file: string | null;
}

export interface MonitorView {
  data_date: string | null;
  rows: MonitorRow[];
  counts: MonitorCounts;
  regime: RegimeInfo | null;
  events: EventItem[];
  git_status: string;
  scores_source: string | null;
  scores_integrity: IntegrityProblem | null;
  /** Kişisel modda gömülü anlık görüntünün künyesi (K-SNAP-3 veri şeridi); repo modunda alan yok. */
  snapshot?: SnapshotInfo | null;
}

export interface ArzView {
  row: MonitorRow;
  p_close_ceiling: (number | null)[];
  record_rel_path: string | null;
  record_models_index_sha256: string | null;
  record_push_proof_created_at: string | null;
  record_added_commit: string | null;
  post_d1_files: string[];
  regime: RegimeInfo | null;
  log: EventItem[];
}

export interface GateEntry {
  model_id: string;
  output: string;
  horizon_or_k: string | null;
  question: string;
  source: string;
  status: "OK" | "NO_FILE" | "NO_MODEL";
  is_primary: boolean;
  featured: boolean;
  primary_metric: string | null;
  primary_rules: string[];
  verdicts: string[];
  label: string | null;
  live_n: number | null;
}

export interface HeadlineGate {
  entries: GateEntry[];
  scores_source: string | null;
}

export interface PerfRow {
  model_id: string;
  question: string;
  source: string;
  scale: string | null;
  output: string | null;
  horizon_or_k: string | null;
  metric: string | null;
  rule_id: string | null;
  label: string | null;
  model_value: number | string | null;
  rule_value: number | string | null;
  diff: number | string | null;
  ci95: [number, number] | null;
  n: number | null;
  n_months: number | null;
  wins: number | null;
  losses: number | null;
  ties: number | null;
  verdict: string | null;
  file_label: string | null;
  featured: boolean;
}

export interface OotSummary {
  status: "OK" | "NO_FILE" | "NO_BLOCK" | "NO_TEST";
  block: string | null;
  verdict: string | null;
  n: number | null;
  rule_id: string | null;
}

export interface LiveSummary {
  n_scored: number | null;
  n_live: number | null;
  n_late: number | null;
  n_refused: number | null;
  n_retro: number | null;
  n_machine: number | null;
}

export interface ScaleSummary {
  model_id: string;
  question: string;
  backtest_verdicts: string[];
  backtest_label: string | null;
  backtest_status: string;
  featured: boolean;
  oot: OotSummary;
  live: LiveSummary;
}

export interface LiveCell {
  class: string | null;
  status: string | null;
  predicted: number | null;
  realized: number | string | null;
  record_source: string | null;
}

export interface PerfLiveRow {
  ticker: string;
  d1: string | null;
  ceiling: LiveCell | null;
  d5: LiveCell | null;
  post_d1_status: string | null;
  break_class: string | null;
}

export interface PerfCounts {
  n_rows: number;
  n_pass: number;
  n_undecided: number;
  n_fail: number;
  n_other: number;
  n_no_verdict: number;
}

export interface PerfView {
  rows: PerfRow[];
  scales: ScaleSummary[];
  live_rows: PerfLiveRow[];
  /** Dosyadaki verdict'e göre ayrı sayımlar (K-FIX-5); toplanmaz. */
  counts: PerfCounts;
  min_n_metric: number;
  min_n_verdict: number;
  n_production: number;
  scores_source: string | null;
  scores_integrity: IntegrityProblem | null;
  has_post_d1: boolean;
  has_break: boolean;
  has_oot: boolean;
}

export interface BreakFeature {
  name: string;
  close_raw: string | null;
  lower_limit_raw: string | null;
  ratio_raw: string | null;
  ln_value: number | null;
  value_f1: number | null;
  clipped_f1: boolean | null;
  z_f1: number | null;
  z_f2: number | null;
  coef_f1: number | null;
  coef_f2: number | null;
}

export interface BreakHead {
  head: "F1" | "F2";
  c: number | string | null;
  intercept: number | null;
  training_n: number | null;
  training_events: number | null;
}

export interface BreakCard {
  backtest_info: {
    F1_product?: { diff: number; ci95: [number, number] | null; n: number; n_months: number };
    F1_zero?: { diff: number; ci95: [number, number] | null; n: number; n_months: number };
    k1?: boolean;
    label?: string;
  } | null;
  promotion_label: string | null;
  promoted: boolean | null;
  promotion_stage: number | null;
  regime_tag: string | null;
  regime_start_d1: string | null;
  regime_text: string | null;
  frozen_at: string | null;
  model_commit: string | null;
  model_push_proof_created_at: string | null;
  n_variants_same_data: number | null;
  training_n_f1: number | null;
  training_n_f2: number | null;
}

export interface BreakView {
  ticker: string;
  status: "OK" | "NO_RECORD" | "NO_MODEL_FILE" | "SHA_MISMATCH";
  record_file: string | null;
  record_params_sha256: string | null;
  model_file_sha256: string | null;
  produced_at_utc: string | null;
  b: number | null;
  l: number | null;
  break_date: string | null;
  b_floor: number | null;
  model_status: string | null;
  p_f1: number | null;
  p_f2: number | null;
  zero_f1: number | null;
  zero_f2: number | null;
  by_type_f1: number | null;
  product_status: string | null;
  product_f1: number | null;
  features: BreakFeature[];
  heads: BreakHead[];
  structural_p: string | null;
  structural_min10: string | null;
  impossible_d10: boolean | null;
  warnings: string[];
  exposure_class: string | null;
  t_open: string | null;
  class: string | null;
  live_n_scored: number | null;
  live_n_retro: number | null;
  card: BreakCard | null;
}

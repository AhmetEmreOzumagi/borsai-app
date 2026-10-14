// Doğruluk paneli (SPEC_APP §3d, SPEC_SCORING §8 birebir) saf render. Bütün sayılar `scores.json`'dan
// gelir; burada yalnız biçimlendirme, sıralama ve yerleşim vardır (U25: uygulama skor hesaplamaz).
// İki terazi ayrı bölümdür ve hiçbir yerde toplanmaz, ortalanmaz, tek hükümde birleşmez (U14).
import { ACCURACY, CARD, KIND_TEXT, PATH, RESULTS, VERDICT } from "../i18n/tr";
import type {
  ModelInfo,
  PathParamsInfo,
  Num,
  ScoreCell,
  ScoreConditional,
  ScoreDescriptive,
  ScoreLive,
  ScoreModel,
  ScoreRow,
  ScoresDoc,
  ScoresPostD1View,
  ScoresView,
} from "../types";
import { esc } from "../dom";
import { MIN_N_METRIC, MIN_N_VERDICT, renderModelCard, type CardVM } from "./card";
import { DASH, metric4, pct0, pctSigned1, points1, points1Bare, pyRepr, sha8 } from "./format";
import { renderOotPanel, type OotPanelVM } from "./accuracy_oot";

export { MIN_N_METRIC, MIN_N_VERDICT };

const CONDITIONAL_SCHEMA = "borsai.scores_conditional/1";
/** Getiri hatası metrikleri "puan" birimiyle; ötekiler 4 ondalık (§3d, §4). */
const POINT_METRICS = ["MAE", "MedAE"];

export interface AccuracyView {
  /** `scores_view` çıktısı; `null` = dosya yok. */
  scores: ScoresView | null;
  /** Gömülü INDEX künyesi (model kartındaki "ne yapar"). */
  models: ModelInfo[];
  /** `path_params`: tavan yolu modellerinin seri modeli satırı (kartta). */
  pathParams: PathParamsInfo[];
  hidden: string[];
  /** Açık model blokları (ekran görüntüsü ve ilk açılış). */
  open: string[];
  /** D1 sonrası skorlar (`scores_post_d1_view`; EK 3 §6.5). `undefined`: yüklenmedi, bölüm çizilmez. */
  postD1?: ScoresPostD1View | null;
  /** Zaman-dışı panel (EK 3 §7; `render/accuracy_oot.ts`). `undefined`: yüklenmedi, bölüm çizilmez. */
  oot?: OotPanelVM;
}

function isPoint(c: { metric: string }): boolean {
  return POINT_METRICS.includes(c.metric);
}

export function value(c: { metric: string }, x: Num | null | undefined): string {
  if (x === null || x === undefined) return DASH;
  return isPoint(c) ? points1(x) : metric4(x);
}

export function ciText(c: { metric: string; ci95: [Num, Num] | null }): string {
  const ci = c.ci95;
  if (!ci) return VERDICT.noInterval;
  return isPoint(c)
    ? `[${points1Bare(ci[0])}, ${points1Bare(ci[1])}] ${ACCURACY.pointsUnit}`
    : `[${metric4(ci[0])}, ${metric4(ci[1])}]`;
}

export function wlt(c: { wins?: number | null; losses?: number | null; ties?: number | null }): string {
  const one = (x: number | null | undefined) => (x === null || x === undefined ? DASH : String(x));
  return `${one(c.wins)} / ${one(c.losses)} / ${one(c.ties)}`;
}

/** Birincil hücre eşlemesi (§3d, U22): `primary_cell` ile aynı çıktı, ufuk, metrik ve kural. */
export function isPrimaryCell(c: ScoreCell, p: ScoreModel["primary_cell"]): boolean {
  if (!p) return false;
  const ids = p.rule_ids ?? (p.rule_id ? [p.rule_id] : []);
  return (
    p.output === c.output &&
    String(p.horizon_or_k) === String(c.horizon_or_k) &&
    p.metric === c.metric &&
    (ids.length === 0 || ids.includes(c.rule_id))
  );
}

/** Ham değerler tooltip'i: dosyadaki binary64'ün Python repr'i (§4). */
export function cellTip(c: { model_value: Num | null; rule_value: Num | null; diff: Num | null; ci95: [Num, Num] | null }): string {
  const ci = c.ci95 ? `[${pyRepr(c.ci95[0])}, ${pyRepr(c.ci95[1])}]` : DASH;
  return `model_value=${pyRepr(c.model_value)}, rule_value=${pyRepr(c.rule_value)}, diff=${pyRepr(c.diff)}, ci95=${ci}`;
}

interface CellOpts {
  /** Hüküm renkleri açık mı (§3d: backtest her zaman; canlı yalnız n ≥ 30). */
  color: boolean;
  /** 10 ≤ n < 30: her satırda "yetersiz örnek" rozeti, kazanan vurgusu yok. */
  smallN: boolean;
  scale: string;
}

function cellRow(c: ScoreCell, primary: ScoreModel["primary_cell"], o: CellOpts): string {
  const isPrimary = isPrimaryCell(c, primary);
  const badge = isPrimary ? ACCURACY.primaryBadge : ACCURACY.exploratoryBadge;
  const colorCls = !o.color || c.verdict === null ? "" : c.verdict === VERDICT.pass ? " win" : c.verdict === VERDICT.fail ? " lose" : "";
  const smallBadge = o.smallN ? ` <span class="badge-small-n">${esc(VERDICT.insufficient)}</span>` : "";
  return `<tr class="cell-row${isPrimary ? " primary" : ""}" data-output="${esc(c.output)}" data-h="${esc(String(c.horizon_or_k))}" ` +
    `data-metric="${esc(c.metric)}" data-rule="${esc(c.rule_id)}" data-scale="${esc(o.scale)}">` +
    `<td>${esc(c.output)} <span class="tag label-tag">${esc(badge)}</span></td>` +
    `<td>${esc(String(c.horizon_or_k))}</td><td>${esc(c.metric)}</td>` +
    `<td class="metric" title="${esc(cellTip(c))}">${esc(value(c, c.model_value))}</td>` +
    `<td class="metric"><span class="mono">${esc(c.rule_id)}</span> ${esc(value(c, c.rule_value))}</td>` +
    `<td class="metric diff">${esc(value(c, c.diff))}</td>` +
    `<td class="metric ci">${esc(ciText(c))}</td>` +
    `<td class="metric n">${esc(String(c.n))}</td>` +
    `<td class="metric wlt">${esc(wlt(c))}</td>` +
    `<td class="verdict${colorCls}" data-verdict="${esc(c.verdict ?? "")}">${esc(c.verdict ?? DASH)}${smallBadge}</td></tr>`;
}

/** İsabet oranı satırı yalnız kuralın isabeti varken gösterilir (§3d, U20). */
function splitAccuracyCells(cells: ScoreCell[]): { shown: ScoreCell[]; hidden: number } {
  const shown = cells.filter((c) => c.metric !== "accuracy" || (c.rule_value !== null && c.rule_value !== undefined));
  return { shown, hidden: cells.length - shown.length };
}

function cellTable(cells: ScoreCell[], primary: ScoreModel["primary_cell"], o: CellOpts): string {
  const { shown, hidden } = splitAccuracyCells(cells);
  const head = [
    ACCURACY.colOutput, ACCURACY.colHorizon, ACCURACY.colMetric, ACCURACY.colModel,
    ACCURACY.colRule, ACCURACY.colDiff, ACCURACY.colCi, ACCURACY.colN, ACCURACY.colWlt, ACCURACY.colVerdict,
  ];
  const note = hidden > 0 ? `<p class="small muted accuracy-hidden">${esc(ACCURACY.accuracyHidden)}</p>` : "";
  return `<div class="scroll"><table class="grid compact cells"><thead><tr>${head.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead>` +
    `<tbody>${shown.map((c) => cellRow(c, primary, o)).join("")}</tbody></table></div>${note}`;
}

// ---------------------------------------------------------------- satır tablosu (n < 10 ve her hâlde)

function ruleIds(rows: ScoreRow[]): string[] {
  const out: string[] = [];
  for (const r of rows) for (const id of Object.keys(r.rules ?? {})) if (!out.includes(id)) out.push(id);
  return out;
}

function horizonText(cell: { return?: Num | null; p_up?: Num | null } | undefined): string {
  if (!cell) return DASH;
  const ret = cell.return === null || cell.return === undefined ? DASH : pctSigned1(cell.return);
  const p = cell.p_up === null || cell.p_up === undefined ? "" : ` · ${pct0(cell.p_up)}`;
  return `${ret}${p}`;
}

/** Tahmin hücresi: getiri modellerinde D1, tavan modellerinde S_1; ret satırında kod. */
function predictionText(p: Record<string, unknown> | null | undefined): string {
  if (!p) return DASH;
  const refused = p.refused as { code?: string } | undefined;
  if (refused) return ACCURACY.refusedPrediction(refused.code ?? "?");
  if (p.D1) return horizonText(p.D1 as { return?: Num | null; p_up?: Num | null });
  const s = p.S as Num[] | undefined;
  if (Array.isArray(s) && s.length > 0) return `S_1 ${pct0(s[0])}`;
  return DASH;
}

function realizedText(r: Record<string, unknown> | null | undefined): string {
  if (!r) return DASH;
  const parts: string[] = [];
  const ret = (r.R as Record<string, Num> | undefined)?.D1;
  if (ret !== undefined && ret !== null) parts.push(pctSigned1(ret));
  const l = r.L as number | null | undefined;
  if (l !== null && l !== undefined) parts.push(`L = ${l}`);
  return parts.length > 0 ? parts.join(" · ") : DASH;
}

function ruleText(entry: { values?: Record<string, unknown> } | undefined): string {
  const v = entry?.values;
  if (!v) return DASH;
  if (v.D1) return horizonText(v.D1 as { return?: Num | null; p_up?: Num | null });
  const s = v.S as Num[] | undefined;
  if (Array.isArray(s) && s.length > 0) return `S_1 ${pct0(s[0])}`;
  return DASH;
}

/** Zaman kanıtı sütunu: `class_evidence`'tan okunur; sınıf ve kanıt UYGULAMADA HESAPLANMAZ (§3d). */
function proofText(r: ScoreRow): string {
  const at = (r.class_evidence as Record<string, unknown> | null | undefined)?.record_push_proof_created_at;
  return typeof at === "string" && at !== "" ? ACCURACY.proofYes(at) : ACCURACY.proofNo;
}

export function rowTable(rows: ScoreRow[], cls = "rows"): string {
  if (rows.length === 0) return "";
  const ids = ruleIds(rows);
  const head = [ACCURACY.colTicker, ACCURACY.colD1, ACCURACY.colClass, ACCURACY.colRecord, ACCURACY.colProof,
    ACCURACY.colPrediction, ACCURACY.colRealized, ...ids, ACCURACY.colStatus];
  const body = rows.map((r) =>
    `<tr data-ticker="${esc(r.ticker)}" data-class="${esc(r.class ?? "")}" data-status="${esc(r.status)}">` +
    `<td class="mono">${esc(r.ticker)}</td><td>${esc(r.d1 ?? DASH)}</td><td>${esc(r.class ?? DASH)}</td>` +
    `<td class="mono small" title="${esc(r.selection_rule ?? "")}">${esc(r.record_id ?? DASH)}</td>` +
    `<td class="small proof">${esc(proofText(r))}</td>` +
    `<td class="pred">${esc(predictionText(r.prediction))}</td>` +
    `<td class="realized">${esc(realizedText(r.realized))}</td>` +
    ids.map((id) => `<td class="rule-pred" data-rule="${esc(id)}">${esc(ruleText(r.rules?.[id]))}</td>`).join("") +
    `<td>${esc(r.status)}</td></tr>`);
  return `<div class="scroll"><table class="grid compact ${esc(cls)}"><thead><tr>${head.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead>` +
    `<tbody>${body.join("")}</tbody></table></div>`;
}

// ---------------------------------------------------------------- bölümler

function descriptiveTable(rows: ScoreDescriptive[]): string {
  if (rows.length === 0) return "";
  const ids: string[] = [];
  for (const r of rows) for (const id of Object.keys(r.rules ?? {})) if (!ids.includes(id)) ids.push(id);
  const head = [ACCURACY.colOutput, ACCURACY.colHorizon, ACCURACY.colMetric, ACCURACY.colModel, ACCURACY.colObserved, ...ids, ACCURACY.colN];
  const body = rows.map((r) =>
    `<tr data-metric="${esc(r.metric)}" data-h="${esc(String(r.horizon_or_k))}">` +
    `<td>${esc(r.output)}</td><td>${esc(String(r.horizon_or_k))}</td><td>${esc(r.metric)}</td>` +
    `<td class="metric">${esc(value(r, r.model_value))}</td>` +
    `<td class="metric">${esc(r.observed === undefined ? DASH : value(r, r.observed))}</td>` +
    ids.map((id) => `<td class="metric" data-rule="${esc(id)}">${esc(value(r, r.rules?.[id]))}</td>`).join("") +
    `<td class="metric n">${esc(String(r.n))}</td></tr>`);
  return `<details class="descriptive"><summary>${esc(ACCURACY.descriptiveTitle)}</summary>` +
    `<div class="scroll"><table class="grid compact"><thead><tr>${head.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead>` +
    `<tbody>${body.join("")}</tbody></table></div></details>`;
}

function invalidUseTable(live: ScoreLive): string {
  const rows = live.invalid_use_rows ?? [];
  if (rows.length === 0) return "";
  const body = rows.map((r) =>
    `<tr data-ticker="${esc(r.ticker)}"><td class="mono">${esc(r.ticker)}</td>` +
    `<td class="mono small">${esc(r.record_id ?? DASH)}</td><td class="note-cell">${esc(r.note)}</td></tr>`);
  return `<details class="invalid-use muted"><summary>${esc(ACCURACY.invalidUseTitle)}</summary>` +
    `<div class="scroll"><table class="grid compact"><thead><tr><th>${esc(ACCURACY.colTicker)}</th>` +
    `<th>${esc(ACCURACY.colRecord)}</th><th>${esc(ACCURACY.colStatus)}</th></tr></thead><tbody>${body.join("")}</tbody></table></div></details>`;
}

function cancelledList(live: ScoreLive): string {
  const rows = live.cancelled_records ?? [];
  if (rows.length === 0) return "";
  const items = rows.map((r) =>
    `<li data-ticker="${esc(r.ticker)}">${esc(ACCURACY.cancelledLine(r.record_id, r.cancelled_at ?? DASH, r.reason ?? DASH))}</li>`);
  return `<div class="cancelled"><h5>${esc(ACCURACY.cancelledTitle)}</h5><ul class="small">${items.join("")}</ul></div>`;
}

function selfReported(m: ScoreModel): string {
  const live = m.live;
  const rows = live.self_reported_rows ?? [];
  const cells = live.self_reported_cells ?? [];
  if (rows.length === 0 && cells.length === 0) return "";
  const n = live.n_self_reported_scored ?? 0;
  const inner = n < MIN_N_METRIC
    ? rowTable(rows, "self-rows")
    : rowTable(rows, "self-rows") +
      cellTable(cells, m.primary_cell, { color: n >= MIN_N_VERDICT, smallN: n < MIN_N_VERDICT, scale: "self_reported" });
  return `<section class="self-reported"><h5>${esc(ACCURACY.selfReportedTitle)}</h5>` +
    `<p class="small muted">${esc(ACCURACY.selfReportedNote(String(n)))}</p>${inner}</section>`;
}

/**
 * Koşullu satırlar kendi şemasındadır (EK 2 §5: `L`, `S_cond`, `rps_cond`, `brier_next`, `brier_10`);
 * koşulsuz satır tablosuyla aynı sütunlara sokulmaz.
 */
function condRowTable(rows: Record<string, unknown>[]): string {
  if (rows.length === 0) return "";
  const head = [ACCURACY.colTicker, ACCURACY.colClass, ACCURACY.colRecord, "L", "RPS", "Brier", "Brier(10)", ACCURACY.colStatus];
  const body = rows.map((r) => {
    const sc = r.S_cond as Record<string, Num> | undefined;
    const tip = sc ? Object.entries(sc).map(([k, x]) => `S_${k}=${pyRepr(x)}`).join(", ") : "";
    const num = (x: unknown) => (x === null || x === undefined ? DASH : metric4(x as Num));
    return `<tr data-ticker="${esc(String(r.ticker ?? ""))}" data-class="${esc(String(r.class ?? ""))}" title="${esc(tip)}">` +
      `<td class="mono">${esc(String(r.ticker ?? DASH))}</td><td>${esc(String(r.class ?? DASH))}</td>` +
      `<td class="mono small">${esc(String(r.record_id ?? DASH))}</td>` +
      `<td class="metric">${esc(r.L === null || r.L === undefined ? DASH : String(r.L))}</td>` +
      `<td class="metric">${esc(num(r.rps_cond))}</td><td class="metric">${esc(num(r.brier_next))}</td>` +
      `<td class="metric">${esc(num(r.brier_10))}</td><td>${esc(String(r.status ?? DASH))}</td></tr>`;
  });
  return `<div class="scroll"><table class="grid compact cond-rows"><thead><tr>${head.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead>` +
    `<tbody>${body.join("")}</tbody></table></div>`;
}

/** EK 2 §5: j başına ayrı blok; j'ler ve koşulsuz tablo asla toplanmaz (U14/U22 taraması). */
function conditional(m: ScoreModel): string {
  const c: ScoreConditional | undefined = m.conditional;
  if (!c) return `<p class="cond-none muted small">${esc(ACCURACY.condNone)}</p>`;
  if (c.schema_version !== CONDITIONAL_SCHEMA) {
    return `<p class="cond-unsupported warn-box">${esc(ACCURACY.condUnsupported(c.schema_version))}</p>`;
  }
  const blocks = (c.by_j ?? []).map((b) => {
    const n = b.n_scored;
    const rows = condRowTable(b.rows ?? []);
    const cells = n < MIN_N_METRIC
      ? `<p class="small muted rows-only">${esc(ACCURACY.rowsOnly)}</p>`
      : cellTable(b.cells ?? [], null, { color: n >= MIN_N_VERDICT, smallN: n < MIN_N_VERDICT, scale: "live_conditional" });
    return `<div class="cond-j" data-j="${esc(String(b.j))}" data-n="${esc(String(n))}">` +
      `<h6>${esc(ACCURACY.condJ(b.j, n))}</h6>${cells}${rows}</div>`;
  });
  return `<section class="cond-scores"><h5>${esc(c.title ?? ACCURACY.condTitle)}</h5>` +
    `<p class="small muted">${esc(ACCURACY.condNote)}</p>${blocks.join("")}</section>`;
}

function backtestSection(m: ScoreModel): string {
  const cells = m.backtest?.cells ?? [];
  const body = cells.length === 0
    ? `<p class="muted small no-cells">${esc(ACCURACY.noBacktestCells)}</p>`
    : cellTable(cells, m.primary_cell, { color: true, smallN: false, scale: "backtest" });
  return `<section class="panel-backtest" data-model="${esc(m.model_id)}"><h4>${esc(m.backtest?.title ?? "")}</h4>${body}</section>`;
}

function liveSection(m: ScoreModel): string {
  const live = m.live;
  const n = live.n_scored;
  const head = `<h4>${esc(ACCURACY.liveHead(live.title, n, live.n_skipped))}</h4>` +
    `<p class="small muted breakdown">${esc(ACCURACY.liveBreakdown(live.n_live, live.n_late, live.n_refused, live.n_target_unavailable, live.n_pending))}</p>`;
  const rows = live.rows ?? [];
  let body: string;
  if (n === 0 && rows.length === 0) {
    body = `<p class="muted small live-none">${esc(ACCURACY.liveNone)}</p>`;
  } else if (n < MIN_N_METRIC) {
    const none = n === 0 ? `<p class="muted small live-none">${esc(ACCURACY.liveNone)}</p>` : "";
    body = `${none}<p class="small muted rows-only">${esc(ACCURACY.rowsOnly)}</p>${rowTable(rows)}`;
  } else {
    const smallN = n < MIN_N_VERDICT;
    const note = smallN ? `<p class="small muted insufficient-note">${esc(ACCURACY.insufficientNote)}</p>` : "";
    body = note + cellTable(live.cells ?? [], m.primary_cell, { color: !smallN, smallN, scale: "live" }) +
      descriptiveTable(live.descriptive ?? []) + rowTable(rows);
  }
  return `<section class="panel-live" data-model="${esc(m.model_id)}" data-n="${esc(String(n))}">${head}${body}` +
    invalidUseTable(live) + cancelledList(live) + selfReported(m) + conditional(m) + `</section>`;
}

/**
 * Doğruluk panelinin kart görünümü (sonuç ekranıyla AYNI fonksiyon, aynı alan sırası; G3).
 * Sha `scores.json` `card.params_sha256_8`'den; karşılaştırma kaynağı gömülü modelin sha'sıdır.
 */
export function accuracyCardVM(m: ScoreModel, info: ModelInfo | undefined, path: PathParamsInfo | undefined): CardVM {
  const c = m.card;
  const p = m.primary_cell;
  const ids = p?.rule_ids ?? (p?.rule_id ? [p.rule_id] : []);
  return {
    modelId: m.model_id,
    description: info?.description ?? null,
    kind: KIND_TEXT[m.kind] ?? m.kind,
    survival: path ? PATH.survivalModel(path.survival_model_id ?? DASH, sha8(path.survival_model_sha256)) : null,
    trainingN: c?.training_n === undefined ? null : String(c.training_n),
    trainingCutoff: c?.training_cutoff ?? null,
    sha: c?.params_sha256_8 ?? null,
    shaCompare: info?.params_sha256 ?? null,
    variants: c?.n_variants_same_data === undefined ? null : String(c.n_variants_same_data),
    primary: p ? `${p.output} · ${p.horizon_or_k} · ${p.metric} · ${ids.join(", ")}` : null,
    liveN: m.live.n_scored,
    liveVerdict: liveVerdict(m),
  };
}

/** Birincil hücrenin canlı hükmü: YALNIZ dosyadaki `verdict` alanından (U19); hesap yok. */
function liveVerdict(m: ScoreModel): string | null {
  const cell = (m.live.cells ?? []).find((c) => isPrimaryCell(c, m.primary_cell));
  return cell?.verdict ?? null;
}

function modelBlock(m: ScoreModel, v: AccuracyView): string {
  const info = v.models.find((x) => x.model_id === m.model_id);
  const open = v.open.includes(m.model_id) ? " open" : "";
  const summary = `<summary><span class="mono">${esc(m.model_id)}</span> · ${esc(KIND_TEXT[m.kind] ?? m.kind)} · ` +
    `${esc(ACCURACY.liveCount(m.live.n_scored, m.live.n_skipped))}</summary>`;
  return `<details class="model-block" data-model="${esc(m.model_id)}" data-kind="${esc(m.kind)}"${open}>${summary}` +
    renderModelCard(accuracyCardVM(m, info, v.pathParams.find((x) => x.model_id === m.model_id)), CARD.caption) +
    backtestSection(m) + liveSection(m) + `</details>`;
}

// ---------------------------------------------------------------- panel düzeyi bölümler

function retroSection(doc: ScoresDoc): string {
  const rows = doc.retro_info ?? [];
  if (rows.length === 0) return "";
  const ids: string[] = [];
  for (const r of rows) if (!ids.includes(r.model_id)) ids.push(r.model_id);
  const items = ids.map((id) => {
    const mine = rows.filter((r) => r.model_id === id);
    const basis = String((mine[0].class_evidence as Record<string, unknown> | undefined)?.basis ?? "");
    return `<li data-model="${esc(id)}" title="${esc(basis)}">` +
      `${esc(ACCURACY.retroLine(id, mine.map((r) => r.ticker).join(", "), mine.length))}</li>`;
  });
  return `<details class="retro muted"><summary>${esc(ACCURACY.retroTitle)}</summary><ul class="small">${items.join("")}</ul></details>`;
}

/**
 * Payda bölümü (G2): satırlar `status`'a göre ayrılır. "Atlanan" (canlı n_skipped) YALNIZ SKIPPED
 * satırlarını sayar; OUT_OF_SCOPE kapsam dışıdır ve hiçbir n'e girmez. Burada satır saymak dışında
 * hesap yoktur (U25).
 */
function denomTable(rows: Record<string, string>[], title: string, cls: string): string {
  const head = `<h5 class="denom-head">${esc(title)}</h5>`;
  if (rows.length === 0) return `${head}<p class="small muted denom-empty" data-group="${esc(cls)}">${esc(ACCURACY.none)}</p>`;
  const body = rows.map((r) =>
    `<tr data-ticker="${esc(r.ticker)}"><td class="mono">${esc(r.ticker)}</td><td>${esc(r.status ?? DASH)}</td>` +
    `<td title="${esc(r.note ?? "")}">${esc(r.skip_reason ?? DASH)}</td></tr>`);
  return `${head}<div class="scroll"><table class="grid compact denom-${esc(cls)}"><thead><tr><th>${esc(ACCURACY.colTicker)}</th>` +
    `<th>${esc(ACCURACY.colStatus)}</th><th>${esc(ACCURACY.skippedReason)}</th></tr></thead><tbody>${body.join("")}</tbody></table></div>`;
}

function skippedSection(doc: ScoresDoc): string {
  const rows = doc.skipped ?? [];
  if (rows.length === 0) return "";
  const skipped = rows.filter((r) => r.status === "SKIPPED");
  const oos = rows.filter((r) => r.status === "OUT_OF_SCOPE");
  const other = rows.filter((r) => r.status !== "SKIPPED" && r.status !== "OUT_OF_SCOPE");
  return `<details class="skipped"><summary>${esc(ACCURACY.denomTitle(rows.length))}</summary>` +
    denomTable(skipped, ACCURACY.denomSkipped(skipped.length), "skipped") +
    denomTable(oos, ACCURACY.denomOutOfScope(oos.length), "out-of-scope") +
    (other.length === 0 ? "" : denomTable(other, ACCURACY.denomOther(other.length), "other")) +
    `<p class="small muted denom-note">${esc(ACCURACY.denomNote)}</p></details>`;
}

function separateSection(doc: ScoresDoc): string {
  const models = doc.separate_models ?? [];
  if (models.length === 0) return "";
  const blocks = models.map((s) => {
    const notes = s.rows.filter((r) => r.note).map((r) => `<li>${esc(r.note ?? "")}</li>`);
    return `<div class="separate-model" data-model="${esc(s.model_id)}"><h5 class="mono">${esc(s.model_id)}</h5>` +
      rowTable(s.rows, "separate-rows") + (notes.length > 0 ? `<ul class="small muted">${notes.join("")}</ul>` : "") + `</div>`;
  });
  return `<section class="separate-models"><h4>${esc(ACCURACY.separateTitle)}</h4>${blocks.join("")}</section>`;
}

function header(s: ScoresView): string {
  const src = `${s.source} (${ACCURACY.sourceText[s.source] ?? s.source})`;
  const line = ACCURACY.source(src, s.generated_at_utc ?? DASH, s.as_of_session ?? DASH, s.sha12);
  return `<p class="small muted scores-source" data-source="${esc(s.source)}">${esc(line)}</p>` +
    (s.synthetic ? `<p class="warn-box synthetic">${esc(ACCURACY.syntheticNote)}</p>` : "") +
    (s.index_mismatch ? `<p class="warn-box index-mismatch">${esc(ACCURACY.indexMismatch)}</p>` : "");
}

function selector(doc: ScoresDoc, hidden: string[]): string {
  const boxes = doc.models.map((m) => {
    const checked = hidden.includes(m.model_id) ? "" : " checked";
    return `<label class="chk"><input type="checkbox" data-action="toggle-model" data-model="${esc(m.model_id)}"${checked}/> ` +
      `<span class="mono">${esc(m.model_id)}</span></label>`;
  });
  return `<details class="selector"><summary>${esc(ACCURACY.modelSelector)}</summary><div class="chk-grid">${boxes.join("")}</div></details>`;
}

// ---------------------------------------------------------------- D1 sonrası (scores_post_d1.json; EK 3 §6.5, U70)

const POST_D1_ID = "post_d1_hazard_v0";

/**
 * Ayrı ölçek (`live_post_d1`): koşulsuz tablo, öteki j'ler ve öteki terazilerle hiçbir satırda toplanmaz. Var olan koşullu
 * blok okuyucusunun aynı parçaları (hücre tablosu, satır tablosu; küçük-n kuralları aynen). Kart H43 adlarıyla:
 * `training_last_session_date` + anlam metni ve `spec_training_cutoff`. RETRO yalnız bilgidir, hiçbir n'e girmez.
 */
function postD1Section(v: ScoresPostD1View | null | undefined): string {
  if (v === undefined) return "";
  const t = ACCURACY.postD1;
  const open = (body: string, title: string = t.title) =>
    `<section class="panel-post-d1" data-scale="live_post_d1"><h4>${esc(title)}</h4>` +
    `<p class="small muted post-d1-note">${esc(t.note)}</p>${body}</section>`;
  if (!v || v.status === "NO_REPO") return open(`<p class="muted post-d1-repo-only">${esc(t.repoOnly)}</p>`);
  if (v.status === "NO_FILE") return open(`<p class="muted post-d1-no-file">${esc(t.noFile)}</p>`);
  if (v.unsupported_version !== null) return open(`<p class="error-box post-d1-version">${esc(t.unsupported(v.unsupported_version))}</p>`);
  if (v.integrity) return open(`<div class="error-box post-d1-integrity" data-rule="${esc(v.integrity.rule)}">${esc(t.integrity(ACCURACY.integrityRule[v.integrity.rule] ?? v.integrity.rule, v.integrity.detail))}</div>`);
  const doc = v.doc;
  const m = doc?.models.find((x) => x.model_id === POST_D1_ID) ?? doc?.models[0];
  if (!doc || !m) return open(`<p class="muted post-d1-no-file">${esc(t.noFile)}</p>`);
  const b = m.conditional_j1;
  const n = b.n_scored;
  const src = `<p class="small muted post-d1-source">${esc(t.source(v.path ?? DASH, v.generated_at_utc ?? DASH, v.as_of_session ?? DASH, v.sha12 ?? DASH))}</p>` +
    (doc.synthetic ? `<p class="warn-box synthetic">${esc(ACCURACY.syntheticNote)}</p>` : "");
  const counts = `<p class="small post-d1-counts" data-n="${n}">${esc(t.counts(n, b.n_live, b.n_late, b.n_refused, b.n_not_applicable, b.n_skipped, b.n_pending))}</p>`;
  const c = m.card ?? {};
  const p = m.primary_cell;
  const ids = p?.rule_ids ?? (p?.rule_id ? [p.rule_id] : []);
  const kv: [string, string][] = [
    [t.trainingN, c.training_n === undefined ? DASH : String(c.training_n)],
    [t.lastSession, c.training_last_session_date ?? DASH],
    [t.specCutoff, c.spec_training_cutoff ?? DASH],
    [t.parent, c.parent_model_id ?? DASH],
    [t.sha, c.params_sha256_8 ?? DASH],
    [t.variants, c.n_variants_same_data === undefined ? DASH : String(c.n_variants_same_data)],
    [t.primary, p ? `${p.output} · ${p.metric} · ${ids.join(", ")}` : DASH],
  ];
  const card = `<details class="post-d1-card" open><summary>${esc(t.cardTitle)} · ${esc(KIND_TEXT[m.kind] ?? m.kind)}</summary>` +
    `<table class="kv">${kv.map(([k, x]) => `<tr><th>${esc(k)}</th><td class="mono">${esc(x)}</td></tr>`).join("")}</table>` +
    `<p class="small muted post-d1-meaning">${esc(t.lastSessionMeaning)}</p></details>`;
  const cells = n < MIN_N_METRIC
    ? `<p class="small muted rows-only">${esc((b.cells ?? []).length ? ACCURACY.rowsOnly : t.noCells)}</p>`
    : (n < MIN_N_VERDICT ? `<p class="small muted insufficient-note">${esc(ACCURACY.insufficientNote)}</p>` : "") +
      cellTable(b.cells ?? [], p, { color: n >= MIN_N_VERDICT, smallN: n < MIN_N_VERDICT, scale: "live_post_d1" });
  const rows = (b.rows ?? []).length ? `<h5>${esc(t.rowsTitle)}</h5>${condRowTable(b.rows)}` : "";
  const retro = (doc.retro_info ?? []).filter((r) => r.model_id === m.model_id);
  const retroBlock = retro.length
    ? `<details class="retro post-d1-retro muted" data-n="${retro.length}"><summary>${esc(t.retro(retro.length))}</summary>` +
      `<ul class="small">${retro.map((r) => `<li data-ticker="${esc(r.ticker)}">${esc(t.retroLine(r.ticker, r.d1 ?? DASH))}</li>`).join("")}</ul></details>`
    : "";
  return open(src + counts + card + cells + rows + retroBlock, b.title ?? t.title);
}

export function renderAccuracy(v: AccuracyView): string {
  // Üçüncü bağımsız bölüm (EK 3 §7.2): zaman-dışı panel; model bloklarının içine gömülmez
  return renderScores(v) + postD1Section(v.postD1) + (v.oot === undefined ? "" : renderOotPanel({ ...v.oot, models: v.oot.models ?? v.models }));
}

function renderScores(v: AccuracyView): string {
  const s = v.scores;
  if (!s) return `<p class="closed-state no-scores">${esc(ACCURACY.noFile)}</p>`;
  if (s.unsupported_version !== null) {
    return `<div class="error-box version-error" data-version="${esc(s.unsupported_version)}">` +
      `${esc(ACCURACY.unsupportedVersion(s.unsupported_version))}</div>`;
  }
  if (s.integrity) {
    const p = s.integrity;
    const rule = ACCURACY.integrityRule[p.rule] ?? p.rule;
    return header(s) +
      `<div class="error-box integrity-error" data-rule="${esc(p.rule)}" data-model="${esc(p.model_id ?? "")}">` +
      `<strong>${esc(ACCURACY.integrityTitle(rule))}</strong>` +
      `<p class="mono small">${esc(p.detail)}</p><p class="small">${esc(ACCURACY.integrityNote)}</p></div>`;
  }
  const doc = s.doc;
  if (!doc) return `<p class="closed-state no-scores">${esc(ACCURACY.noFile)}</p>`;
  const shown = doc.models.filter((m) => !v.hidden.includes(m.model_id));
  return header(s) +
    `<div class="regime" data-role="regime">${esc(RESULTS.regime)}</div>` +
    `<p class="small muted scales-note">${esc(ACCURACY.scalesNote)}</p>` +
    selector(doc, v.hidden) +
    `<div class="model-blocks">${shown.map((m) => modelBlock(m, v)).join("")}</div>` +
    retroSection(doc) + skippedSection(doc) + separateSection(doc);
}

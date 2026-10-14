// Sonuç ekranı (SPEC_APP §3b, §3c) saf render. Bütün sayılar Rust komutlarından gelir (predict_all,
// ceiling_display, score_hints); burada yalnız biçimlendirme ve yerleşim vardır.
import { CARD, CEILING, F6_ORIGIN_TEXT, KIND_TEXT, PATH, RESULTS, SUMMARY } from "../i18n/tr";
import type {
  CeilingDisplay,
  CeilingRow,
  F6Doc,
  HorizonCell,
  ModelInfo,
  ModelRun,
  Num,
  PathDisplayRow,
  PathHorizon,
  PathParamsInfo,
  PathPriceCell,
  ScoreHints,
} from "../types";
import { esc } from "../dom";
import { renderModelCard, type CardVM } from "./card";
import { codeText } from "./codes";
import { colorOf } from "./colors";
import { DASH, fixed1, pct0, pctSigned1, points1, pyRepr, sha8, tl2, toNum } from "./format";
import { barChart, fanChart, legend, lineChart, type FanSeries, type Series } from "./svg";

export const HORIZONS = ["D1", "D3", "D5", "D10"] as const;
export const ALWAYS_CEILING_ID = "ALWAYS_CEILING";
const APPROX_PRICE_MODEL = "base_always_ceiling";

export function isGroupB(r: ModelRun): boolean {
  return r.kind === "hazard" || r.kind === "km";
}

/**
 * Tavan yolu (Faz 4) modelleri: S'leri gömülü seri modelinin bit-eşit kopyası olduğundan Grup B'de
 * GÖRÜNMEZ (SPEC_APP EK 2 §4.1); Grup A'da sütunları, Grup C'de getiri dağılımı vardır.
 */
export function isPathModel(r: ModelRun): boolean {
  return r.kind === "ceiling_path";
}

/**
 * Grup A sütun sırası (EK 2 §4.1 [KARAR]): doğrusal/PB/market20 → tavan yolu (INDEX sırası) →
 * basit kurallar.
 */
export function groupA(runs: ModelRun[]): ModelRun[] {
  const a = runs.filter((r) => !isGroupB(r));
  return [
    ...a.filter((r) => r.kind !== "rule" && !isPathModel(r)),
    ...a.filter(isPathModel),
    ...a.filter((r) => r.kind === "rule"),
  ];
}

/** Grup B: hazard modelleri önce, KM kuralları sonra. */
export function groupB(runs: ModelRun[]): ModelRun[] {
  const b = runs.filter(isGroupB);
  return [...b.filter((r) => r.kind === "hazard"), ...b.filter((r) => r.kind === "km")];
}

export interface ScenarioHeader {
  title: string;
  created_at_local: string;
  same_index: boolean;
}

export interface ResultsView {
  runs: ModelRun[];
  /** `path_display`: fiyat satırı türevleri (model başına). */
  pathDisplay: PathDisplayRow[];
  /** `path_params`: gömülü tavan yolu modellerinin künyesi (hücre notu, seri modeli). */
  pathParams: PathParamsInfo[];
  /** j = 0'da (koşulsuz) tavan görüntüleme türevleri; Rust `ceiling_display`. */
  ceiling: CeilingDisplay | null;
  hints: ScoreHints | null;
  models: ModelInfo[];
  hidden: string[];
  scenario: ScenarioHeader | null;
  f6: F6Doc | null;
  openCard: string | null;
  openWarnings: string | null;
  savedId: string | null;
  canSave: boolean;
  /** Repo modu: "Dondur akışına geç" ancak repo modunda açıktır. */
  repoMode: boolean;
  /** Resmi sicil görünümü: dondurulmuş kayıt değerleri, "SENARYO" filigranı YOKTUR (§3c). */
  official?: boolean;
  /** "Tavan serisi — kaç gün tavan?" kartı (EK 3 §5; `render/summary.ts`, ekran çizer): Grup A'dan önce; Grup B katlanır. */
  summaryHtml?: string;
}

function tip(raw: string, official = false): string {
  return official ? `${RESULTS.raw}: ${raw}` : `${RESULTS.scenarioTooltip} · ${RESULTS.raw}: ${raw}`;
}

export function refusalBlock(run: ModelRun): string {
  const code = run.refusal?.code ?? "?";
  const head = run.status === "ERROR" ? RESULTS.error : RESULTS.refused;
  const field = run.refusal?.field ?? null;
  return `<div class="refusal" data-model="${esc(run.model_id)}" data-code="${esc(code)}">` +
    `<div class="refusal-head">${esc(head)} · <span class="mono">${esc(code)}</span></div>` +
    (field ? `<div class="mono small">${esc(field)}</div>` : "") +
    `<div class="refusal-text">${esc(codeText(code, field))}</div></div>`;
}

function isShown(run: ModelRun): boolean {
  return run.status === "PREDICTED" && run.output !== null;
}

export function pathInfo(v: ResultsView, id: string): PathParamsInfo | undefined {
  return v.pathParams.find((p) => p.model_id === id);
}

function headerCell(run: ModelRun, v: ResultsView): string {
  const n = run.output?.warnings.length ?? 0;
  const badge = `<button class="badge ${n ? "badge-warn" : "badge-none"}" data-action="warnings" data-model="${esc(run.model_id)}" data-count="${n}">${esc(RESULTS.warningsBadge(n))}</button>`;
  const hidden = v.hidden.includes(run.model_id) ? " hidden-col" : "";
  // Tavan yolu sütunu Grup B'de çizilmez; S'in kaynağı başlıkta yazar (EK 2 §4.1).
  const sid = isPathModel(run) ? pathInfo(v, run.model_id)?.survival_model_id ?? null : null;
  const note = sid ? `<div class="small muted survival-note">${esc(PATH.survivalNote(sid))}</div>` : "";
  const mark = v.official ? "" : `<div class="watermark">${esc(RESULTS.watermark)}</div>`;
  return `<th class="model-col${hidden}" data-model="${esc(run.model_id)}" style="border-top-color:${colorOf(run.model_id)}">` +
    `<div class="mid mono">${esc(run.model_id)}</div>${mark}` +
    `<div class="sha mono">${esc(sha8(run.params_sha256))}</div>${note}` +
    `<button class="link" data-action="card" data-model="${esc(run.model_id)}">${esc(RESULTS.cardButton)}</button> ${badge}</th>`;
}

function maeLine(v: ResultsView, modelId: string, h: string): string {
  const m = v.hints?.models[modelId]?.mae[h];
  if (!m || m.model_value === null || m.model_value === undefined) return "";
  return `<div class="mae small muted">${esc(RESULTS.maeLine(String(m.n ?? DASH), points1(m.model_value)))}</div>`;
}

function horizonCell(run: ModelRun, h: string, v: ResultsView): string {
  const c = (run.output as unknown as Record<string, HorizonCell | null | undefined>)[h] ?? null;
  if (!c) return `<td class="cell empty" data-model="${esc(run.model_id)}" data-h="${h}">${DASH}</td>`;
  const raw = [`return=${pyRepr(c.return)}`, `return_unclipped=${pyRepr(c.return_unclipped)}`, `price=${pyRepr(c.price)}`, `p_up=${pyRepr(c.p_up)}`].join(", ");
  const clip = c.return_clipped
    ? `<span class="clip" data-clipped="${esc(c.return_clipped)}" title="${esc(RESULTS.clipTooltip(pctSigned1(c.return_unclipped)))}">${RESULTS.clipMark}</span>`
    : "";
  const ret = c.return === null ? DASH : pctSigned1(c.return);
  const approx = run.model_id === APPROX_PRICE_MODEL && c.price !== null;
  const price = c.price === null ? DASH : `${approx ? "≈ " : ""}${tl2(c.price)}`;
  const approxTag = approx ? ` <span class="tag" title="${esc(RESULTS.approxTooltip)}">${esc(RESULTS.approx)}</span>` : "";
  const arrow = c.p_up === null ? "" : c.direction === "UP" ? ` ${RESULTS.up}` : c.direction === "DOWN" ? ` ${RESULTS.down}` : "";
  const pup = c.p_up === null ? DASH : `${pct0(c.p_up)}${arrow}`;
  return `<td class="cell" data-model="${esc(run.model_id)}" data-h="${h}" title="${esc(tip(raw))}">` +
    `<div class="ret">${esc(ret)}${clip}</div><div class="price">${esc(price)}${approxTag}</div>` +
    `<div class="pup" title="${esc(RESULTS.pUpLabel)}">${esc(pup)}</div>${maeLine(v, run.model_id, h)}</td>`;
}

/** Tavan yolu çıktısının D_h hücresi (`HorizonCell` değil: karışım özeti). */
export function pathCell(run: ModelRun, h: string): PathHorizon | null {
  return (run.output as unknown as Record<string, PathHorizon | null | undefined>)[h] ?? null;
}

export function priceCell(v: ResultsView, id: string, h: number): PathPriceCell | undefined {
  return v.pathDisplay.find((d) => d.model_id === id)?.cells[h - 1];
}

/** Ham değerler tooltip'i (EK 2 §4.1): `return, p_up, mean, q10, q90, S_h, n_atoms`. */
function pathRaw(c: PathHorizon): string {
  return [
    `return=${pyRepr(c.return)}`,
    `p_up=${pyRepr(c.p_up)}`,
    `mean=${pyRepr(c.mean)}`,
    `q10=${pyRepr(c.q10)}`,
    `q90=${pyRepr(c.q90)}`,
    `S_h=${pyRepr(c.S_h)}`,
    `n_atoms=${c.n_atoms}`,
  ].join(", ");
}

export function pathIsOk(c: PathHorizon | null): boolean {
  return c !== null && c.post_break?.status !== "POST_BREAK_INSUFFICIENT" && c.return !== null;
}

/** Yön oku: görüntüleme kuralı (`p_up ≥ 0.5 → ↑`); çıktıda `direction` yoktur. */
function pathArrow(p: Num | null): string {
  const n = toNum(p);
  if (n === null || !Number.isFinite(n)) return "";
  return n >= 0.5 ? ` ${RESULTS.up}` : ` ${RESULTS.down}`;
}

function pathPriceText(v: ResultsView, id: string, h: number): string {
  const pc = priceCell(v, id, h);
  if (!pc) return DASH;
  if (pc.on_limit_path && pc.c_text !== null) {
    return `<span class="price exact">${esc(tlText(pc.c_text))}</span> <span class="tag limit-tag">${esc(PATH.limitBadge)}</span>`;
  }
  if (pc.approx_price === null) return DASH;
  return `<span class="price approx muted" title="${esc(PATH.approxTooltip)}">≈ ${esc(tl2(pc.approx_price))}</span>`;
}

/** `C_h` metni kayıttaki dizedir: biçimlendirilmez, yalnız birim eklenir. */
function tlText(c: string): string {
  return `${c} TL`;
}

function pathHorizonCell(run: ModelRun, h: string, v: ResultsView): string {
  const c = pathCell(run, h);
  const hNum = Number(h.slice(1));
  if (!c) return `<td class="cell empty" data-model="${esc(run.model_id)}" data-h="${h}">${DASH}</td>`;
  if (!pathIsOk(c)) {
    return `<td class="cell insufficient" data-model="${esc(run.model_id)}" data-h="${h}" data-status="${esc(c.post_break?.status ?? "")}" ` +
      `title="${esc(PATH.insufficient)}">${DASH}</td>`;
  }
  return `<td class="cell path-cell" data-model="${esc(run.model_id)}" data-h="${h}" title="${esc(tip(pathRaw(c), v.official))}">` +
    `<div class="ret">${esc(pctSigned1(c.return))} <span class="tag median-tag">${esc(PATH.medianBadge)}</span></div>` +
    `<div class="band small muted">${esc(PATH.bandLabel(pctSigned1(c.q10), pctSigned1(c.q90)))}</div>` +
    `<div class="pup" title="${esc(RESULTS.pUpLabel)}">${esc(`${pct0(c.p_up)}${pathArrow(c.p_up)}`)}</div>` +
    `<div class="s-h small" title="${esc(PATH.sTooltip(hNum))}">${esc(`S_${hNum} ${pct0(c.S_h)}`)}</div>` +
    `<div class="price-row">${pathPriceText(v, run.model_id, hNum)}</div>${maeLine(v, run.model_id, h)}</td>`;
}

export function renderGroupA(v: ResultsView): string {
  const runs = groupA(v.runs).filter((r) => !v.hidden.includes(r.model_id));
  const head = `<tr><th>${esc(RESULTS.horizon)}</th>${runs.map((r) => headerCell(r, v)).join("")}</tr>`;
  const rows = HORIZONS.map((h, i) => {
    const cells = runs.map((r) => {
      if (isShown(r)) return isPathModel(r) ? pathHorizonCell(r, h, v) : horizonCell(r, h, v);
      return i === 0 ? `<td class="refused-cell" rowspan="${HORIZONS.length}">${refusalBlock(r)}</td>` : "";
    });
    return `<tr><th>${h}</th>${cells.join("")}</tr>`;
  });
  return `<section class="group group-a"><h3>${esc(RESULTS.groupA)}</h3><div class="scroll"><table class="grid">` +
    `<thead>${head}</thead><tbody>${rows.join("")}</tbody></table></div></section>`;
}

function rowOf(v: ResultsView, id: string): CeilingRow | undefined {
  return v.ceiling?.rows.find((r) => r.model_id === id);
}

function numList(xs: Num[] | null | undefined): (number | null)[] {
  return (xs ?? []).map((x) => toNum(x));
}

export function renderGroupB(v: ResultsView): string {
  const runs = groupB(v.runs).filter((r) => !v.hidden.includes(r.model_id));
  const always = rowOf(v, ALWAYS_CEILING_ID);
  const nRows = 12;
  const head = `<tr><th>k</th>${runs.map((r) => headerCell(r, v)).join("")}` +
    `<th class="model-col constant" title="${esc(CEILING.alwaysNote)}"><div class="mid">${esc(CEILING.always)}</div><div class="small muted">${esc(CEILING.alwaysNote)}</div></th></tr>`;
  const sCell = (row: CeilingRow | undefined, k: number, id: string) =>
    row ? `<td class="cell s" data-model="${esc(id)}" data-k="${k}" title="${esc(tip(pyRepr(row.S[k - 1])))}">${esc(pct0(row.S[k - 1]))}</td>` : `<td class="undef">${DASH}</td>`;
  const body: string[] = [];
  for (let k = 1; k <= 10; k += 1) {
    const cells = runs.map((r) => {
      if (isShown(r)) return sCell(rowOf(v, r.model_id), k, r.model_id);
      return k === 1 ? `<td class="refused-cell" rowspan="${nRows}">${refusalBlock(r)}</td>` : "";
    });
    body.push(`<tr><th title="${esc(CEILING.axisY)}">${esc(CEILING.kRow(k))}</th>${cells.join("")}<td class="cell constant">${always ? esc(pct0(always.S[k - 1])) : DASH}</td></tr>`);
  }
  const statRow = (label: string, tipText: string, f: (r: CeilingRow) => string) =>
    `<tr class="stat"><th title="${esc(tipText)}">${esc(label)}</th>${runs
      .filter(isShown)
      .map((r) => {
        const row = rowOf(v, r.model_id);
        return row ? `<td class="cell" data-model="${esc(r.model_id)}" title="${esc(tipText)}">${esc(f(row))}</td>` : `<td class="undef">${DASH}</td>`;
      })
      .join("")}<td class="cell constant">${always ? esc(f(always)) : DASH}</td></tr>`;
  body.push(statRow(CEILING.expectedL, CEILING.expectedLTip, (r) => CEILING.days(fixed1(r.expected_l))));
  body.push(statRow(CEILING.medianL, CEILING.medianLTip, (r) => CEILING.days(String(r.median_l))));

  const series: Series[] = runs.filter(isShown).flatMap((r) => {
    const row = rowOf(v, r.model_id);
    return row ? [{ id: r.model_id, label: r.model_id, color: colorOf(r.model_id), points: row.S.map((s, i) => [i + 1, s] as [number, number]) }] : [];
  });
  if (always) series.push({ id: ALWAYS_CEILING_ID, label: CEILING.always, color: colorOf(ALWAYS_CEILING_ID), dashed: true, points: always.S.map((s, i) => [i + 1, s] as [number, number]) });
  const chart = lineChart(series, { xMin: 1, xMax: 10, xLabel: CEILING.axisX, yLabel: CEILING.axisY, cls: "s-curve" });


  const bars = runs.filter(isShown).map((r) =>
    barChart(numList(r.output?.P_L), {
      color: colorOf(r.model_id),
      title: r.model_id,
      tooltip: CEILING.plTip,
      labels: numList(r.output?.P_L).map((p, l) => `P(L = ${l}) = ${pct0(p)}`),
    }),
  );
  if (always) bars.push(barChart(always.P_L, { color: colorOf(ALWAYS_CEILING_ID), title: CEILING.always, tooltip: CEILING.plTip, labels: always.P_L.map((p, l) => `P(L = ${l}) = ${pct0(p)}`) }));

  const shown = runs.filter(isShown);
  const pClose = `<table class="grid compact"><thead><tr><th>k</th>${shown.map((r) => `<th class="mono">${esc(r.model_id)}</th>`).join("")}</tr></thead><tbody>` +
    Array.from({ length: 10 }, (_, i) =>
      `<tr><th>D${i + 1}</th>${shown.map((r) => `<td class="cell" data-model="${esc(r.model_id)}" title="${esc(tip(pyRepr((r.output?.P_close_ceiling ?? [])[i])))}">${esc(pct0((r.output?.P_close_ceiling ?? [])[i]))}</td>`).join("")}</tr>`,
    ).join("") + `</tbody></table>`;
  const hazards = `<details><summary>${esc(CEILING.hazards)}</summary><table class="grid compact"><thead><tr><th>d</th>${shown.map((r) => `<th class="mono">${esc(r.model_id)}</th>`).join("")}</tr></thead><tbody>` +
    Array.from({ length: 10 }, (_, i) =>
      `<tr><th>${i + 1}</th>${shown.map((r) => `<td class="cell" title="${esc(pyRepr((r.output?.hazard ?? [])[i]))}">${esc(pct0((r.output?.hazard ?? [])[i]))}</td>`).join("")}</tr>`,
    ).join("") + `</tbody></table></details>`;
  const hint = v.ceiling?.price_hint
    ? `<p class="info-line">${esc(CEILING.priceHint)}: ${v.ceiling.price_hint.map((p) => esc(CEILING.priceHintItem(p.k, tl2(p.price)))).join(" · ")}</p>`
    : "";

  return `<section class="group group-b"><h3>${esc(RESULTS.groupB)}</h3>` +
    `<h4>${esc(CEILING.sTitle)}</h4><div class="scroll"><table class="grid"><thead>${head}</thead><tbody>${body.join("")}</tbody></table></div>` +
    `<div class="chart-wrap">${chart}${legend(series)}</div>` +
    `<h4 title="${esc(CEILING.plTip)}">${esc(CEILING.plTitle)}</h4><div class="bars-row">${bars.join("")}</div>` +
    `<h4>${esc(CEILING.pCloseTitle)} <span class="small muted">${esc(CEILING.pCloseNote)}</span></h4><div class="scroll">${pClose}</div>` +
    hint + hazards + `</section>`;
}

// ---------------------------------------------------------------- Grup C (EK 2 §4.2)

const H_ALL = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] as const;

function cellNote(v: ResultsView, run: ModelRun): string {
  const info = pathInfo(v, run.model_id);
  const head = info
    ? `<p class="small muted cells-note">${esc(PATH.cellsNote(String(info.n_ipo ?? DASH), info.cutoff_date ?? DASH, info.n_min))}</p>`
    : "";
  const lines = H_ALL.flatMap((h) => {
    const c = pathCell(run, `D${h}`);
    return (c?.post_break?.cells ?? []).map((pc) => {
      const src = pc.sources.map(([g, m]) => `${g}${m}`).join(", ");
      return `<li data-h="${h}" data-group="${esc(pc.group)}" data-m="${pc.m}">D${h} · ` +
        `${esc(PATH.cellLine(pc.group, pc.m, pc.n, pc.pooled ? PATH.cellPooled : PATH.cellOwn, src))}</li>`;
    });
  });
  return `<details class="post-break-cells" data-model="${esc(run.model_id)}"><summary>${esc(PATH.cellsTitle)}</summary>` +
    `${head}<ul class="small mono">${lines.join("")}</ul></details>`;
}

function limitPathRow(v: ResultsView, run: ModelRun): string {
  const d = v.pathDisplay.find((x) => x.model_id === run.model_id);
  if (!d || d.ipo_price === null) return "";
  const snapDiff = d.snapped_ipo_price !== null && d.snapped_ipo_price !== d.ipo_price;
  const w = run.output?.warnings.find((x) => x.code === "IPO_PRICE_NOT_ON_TICK_GRID");
  const snapBox = snapDiff && w ? `<p class="warn-box tick-grid" data-model="${esc(run.model_id)}">${esc(codeText(w.code, w.field ?? null, w))}</p>` : "";
  const cs = d.c.map((c, i) => `<li data-k="${i + 1}"><span class="mono">C_${i + 1}</span> ${esc(tlText(c))}</li>`).join("");
  return `<div class="limit-path" data-model="${esc(run.model_id)}"><h5>${esc(PATH.limitTitle)} · <span class="mono">${esc(run.model_id)}</span></h5>` +
    `<p class="small mono">${esc(PATH.limitPrice(d.ipo_price))} · ${esc(PATH.limitSnapped(d.snapped_ipo_price ?? DASH))} · ${esc(PATH.limitTick(d.tick ?? DASH))}</p>` +
    snapBox + `<ul class="c-list small mono">${cs}</ul></div>`;
}

export function renderGroupC(v: ResultsView): string {
  const all = v.runs.filter(isPathModel);
  if (!all.length) return "";
  const runs = all.filter((r) => !v.hidden.includes(r.model_id));
  const shown = runs.filter(isShown);
  const head = `<tr><th>${esc(PATH.colH)}</th>${runs.map((r) => headerCell(r, v)).join("")}</tr>`;
  const body = H_ALL.map((h) => {
    const cells = runs.map((r) => {
      if (!isShown(r)) return h === 1 ? `<td class="refused-cell" rowspan="${H_ALL.length}">${refusalBlock(r)}</td>` : "";
      const c = pathCell(r, `D${h}`);
      if (!pathIsOk(c) || c === null) {
        return `<td class="cell insufficient" data-model="${esc(r.model_id)}" data-h="D${h}" title="${esc(PATH.insufficient)}">${DASH}</td>`;
      }
      const parts = [
        `<span class="ret">${esc(pctSigned1(c.return))}</span>`,
        `<span class="band muted">[${esc(pctSigned1(c.q10))}, ${esc(pctSigned1(c.q90))}]</span>`,
        `<span class="pup">${esc(pct0(c.p_up))}</span>`,
        `<span class="s-h">${esc(pct0(c.S_h))}</span>`,
        `<span class="price">${pathPriceText(v, r.model_id, h)}</span>`,
        `<span class="atoms muted">${esc(String(c.n_atoms))}</span>`,
      ];
      return `<td class="cell path-cell" data-model="${esc(r.model_id)}" data-h="D${h}" title="${esc(tip(pathRaw(c), v.official))}">${parts.join(" · ")}</td>`;
    });
    return `<tr><th>${esc(PATH.hRow(h))}</th>${cells.join("")}</tr>`;
  });
  const cols = `<p class="small muted group-c-cols">${esc([PATH.colMedian, PATH.colBand, PATH.colPUp, PATH.colS, PATH.colPrice, PATH.colAtoms].join(" · "))}</p>`;
  const fan: FanSeries[] = shown.map((r) => ({
    id: r.model_id,
    label: r.model_id,
    color: colorOf(r.model_id),
    q10: H_ALL.map((h) => toNum(pathCell(r, `D${h}`)?.q10 ?? null)),
    q50: H_ALL.map((h) => toNum(pathCell(r, `D${h}`)?.q50 ?? null)),
    q90: H_ALL.map((h) => toNum(pathCell(r, `D${h}`)?.q90 ?? null)),
    rho: numList(r.output?.limit_path?.rho),
  }));
  const chart = fan.length ? fanChart(fan, { xMin: 1, xMax: 10, xLabel: PATH.chartX, yLabel: PATH.chartY, cls: "fan-chart" }) : "";
  const fanLegend = legend(
    fan.flatMap((f) => [
      { id: `${f.id}:q50`, label: PATH.q50Label(f.id), color: f.color, points: [] },
      { id: `${f.id}:band`, label: PATH.bandSeries(f.id), color: f.color, points: [] },
      { id: `${f.id}:rho`, label: PATH.rhoLabel(f.id), color: f.color, points: [], dashed: true },
    ]),
  );
  return `<section class="group group-c"><h3>${esc(PATH.groupC)}</h3>${cols}` +
    `<div class="scroll"><table class="grid compact path-table"><thead>${head}</thead><tbody>${body.join("")}</tbody></table></div>` +
    (chart ? `<div class="chart-wrap">${chart}${fanLegend}</div>` : "") +
    shown.map((r) => limitPathRow(v, r)).join("") +
    `<p class="small muted limit-compare">${esc(PATH.limitCompare)}</p>` +
    shown.map((r) => cellNote(v, r)).join("") +
    `</section>`;
}

function renderWarningsPanel(v: ResultsView): string {
  const run = v.runs.find((r) => r.model_id === v.openWarnings);
  if (!run) return "";
  const ws = run.output?.warnings ?? [];
  const items = ws.length
    ? ws.map((w) => `<li data-code="${esc(w.code)}"><span class="mono">${esc(w.code)}</span>${w.horizon ? ` · ${esc(w.horizon)}` : ""}: ${esc(codeText(w.code, w.feature ?? null, w))}</li>`).join("")
    : `<li>${esc(RESULTS.noWarnings)}</li>`;
  return `<section class="panel warnings-panel" data-model="${esc(run.model_id)}"><h4>${esc(RESULTS.warningsTitle(run.model_id))}</h4><ul>${items}</ul>` +
    `<button data-action="close-panel">${esc(RESULTS.close)}</button></section>`;
}

/** Kart alanları metindir: sayı varsa aynen, yoksa null (satırda "—"). */
function num(x: number | null | undefined): string | null {
  return x === null || x === undefined ? null : String(x);
}

/**
 * Sonuç ekranının kart görünümü. Sha çalıştırılan modelin `params_sha256`'sındandır; karşılaştırma
 * kaynağı `scores.json` kartıdır (ilk 8 hane farklıysa kartta sarı uyarı; metrik değil, sha denetimi).
 */
export function resultsCardVM(v: ResultsView, id: string): CardVM {
  const m = v.models.find((x) => x.model_id === id);
  const run = v.runs.find((r) => r.model_id === id);
  const h = v.hints?.models[id];
  const card = h?.card ?? null;
  const pc = h?.primary_cell;
  const info = v.pathParams.find((x) => x.model_id === id);
  return {
    modelId: id,
    description: m?.description ?? null,
    kind: KIND_TEXT[run?.kind ?? m?.kind ?? ""] ?? null,
    survival: info ? PATH.survivalModel(info.survival_model_id ?? DASH, sha8(info.survival_model_sha256)) : null,
    trainingN: num(card?.training_n ?? m?.training_n),
    trainingCutoff: card?.training_cutoff ?? m?.training_cutoff_date ?? null,
    sha: run?.params_sha256 ?? m?.params_sha256 ?? null,
    shaCompare: card?.params_sha256_8 ?? null,
    variants: num(card?.n_variants_same_data),
    primary: pc ? `${pc.output ?? ""} · ${pc.horizon_or_k ?? ""} · ${pc.metric ?? ""} · ${(pc.rule_ids ?? []).join(", ")}` : null,
    liveN: h?.live_n_scored ?? null,
    liveVerdict: h?.live_primary_verdict ?? null,
  };
}

function renderCard(v: ResultsView): string {
  const id = v.openCard;
  if (!id) return "";
  const src = v.hints
    ? `<p class="small muted">${esc(CARD.scoresSource(v.hints.source, v.hints.generated_at_utc ?? DASH, v.hints.as_of_session ?? DASH, v.hints.sha12))}</p>` +
      (v.hints.index_mismatch ? `<p class="warn-box">${esc(CARD.scoresIndexMismatch)}</p>` : "")
    : `<p class="small muted">${esc(CARD.noScores)}</p>`;
  return `<section class="panel card-panel" data-model="${esc(id)}"><h4>${esc(CARD.title(id))}</h4>` +
    renderModelCard(resultsCardVM(v, id), CARD.caption) +
    `${src}<button data-action="close-panel">${esc(RESULTS.close)}</button></section>`;
}

function renderSelector(v: ResultsView): string {
  const boxes = [...groupA(v.runs), ...groupB(v.runs)].map((r) => {
    const checked = v.hidden.includes(r.model_id) ? "" : " checked";
    return `<label class="chk"><input type="checkbox" data-action="toggle-model" data-model="${esc(r.model_id)}"${checked}/> <span class="mono">${esc(r.model_id)}</span></label>`;
  });
  return `<details class="selector"><summary>${esc(RESULTS.modelSelector)}</summary><div class="chk-grid">${boxes.join("")}</div></details>`;
}

function renderHeader(v: ResultsView): string {
  const parts: string[] = [];
  if (v.scenario) {
    parts.push(`<p class="scenario-head">${esc(RESULTS.scenarioLoaded(v.scenario.title, v.scenario.created_at_local))} ` +
      `<button data-action="to-inputs">${esc(RESULTS.toInputs)}</button></p>`);
    if (!v.scenario.same_index) parts.push(`<p class="warn-box other-index">${esc(RESULTS.otherIndex)}</p>`);
  }
  if (v.f6) {
    parts.push(`<p class="small muted">${esc(RESULTS.f6Summary(F6_ORIGIN_TEXT[v.f6.origin] ?? v.f6.origin, v.f6.value ?? v.f6.refusal ?? DASH))}</p>`);
  }
  if (v.canSave) {
    parts.push(`<div class="save-row"><input type="text" data-role="save-title" placeholder="${esc(RESULTS.saveTitle)}"/> ` +
      `<button data-action="save-scenario">${esc(RESULTS.saveButton)}</button> <span class="small muted">${esc(RESULTS.saveNote)}</span> ` +
      `<button data-action="official-flow"${v.repoMode ? "" : ` disabled title="${esc(RESULTS.officialFlowClosed)}"`}>${esc(RESULTS.officialFlow)}</button></div>`);
  }
  if (v.savedId) parts.push(`<p class="ok-box">${esc(RESULTS.savedAs(v.savedId))}</p>`);
  return parts.join("");
}

/** Grup B katlanır ayrıntıdır (EK 3 §5.1; varsayılan kapalı). */
export function renderGroupBDetails(v: ResultsView): string {
  return `<details class="group-b-details" id="group-b-details"><summary>${esc(SUMMARY.detailGroupB)}</summary>${renderGroupB(v)}</details>`;
}

export function renderResults(v: ResultsView): string {
  if (!v.runs.length) return `<p class="muted empty-state">${esc(RESULTS.empty)}</p><button data-action="go-inputs">${esc(RESULTS.goInputs)}</button>`;
  return renderHeader(v) +
    `<div class="regime" data-role="regime">${esc(RESULTS.regime)}</div>` +
    (v.summaryHtml ?? "") +
    renderSelector(v) + renderCard(v) + renderWarningsPanel(v) +
    renderGroupA(v) + renderGroupBDetails(v) + renderGroupC(v);
}


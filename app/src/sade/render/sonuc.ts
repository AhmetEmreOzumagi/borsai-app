// Tahmin sonucu (pano `Sonuc`): senaryo. Sayılar `predict_all` (ya da kişisel kayıttaki çıktı; yeniden hesaplanmaz),
// `ceiling_display`, `ceiling_summary` ve `headline_gate`'ten; geçmiş test değerleri `perf_view` / `score_hints`'ten aynen.
import { esc } from "../../dom";
import { F6_ORIGIN_TEXT, RESULTS, SADE, STAGES } from "../../i18n/tr";
import { fixed1, metric4, pct0, pctSigned1, points1, price2 } from "../../render/format";
import { distBars, fillPct } from "../../render/svg";
import type { ResultsState } from "../../state";
import type { CeilingDisplay, CeilingSummary, ModelRun, ScoreHints, SummaryRow } from "../../types";
import type { HeadlineGate, PerfView } from "../types";
import { renderCalc } from "./calc";
import { gated, gateOf, notPrimaryLabel, verdictCell, verdictPlain } from "./common";

export interface SonucVM {
  results: ResultsState | null;
  summary: CeilingSummary | null;
  disp0: CeilingDisplay | null;
  dispJ: CeilingDisplay | null;
  j: number;
  gate: HeadlineGate | null;
  perf: PerfView | null;
  hints: ScoreHints | null;
  integrityOk: boolean;
  repoMode: boolean;
  savedId: string | null;
  errorHtml: string;
}

const S = SADE.sonuc;
const RETURN_MODEL = "v1_5_h99";
const HORIZONS = ["D1", "D3", "D5", "D10"] as const;

export function stageLabel(stage: string | null | undefined): string {
  if (stage === "PRE_BOOKBUILD") return SADE.giris.stagePre;
  if (stage === "POST_BOOKBUILD_PRE_LISTING") return SADE.giris.stagePost;
  return STAGES.find((s) => s.id === stage)?.label ?? SADE.dash;
}

function featuredRow(s: CeilingSummary | null): SummaryRow | null {
  return s?.rows.find((r) => r.role === "FEATURED") ?? null;
}

function returnRun(r: ResultsState): ModelRun | null {
  return r.runs.find((x) => x.model_id === RETURN_MODEL) ?? null;
}

function headline(vm: SonucVM, r: ResultsState): string {
  const f = featuredRow(vm.summary);
  const ce = gateOf(vm.gate, f?.model_id ?? "ceiling_hazard_v0", "S", null);
  let text = "";
  if (f && f.status === "PREDICTED" && ce?.featured) {
    const e = fixed1(f.expected_l);
    text = f.mode_break_day !== null && f.mode_l !== null ? S.headCeiling(e, f.mode_l, f.mode_break_day) : S.headCeilingNone(e);
  }
  const d5 = returnRun(r)?.output?.D5 ?? null;
  if (d5 && returnRun(r)?.status === "PREDICTED" && gateOf(vm.gate, RETURN_MODEL, "return", "D5")?.featured) {
    text += S.headReturn(pctSigned1(d5.return));
  }
  return text === "" ? "" : `<p class="s-headline sonuc-headline">${esc(text)}</p>`;
}

function kacPanel(vm: SonucVM): string {
  const f = featuredRow(vm.summary);
  const id = f?.model_id ?? "ceiling_hazard_v0";
  const head = `<div class="s-panel-head"><div><h2>${esc(S.kacTitle)}</h2><div class="s-panel-sub">${esc(S.kacSub)}</div></div>` +
    `<span class="s-id gold">${esc(id)}</span></div>`;
  if (!f || f.status !== "PREDICTED") {
    const code = f?.refused?.code ?? SADE.dash;
    return `<section class="s-panel grow-1 kac">${head}<div class="s-panel-body"><p class="s-text2">${esc(S.refused(id, code))}</p></div></section>`;
  }
  const g = gateOf(vm.gate, id, "S", null);
  const row = vm.disp0?.rows.find((x) => x.model_id === id) ?? null;
  const bars = row
    ? distBars(row.P_L, { w: 560, h: 150, highlight: row.mode_l, ring: null, titles: row.P_L.map((p, l) => `P(L = ${l}) ${pct0(p)}`) })
    : "";
  const rule = vm.summary?.rows.find((x) => x.model_id === "base_km_last10") ?? null;
  const line = (label: string, x: SummaryRow | null, cls: string) =>
    x
      ? `<tr class="${cls}" data-row="${esc(x.model_id)}"><td>${esc(label)}</td><td class="num">${esc(fixed1(x.expected_l))}</td><td class="num">${esc(x.median_l ?? SADE.dash)}</td>` +
        `<td class="num">${esc(pct0(x.p_ge3))}</td><td class="num">${esc(pct0(x.p_ge5))}</td><td class="num">${esc(pct0(x.p_10))}</td></tr>`
      : "";
  const cell = vm.perf?.rows.find((x) => x.model_id === id && x.rule_id === "base_km_last10") ?? null;
  const bt = cell
    ? `<div class="backtest-line"><p class="s-note">${esc(S.backtestLine(metric4(cell.model_value), metric4(cell.rule_value), String(cell.n ?? SADE.dash)))}` +
      `${verdictCell(cell.verdict)}</p>${verdictPlain(cell.verdict)}</div>`
    : "";
  return `<section class="s-panel grow-1 kac">${head}<div class="s-panel-body">` +
    `<div><span class="s-big">${gated(g, esc(fixed1(f.expected_l)))}</span> <span class="s-text2">${esc(S.expectedDays(String(f.median_l ?? SADE.dash)))}</span></div>` +
    bars + `<p class="s-note">${esc(S.barsNote)}</p>` +
    `<table class="s-table"><thead><tr><th></th><th class="num">${esc(S.colExpected)}</th><th class="num">${esc(S.colMedian)}</th>` +
    `<th class="num">${esc(S.colGe3)}</th><th class="num">${esc(S.colGe5)}</th><th class="num">${esc(S.col10)}</th></tr></thead>` +
    `<tbody>${line(S.rowModel, f, "gold")}${line(S.rowRule, rule, "rule-text")}</tbody></table>${bt}</div></section>`;
}

function returnPanel(vm: SonucVM, r: ResultsState): string {
  const run = returnRun(r);
  const head = `<div class="s-panel-head"><div><h2>${esc(S.returnTitle)}</h2><div class="s-panel-sub">${esc(S.returnSub)}</div></div>` +
    `<span class="s-id gold">${esc(RETURN_MODEL)}</span></div>`;
  if (!run || run.status !== "PREDICTED" || !run.output) {
    const code = run?.refusal?.code ?? SADE.dash;
    return `<section class="s-panel grow-1 returns">${head}<div class="s-panel-body"><p class="s-text2">${esc(S.refused(RETURN_MODEL, code))}</p></div></section>`;
  }
  const out = run.output;
  const rets = HORIZONS.map((h) => out[h]?.return ?? null);
  const max = Math.max(...rets.map((x) => (typeof x === "number" ? Math.abs(x) : 0)), 0);
  const rows = HORIZONS.map((h, i) => {
    const c = out[h];
    const gr = gateOf(vm.gate, RETURN_MODEL, "return", h);
    const gp = gateOf(vm.gate, RETURN_MODEL, "p_up", h);
    const mark = gr?.featured ? `<span class="s-note">${esc(S.featuredMark)}</span> ${verdictCell(gr.verdicts[0] ?? null)}` : notPrimaryLabel();
    const ret = typeof rets[i] === "number" ? (rets[i] as number) : null;
    return `<tr data-h="${h}" class="${gr?.featured ? "sel" : ""}"><td><strong>${h}</strong></td>` +
      `<td class="bar-cell"><div class="s-hbar-track"><div class="s-hbar-fill ${gr?.featured ? "gold" : ""}" style="width:${fillPct(ret === null ? null : Math.abs(ret), max)}"></div></div></td>` +
      `<td class="num">${gated(gr, esc(pctSigned1(c?.return)))}</td><td class="num">${esc(price2(c?.price))}</td>` +
      `<td class="num">${gated(gp, esc(pct0(c?.p_up)))}</td><td>${mark}</td></tr>`;
  }).join("");
  const mae = vm.hints?.models[RETURN_MODEL]?.mae["D5"] ?? null;
  const maeLine = mae && mae.model_value !== null ? `<p class="s-note">${esc(S.maeLine(points1(mae.model_value), String(mae.n ?? SADE.dash)))}</p>` : "";
  return `<section class="s-panel grow-1 returns">${head}<div class="s-panel-body"><table class="s-table"><thead><tr><th>${esc(S.colDay)}</th>` +
    `<th>${esc(S.colForecast)}</th><th></th><th class="num">${esc(S.colPrice)}</th><th class="num">${esc(S.colPUp)}</th><th>${esc(S.colBacktest)}</th></tr></thead>` +
    `<tbody>${rows}</tbody></table>${maeLine}</div></section>`;
}

function basis(vm: SonucVM, r: ResultsState): string {
  const ids = [featuredRow(vm.summary)?.model_id ?? "ceiling_hazard_v0", RETURN_MODEL];
  const warnings = r.runs.filter((x) => ids.includes(x.model_id)).flatMap((x) => x.output?.warnings ?? []);
  const tufe = vm.summary?.tufe ?? null;
  const tufeText = tufe?.month && tufe.index ? `${tufe.month} = ${tufe.index}` : tufe?.refusal ?? SADE.dash;
  const f6 = r.f6.value !== null ? pctSigned1(r.f6.value) : r.f6.refusal ?? F6_ORIGIN_TEXT[r.f6.origin] ?? SADE.dash;
  const src = r.scenario ? r.scenario.title : r.tickerLabel || S.basisSourceForm;
  const kv: [string, string][] = [
    [S.basisWarnings, warnings.length ? S.basisWarningsN(warnings.length) : S.basisNoWarnings],
    [S.basisTufe, tufeText],
    [S.basisXu100, f6],
    [S.basisSource, src],
  ];
  return `<section class="s-plain basis"><h2 class="s-h2">${esc(S.basisTitle)}</h2><div class="s-kv">` +
    kv.map(([k, v]) => `<div>${esc(k)}</div><div>${esc(v)}</div>`).join("") + `</div>` +
    `<p><button class="s-link" data-detailed="results">${esc(SADE.detailedLink)}</button></p></section>`;
}

function savePanel(vm: SonucVM, r: ResultsState): string {
  if (r.source !== "FORM") return "";
  const title = `${r.tickerLabel || S.title("")}, ${stageLabel(r.stage)}`;
  const saved = vm.savedId ? `<p class="s-note mark-pass">${esc(S.saved(vm.savedId))}</p>` : "";
  return `<section class="s-panel save"><div class="s-panel-head"><h2>${esc(S.saveTitle)}</h2></div><div class="s-panel-body">` +
    `<label class="s-note">${esc(S.saveLabel)}</label><div class="s-actions"><input type="text" data-role="save-title" value="${esc(title)}" style="flex:1 1 200px"/>` +
    `<button class="primary" data-action="save">${esc(S.save)}</button></div>${saved}` +
    `<p class="s-note">${esc(S.saveNote)} <button class="s-link" data-go="kayitlarim">${esc(S.myRecords)}</button></p></div></section>`;
}

export function renderSonuc(vm: SonucVM): string {
  const r = vm.results;
  if (!r) {
    return `<div class="s-main"><section class="s-panel s-empty"><h2>${esc(S.crumbHere)}</h2><p>${esc(S.empty)}</p>` +
      `<button class="primary" data-go="giris">${esc(SADE.newIpo)}</button></section></div>`;
  }
  if (!vm.integrityOk) return `<div class="s-main"><div class="s-legacy"><div class="band-error">${esc(RESULTS.integrityBand)}</div></div></div>`;
  const src = r.source === "SCENARIO" && r.scenario ? S.srcScenario(r.scenario.title) : S.srcForm;
  const official = vm.repoMode
    ? `<button data-action="official">${esc(SADE.giris.official)}</button>`
    : `<button disabled title="${esc(SADE.giris.officialClosed)}">${esc(SADE.giris.official)}</button>`;
  const calcRow = vm.dispJ?.rows.find((x) => x.model_id === (featuredRow(vm.summary)?.model_id ?? "ceiling_hazard_v0")) ?? null;
  const calc = renderCalc({
    mode: "SCENARIO",
    j: vm.j,
    row: calcRow,
    modelId: featuredRow(vm.summary)?.model_id ?? "ceiling_hazard_v0",
    gate: gateOf(vm.gate, featuredRow(vm.summary)?.model_id ?? "ceiling_hazard_v0", "S", null),
    streak: null,
    calc: vm.dispJ?.calc ?? null,
    postD1Html: `<p class="s-note">${esc(SADE.calc.postD1Scenario)}</p>`,
  });
  return `<div class="s-main sonuc"><div class="s-head-row"><div><div class="s-crumb"><button class="s-link" data-go="giris">${esc(S.crumb)}</button> / ${esc(S.crumbHere)}</div>` +
    `<h1 class="s-h1">${esc(S.title(r.tickerLabel))}</h1><p class="s-lead">${esc(S.sub(stageLabel(r.stage), src))}</p></div>` +
    `<div class="s-actions"><button data-action="edit-inputs">${esc(S.editInputs)}</button>${official}</div></div>` +
    headline(vm, r) +
    `<div class="s-row">${kacPanel(vm)}<div class="calc-wrap">${calc}</div></div>` +
    `<div class="s-row">${returnPanel(vm, r)}<div class="s-col side" style="flex:1 1 380px">` +
    `<section class="s-panel regime-panel"><div class="s-panel-head"><h2>${esc(S.regimeTitle)}</h2></div><div class="s-panel-body"><p class="s-text2" style="margin:0">${esc(RESULTS.regime)}</p></div></section>` +
    basis(vm, r) + savePanel(vm, r) + `</div></div>${vm.errorHtml}</div>`;
}

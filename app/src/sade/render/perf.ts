// Model performansı (pano `Dogruluk`): yalnız skor dosyalarından (`perf_view`; K-UI-3). Hüküm hücresi dosyadaki
// `verdict` (U19); sade açıklama ayrı satır (K-UI-5); okuma rehberi (nokta, çizgi, sıfır) aynen. Üç terazi ayrı tutulur,
// hiçbir yerde toplanmaz (kural 3). Oran ("%25 daha düşük") yok: iki değer yan yana (K-UI-7). Sayım cümlesi dosyadaki
// verdict'e göre ayrı parçalardan (K-FIX-5): "ayırt edilemiyor" ile "geçemiyor" ayrı sayılır, sıfır olan parça yazılmaz.
import { esc } from "../../dom";
import { SADE } from "../../i18n/tr";
import { ciText, value } from "../../render/accuracy";
import { dateTr, pctSigned1, fixed1, toNum } from "../../render/format";
import { fillPct, intervalBar, progressPct } from "../../render/svg";
import type { SnapshotInfo } from "../../types";
import type { HeadlineGate, LiveCell, PerfRow, PerfView, ScaleSummary } from "../types";
import { classText, gateOf, ootVerdictCell, promotionCell, renderSnapshotSource, verdictCell, verdictClass, verdictPlain } from "./common";

export interface PerfVM {
  perf: PerfView;
  gate: HeadlineGate | null;
  repoMode: boolean;
  /** Kişisel modda gömülü sicil anlık görüntüsü (FAZ9_SNAPSHOT): D1 sonrası ve kırılma bölümleri ondan; not yerine kaynak. */
  snapshot?: SnapshotInfo | null;
}

const P = SADE.perf;

function scaleRange(rows: PerfRow[]): { min: number; max: number } {
  const lo: number[] = [0];
  const hi: number[] = [0];
  for (const r of rows) {
    const d = toNum(r.diff);
    if (d !== null) {
      lo.push(d);
      hi.push(d);
    }
    if (r.ci95) {
      lo.push(r.ci95[0]);
      hi.push(r.ci95[1]);
    }
  }
  return { min: Math.min(...lo), max: Math.max(...hi, 0.02) };
}

function ruleName(id: string | null): string {
  return id ? SADE.rule[id] ?? id : SADE.dash;
}

function scoreBars(r: PerfRow): string {
  const m = toNum(r.model_value);
  const k = toNum(r.rule_value);
  if (m === null || k === null) return `<span class="muted">${esc(SADE.dash)}</span>`;
  const max = Math.max(m, k);
  const c = { metric: r.metric ?? "" };
  return `<div class="score-bars"><div class="sb"><span class="gold">${esc(P.model)}</span><div class="s-hbar-track"><div class="s-hbar-fill gold" style="width:${fillPct(m, max)}"></div></div>` +
    `<span class="num gold">${esc(value(c, m))}</span></div><div class="sb"><span class="rule-text">${esc(P.rule)}</span>` +
    `<div class="s-hbar-track"><div class="s-hbar-fill rule" style="width:${fillPct(k, max)}"></div></div><span class="num rule-text">${esc(value(c, k))}</span></div></div>`;
}

function rowHtml(r: PerfRow, range: { min: number; max: number }, g: HeadlineGate | null): string {
  const c = { metric: r.metric ?? "", ci95: r.ci95 };
  const vcls = r.verdict ? verdictClass(r.verdict).replace("mark-", "iv-") : r.featured ? "iv-pass" : "iv-undecided";
  const label = r.label ? `<span class="s-chip">${esc(r.label)}</span>` : "";
  const verdict = r.verdict
    ? `${verdictCell(r.verdict)}${verdictPlain(r.verdict)}`
    : `<span class="muted">${esc(P.noVerdict)}</span><div class="s-note">${promotionCell(gateOf(g, r.model_id, r.output ?? "", r.horizon_or_k))}</div>`;
  const n = r.n ?? null;
  return `<tr class="perf-row" data-model="${esc(r.model_id)}" data-rule="${esc(r.rule_id ?? "")}" data-scale="${esc(r.scale ?? "")}">` +
    `<td><div><strong>${esc(P.vsRule(SADE.perfQuestion[r.question] ?? r.question, ruleName(r.rule_id), r.metric ?? ""))}</strong> ${label}</div>` +
    `<div class="s-id">${esc(r.model_id)} · ${esc(r.rule_id ?? "")}</div></td>` +
    `<td>${scoreBars(r)}</td>` +
    `<td>${intervalBar(toNum(r.diff), r.ci95, { w: 220, h: 26, min: range.min, max: range.max, cls: vcls })}</td>` +
    `<td class="num"><div class="cond" style="font-size:16px;font-weight:600">${esc(value(c, r.diff))}</div><div class="s-note">${esc(ciText(c))}</div></td>` +
    `<td class="num">${esc(n === null ? SADE.dash : r.wins === null ? P.nOnly(String(n), String(r.n_months ?? SADE.dash)) : P.wins(String(r.wins), String(n)))}` +
    (r.wins !== null ? `<div class="s-note">${esc(P.wlt(String(r.wins), String(r.losses ?? SADE.dash), String(r.ties ?? SADE.dash)))}</div>` : "") +
    `</td><td>${verdict}</td></tr>`;
}

function guide(): string {
  return `<div class="s-guide"><div class="guide-axis"><span class="mark-pass">${esc(P.guideLeft)}</span><span>${esc(P.guide0)}</span>` +
    `<span class="muted">${esc(P.guideRight)}</span></div><p class="s-note"><strong>${esc(P.guideDot)}</strong></p>` +
    `<p class="s-note">${esc(P.guideLine)}</p><p class="s-note">${esc(P.guideZero)}</p></div>`;
}

function diffPanel(v: PerfView, g: HeadlineGate | null): string {
  const range = scaleRange(v.rows);
  return `<section class="s-panel perf-diff"><div class="s-panel-head"><div><h2>${esc(P.diffTitle)}</h2><div class="s-panel-sub">${esc(P.diffSub)}</div></div>` +
    `<div class="s-note">${esc(P.stripRowsSub(v.counts))}</div></div>` +
    `<div class="s-panel-body">${guide()}<div class="s-scroll"><table class="s-table"><thead><tr><th>${esc(P.colQuestion)}</th><th>${esc(P.colScore)}</th>` +
    `<th>${esc(P.guide0)}</th><th class="num">${esc(P.colInterval)}</th><th class="num">${esc(P.colWins)}</th><th>${esc(P.colVerdict)}</th></tr></thead>` +
    `<tbody>${v.rows.map((r) => rowHtml(r, range, g)).join("")}</tbody></table></div><p class="s-note">${esc(P.legend)}</p></div></section>`;
}

function scaleRow(s: ScaleSummary, g: HeadlineGate | null): string {
  const unique = [...new Set(s.backtest_verdicts)];
  const bt = s.model_id === "break_floor_v0"
    ? promotionCell(gateOf(g, "break_floor_v0", "p_floor", "F1"))
    : unique.length ? unique.map((v) => verdictCell(v)).join(" ") : `<span class="muted">${esc(SADE.dash)}</span>`;
  const old = s.oot.status === "OK"
    ? `${ootVerdictCell(s.oot.verdict)} <span class="s-note">${esc(P.oldN(String(s.oot.n ?? SADE.dash)))}</span>`
    : `<span class="muted">${esc(SADE.monitor.noTest)}</span>`;
  const live = `${esc(P.liveLine(String(s.live.n_live ?? 0), String(s.live.n_late ?? 0)))}` +
    (s.live.n_retro ? `<div class="s-note">${esc(P.liveRetro(String(s.live.n_retro)))}</div>` : "");
  return `<tr data-model="${esc(s.model_id)}"><td><div>${esc(SADE.question[s.question] ?? s.model_id)}</div><div class="s-id">${esc(s.model_id)}</div></td>` +
    `<td>${bt}</td><td>${old}</td><td>${live}</td></tr>`;
}

function scales(v: PerfView, g: HeadlineGate | null): string {
  return `<section class="s-panel grow-2 perf-scales"><div class="s-panel-head"><div><h2>${esc(P.scalesTitle)}</h2><div class="s-panel-sub">${esc(P.scalesSub)}</div></div>` +
    `<span class="gold s-note">${esc(P.scalesMain)}</span></div><div class="s-panel-body"><table class="s-table"><thead><tr><th>${esc(P.colModel)}</th>` +
    `<th>${esc(P.colBacktest)}</th><th>${esc(P.colOld)}</th><th>${esc(P.colLive)}</th></tr></thead><tbody>${v.scales.map((x) => scaleRow(x, g)).join("")}</tbody></table></div></section>`;
}

function liveProgress(v: PerfView): string {
  const of = v.min_n_verdict;
  const stage = (key: string, model: string) => {
    const s = v.scales.find((x) => x.model_id === model);
    const n = s?.live.n_live ?? 0;
    return `<div class="s-hbar live-stage" data-model="${esc(model)}"><span><div>${esc(P.liveStage[key])}</div><div class="s-note">${esc(P.liveStage[`${key}_SUB`])}</div></span>` +
      `<div class="track"><div class="fill gold" style="width:${progressPct(n, of)}"></div></div><span class="num">${n} / ${of}</span></div>`;
  };
  return `<section class="s-plain grow-1 live-progress"><h2 class="s-h2">${esc(P.liveTitle)}</h2><p class="s-note">${esc(P.liveSub(String(of)))}</p>` +
    stage("PRE", "ceiling_hazard_v0") + stage("PRE_RET", "v1_5_h99") + stage("POST_D1", "post_d1_hazard_v0") + stage("BREAK", "break_floor_v0") + `</section>`;
}

function liveCell(c: LiveCell | null, kind: "L" | "R"): string {
  if (!c) return `<td>${esc(SADE.dash)}</td><td></td><td></td>`;
  const cls = c.status === "REFUSED" ? SADE.classText.REFUSED : classText(c.class);
  const live = c.class === "LIVE" && c.status !== "REFUSED" ? "chip-live" : "";
  const pred = c.status === "REFUSED" ? SADE.dash : kind === "L" ? fixed1(c.predicted) : pctSigned1(c.predicted);
  const real = kind === "L" ? String(c.realized ?? SADE.dash) : pctSigned1(typeof c.realized === "string" || typeof c.realized === "number" ? c.realized : null);
  const realCls = kind === "R" && toNum(c.realized as string | number | null) !== null ? ((toNum(c.realized as string | number | null) ?? 0) < 0 ? "down" : "up") : "";
  return `<td class="${live}">${esc(cls)}</td><td class="num gold">${esc(pred)}</td><td class="num ${realCls}">${esc(real)}</td>`;
}

function liveRows(v: PerfView): string {
  if (!v.live_rows.length) return "";
  const rows = v.live_rows
    .map((r) => `<tr data-ticker="${esc(r.ticker)}"><td class="t-ticker">${esc(r.ticker)}</td><td class="num">${esc(dateTr(r.d1))}</td>` +
      liveCell(r.ceiling, "L") + liveCell(r.d5, "R") +
      `<td>${esc(classText(r.post_d1_status))}</td><td>${esc(classText(r.break_class))}</td></tr>`)
    .join("");
  return `<section class="s-panel live-rows"><div class="s-panel-head"><div><h2>${esc(P.rowsTitle)}</h2><div class="s-panel-sub">${esc(P.rowsSub)}</div></div></div>` +
    `<div class="s-panel-body"><div class="s-scroll"><table class="s-table"><thead><tr><th rowspan="2">${esc(P.colIpo)}</th><th rowspan="2" class="num">${esc(P.colD1)}</th>` +
    `<th colspan="3" class="group">${esc(P.groupCeiling)}</th><th colspan="3" class="group">${esc(P.groupD5)}</th><th rowspan="2">${esc(P.groupPostD1)}</th><th rowspan="2">${esc(P.groupBreak)}</th></tr>` +
    `<tr><th>${esc(P.colClass)}</th><th class="num">${esc(P.colPredicted)}</th><th class="num">${esc(P.colRealized)}</th>` +
    `<th>${esc(P.colClass)}</th><th class="num">${esc(P.colForecast)}</th><th class="num">${esc(P.colRealized)}</th></tr></thead>` +
    `<tbody>${rows}</tbody></table></div><p class="s-note">${esc(P.rowsNote)}</p></div></section>`;
}

export function renderPerf(vm: PerfVM): string {
  const v = vm.perf;
  const head = `<div><h1 class="s-h1">${esc(P.title)}</h1><p class="s-lead">${esc(P.intro)}</p></div>`;
  if (v.scores_integrity) {
    return `<div class="s-main perf">${head}<div class="s-legacy"><div class="band-error">${esc(P.integrity(v.scores_integrity.rule))}</div></div></div>`;
  }
  const item = (label: string, value: string, sub: string) =>
    `<div class="s-strip-item"><div class="s-strip-label">${esc(label)}</div><div class="s-strip-value">${value}</div><div class="s-strip-sub">${esc(sub)}</div></div>`;
  const strip = `<div class="s-strip">` +
    item(P.stripProd, `<span class="gold">${v.n_production}</span>`, P.stripProdSub) +
    item(P.stripRows, `${v.counts.n_rows}`, P.stripRowsSub(v.counts)) +
    item(P.stripMinN, `${v.min_n_verdict}`, P.stripMinNSub(String(v.min_n_metric), String(v.min_n_verdict))) +
    `</div>`;
  const body = v.rows.length ? diffPanel(v, vm.gate) : `<p class="s-text2">${esc(P.noScores)}</p>`;
  const repoNote = vm.repoMode ? "" : vm.snapshot ? renderSnapshotSource(vm.snapshot) : `<p class="s-note repo-only">${esc(P.repoOnlyPart)}</p>`;
  return `<div class="s-main perf">${head}${strip}${repoNote}${body}<div class="s-row">${scales(v, vm.gate)}${liveProgress(v)}</div>${liveRows(v)}` +
    `<p><button class="s-link" data-detailed="accuracy">${esc(P.detailedLink)}</button></p></div>`;
}

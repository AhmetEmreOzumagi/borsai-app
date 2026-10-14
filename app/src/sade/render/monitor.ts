// Monitör (pano `Main`): bütün sayılar `monitor_view`, `headline_gate` ve `perf_view`'dan (K-UI-3). Ön uç yalnız biçimler;
// sayımlar Rust'tan; ortalama, oran ve "en güçlü seyir" yok (K-UI-7, README §3).
import { esc } from "../../dom";
import { SADE } from "../../i18n/tr";
import { dateTr, fixed1, pct0, pctSigned1, price2, toNum } from "../../render/format";
import { sparkline } from "../../render/svg";
import type { EventItem, HeadlineGate, MonitorRow, MonitorView, PerfView, ScaleSummary } from "../types";
import { classText, gated, gateOf, ootVerdictCell, promotionCell, renderRegimeStripe, renderSnapshotSource, verdictCell } from "./common";

export interface MonitorVM {
  view: MonitorView;
  gate: HeadlineGate | null;
  perf: PerfView | null;
  selected: string | null;
  filter: "ALL" | "STREAK";
}

const T = SADE.monitor;

function closes(r: MonitorRow): (number | null)[] {
  return r.days.map((d) => toNum(d.close_raw));
}

function trend(r: MonitorRow): string {
  if (r.r10_below === true) return "down";
  if (r.r10_below === false) return "up";
  return "";
}

function strip(v: MonitorView, perf: PerfView | null): string {
  const c = v.counts;
  const below = v.rows.filter((r) => r.r10_below === true).map((r) => r.ticker).join(", ");
  const item = (label: string, value: string, sub: string, cls = "") =>
    `<div class="s-strip-item ${cls}"><div class="s-strip-label">${esc(label)}</div><div class="s-strip-value">${value}</div>` +
    `<div class="s-strip-sub">${esc(sub)}</div></div>`;
  const frac = (a: number, b: number) => `${a} <small>/ ${b}</small>`;
  return `<div class="s-strip" data-role="strip">` +
    item(T.stripIpos, `${c.n_ipos}`, T.stripIposSub(dateTr(c.first_d1), dateTr(c.last_d1)), "strip-ipos") +
    item(T.stripStreak, `${c.n_in_streak}`, T.stripStreakSub, "strip-streak") +
    item(T.stripBelow, `<span class="${c.n_d10_below ? "down" : ""}">${frac(c.n_d10_below, c.n_d10_known)}</span>`, T.stripBelowSub(below), "strip-below") +
    item(T.stripFloor, frac(c.n_break_floor, c.n_break_known), T.stripFloorSub, "strip-floor") +
    item(T.stripModels, `<span class="gold">${perf?.n_production ?? SADE.dash}</span>`, T.stripModelsSub, "strip-models") +
    `</div>`;
}

function ceilingCells(r: MonitorRow, g: HeadlineGate | null): string {
  const c = r.ceiling;
  if (!c) return `<td class="num muted" colspan="2">${esc(SADE.classNone)}</td>`;
  if (c.status !== "PREDICTED") return `<td class="num muted" colspan="2">${esc(SADE.refusedShort(c.refusal_code ?? SADE.dash))}</td>`;
  const e = gateOf(g, "ceiling_hazard_v0", "S", null);
  return `<td class="num" data-col="expected">${gated(e, `${esc(fixed1(c.expected_l))} / ${esc(c.median_l ?? SADE.dash)}`)}</td>` +
    `<td class="num" data-col="ge5">${gated(e, esc(pct0(c.p_ge5)))}</td>`;
}

function breakCells(r: MonitorRow, g: HeadlineGate | null): string {
  const b = r.break_info;
  if (!b || b.b === null) return `<td class="muted">${esc(T.noBreak)}</td><td class="num muted">${esc(SADE.dash)}</td>`;
  const kind = b.b_floor === 1 ? `<span class="down">${esc(T.breakFloor(b.b))}</span>` : esc(T.breakAbove(b.b));
  const e = gateOf(g, "break_floor_v0", "p_floor", "F1");
  const chip = b.impossible_d10 ? `<div><span class="s-chip chip-impossible" title="${esc(T.impossibleTip)}">${esc(T.impossibleBadge)}</span></div>` : "";
  const cls = classText(r.classes.find((c) => c.model_id === "break_floor_v0")?.class);
  return `<td data-col="break">${kind}</td><td class="num" data-col="next-floor">${gated(e, esc(pct0(b.p_floor_f1)))}` +
    `<div class="s-note break-class">${esc(cls)}</div>${chip}</td>`;
}

/** Kayıt sütunu (model başına sınıf; K-UI-4 notu): listeleme öncesi tavan modelinin sınıfı, getiri modelininki farklıysa ek satır. */
function recordCell(r: MonitorRow): string {
  const of = (m: string) => r.classes.find((c) => c.model_id === m) ?? null;
  const text = (c: ReturnType<typeof of>) => (c?.status === "REFUSED" ? SADE.classText.REFUSED : classText(c?.class));
  const ceil = of("ceiling_hazard_v0");
  const ret = of("v1_5_h99");
  const live = (c: ReturnType<typeof of>) => (c?.class === "LIVE" && c.status !== "REFUSED" ? "chip-live" : "");
  const first = `<div class="${live(ceil)}" data-model="ceiling_hazard_v0" data-class="${esc(ceil?.class ?? "")}">${esc(text(ceil))}</div>`;
  const second = ret && text(ret) !== text(ceil)
    ? `<div class="${live(ret)}" data-model="v1_5_h99" data-class="${esc(ret.class ?? "")}">${esc(T.recordReturn(text(ret)))}</div>`
    : "";
  return first + second;
}

function rowHtml(r: MonitorRow, g: HeadlineGate | null, selected: boolean): string {
  const r10cls = r.r10_below === true ? "down" : r.r10_below === false ? "up" : "";
  const streak = r.streak.realized_l ?? r.streak.j_observed;
  return `<tr class="clickable${selected ? " sel" : ""}" data-action="select" data-ticker="${esc(r.ticker)}">` +
    `<td><div class="t-ticker">${esc(r.ticker)}</div><div class="t-company">${esc(r.company ?? "")}</div></td>` +
    `<td class="num">${esc(dateTr(r.first_trading_date))}</td>` +
    `<td class="num">${esc(price2(r.ipo_price))}</td>` +
    `<td class="num">${esc(price2(r.d10_close))}</td>` +
    `<td class="num ${r10cls}" data-col="vs-ipo">${esc(pctSigned1(r.r10))}</td>` +
    `<td>${sparkline(closes(r), { w: 88, h: 30, ref: toNum(r.ipo_price), cls: trend(r) })}</td>` +
    `<td class="num" data-col="streak">${esc(streak ?? SADE.dash)}</td>` +
    ceilingCells(r, g) +
    breakCells(r, g) +
    `<td class="s-class">${recordCell(r)}</td></tr>`;
}

function table(v: MonitorView, vm: MonitorVM): string {
  const rows = vm.filter === "STREAK" ? v.rows.filter((r) => r.streak.in_streak) : v.rows;
  const sel = vm.selected ?? v.rows[0]?.ticker ?? null;
  const body = rows.length
    ? rows.map((r) => rowHtml(r, vm.gate, r.ticker === sel)).join("")
    : `<tr><td colspan="13" class="muted">${esc(T.emptyRows)}</td></tr>`;
  const seg = `<div class="s-seg" role="tablist"><button data-action="filter" data-filter="ALL" class="${vm.filter === "ALL" ? "active" : ""}">${esc(T.filterAll(v.counts.n_ipos))}</button>` +
    `<button data-action="filter" data-filter="STREAK" class="${vm.filter === "STREAK" ? "active" : ""}">${esc(T.filterStreak(v.counts.n_in_streak))}</button></div>`;
  return `<section class="s-panel grow-2 monitor-table"><div class="s-panel-head"><div><h2>${esc(T.tableTitle)}</h2>` +
    `<div class="s-panel-sub">${esc(T.tableSub)}</div></div>${seg}</div>` +
    `<div class="s-scroll"><table class="s-table"><thead><tr>` +
    `<th rowspan="2">${esc(T.colIpo)}</th><th rowspan="2" class="num">${esc(T.colD1)}</th><th rowspan="2" class="num">${esc(T.colPrice)}</th>` +
    `<th rowspan="2" class="num">${esc(T.colD10)}</th><th rowspan="2" class="num">${esc(T.colVsIpo)}</th><th rowspan="2">${esc(T.colSpark)}</th>` +
    `<th rowspan="2" class="num">${esc(T.colStreak)}</th><th colspan="2" class="group">${esc(T.groupPre)}</th>` +
    `<th rowspan="2">${esc(T.colBreak)}</th><th class="group">${esc(T.groupBreak)}</th><th rowspan="2">${esc(T.colRecord)}</th></tr>` +
    `<tr><th class="num">${esc(T.colExpected)}</th><th class="num">${esc(T.colGe5)}</th><th class="num">${esc(T.colNextFloor)}</th></tr></thead>` +
    `<tbody>${body}</tbody></table></div><p class="s-note" style="padding:12px 18px 16px">${esc(T.tableNote)}</p></section>`;
}

function selectedPanel(v: MonitorView, vm: MonitorVM): string {
  const r = v.rows.find((x) => x.ticker === (vm.selected ?? v.rows[0]?.ticker));
  if (!r) return "";
  const last = [...r.days].filter((d) => d.close_raw !== null).pop();
  const r10cls = r.r10_below === true ? "down" : "up";
  const kv: [string, string][] = [];
  const streak = r.streak.realized_l ?? r.streak.j_observed;
  kv.push([T.selStreak, esc(T.selStreakVal(String(r.ceiling?.median_l ?? SADE.dash), String(streak ?? SADE.dash)))]);
  const b = r.break_info;
  if (b && b.b !== null) kv.push([T.selBreak(b.b), gated(gateOf(vm.gate, "break_floor_v0", "p_floor", "F1"), esc(pct0(b.p_floor_f1)))]);
  const d5 = r.returns?.rows.find((x) => x.horizon === "D5");
  if (d5) {
    const pred = gated(gateOf(vm.gate, "v1_5_h99", "return", "D5"), esc(pctSigned1(d5.ret)));
    kv.push([T.selD5, `${pred} / <span class="${d5.realized && toNum(d5.realized) !== null ? "" : "muted"}">${esc(pctSigned1(d5.realized))}</span>`]);
  }
  return `<section class="s-panel selected-ipo" data-ticker="${esc(r.ticker)}"><div class="s-panel-head"><div><div class="s-panel-sub">${esc(T.selected)}</div>` +
    `<h2>${esc(r.ticker)}</h2></div><button data-action="open-analysis" data-ticker="${esc(r.ticker)}">${esc(T.openAnalysis)}</button></div>` +
    `<div class="s-panel-body"><div><span class="s-big">${esc(price2(last?.close_raw ?? null))}</span> ` +
    `<span class="${r10cls}">${esc(pctSigned1(r.r10))} ${esc(T.vsIpo)}</span></div>` +
    sparkline(closes(r), { w: 280, h: 90, ref: toNum(r.ipo_price), cls: trend(r) }) +
    `<div class="s-kv">${kv.map(([k, x]) => `<div>${esc(k)}</div><div class="num">${x}</div>`).join("")}</div></div></section>`;
}

function prodRow(s: ScaleSummary, g: HeadlineGate | null): string {
  const unique = [...new Set(s.backtest_verdicts)];
  const backtest = s.model_id === "break_floor_v0"
    ? promotionCell(gateOf(g, "break_floor_v0", "p_floor", "F1"))
    : unique.length
      ? unique.map((v) => verdictCell(v)).join(" ")
      : `<span class="muted">${esc(SADE.dash)}</span>`;
  const old = s.oot.status === "OK" ? ootVerdictCell(s.oot.verdict, true) : `<span class="muted">${esc(T.noTest)}</span>`;
  return `<tr data-model="${esc(s.model_id)}"><td><div>${esc(SADE.question[s.question] ?? s.model_id)}</div><div class="s-id">${esc(s.model_id)}</div></td>` +
    `<td>${backtest}</td><td>${old}</td><td class="num">${esc(s.live.n_live ?? SADE.dash)}</td></tr>`;
}

function production(perf: PerfView | null, g: HeadlineGate | null): string {
  if (!perf) return "";
  return `<section class="s-plain production"><div class="s-head-row"><h2 class="s-h2">${esc(T.prodTitle)}</h2>` +
    `<button class="s-link" data-go="perf">${esc(T.prodPerf)}</button></div>` +
    `<table class="s-table"><thead><tr><th>${esc(T.colModel)}</th><th>${esc(T.colBacktest)}</th><th>${esc(T.colOld)}</th><th class="num">${esc(T.colLive)}</th></tr></thead>` +
    `<tbody>${perf.scales.map((x) => prodRow(x, g)).join("")}</tbody></table><p class="s-note">${esc(T.prodNote)}</p></section>`;
}

/** Olay metni (tr.ts kalıpları; değerler olaydan aynen). */
export function eventText(e: EventItem): string {
  const ev = SADE.event;
  const cls = e.class ? classText(e.class) : "";
  switch (e.kind) {
    case "RECORD":
      return e.tickers.length > 1 ? ev.RECORD(e.tickers.length, cls) : ev.RECORD_ONE(cls);
    case "LEGACY_RECORD":
      return ev.LEGACY_RECORD(e.model_id ?? SADE.dash, cls);
    case "STREAK":
      return ev.STREAK(e.h_from ?? 1, e.h_to ?? 1, e.closes.join(", "));
    case "BREAK":
      return ev.BREAK(e.b ?? 0, e.close_raw ?? SADE.dash, e.b_floor === 1);
    case "D10":
      return ev.D10(e.close_raw ?? SADE.dash, pctSigned1(e.r));
    case "MACHINE":
      return e.tickers.length > 1 ? ev.MACHINE(e.tickers.length, cls) : ev.MACHINE_ONE(cls);
    case "MODEL_FROZEN":
      return ev.MODEL_FROZEN(e.model_id ?? SADE.dash, e.proof_at ? dateTr(e.proof_at) : "");
    case "REGIME":
      return ev.REGIME;
    default:
      return e.kind;
  }
}

export function eventSource(e: EventItem): string {
  const single = e.tickers.length === 1 && ["STREAK", "BREAK", "D10", "LEGACY_RECORD"].includes(e.kind);
  return single ? (e.ticker ?? "") : (SADE.eventSource[e.kind] ?? e.kind);
}

export function renderEvents(events: EventItem[], title: string): string {
  if (!events.length) return "";
  const rows = events
    .map((e) => `<div class="f-at">${esc(dateTr(e.at))}</div><div class="f-src k-${esc(e.kind)}">${esc(eventSource(e))}</div><div class="f-text">${esc(eventText(e))}</div>`)
    .join("");
  return `<section class="s-plain events"><h2 class="s-h2">${esc(title)}</h2><div class="s-feed">${rows}</div></section>`;
}

export function renderMonitor(vm: MonitorVM): string {
  const v = vm.view;
  const below = v.rows.filter((r) => r.r10_below === true).map((r) => r.ticker).join(", ");
  const summary = `<p class="s-headline monitor-summary"><strong>${esc(T.summary(v.counts.n_ipos, v.counts.n_in_streak))}</strong>` +
    (below ? esc(T.belowList(below)) : "") + `</p>`;
  return renderRegimeStripe(v.regime, v.rows.some((r) => r.regime_tags.length > 0)) +
    `<div class="s-main monitor">${renderSnapshotSource(v.snapshot)}${summary}${strip(v, vm.perf)}` +
    `<div class="s-row">${table(v, vm)}<div class="s-col side">${selectedPanel(v, vm)}${production(vm.perf, vm.gate)}</div></div>` +
    renderEvents(v.events, T.eventsTitle) + `</div>`;
}

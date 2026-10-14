// Analiz (pano `Arz`): arz sayfası. Sayılar `arz_view`, `break_view`, `streak_view`, `record_summary`, `record_ceiling`
// (S yalnız dondurulmuş kayıttan; U38) ve `post_d1_view`'dan. Kırılma kartı yalnız makine kaydından ve skor dosyasından;
// senaryo modunda kırılma tahmini yok (EK 5 portu ayrı görev). FAZ9_UI_FIX: yol "Analiz › T" + "Tüm arzlar" + arz
// değiştirici (K-FIX-1); koridorun altında işlem sayısı çubukları (`DayRow.trade_count_*`, K-FIX-4); arz seçilmemişken
// takipteki arzların tablosu (monitör satırlarından, en yeni ilk işlem günü üstte).
import { esc } from "../../dom";
import { COND, SADE } from "../../i18n/tr";
import { countTr, dateTr, fixed1, pct0, pctSigned1, price2, readableCount, short, signed4, toNum } from "../../render/format";
import { corridorChart, distBars, fillPct, returnDots, tradeBar } from "../../render/svg";
import type { CeilingSummary, PostD1View, RecordCeiling, StreakView, SummaryRow } from "../../types";
import type { ArzView, BreakView, HeadlineGate } from "../types";
import { renderCalc } from "./calc";
import { classLines, classText, gated, gateOf, notPrimaryLabel, renderRegimeStripe, verdictCell } from "./common";
import { renderEvents } from "./monitor";

/** Takipteki arz (monitör satırından): liste ve değiştirici için. */
export interface PickRow {
  ticker: string;
  company: string | null;
  first_trading_date: string | null;
}

export interface AnalizVM {
  arz: ArzView;
  brk: BreakView | null;
  streak: StreakView | null;
  summary: CeilingSummary | null;
  ceiling: RecordCeiling | null;
  postD1: PostD1View | null;
  j: number;
  gate: HeadlineGate | null;
  /** Arz değiştirici (K-FIX-1): monitördeki arzlar. */
  tickers: PickRow[];
}

/** En yeni ilk işlem günü üstte, eşitlikte kod sırası (monitör sırasıyla aynı; ISO metin sırası, hesap yok). */
function byNewest(rows: PickRow[]): PickRow[] {
  return [...rows].sort((a, b) => (b.first_trading_date ?? "").localeCompare(a.first_trading_date ?? "") || a.ticker.localeCompare(b.ticker));
}

/** Yol: "Analiz › T", "Tüm arzlar" (listeye döner; kabuk `data-go="analiz"` ile arzı boşaltır) ve arz değiştirici. */
function crumb(vm: AnalizVM): string {
  const t = vm.arz.row.ticker;
  const options = byNewest(vm.tickers)
    .map((r) => `<option value="${esc(r.ticker)}"${r.ticker === t ? " selected" : ""}>${esc(r.ticker)}</option>`)
    .join("");
  const switcher = options
    ? `<label class="arz-switch"><span class="s-note">${esc(A.switchIpo)}</span><select data-role="arz-switch" aria-label="${esc(A.switchIpo)}">${options}</select></label>`
    : "";
  return `<div class="s-crumb arz-crumb"><button class="s-link" data-go="analiz">${esc(A.title)}</button> <span class="crumb-sep">›</span> ` +
    `<strong data-role="crumb-ticker">${esc(t)}</strong><span class="arz-nav"><button data-go="analiz" data-role="all-ipos">${esc(A.allIpos)}</button>${switcher}</span></div>`;
}

const A = SADE.analiz;
const DAYS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

function featuredId(vm: AnalizVM): string {
  return vm.summary?.featured.model_id ?? "ceiling_hazard_v0";
}

function header(vm: AnalizVM): string {
  const r = vm.arz.row;
  const l = r.streak.realized_l ?? r.streak.j_observed;
  const kpi = (label: string, value: string, cls = "") => `<div><div class="s-strip-label">${esc(label)}</div><div class="s-mid ${cls}">${value}</div></div>`;
  const r10cls = r.r10_below === true ? "down" : r.r10_below === false ? "up" : "";
  const regime = r.regime_tags.length ? `<span class="s-badge-regime">${esc(SADE.regimeBadge)}</span>` : "";
  return `<div class="s-head-row arz-head"><div><h1 class="s-h1">${esc(r.ticker)}</h1><div class="s-text2">${esc(r.company ?? "")}</div></div>` +
    `<div class="s-actions" style="gap:28px">` +
    kpi(A.ipoPrice, esc(price2(r.ipo_price))) +
    kpi(A.d10, esc(price2(r.d10_close))) +
    kpi(A.vsIpo, esc(pctSigned1(r.r10)), r10cls) +
    kpi(A.d1, esc(dateTr(r.first_trading_date))) +
    kpi(A.streak, esc(l === null ? SADE.dash : A.streakDays(String(l)))) +
    kpi(A.shares, esc(readableCount(r.shares_offered, SADE.units))) +
    `</div></div><div class="s-head-row"><div class="s-class">${classLines(r.classes, ["ceiling_hazard_v0", "v1_5_h99", "break_floor_v0"])}</div>${regime}</div>`;
}

function timeline(vm: AnalizVM): string {
  const r = vm.arz.row;
  const g = vm.gate;
  const ceilingClass = classText(r.classes.find((c) => c.model_id === "ceiling_hazard_v0")?.class);
  const d5 = r.returns?.rows.find((x) => x.horizon === "D5");
  const d5Text = d5 && gateOf(g, "v1_5_h99", "return", "D5")?.featured ? pctSigned1(d5.ret) : "";
  const step = (cls: string, title: string, sub: string, value: string) =>
    `<div class="tl-step ${cls}"><div class="tl-dot"></div><div class="tl-title">${esc(title)}</div><div class="s-note">${esc(sub)}</div><div class="tl-value">${value}</div></div>`;
  const pre = r.record_file
    ? step("tl-pre", A.tlPre, A.tlPreRec(dateTr(r.recorded_at_istanbul), ceilingClass),
        r.ceiling?.status === "PREDICTED" ? esc(A.tlPreVal(fixed1(r.ceiling.expected_l), d5Text)) : esc(SADE.refusedShort(r.ceiling?.refusal_code ?? SADE.dash)))
    : step("tl-pre", A.tlPre, A.tlPreNone, "");
  const d1 = step("tl-d1", A.tlD1(dateTr(r.days[0]?.session_date ?? null)), "",
    esc(vm.arz.post_d1_files.length ? A.tlD1Rec(vm.arz.post_d1_files.length) : A.tlD1None));
  const b = r.break_info;
  const brk = b && b.b !== null
    ? step("tl-break", A.tlBreak(dateTr(b.break_date)), A.tlBreakSub(b.b, b.b_floor === 1),
        gated(gateOf(g, "break_floor_v0", "p_floor", "F1"), esc(A.tlBreakVal(pct0(b.p_floor_f1)))))
    : step("tl-break", A.tlBreakNone, "", "");
  const l = r.streak.realized_l ?? r.streak.j_observed;
  const d10 = r.d10_close
    ? step("tl-d10", A.tlD10(dateTr(r.d10_date)), A.tlD10Sub, esc(A.tlD10Val(String(l ?? SADE.dash), pctSigned1(r.r10))))
    : step("tl-d10", A.tlD10(SADE.dash), A.tlD10Sub, "");
  return `<div class="s-timeline">${pre}${d1}${brk}${d10}</div>`;
}

function corridor(vm: AnalizVM): string {
  const r = vm.arz.row;
  const ipo = toNum(r.ipo_price);
  const model: [number, number | null][] = (r.returns?.rows ?? []).map((x) => [x.h, x.price]);
  const last = [...r.days].filter((d) => d.close_raw !== null).pop();
  const chart = corridorChart(
    {
      closes: r.days.map((d) => toNum(d.close_raw)),
      uppers: r.days.map((d) => toNum(d.upper_limit_raw)),
      ceilings: r.days.map((d) => d.ceiling_close),
      ipo,
      model,
      breakDay: r.break_info?.b ?? null,
      xLabels: [A.xIpo, ...DAYS.map((d) => `D${d}`)],
      ipoLabel: A.ipoLine(price2(r.ipo_price)),
      breakLabel: r.break_info?.b ? A.breakMark(r.break_info.b) : "",
      lastLabel: price2(last?.close_raw ?? null),
    },
    { w: 760, h: 300 },
  );
  const g = gateOf(vm.gate, "ceiling_hazard_v0", "S", null);
  const pRow = DAYS.map((_d, i) => `<div class="d-cell p-close">${gated(g, esc(pct0(vm.arz.p_close_ceiling[i] ?? null)))}</div>`).join("");
  const realized = r.days
    .map((d) => {
      const cls = d.ceiling_close === 1 ? "ceil" : d.ceiling_close === 0 ? "notceil" : "";
      const text = d.ceiling_close === 1 ? A.ceiling : d.ceiling_close === 0 ? A.notCeiling : A.noOutcome;
      return `<div class="d-cell ${cls}">${esc(text)}</div>`;
    })
    .join("");
  const labels = DAYS.map((d) => `<div class="d-label">D${d}</div>`).join("");
  // işlem sayısı (K-FIX-4): çubuk yüksekliği Rust'ın 0–1 oranından (svg.ts piksele çevirir); sayı binlik ayırıcıyla, yoksa tire
  const trade = r.days
    .map((d) => `<div class="d-cell trade-cell" data-h="${d.h}">${tradeBar(d.trade_count_rel, { w: 36, h: 26, title: countTr(d.trade_count_raw) })}` +
      `<div class="trade-num">${esc(countTr(d.trade_count_raw))}</div></div>`)
    .join("");
  const tradeRow = `<div class="s-note trade-title">${esc(A.tradeTitle)}</div><div class="s-days trade-row">${trade}</div><div class="s-note">${esc(A.tradeSub)}</div>`;
  return `<section class="s-panel grow-2 corridor-panel"><div class="s-panel-head"><div><h2>${esc(A.corridorTitle)}</h2>` +
    `<div class="s-panel-sub">${esc(A.corridorSub)}</div></div><div class="s-legend"><span class="up">■ ${esc(A.legendCeiling)}</span>` +
    `<span class="down">■ ${esc(A.legendNotCeiling)}</span><span class="up">— ${esc(A.legendUpper)}</span><span class="gold">- - ${esc(A.legendModel)}</span></div></div>` +
    `<div class="s-panel-body">${chart}<div class="s-days">${labels}</div><div class="s-note">${esc(A.rowModel)}</div><div class="s-days p-close-row">${pRow}</div>` +
    `<div class="s-note">${esc(A.rowRealized)}</div><div class="s-days realized-row">${realized}</div>${tradeRow}</div></section>`;
}

function kac(vm: AnalizVM): string {
  const id = featuredId(vm);
  const row = vm.ceiling?.display.rows.find((x) => x.model_id === id) ?? null;
  const f = vm.summary?.rows.find((x) => x.role === "FEATURED") ?? null;
  const rule = vm.summary?.rows.find((x) => x.model_id === "base_km_last10") ?? null;
  const g = gateOf(vm.gate, id, "S", null);
  const head = `<div class="s-panel-head"><div><h2>${esc(A.kacTitle)}</h2><div class="s-panel-sub">${esc(A.kacSub)}</div></div><span class="s-id gold">${esc(id)}</span></div>`;
  if (!row || !f || f.status !== "PREDICTED") {
    return `<section class="s-panel side kac">${head}<div class="s-panel-body"><p class="s-text2">${esc(SADE.refusedShort(f?.refused?.code ?? SADE.dash))}</p></div></section>`;
  }
  const ring = vm.streak?.broken ? vm.streak.j_observed : null;
  const line = (label: string, x: SummaryRow | null, cls: string) =>
    x ? `<tr class="${cls}"><td>${esc(label)}</td><td class="num">${esc(fixed1(x.expected_l))}</td><td class="num">${esc(x.median_l ?? SADE.dash)}</td>` +
      `<td class="num">${esc(pct0(x.p_ge3))}</td><td class="num">${esc(pct0(x.p_ge5))}</td><td class="num">${esc(pct0(x.p_10))}</td></tr>` : "";
  return `<section class="s-panel side kac">${head}<div class="s-panel-body">` +
    `<div><span class="s-big">${gated(g, esc(fixed1(row.expected_l)))}</span> <span class="s-text2">${esc(SADE.sonuc.expectedDays(String(row.median_l)))}</span></div>` +
    distBars(row.P_L, { w: 300, h: 120, highlight: row.mode_l, ring, titles: row.P_L.map((p, l) => `P(L = ${l}) ${pct0(p)}`) }) +
    (ring !== null ? `<p class="s-note">${esc(A.realizedMark)}</p>` : "") +
    `<table class="s-table"><thead><tr><th></th><th class="num">${esc(SADE.sonuc.colExpected)}</th><th class="num">${esc(SADE.sonuc.colMedian)}</th>` +
    `<th class="num">${esc(SADE.sonuc.colGe3)}</th><th class="num">${esc(SADE.sonuc.colGe5)}</th><th class="num">${esc(SADE.sonuc.col10)}</th></tr></thead>` +
    `<tbody>${line(SADE.sonuc.rowModel, f, "gold")}${line(SADE.sonuc.rowRule, rule, "rule-text")}</tbody></table></div></section>`;
}

function postD1Html(vm: AnalizVM): string {
  const p = vm.postD1;
  if (!p || p.state === "NO_RECORD") return `<p class="s-note">${esc(SADE.calc.postD1None)}</p>`;
  if (p.state === "J0") return `<p class="s-note">${esc(COND.postD1J0)}</p>`;
  if (p.state === "PREDICTED" && p.row?.cond) {
    return `<p class="s-note post-d1-row">${gated(gateOf(vm.gate, "post_d1_hazard_v0", "S_cond", null), esc(SADE.calc.postD1Row(pct0(p.row.cond.p_break_next))))}</p>`;
  }
  if (p.state === "NOT_APPLICABLE") return `<p class="s-note">${esc(COND.postD1NotApplicable)}</p>`;
  if (p.state === "REFUSED") return `<p class="s-note">${esc(COND.postD1Refused(p.refusal?.code ?? SADE.dash))}</p>`;
  return `<p class="s-note">${esc(COND.postD1NoCell)}</p>`;
}

function hbar(label: string, value: number | null, cls: string, text: string): string {
  return `<div class="s-hbar"><span>${esc(label)}</span><div class="track"><div class="fill ${cls}" style="width:${fillPct(value)}"></div></div>` +
    `<span class="num">${esc(text)}</span></div>`;
}

function breakCard(vm: AnalizVM): string {
  const b = vm.brk;
  const head = (sub: string) => `<div class="s-panel-head"><div><h2>${esc(A.breakTitle)}</h2><div class="s-panel-sub">${esc(sub)}</div></div>` +
    `<span class="s-id gold">break_floor_v0</span></div>`;
  if (!b || b.status !== "OK") {
    const msg = !b || b.status === "NO_RECORD" ? A.breakNone : b.status === "SHA_MISMATCH" ? A.breakClosed : A.breakNoModel;
    return `<section class="s-panel grow-1 break-card" data-status="${esc(b?.status ?? "NONE")}">${head("")}<div class="s-panel-body"><p class="s-text2">${esc(msg)}</p></div></section>`;
  }
  const g = gateOf(vm.gate, "break_floor_v0", "p_floor", "F1");
  const bb = b.b ?? 0;
  const floor = b.b_floor === 1;
  const feat = (name: string) => b.features.find((f) => f.name === name);
  const ff = feat("b_floor");
  const ft = feat("b_turnover");
  const h1 = b.heads.find((h) => h.head === "F1");
  const featRows =
    (ff ? `<tr><td>${esc(A.featFloor)}</td><td class="num">${esc(A.eq(ff.close_raw ?? SADE.dash, ff.lower_limit_raw ?? SADE.dash, floor))}</td>` +
      `<td class="num">${esc(ff.value_f1 ?? SADE.dash)}</td><td class="num">${esc(signed4(ff.z_f1))}</td><td class="num">${esc(signed4(ff.coef_f1))}</td></tr>` : "") +
    (ft ? `<tr><td>${esc(A.featTurnover)}</td><td class="num">${esc(A.lnOf(short(ft.ratio_raw)))}</td>` +
      `<td class="num">${esc(signed4(ft.value_f1))}${ft.clipped_f1 ? "*" : ""}</td><td class="num">${esc(signed4(ft.z_f1))}</td><td class="num">${esc(signed4(ft.coef_f1))}</td></tr>` : "") +
    (h1 ? `<tr><td>${esc(A.featConst(String(h1.c ?? SADE.dash)))}</td><td></td><td></td><td></td><td class="num">${esc(signed4(h1.intercept))}</td></tr>` : "");
  const n = String(h1?.training_n ?? SADE.dash);
  const ev = String(h1?.training_events ?? SADE.dash);
  const note = ft?.clipped_f1 ? A.clippedNote(signed4(ft.ln_value), n, ev) : A.trainingNote(n, ev);
  const card = b.card;
  const btN = card?.backtest_info?.F1_product?.n;
  const promo = card?.promotion_label
    ? `<p class="s-note promotion"><span class="${card.promoted ? "mark-pass" : "mark-approx"}">${esc(card.promoted ? A.promoted : SADE.approxMark)}</span> ` +
      `${esc(A.promotion(card.promotion_label, String(btN ?? SADE.dash)))} ${esc(A.breakClass(classText(b.class)))}</p>`
    : "";
  const product = b.product_status === "OK" ? pct0(b.product_f1) : A.breakProductNone;
  return `<section class="s-panel grow-1 break-card" data-status="OK">${head(A.breakSub(bb))}<div class="s-panel-body">` +
    `<div class="s-row" style="gap:28px;align-items:flex-end"><div><div class="s-note">${esc(A.breakF1(bb + 1))}</div><div class="s-big">${gated(g, esc(pct0(b.p_f1)))}</div></div>` +
    `<div><div class="s-note">${esc(A.breakF2(bb + 1, bb + 2))}</div><div class="s-mid">${gated(gateOf(vm.gate, "break_floor_v0", "p_floor", "F2"), esc(pct0(b.p_f2)))}</div></div></div>` +
    hbar(A.breakModel, b.p_f1, "gold", pct0(b.p_f1)) +
    hbar(floor ? A.breakByTypeFloor : A.breakByTypeAbove, b.by_type_f1, "", pct0(b.by_type_f1)) +
    hbar(A.breakZero, b.zero_f1, "", pct0(b.zero_f1)) +
    hbar(A.breakProduct, b.product_status === "OK" ? b.product_f1 : null, "", product) +
    `<table class="s-table"><thead><tr><th>${esc(A.featTitle)}</th><th class="num">${esc(A.featRaw)}</th><th class="num">${esc(A.featInput)}</th>` +
    `<th class="num">${esc(A.featZ)}</th><th class="num">${esc(A.featCoef)}</th></tr></thead><tbody>${featRows}</tbody></table>` +
    `<p class="s-note">${esc(note)}</p>` +
    (b.structural_min10 ? `<p class="s-note">${esc(A.structural(b.structural_min10, b.structural_p ?? SADE.dash))}</p>` : "") +
    (b.impossible_d10 ? `<p class="s-note"><span class="s-chip chip-impossible">${esc(A.impossible)}</span></p>` : "") +
    promo + `</div></section>`;
}

function returns(vm: AnalizVM): string {
  const r = vm.arz.row.returns;
  const head = `<div class="s-panel-head"><div><h2>${esc(A.returnTitle)}</h2><div class="s-panel-sub">${esc(A.returnSub)}</div></div><span class="s-id gold">v1_5_h99</span></div>`;
  if (!r || r.status !== "PREDICTED") {
    return `<section class="s-panel grow-1 returns">${head}<div class="s-panel-body"><p class="s-text2">${esc(SADE.refusedShort(r?.refusal_code ?? SADE.dash))}</p></div></section>`;
  }
  const dots = returnDots(r.rows.map((x) => ({ label: x.horizon, forecast: x.ret, realized: toNum(x.realized) })), { w: 460, h: 220 });
  const rows = r.rows
    .map((x) => {
      const gr = gateOf(vm.gate, "v1_5_h99", "return", x.horizon);
      const gp = gateOf(vm.gate, "v1_5_h99", "p_up", x.horizon);
      const real = toNum(x.realized);
      const cls = real === null ? "muted" : real < 0 ? "down" : "up";
      const mark = gr?.featured ? `<span class="s-note">${esc(SADE.sonuc.featuredMark)}</span> ${verdictCell(gr.verdicts[0] ?? null)}` : notPrimaryLabel();
      return `<tr data-h="${x.horizon}" class="${gr?.featured ? "sel" : ""}"><td><strong>${x.horizon}</strong></td><td class="num">${gated(gr, esc(pctSigned1(x.ret)))}</td>` +
        `<td class="num">${gated(gp, esc(pct0(x.p_up)))}</td><td class="num ${cls}">${esc(pctSigned1(x.realized))}</td><td>${mark}</td></tr>`;
    })
    .join("");
  const cls = classText(vm.arz.row.classes.find((c) => c.model_id === "v1_5_h99")?.class);
  return `<section class="s-panel grow-1 returns">${head}<div class="s-panel-body">${dots}<table class="s-table"><thead><tr><th>${esc(A.colDay)}</th>` +
    `<th class="num">${esc(A.colForecast)}</th><th class="num">${esc(A.colPUp)}</th><th class="num">${esc(A.colRealized)}</th><th>${esc(A.colBacktest)}</th></tr></thead>` +
    `<tbody>${rows}</tbody></table><p class="s-note">${esc(A.returnNote(cls))}</p></div></section>`;
}

export function renderAnaliz(vm: AnalizVM): string {
  const id = featuredId(vm);
  const calc = renderCalc({
    mode: "OFFICIAL",
    j: vm.j,
    row: vm.ceiling?.display.rows.find((x) => x.model_id === id) ?? null,
    modelId: id,
    gate: gateOf(vm.gate, id, "S", null),
    streak: vm.streak,
    calc: vm.ceiling?.display.calc ?? null,
    postD1Html: postD1Html(vm),
  });
  return renderRegimeStripe(vm.arz.regime, vm.arz.row.regime_tags.length > 0) +
    `<div class="s-main analiz" data-ticker="${esc(vm.arz.row.ticker)}">${crumb(vm)}${header(vm)}${timeline(vm)}` +
    `<div class="s-row">${corridor(vm)}${kac(vm)}</div>${calc}` +
    `<div class="s-row">${breakCard(vm)}${returns(vm)}</div>` +
    renderEvents(vm.arz.log, A.logTitle) +
    `<p><button class="s-link" data-go="sicil">${esc(A.goSicil)}</button> · <button class="s-link" data-detailed="registry">${esc(SADE.detailed)}</button></p></div>`;
}

/** Arz seçilmemişken (K-FIX-1): takipteki arzların tablosu (monitör satırlarından; kod, şirket, ilk işlem günü), en yeni üstte. */
export function renderAnalizPick(rows: PickRow[]): string {
  const body = byNewest(rows)
    .map((r) => `<tr class="clickable" data-action="pick" data-ticker="${esc(r.ticker)}"><td><div class="t-ticker">${esc(r.ticker)}</div>` +
      `<div class="t-company">${esc(r.company ?? "")}</div></td><td class="num">${esc(dateTr(r.first_trading_date))}</td>` +
      `<td><button class="s-link" data-action="pick" data-ticker="${esc(r.ticker)}">${esc(A.open)}</button></td></tr>`)
    .join("");
  const empty = `<tr><td colspan="3" class="muted">${esc(SADE.monitor.emptyRows)}</td></tr>`;
  return `<div class="s-main analiz-pick"><div class="s-head-row"><div><h1 class="s-h1">${esc(A.title)}</h1><p class="s-lead">${esc(A.pickNote)}</p></div></div>` +
    `<section class="s-panel pick-table"><div class="s-panel-head"><div><h2>${esc(A.pickList)}</h2><div class="s-panel-sub">${esc(A.pick)}</div></div></div>` +
    `<div class="s-scroll"><table class="s-table"><thead><tr><th>${esc(A.colIpo)}</th><th class="num">${esc(A.colD1)}</th><th></th></tr></thead>` +
    `<tbody>${body || empty}</tbody></table></div></section></div>`;
}

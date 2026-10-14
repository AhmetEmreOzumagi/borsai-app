// Seri hesaplayıcı "Seri j gün sürdüyse yarın ne olur?" (K-UI-8). Değerler Rust'tan: senaryoda `ceiling_display`
// (öne çıkan modelin satırı; `cond` seçilen j'de), resmi görünümde `record_ceiling` (kayıttaki S) + `record_summary`;
// gözlenen j `streak_view`'den. Yarın da tavan = P(L ≥ j+1 | L ≥ j) = cond.S_cond[j] (Rust alanı; ön uçta hesap yok).
// FAZ9_UI_FIX K-FIX-3: "Geçmiş arzlarda" (basit kural `base_km_expanding`, aynı kaydın/koşunun S'i; `display.calc.history`,
// Rust) model okumasının yanında gri; modelin gün grupları notu `display.calc.day_groups`'tan (model dosyası; sabit metin yok).
// Kullanıcı beyanı (U52 şeridi) sade görünümde yoktur; ayrıntılı görünümde aynen vardır.
import { esc } from "../../dom";
import { COND, SADE } from "../../i18n/tr";
import { fixed1, pct0 } from "../../render/format";
import { calcCurve } from "../../render/svg";
import type { CalcView, CeilingRow, StreakView } from "../../types";
import type { GateEntry } from "../types";
import { gated } from "./common";

export interface CalcVM {
  mode: "SCENARIO" | "OFFICIAL";
  j: number;
  /** Öne çıkan modelin satırı: S (koşulsuz) ve seçilen j'deki `cond`. */
  row: CeilingRow | null;
  modelId: string;
  gate: GateEntry | null;
  /** Resmi görünüm: bültendeki seri (streak_view). */
  streak: StreakView | null;
  /** Hesaplayıcı eki (Rust): kuralın koşullu değeri ve gün grupları; eski display çıktısında yok → null. */
  calc: CalcView | null;
  /** D1 sonrası satırı ya da notu (hazır HTML; post_d1_view ya da tasarım notu). */
  postD1Html: string;
}

const C = SADE.calc;
const J_VALUES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];

function observedBox(s: StreakView | null, j: number): string {
  if (!s || s.j_observed === null) return `<div class="s-observed"><span class="muted">${esc(C.observedNone)}</span></div>`;
  const obs = s.j_observed;
  const state = s.broken ? COND.broken(obs + 1, obs) : C.observedOngoing;
  const back = j === obs ? "" : `<button data-action="calc-observed">${esc(C.backToObserved)}</button>`;
  const cells = s.days
    .map((d) => {
      const cls = d.file === "CEILING" ? "ceil" : d.file === "NOT_CEILING" ? "notceil" : "";
      return `<div class="d-cell ${cls}" data-h="${d.h}">${esc(COND.state[d.file ?? "NONE"] ?? SADE.dash)}</div>`;
    })
    .join("");
  return `<div class="s-observed" data-observed="${obs}"><div class="s-head-row"><div><strong>${esc(C.observedTitle(obs))}</strong> ` +
    `<span class="s-text2">${esc(state)}</span></div>${back}</div><div class="s-days">${cells}</div></div>`;
}

function dayStrip(j: number): string {
  const labels = J_VALUES.map((k) => `<div class="d-label">D${k + 1}</div>`).join("");
  const cells = J_VALUES.map((k) => {
    const d = k + 1;
    if (d <= j) return `<div class="d-cell ceil">${esc(C.past)}</div>`;
    if (d === j + 1) return `<div class="d-cell tomorrow">${esc(C.tomorrow)}</div>`;
    return `<div class="d-cell">${esc(SADE.dash)}</div>`;
  }).join("");
  return `<div class="s-days day-labels">${labels}</div><div class="s-days day-strip">${cells}</div>`;
}

/** "Geçmiş arzlarda": kural değeri gri (karşılaştırma rengi), altın yalnız model çıktısında; sayım yalnız Rust verdiyse. */
function history(vm: CalcVM): string {
  const h = vm.calc?.history ?? null;
  if (!h || !h.in_rows) return "";
  const count = h.n_at_j !== null && h.n_next !== null
    ? `<div class="s-note history-count">${esc(C.historyCount(vm.j, String(h.n_at_j), String(h.n_next), vm.j + 1))}</div>`
    : "";
  return `<div class="s-history" data-rule="${esc(h.rule_id)}"><div class="s-reading-label">${esc(C.historyLabel)} ` +
    `<span class="s-note">(${esc(C.historySub)})</span></div><div class="s-reading-value rule-text">${esc(pct0(h.p_next))}</div>${count}</div>`;
}

function readings(vm: CalcVM): string {
  const c = vm.row?.cond ?? null;
  if (!c) return `<p class="s-note calc-undefined">${esc(C.undefinedAll)}</p>`;
  const v = (x: number | null | undefined, f: (n: number | null | undefined) => string) => gated(vm.gate, esc(f(x)));
  const tomorrow = c.S_cond[vm.j] ?? null;
  const lead = vm.j === 0 ? C.day0(pct0(tomorrow)) : C.dayJ(vm.j, vm.j + 1, pct0(tomorrow));
  return `<p class="calc-lead">${esc(lead)}</p><div class="s-readings">` +
    `<div data-reading="tomorrow"><div class="s-reading-label">${esc(C.stillCeiling)}</div><div class="s-reading-value">${v(tomorrow, pct0)}</div>` +
    `<div class="s-reading-sub">${esc(C.breakProb(pct0(c.p_break_next)))}</div>${history(vm)}</div>` +
    `<div data-reading="remaining"><div class="s-reading-label">${esc(C.remaining)}</div><div class="s-reading-value">${v(c.expected_remaining, fixed1)}</div>` +
    `<div class="s-reading-sub">${esc(C.condMedian(String(c.median_l)))}</div></div>` +
    `<div data-reading="ge5"><div class="s-reading-label">${esc(C.ge5)}</div><div class="s-reading-value">${v(c.S_cond[4], pct0)}</div></div>` +
    `<div data-reading="all10"><div class="s-reading-label">${esc(C.all10)}</div><div class="s-reading-value">${v(c.S_cond[9], pct0)}</div></div></div>`;
}

/** Gün grupları notu: yalnız öne çıkan modelin dosyasında `day_groups` varsa (Rust okur); metin gruplardan kurulur. */
function groupsNote(vm: CalcVM): string {
  const g = vm.calc?.day_groups.find((x) => x.model_id === vm.modelId) ?? null;
  const groups = (g?.groups ?? []).filter((d) => d.length > 0);
  if (groups.length < 2) return "";
  const parts = groups.map((d) => (d.length === 1 ? C.groupOne(d[0]) : C.groupRange(d[0], d[d.length - 1]))).join(" · ");
  const before = groups[groups.length - 2];
  const n = C.groupWord[groups.length] ?? String(groups.length);
  return `<p class="s-note calc-groups" data-model="${esc(g?.model_id ?? "")}">${esc(C.groupsNote(n, parts, before[before.length - 1]))}</p>`;
}

export function renderCalc(vm: CalcVM): string {
  const official = vm.mode === "OFFICIAL";
  const obs = vm.streak?.j_observed ?? null;
  const buttons = J_VALUES.map((k) => {
    const cls = [k === vm.j ? "active" : "", official && k === obs ? "observed" : ""].filter((x) => x !== "").join(" ");
    return `<button data-action="calc-j" data-j="${k}" class="${cls}" aria-pressed="${k === vm.j}">${k}</button>`;
  }).join("");
  const kind = official ? (obs !== null && vm.j === obs ? C.official : C.hypothetical) : C.hypothetical;
  const rule = vm.calc?.history.in_rows ? vm.calc.history.s_cond : null;
  const curve = vm.row ? calcCurve(vm.row.S, vm.row.cond?.S_cond ?? null, rule, vm.j, { w: 420, h: 230, tip: C.formula }) : "";
  const legendRule = rule ? `<span class="lg-rule">${esc(C.legendRule)}</span>` : "";
  return `<section class="s-panel s-accent calc" data-mode="${vm.mode}" data-j="${vm.j}"><div class="s-panel-head"><div><h2>${esc(C.title)}</h2>` +
    `<div class="s-panel-sub">${esc(official ? C.subOfficial : C.subScenario)}</div></div><span class="s-id gold">${esc(vm.modelId)}</span></div>` +
    `<div class="s-panel-body"><div class="s-row"><div class="s-col grow-1">` +
    `<div class="s-text2">${esc(C.question)} <span class="s-chip" data-kind="${esc(kind)}">${esc(kind)}</span></div><div class="s-jbtns">${buttons}</div>` +
    `<p class="s-note">${esc(official ? C.helpOfficial : C.help)}</p>` +
    (official ? observedBox(vm.streak, vm.j) : "") +
    dayStrip(vm.j) + readings(vm) + groupsNote(vm) + `<div class="post-d1-line">${vm.postD1Html}</div></div>` +
    `<div class="s-col grow-1">${curve}<div class="s-legend"><span class="lg-cond">${esc(C.legendCond)}</span>` +
    `<span class="lg-uncond">${esc(C.legendUncond)}</span>${legendRule}<span class="lg-past">${esc(C.legendPast)}</span></div>` +
    `<p class="s-note">${esc(C.formula)}</p></div></div></div></section>`;
}

// Koşullu tavan güncellemesi (SPEC_APP §3g, EK 1) saf render: gün gün şerit, j seçici, koşullu eğri
// ve tablo. Gözlenen j, koşullu S/P_L, beklenen/medyan L Rust'tan (`streak_view`, `ceiling_display`).
import { CEILING, COND, PATH, PATH_COND } from "../i18n/tr";
import type {
  AppError,
  CeilingDisplay,
  DeclarationState,
  Num,
  PathConditional,
  PathHorizon,
  PathParamsInfo,
  StreakView,
} from "../types";
import { esc, renderError } from "../dom";
import { colorOf } from "./colors";
import { DASH, fixed1, pct0, pctSigned1, pyRepr, sha8 } from "./format";
import { ALWAYS_CEILING_ID } from "./results";
import { barChart, fanChart, legend, lineChart, type FanSeries, type Series } from "./svg";
import { POST_D1_MODEL_ID, postD1Row, renderPostD1Note, type PostD1VM } from "./post_d1";

/** Koşullu getiri: model başına Rust sonucu ya da hatası (EK 2 §4.3). */
export interface PathCondVM {
  model_id: string;
  result: PathConditional | null;
  error: AppError | null;
}

export interface ConditionalVM {
  streak: StreakView | null;
  /** Seçilen j'deki `ceiling_display` (satırlar: tavan modelleri + her zaman tavan). */
  cond: CeilingDisplay | null;
  jSelected: number;
  tab: "ceiling" | "return";
  hidden: string[];
  /** D1..D10 "seri sürüyor" beyanı (yalnız etiket; hiçbir hesaba girmez, U52). */
  declared: boolean[];
  /** Kişisel kayıttaki eski beyan türleri yüklemede yok sayıldı. */
  declDropped: boolean;
  /** INDEX'te tavan yolu modeli var mı (yoksa "henüz yok" metni kalır). */
  pathAvailable: boolean;
  /** Koşullu getiri sonuçları (model başına); boşsa hesaplanmadı. */
  pathCond: PathCondVM[];
  pathParams: PathParamsInfo[];
  /** Kayıt Faz 4 modellerini içermiyor (resmi görünüm, 16 modelli kayıt). */
  recordWithoutPath: boolean;
  /** D1 sonrası (EK 3 §6.5): resmi görünümde kayıttan satır; senaryoda yalnız not. Yoksa blok çizilmez. */
  postD1?: PostD1VM | null;
}

function stateText(s: string | null): string {
  return COND.state[s ?? "NONE"] ?? s ?? "";
}

/**
 * Beyanın resmi veriye göre durumu (yalnız etiket; sayı üretmez):
 * dosyada tavan → SUPERSEDED (etiket kalkar), tavan değil → CONFLICT, aksi hâlde AHEAD.
 */
export function declarationState(file: string | null, declared: boolean): DeclarationState | null {
  if (!declared) return null;
  if (file === "CEILING") return "SUPERSEDED";
  if (file === "NOT_CEILING") return "CONFLICT";
  return "AHEAD";
}

function declStates(vm: ConditionalVM): (DeclarationState | null)[] {
  const days = vm.streak?.days ?? [];
  return days.map((d, i) => declarationState(d.file, vm.declared[i] === true));
}

export function renderStrip(s: StreakView, declared: boolean[] = [], declDropped = false): string {
  const states = s.days.map((d, i) => declarationState(d.file, declared[i] === true));
  const days = s.days.map((d, i) => {
    const st = d.file ?? "NONE";
    const ahead = states[i] === "AHEAD";
    const cls = [`day`, `day-${st}`, ahead ? "declared" : "", states[i] === "CONFLICT" ? "conflict" : ""].filter(Boolean).join(" ");
    const title = [`D${d.h}`, d.session_date ?? "", stateText(d.file), ahead ? COND.userBadge : "", states[i] === "CONFLICT" ? COND.declarationConflict : ""]
      .filter(Boolean)
      .join(" · ");
    return `<button class="${cls}" data-action="declare" data-h="${d.h}" data-state="${esc(st)}" title="${esc(title)}">` +
      `<span class="d">D${d.h}</span><span class="s">${esc(stateText(d.file))}</span>` +
      (ahead ? `<span class="f decl">${esc(COND.userBadge)}</span>` : "") + `</button>`;
  });
  const src: string[] = [];
  if (s.file_status === "FOUND") src.push(COND.sourceFile(s.file_rel_path ?? "", s.as_of ?? DASH));
  if (s.file_status === "MISSING") src.push(COND.fileMissing(s.file_rel_path ?? ""));
  if (s.file_status === "NO_REPO") src.push(COND.noRepo);
  if (s.file_status === "NO_TICKER") src.push(COND.noTicker);
  s.days.forEach((d, i) => {
    if (states[i] === "AHEAD") src.push(COND.declaredNotCounted(d.h));
  });
  const anyAhead = states.some((x) => x === "AHEAD");
  const badge = anyAhead ? ` <span class="user-badge">${esc(COND.userBadge)}</span>` : "";
  return `<div class="strip-wrap"><h4>${esc(COND.strip)}${badge}</h4><div class="strip">${days.join("")}</div>` +
    `<p class="small muted">${esc(COND.stripHelp)} ${esc(COND.userNote)}</p>` +
    src.map((t) => `<p class="source-line small">${esc(t)}</p>`).join("") +
    (states.some((x) => x === "CONFLICT") ? `<p class="warn-box decl-conflict">${esc(COND.declarationConflict)}</p>` : "") +
    (declDropped ? `<p class="warn-box decl-dropped">${esc(COND.declarationDropped)}</p>` : "") +
    (states.some((x) => x !== null) ? `<button data-action="clear-declarations">${esc(COND.clearUser)}</button>` : "") + `</div>`;
}

function jSelector(vm: ConditionalVM): string {
  const obs = vm.streak?.j_observed ?? null;
  const opts: number[] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];
  if (obs !== null && !opts.includes(obs)) opts.push(obs);
  const options = opts.map((j) => `<option value="${j}"${j === vm.jSelected ? " selected" : ""}>${j}</option>`).join("");
  const obsText = obs === null ? COND.jNone : COND.jObserved(obs);
  const hypo = obs !== null && vm.jSelected !== obs ? ` <span class="hypo">${esc(COND.hypothetical)}</span>` : "";
  return `<div class="j-row"><label>${esc(COND.jLabel)} <select data-action="select-j">${options}</select></label> ` +
    `<span class="small muted">${esc(obsText)}</span>${hypo}</div>`;
}

function condCurve(vm: ConditionalVM): string {
  const d = vm.cond;
  if (!d) return "";
  // D1 sonrası satırı (EK 3 §6.5): S yalnız POST_D1 kaydından, aynı Rust `ceiling_display`; yalnız resmi j ≥ 1
  const post = postD1Row(vm.postD1, d.j);
  const base = d.rows.filter((r) => !vm.hidden.includes(r.model_id));
  const rows = post ? [...base.filter((r) => !r.constant), post, ...base.filter((r) => r.constant)] : base;
  const defined = rows.filter((r) => r.cond !== null);
  const label = (id: string) => (id === ALWAYS_CEILING_ID ? CEILING.always : id === POST_D1_MODEL_ID ? COND.postD1Row : id);
  const head = `<tr><th>${esc(COND.tableK)}</th>${rows.map((r) => `<th class="mono">${esc(label(r.model_id))}</th>`).join("")}</tr>`;
  const cell = (id: string, x: number | null | undefined) =>
    x === null || x === undefined ? `<td class="cell undef" data-model="${esc(id)}">${DASH}</td>` : `<td class="cell" data-model="${esc(id)}" title="${esc(pyRepr(x))}">${esc(pct0(x))}</td>`;
  const body: string[] = [];
  for (let k = d.j + 1; k <= 10; k += 1) {
    body.push(`<tr><th>${esc(COND.kRow(k))}</th>${rows.map((r) => cell(r.model_id, r.cond?.S_cond[k - 1])).join("")}</tr>`);
  }
  const stat = (name: string, f: (c: NonNullable<(typeof rows)[number]["cond"]>) => string) =>
    `<tr class="stat"><th>${esc(name)}</th>${rows.map((r) => (r.cond ? `<td class="cell" data-model="${esc(r.model_id)}">${esc(f(r.cond))}</td>` : `<td class="cell undef">${DASH}</td>`)).join("")}</tr>`;
  body.push(stat(COND.breakNext, (c) => pct0(c.p_break_next)));
  body.push(stat(COND.condExpected, (c) => CEILING.days(fixed1(c.expected_l))));
  body.push(stat(COND.condRemaining, (c) => CEILING.days(fixed1(c.expected_remaining))));
  body.push(stat(COND.condMedian, (c) => CEILING.days(String(c.median_l))));
  const table = `<h4>${esc(COND.curveTitle(d.j))}</h4><div class="scroll"><table class="grid compact cond-table" data-j="${d.j}"><thead>${head}</thead><tbody>${body.join("")}</tbody></table></div>`;
  if (!defined.length) return `<p class="muted undefined-all">${esc(COND.undefinedAll)}</p>${table}`;
  const series: Series[] = defined.map((r) => ({
    id: r.model_id,
    label: label(r.model_id),
    color: colorOf(r.model_id),
    dashed: r.constant,
    points: (r.cond?.S_cond ?? []).map((x, i) => [i + 1, x] as [number, number | null]).filter(([k]) => k > d.j),
  }));
  const chart = lineChart(series, { xMin: d.j + 1 > 10 ? 10 : d.j + 1, xMax: 10, xLabel: CEILING.axisX, yLabel: COND.curveTitle(d.j), cls: "cond-curve" });
  return `<div class="chart-wrap">${chart}${legend(series)}</div>${table}`;
}

// ---------------------------------------------------------------- "Getiri (koşullu)" (EK 2 §4.3)

const H_ALL = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] as const;

function condHorizon(r: PathConditional, h: number): PathHorizon | null {
  return (r.result as unknown as Record<string, PathHorizon | null | undefined>)[`D${h}`] ?? null;
}

function condRaw(c: PathHorizon): string {
  return [`return=${pyRepr(c.return)}`, `p_up=${pyRepr(c.p_up)}`, `q10=${pyRepr(c.q10)}`, `q90=${pyRepr(c.q90)}`,
    `S_h=${pyRepr(c.S_h)}`, `n_atoms=${c.n_atoms}`].join(", ");
}

function closesList(r: PathConditional): string {
  if (!r.closes.length) return "";
  const items = r.closes
    .map((c) =>
      `<li data-h="${c.h}" data-origin="${esc(c.origin)}">` +
      esc(c.origin === "FILE" ? PATH_COND.closeFile(c.h, c.close, c.session_date ?? DASH) : PATH_COND.closeAssumed(c.h, c.close)) +
      `</li>`,
    )
    .join("");
  return `<details class="cond-closes"><summary>${esc(PATH_COND.closesTitle)}</summary><ul class="small mono">${items}</ul></details>`;
}

function condBars(r: PathConditional): string {
  if (r.state !== "STREAK_ONGOING") return "";
  const j = r.j_or_t;
  const pl = r.result.P_L_cond ?? {};
  const keys = Object.keys(pl).sort((a, b) => Number(a) - Number(b));
  const values = keys.map((k) => num(pl[k]));
  if (!values.length) return "";
  return barChart(values, {
    color: colorOf(r.model_id),
    title: PATH_COND.pLCond(j),
    tooltip: PATH_COND.pLCond(j),
    labels: keys.map((k, i) => `P(L = ${k} | L ≥ ${j}) = ${pct0(values[i])}`),
    ticks: keys,
  });
}

function num(x: Num | null | undefined): number | null {
  if (x === null || x === undefined) return null;
  return typeof x === "number" ? x : null;
}

function condFan(r: PathConditional): string {
  const from = r.state === "STREAK_ONGOING" ? r.j_or_t : r.j_or_t + 1;
  const pick = (f: (c: PathHorizon) => Num | null) =>
    H_ALL.map((h) => {
      const c = condHorizon(r, h);
      return h > from && c !== null && c.status !== "REALIZED" ? num(f(c)) : null;
    });
  const series: FanSeries[] = [
    {
      id: r.model_id,
      label: r.model_id,
      color: colorOf(r.model_id),
      q10: pick((c) => c.q10),
      q50: pick((c) => c.q50),
      q90: pick((c) => c.q90),
      rho: H_ALL.map((h) => (h > from ? num(condHorizon(r, h)?.limit_path_return ?? null) : null)),
    },
  ];
  if (series[0].q50.every((x) => x === null)) return "";
  return `<div class="chart-wrap">${fanChart(series, { xMin: 1, xMax: 10, xLabel: PATH.chartX, yLabel: PATH.chartY, cls: "cond-fan" })}</div>`;
}

function condRow(r: PathConditional, h: number): string {
  const c = condHorizon(r, h);
  const model = esc(r.model_id);
  if (!c) return `<tr data-h="${h}"><th>${esc(PATH.hRow(h))}</th><td class="cell undef" data-model="${model}">${DASH}</td></tr>`;
  if (c.status === "REALIZED") {
    return `<tr data-h="${h}" class="realized"><th>${esc(PATH.hRow(h))}</th>` +
      `<td class="cell realized-cell" data-model="${model}" title="${esc(pyRepr(c.realized_return ?? null))}">` +
      `${esc(pctSigned1(c.realized_return ?? null))} <span class="tag">${esc(PATH_COND.realized)}</span>` +
      (r.closes[h - 1]?.session_date ? ` <span class="small muted">${esc(r.closes[h - 1].session_date ?? "")}</span>` : "") +
      `</td></tr>`;
  }
  if (c.status === "POST_BREAK_INSUFFICIENT" || c.return === null) {
    return `<tr data-h="${h}"><th>${esc(PATH.hRow(h))}</th>` +
      `<td class="cell insufficient" data-model="${model}" title="${esc(PATH.insufficient)}">${DASH}</td></tr>`;
  }
  // Durum 2'de S bileşeni düşer (SPEC_CEILING_PATH_V0 §7-2): S_h yoktur, sütun da çizilmez.
  const parts = [
    `<span class="ret">${esc(pctSigned1(c.return))}</span>`,
    `<span class="band muted">[${esc(pctSigned1(c.q10))}, ${esc(pctSigned1(c.q90))}]</span>`,
    `<span class="pup">${esc(pct0(c.p_up))}</span>`,
    ...(c.S_h === null || c.S_h === undefined ? [] : [`<span class="s-h">${esc(pct0(c.S_h))}</span>`]),
    `<span class="atoms muted">${esc(String(c.n_atoms))}</span>`,
  ];
  return `<tr data-h="${h}"><th>${esc(PATH.hRow(h))}</th>` +
    `<td class="cell path-cell" data-model="${model}" title="${esc(condRaw(c))}">${parts.join(" · ")}</td></tr>`;
}

function condCard(vm: ConditionalVM, x: PathCondVM): string {
  const head = `<h4 class="mono">${esc(x.model_id)}</h4>`;
  if (x.error) return `<section class="path-cond error" data-model="${esc(x.model_id)}">${head}${renderError(x.error)}</section>`;
  const r = x.result;
  // Model bu girdiyle tahmin vermediyse (RET) koşullu getiri de yoktur.
  if (!r) return `<section class="path-cond refused" data-model="${esc(x.model_id)}">${head}<p class="muted cond-refused">${esc(COND.returnRefused)}</p></section>`;
  const obs = vm.streak?.j_observed ?? null;
  const hypo = r.state === "STREAK_ONGOING" && obs !== null && r.j_or_t !== obs;
  const state = r.state === "STREAK_ONGOING" ? PATH_COND.stateOngoing(r.j_or_t) : PATH_COND.stateBreak(r.j_or_t);
  const info = vm.pathParams.find((p) => p.model_id === x.model_id);
  const lines: string[] = [`<p class="cond-state">${esc(state)}` + (hypo ? ` <span class="hypo">${esc(PATH_COND.hypothetical)}</span>` : "") + `</p>`];
  if (hypo && vm.streak?.broken && obs !== null) lines.push(`<p class="warn-box hypo-broken">${esc(PATH_COND.hypotheticalBroken(obs))}</p>`);
  if (r.state === "STREAK_ONGOING") {
    lines.push(`<p class="s-j small mono" title="${esc(pyRepr(r.result.S_j ?? null))}">${esc(PATH_COND.sJ(r.j_or_t))} = ${esc(pct0(num(r.result.S_j)))}</p>`);
  } else {
    lines.push(`<p class="small muted after-break-note">${esc(r.result.note ?? PATH_COND.afterBreakNote)}</p>`);
  }
  if (r.mismatch) {
    lines.push(`<p class="warn-box limit-mismatch" data-t="${r.mismatch.t}">` +
      `${esc(PATH_COND.mismatch(r.mismatch.t, r.mismatch.close, r.mismatch.c))} ${esc(PATH_COND.mismatchNote)}</p>`);
  }
  const source = r.source_kind === "RECORD"
    ? PATH_COND.sourceRecord(r.source_file ?? DASH, sha8(r.params_sha256))
    : r.source_kind === "RECORD_POST_D1"
      ? PATH_COND.sourceRecordPostD1(r.source_file ?? DASH, sha8(r.params_sha256))
      : PATH_COND.sourceOutput;
  const rows = H_ALL.map((h) => condRow(r, h)).join("");
  const survival = info ? `<p class="small muted">${esc(PATH.survivalModel(info.survival_model_id ?? DASH, sha8(info.survival_model_sha256)))}</p>` : "";
  return `<section class="path-cond" data-model="${esc(x.model_id)}" data-state="${esc(r.state)}" data-j="${r.j_or_t}">` +
    head + lines.join("") + closesList(r) +
    `<div class="scroll"><table class="grid compact cond-return-table" data-model="${esc(x.model_id)}"><tbody>${rows}</tbody></table></div>` +
    condBars(r) + condFan(r) +
    `<p class="source-line small">${esc(source)}</p>${survival}</section>`;
}

/** "Getiri (koşullu)" ek kartı (EK 3 §6.5): D1 sonrası kaydın `path_conditional`'ı, Rust sarar; hesap yok. */
function postD1PathCard(vm: ConditionalVM): string {
  const card = vm.postD1?.mode === "OFFICIAL" && vm.postD1.view?.state === "PREDICTED" ? vm.postD1.view.path_card : null;
  if (!card) return "";
  const inner = condCard(vm, { model_id: card.model_id, result: card, error: null });
  return `<div class="post-d1-path"><h4>${esc(COND.postD1PathCard)}</h4>${inner}</div>`;
}

function renderReturnTab(vm: ConditionalVM): string {
  if (!vm.pathAvailable) return `<p class="muted return-none">${esc(COND.returnNone)}</p>`;
  if (vm.recordWithoutPath) return `<p class="warn-box record-no-path">${esc(PATH_COND.noRecordModels)}</p>` + postD1PathCard(vm);
  const cols = `<p class="small muted cond-cols">${esc([PATH.colMedian, PATH.colBand, PATH.colPUp, PATH.colS, PATH.colAtoms].join(" · "))}</p>`;
  return cols + vm.pathCond.map((x) => condCard(vm, x)).join("") + postD1PathCard(vm);
}

export function renderConditional(vm: ConditionalVM): string {
  const tabs = `<div class="tabs"><button class="tab${vm.tab === "ceiling" ? " active" : ""}" data-action="cond-tab" data-tab="ceiling">${esc(COND.tabCeiling)}</button>` +
    `<button class="tab${vm.tab === "return" ? " active" : ""}" data-action="cond-tab" data-tab="return">${esc(COND.tabReturn)}</button></div>`;
  const head = `<section class="group conditional"><h3>${esc(COND.title)}</h3><p class="small muted">${esc(COND.definition)}</p>${tabs}`;
  // Beyan resmi verinin önündeyse hiçbir koşullu sayı gösterilmez (SPEC_APP §3g, U52-3).
  const ahead = declStates(vm).some((x) => x === "AHEAD");
  const pending = `<p class="warn-box official-pending">${esc(COND.officialPending)}</p>`;
  // Beyan resmi verinin önündeyse koşullu getiri kartı da boş kalır (U52, proje sahibi kararı).
  if (vm.tab === "return") return `${head}${ahead ? pending : renderReturnTab(vm)}</section>`;
  const s = vm.streak;
  const strip = s ? renderStrip(s, vm.declared, vm.declDropped) : "";
  const obs = s?.j_observed ?? null;
  const msgs: string[] = [];
  const brokenNow = !!s && s.broken && obs !== null && vm.jSelected === obs;
  if (s && s.broken && obs !== null) msgs.push(`<p class="broken-box">${esc(COND.broken(obs + 1, obs))}</p>`);
  if (s && s.unlabeled) msgs.push(`<p class="warn-box unlabeled">${esc(COND.unlabeled)}</p>`);
  // Beyan resmi verinin önündeyse D1 sonrası satırı da yok (U52): yalnız "resmi kapanış bekleniyor"
  if (ahead) return `${head}${strip}${msgs.join("")}${pending}</section>`;
  const curve = brokenNow ? "" : condCurve(vm);
  return `${head}${strip}${msgs.join("")}${renderPostD1Note(vm.postD1, vm.cond?.j ?? vm.jSelected)}${jSelector(vm)}${curve}</section>`;
}

// Girdi formu (SPEC_APP §3a) saf render. Denetim notları, öneriler ve zorunluluk Rust `check_form`'dan.
import { F3_DEFINITION, F6, FIELDS, FORM_NOTE_TEXT, INPUTS, REQUIREMENT_TEXT, STAGES, TR, type StageId } from "../i18n/tr";
import type { AppError, FormCheck, Market20View } from "../types";
import { esc, renderError } from "../dom";
import { codeText } from "./codes";
import { DASH, sha12 } from "./format";

export type F6Mode = "REPO_PYTHON" | "MANUAL" | "NONE";

export interface F6VM {
  mode: F6Mode;
  manual: string;
  market20: Market20View | null;
  /** market20 sonucunun hesaplandığı T; formdaki T farklıysa bayat. */
  market20ForT: string | null;
  busy: boolean;
  error: AppError | null;
}

export interface InputsVM {
  stage: StageId | null;
  fields: Record<string, string>;
  tickerLabel: string;
  check: FormCheck | null;
  repoMode: boolean;
  tickers: string[];
  prefillTicker: string;
  prefillMsg: string | null;
  missingReasons: Record<string, string>;
  f6: F6VM;
  busy: boolean;
  error: AppError | null;
}

const FILTER_OPTIONS = ["NOT_SPECIFIED", "UNFILTERED", "FILTERED"];

/** "Bu aşamada" sütunu (Rust `check_form.requirements`). */
export function requirementText(field: string, check: FormCheck | null): string {
  const req = check?.requirements[field];
  return req ? REQUIREMENT_TEXT[req] ?? req : DASH;
}

export function renderFieldNotes(field: string, check: FormCheck | null, missingReasons: Record<string, string>): string {
  const notes = (check?.notes ?? []).filter((n) => n.field === field);
  const items = notes.map((n) => {
    const text = FORM_NOTE_TEXT[n.code]?.({ value: n.value, name: n.name }) ?? codeText(n.code, field);
    return `<div class="note note-${n.level}" data-code="${esc(n.code)}"><span class="mono">${esc(n.code)}</span> ${esc(text)}</div>`;
  });
  const sug = check?.suggestions[field];
  if (sug !== undefined) {
    items.push(`<div class="note note-suggest">${esc(INPUTS.suggestion(sug))} <button class="link" data-action="apply-suggestion" data-field="${esc(field)}" data-value="${esc(sug)}">${esc(INPUTS.applySuggestion)}</button></div>`);
  }
  const mr = missingReasons[field];
  if (mr) items.push(`<div class="note note-info">${esc(INPUTS.missingReasonFromDoc(mr))}</div>`);
  return items.join("");
}

function inputFor(name: string, value: string, disabled: boolean, placeholder: string): string {
  const dis = disabled ? " disabled" : "";
  if (name === "total_demand_filter_status") {
    const opts = [`<option value="">${esc(INPUTS.filterStatusEmpty)}</option>`, ...FILTER_OPTIONS.map((o) => `<option value="${o}"${o === value ? " selected" : ""}>${o}</option>`)];
    return `<select data-field="${name}"${dis}>${opts.join("")}</select>`;
  }
  return `<input type="text" data-field="${name}" value="${esc(value)}" placeholder="${esc(placeholder)}" autocomplete="off" spellcheck="false"${dis}/>`;
}

export function renderF6(v: InputsVM): string {
  const f = v.f6;
  const radio = (mode: F6Mode, label: string, disabled: boolean) =>
    `<label class="radio${disabled ? " disabled" : ""}"><input type="radio" name="f6mode" data-action="f6-mode" value="${mode}"${f.mode === mode ? " checked" : ""}${disabled || !v.stage ? " disabled" : ""}/> ${esc(label)}${disabled ? ` <span class="small muted">(${esc(F6.repoClosed)})</span>` : ""}</label>`;
  const parts = [radio("REPO_PYTHON", F6.modeRepo, !v.repoMode), radio("MANUAL", F6.modeManual, false), radio("NONE", F6.modeNone, false)];
  let body = "";
  if (f.mode === "REPO_PYTHON") {
    const t = (v.fields.first_trading_date ?? "").trim();
    const stale = f.market20 !== null && (f.market20ForT ?? "") !== t;
    body += `<button data-action="f6-compute"${f.busy || !v.repoMode ? " disabled" : ""}>${esc(f.busy ? F6.computing : F6.compute)}</button>`;
    if (f.market20) {
      const r = f.market20.record;
      const rows: [string, string][] = [
        [F6.value, r.f6 ?? DASH],
        [F6.refDate, r.ref_date],
        [F6.s0, r.S0_date ?? DASH],
        [F6.s20, r.S20_date ?? DASH],
        [F6.xu100, sha12(r.xu100_sha256)],
      ];
      body += `<table class="kv f6-result">${rows.map(([k, val]) => `<tr><th>${esc(k)}</th><td class="mono">${esc(val)}</td></tr>`).join("")}</table>`;
      if (r.refusal) body += `<div class="note note-error" data-code="MARKET20_${esc(r.refusal)}"><span class="mono">MARKET20_${esc(r.refusal)}</span> ${esc(codeText(`MARKET20_${r.refusal}`, "f6_market20"))}</div>`;
      if (f.market20.t_unknown) body += `<div class="note note-warn">${esc(F6.tUnknown)}</div>`;
      if (stale) body += `<div class="note note-warn">${esc(F6.stale)}</div>`;
    }
    if (f.error) body += renderError(f.error);
  } else if (f.mode === "MANUAL") {
    body += `<label>${esc(F6.value)} <input type="text" data-f6-manual value="${esc(f.manual)}" autocomplete="off"${v.stage ? "" : " disabled"}/></label> <span class="tag tag-scenario">${esc(F6.manualLabel)}</span>`;
    body += `<table class="kv"><tr><th>${esc(F6.s0)}</th><td>${DASH}</td></tr><tr><th>${esc(F6.s20)}</th><td>${DASH}</td></tr></table>`;
    body += `<div data-notes="f6_market20">${renderFieldNotes("f6_market20", v.check, {})}</div>`;
  }
  return `<section class="f6"><h3>${esc(F6.title)}</h3><div class="radios">${parts.join("")}</div><div class="f6-body">${body}</div>` +
    `<p class="small muted">${esc(F6.officialNote)} ${esc(F6.noNetwork)}</p></section>`;
}

export function renderInputs(v: InputsVM): string {
  const stageRadios = STAGES.map(
    (s) => `<label class="radio"><input type="radio" name="stage" data-action="stage" value="${s.id}"${v.stage === s.id ? " checked" : ""}/> ${esc(s.label)}</label>`,
  ).join("");
  const disabled = v.stage === null;
  const prefill = v.repoMode
    ? `<div class="prefill"><strong>${esc(INPUTS.prefillTitle)}</strong> <select data-role="prefill-ticker">${v.tickers
        .map((t) => `<option value="${esc(t)}"${t === v.prefillTicker ? " selected" : ""}>${esc(t)}</option>`)
        .join("")}</select> <button data-action="prefill"${v.tickers.length ? "" : " disabled"}>${esc(INPUTS.prefillButton)}</button>` +
      `<div class="small muted">${esc(INPUTS.prefillNote)}</div>${v.prefillMsg ? `<div class="ok-box">${esc(v.prefillMsg)}</div>` : ""}</div>`
    : `<div class="prefill small muted">${esc(INPUTS.prefillNeedsRepo)}</div>`;
  const rows = FIELDS.map((f, i) => {
    const req = v.check?.requirements[f.name];
    const reqText = requirementText(f.name, v.check);
    const placeholder = v.stage === "PRE_BOOKBUILD" && f.pbEmpty && req === "EMPTY" ? INPUTS.pbEmptyPlaceholder(f.pbEmpty) : "";
    return `<tr data-row="${f.name}" class="req-${esc(req ?? "none")}"><td class="num">${i + 1}</td>` +
      `<td><div class="flabel">${esc(f.label)}</div><div class="mono small">${esc(f.name)}</div><div class="small muted">${esc(f.def)}</div></td>` +
      `<td class="small muted">${esc(f.hint)}<div class="users">${esc(f.users)}</div></td>` +
      `<td class="small" data-req="${f.name}">${esc(reqText)}</td>` +
      `<td>${inputFor(f.name, v.fields[f.name] ?? "", disabled, placeholder)}<div class="tag tag-source">${esc(INPUTS.sourceScenario)}</div></td>` +
      `<td class="notes" data-notes="${f.name}">${renderFieldNotes(f.name, v.check, v.missingReasons)}</td></tr>`;
  }).join("");
  const f3 = `<details class="f3-def"><summary>${esc(INPUTS.f3Title)}</summary>${F3_DEFINITION.map((p) => `<p>${esc(p)}</p>`).join("")}</details>`;
  return `<h2>${esc(INPUTS.title)}</h2>` +
    `<section class="stage"><strong>${esc(INPUTS.stageLegend)}</strong> ${stageRadios}<p class="small muted">${esc(v.stage ? INPUTS.stageNote : INPUTS.stageNone)}</p></section>` +
    prefill +
    `<label class="ticker">${esc(INPUTS.tickerLabel)} <input type="text" data-role="ticker-label" value="${esc(v.tickerLabel)}" autocomplete="off"${disabled ? " disabled" : ""}/></label>` +
    `<p class="small muted">${esc(INPUTS.units)}</p>` +
    `<div class="scroll"><table class="form-table"><thead><tr><th>${esc(INPUTS.colNo)}</th><th>${esc(INPUTS.colField)}</th><th>${esc(INPUTS.colHint)}</th>` +
    `<th>${esc(INPUTS.colRequirement)}</th><th>${esc(INPUTS.colValue)}</th><th>${esc(INPUTS.colNotes)}</th></tr></thead><tbody>${rows}</tbody></table></div>` +
    f3 + `<div data-role="f6">${renderF6(v)}</div>` +
    `<div class="actions"><button class="primary" data-action="predict"${disabled || v.busy ? " disabled" : ""}>${esc(v.busy ? INPUTS.predicting : INPUTS.predict)}</button> ` +
    `<button data-action="official-flow"${v.repoMode ? "" : ` disabled title="${esc(INPUTS.prepareOfficialClosed)}"`}>${esc(INPUTS.prepareOfficial)}</button>` +
    `<p class="small muted">${esc(INPUTS.predictNote)}</p>` +
    `<p class="small muted">${esc(v.repoMode ? INPUTS.prepareOfficialNote : INPUTS.prepareOfficialClosed)}</p></div>` +
    (v.error ? renderError(v.error) : "") +
    `<p class="small muted">${esc(TR.modeScenarioNote)}</p>`;
}

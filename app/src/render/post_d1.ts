// D1 sonrası güncelleme (SPEC_APP EK 3 §6.5–§6.6) saf render: arz sayfasının koşullu sekmesindeki "D1 sonrası" bilgi
// bloğu (kaynak satırı, sekmeler, birincil seçim notu, push kanıtı göstergesi) ve "D1 sonrası kayıt" sihirbazı. Bütün
// değerler Rust `post_d1_view` / `post_d1_preflight` / `post_d1_freeze`'den gelir (S yalnız kayıttan; koşullu satır aynı
// `ceiling_display`); burada hesap yoktur. Senaryo modunda satır yok. Komut blokları Rust'ın tek fonksiyonundan
// (`post_d1_commands`); uygulama onları ÇALIŞTIRMAZ.
import { COND, POST_D1, REGISTRY, TR } from "../i18n/tr";
import type {
  AppError,
  PostD1CancelResult,
  PostD1FreezeResult,
  PostD1Preflight,
  PostD1RecordRow,
  PostD1View,
} from "../types";
import { esc, renderError } from "../dom";
import { sha12 } from "./format";

export const POST_D1_MODEL_ID = "post_d1_hazard_v0";

/** Koşullu sekmenin D1 sonrası girdisi: resmi görünüm (arz sayfası, kayıttan) ya da senaryo (satır yok). */
export interface PostD1VM {
  mode: "OFFICIAL" | "SCENARIO";
  view: PostD1View | null;
  error: AppError | null;
}

/** Tabloya ve eğriye eklenecek satır yalnız resmi görünümde, PREDICTED kayıtta ve j ≥ 1'de (Rust `row`'u j'de kurar). */
export function postD1Row(vm: PostD1VM | null | undefined, j: number): PostD1View["row"] {
  const v = vm?.view;
  if (!vm || vm.mode !== "OFFICIAL" || !v || v.state !== "PREDICTED" || j < 1 || v.j !== j) return null;
  return v.row;
}

function proofLine(r: PostD1RecordRow | undefined): string {
  if (!r) return "";
  const git = r.tracked ? REGISTRY.tracked : REGISTRY.untracked;
  const proof = r.push_proof ? REGISTRY.proofFound(sha12(r.push_proof.sha), r.push_proof.created_at ?? TR.dash) : REGISTRY.proofMissing;
  return `<p class="small post-d1-proof">${esc(git)} · <span class="proof">${esc(proof)}</span></p>`;
}

function tabs(v: PostD1View): string {
  if (v.active.length < 2) return "";
  const buttons = v.active
    .map((f, i) => {
      const r = v.records.find((x) => x.file === f);
      const cls = ["tab", f === v.selected ? "active" : ""].filter(Boolean).join(" ");
      return `<button class="${cls}" data-action="post-d1-tab" data-file="${esc(f)}">${esc(COND.postD1Tab(i + 1, r?.recorded_at_istanbul ?? f))}</button>`;
    })
    .join("");
  return `<div class="tabs post-d1-tabs">${buttons}</div>`;
}

/** Şeritin altındaki D1 sonrası bilgi bloğu (gri not ya da durum, kaynak satırı, sekmeler, birincil seçim etiketi). */
export function renderPostD1Note(vm: PostD1VM | null | undefined, j: number): string {
  if (!vm) return "";
  if (vm.mode === "SCENARIO") return `<p class="small muted post-d1-scenario">${esc(COND.postD1Scenario)}</p>`;
  if (vm.error) return `<div class="post-d1 error">${renderError(vm.error)}</div>`;
  const v = vm.view;
  if (!v || v.state === "NO_RECORD") return `<p class="small muted post-d1-none">${esc(COND.postD1None)}</p>`;
  const lines: string[] = [];
  if (j === 0 || v.state === "J0") lines.push(`<p class="small muted post-d1-j0">${esc(COND.postD1J0)}</p>`);
  else if (v.state === "REFUSED") lines.push(`<p class="post-d1-refused" data-code="${esc(v.refusal?.code ?? "")}">${esc(COND.postD1Refused(v.refusal?.code ?? TR.dash))}</p>`);
  else if (v.state === "NOT_APPLICABLE") lines.push(`<p class="post-d1-na">${esc(COND.postD1NotApplicable)}</p>`);
  else if (v.state === "NO_CELL") lines.push(`<p class="warn-box post-d1-no-cell">${esc(COND.postD1NoCell)}</p>`);
  else if (v.state === "PREDICTED" && v.row && !v.row.cond) lines.push(`<p class="small muted post-d1-undefined">${esc(COND.postD1Undefined)}</p>`);
  const src = v.source;
  if (src) {
    lines.push(`<p class="source-line small post-d1-source">${esc(COND.postD1Source(src.rel_path, src.params_sha8, src.d1_session_date ?? TR.dash, src.thb_sha8 ?? TR.dash, src.thm_sha8 ?? TR.dash))}</p>`);
  }
  lines.push(proofLine(v.records.find((r) => r.file === v.selected)));
  if (v.active.length > 1) lines.push(`<p class="small muted post-d1-primary">${esc(COND.postD1Primary)}</p>`);
  return `<div class="post-d1" data-state="${esc(v.state)}" data-selected="${esc(v.selected ?? "")}">` +
    `<h4>${esc(COND.postD1Row)}</h4>${tabs(v)}${lines.join("")}</div>`;
}

// ---------------------------------------------------------------- sihirbaz (EK 3 §6.6)

export interface PostD1WizardVM {
  repoMode: boolean;
  ticker: string;
  preflight: PostD1Preflight | null;
  /** Adım 2 komut bloğu (Rust `post_d1_todo` OUTCOMES). */
  outcomesTodo: string[] | null;
  frozen: PostD1FreezeResult | null;
  cancelFile: string;
  cancelReason: string;
  cancelled: PostD1CancelResult | null;
  busy: string | null;
  error: AppError | null;
}

function step(n: number, body: string, cls = ""): string {
  return `<section class="wizard-step post-d1-step ${cls}" data-step="${n}"><h3>${esc(POST_D1.step(n, POST_D1.steps[n - 1]))}</h3>${body}</section>`;
}

function mark(ok: boolean): string {
  return `<span class="${ok ? "ok" : "bad"}">${esc(ok ? POST_D1.yes : POST_D1.no)}</span>`;
}

function commandBlock(lines: string[], cls: string): string {
  return `<pre class="mono todo-block ${cls}">${esc(lines.join("\n"))}</pre>` +
    `<div class="actions"><button data-action="pd1-copy" data-block="${esc(cls)}">${esc(POST_D1.copy)}</button></div>`;
}

function preflightBody(p: PostD1Preflight): string {
  const row = (k: string, v: string, ok?: boolean) =>
    `<tr><th>${esc(k)}</th><td class="mono">${ok === undefined ? "" : `${mark(ok)} `}${esc(v)}</td></tr>`;
  const rows = [
    row(POST_D1.gitHead, sha12(p.git_head), p.git_head !== null),
    row(POST_D1.indexSha, sha12(p.index_sha_repo), p.index_match),
    row(POST_D1.indexPostD1Sha, sha12(p.index_post_d1_sha_repo), p.index_post_d1_match),
    row(POST_D1.borsaiImport, p.borsai_file ?? TR.dash, p.borsai_in_repo),
    row(POST_D1.baseRecords, p.base_records.length ? p.base_records.join(", ") : POST_D1.blockerText.NO_PRE_LISTING_RECORD, p.base_records.length > 0),
    row(POST_D1.d1, p.d1 ? POST_D1.d1Found(p.d1, p.d1_status ?? TR.dash) : POST_D1.d1Pending, p.d1 !== null),
  ];
  const tOpen = p.t_open
    ? `<p class="t-open">${esc(POST_D1.tOpen(p.t_open))}</p><p class="small muted">${esc(POST_D1.tOpenNote)}</p>` +
      (p.minutes_to_t_open !== null ? `<p class="small muted minutes-left">${esc(POST_D1.minutesLeft(String(p.minutes_to_t_open)))}</p>` : "")
    : p.t_open_error
      ? `<p class="warn-box calendar-na">${esc(POST_D1.blockerText.CALENDAR_NOT_AVAILABLE)}</p><pre class="mono small">${esc(p.t_open_error.trim())}</pre>`
      : "";
  const git = p.committed
    ? `<p class="ok-box committed">${esc(POST_D1.committed)}</p>`
    : `<p class="warn-box uncommitted">${esc(POST_D1.uncommitted)}</p><pre class="mono small git-status">${esc(p.git_status_pending.trim())}</pre>`;
  const warnings = p.warnings.filter((w) => w !== "UNCOMMITTED")
    .map((w) => `<p class="warn-box" data-warning="${esc(w)}">${esc(POST_D1.warningText[w] ?? w)}</p>`).join("");
  const blockers = p.ok
    ? `<p class="ok-box preflight-ok">${esc(POST_D1.ok)}</p>`
    : `<div class="band-error preflight-blocked"><strong>${esc(POST_D1.blocked)}</strong><ul>` +
      p.blockers.map((b) => `<li data-blocker="${esc(b)}">${esc(POST_D1.blockerText[b] ?? b)}</li>`).join("") + `</ul></div>`;
  const active = `<p class="small muted">${esc(POST_D1.activePostD1(p.active_post_d1.length))}</p>`;
  return `<table class="kv post-d1-checks">${rows.join("")}</table>${tOpen}${git}${warnings}${active}${blockers}`;
}

function frozenBody(f: PostD1FreezeResult): string {
  const s = f.summary ?? {};
  const pr = f.parity;
  const ok = pr.mismatches.length === 0;
  const rows: [string, string][] = [
    [POST_D1.recordPath, f.record_rel_path],
    [POST_D1.recordD1, f.d1 ?? TR.dash],
    [POST_D1.ceilingClose, f.ceiling_close_d1 === null ? TR.dash : String(f.ceiling_close_d1)],
    [POST_D1.summaryLabel, POST_D1.summary(String(s.n_predicted ?? 0), String(s.n_refused ?? 0), String(s.n_not_applicable ?? 0))],
    [POST_D1.baseRecord, f.base_record_file ?? TR.dash],
  ];
  const parity = `<p class="${ok ? "ok-box" : "band-error"} post-d1-parity" data-ok="${ok}">` +
    `${esc(POST_D1.parity(ok, pr.n_supported, String(pr.max_abs)))}</p>` +
    (ok ? "" : `<ul class="small mono">${pr.mismatches.map((m) => `<li>${esc(`${m.model_id}: ${m.failures.slice(0, 3).join(" | ")}`)}</li>`).join("")}</ul>`) +
    (pr.incident_rel_path ? `<p class="small mono">${esc(POST_D1.incident(pr.incident_rel_path))}</p>` : "");
  const comps = `<p class="small post-d1-comparators" data-ok="${f.comparators.failures.length === 0}">` +
    `${esc(POST_D1.comparators(f.comparators.n_checked, String(f.comparators.max_abs)))}</p>`;
  const note = f.t_open ? `<p class="small muted">${esc(POST_D1.pythonNote(f.t_open, f.python_note ?? ""))}</p>` : "";
  return `<table class="kv post-d1-frozen">${rows.map(([k, v]) => `<tr><th>${esc(k)}</th><td class="mono">${esc(v)}</td></tr>`).join("")}</table>` +
    parity + comps + note;
}

function cancelBody(vm: PostD1WizardVM): string {
  const active = vm.preflight?.active_post_d1 ?? [];
  const head = `<h3>${esc(POST_D1.cancelTitle)}</h3><p class="small muted">${esc(POST_D1.cancelRule)}</p>`;
  const done = vm.cancelled
    ? `<p class="ok-box">${esc(POST_D1.cancelDone(vm.cancelled.cancel_rel_path))}</p>` + commandBlock(vm.cancelled.todo, "post-d1-cancel-todo")
    : "";
  if (!active.length) return `<section class="post-d1-cancel">${head}<p class="muted">${esc(POST_D1.noActive)}</p>${done}</section>`;
  const opts = active.map((f) => `<option value="${esc(f)}"${f === vm.cancelFile ? " selected" : ""}>${esc(f)}</option>`).join("");
  return `<section class="post-d1-cancel">${head}` +
    `<label>${esc(POST_D1.cancelPick)} <select data-role="pd1-cancel-file">${opts}</select></label><br/>` +
    `<label>${esc(POST_D1.cancelReason)}<br/><input type="text" data-role="pd1-cancel-reason" size="70" value="${esc(vm.cancelReason)}" autocomplete="off"/></label> ` +
    `<button data-action="pd1-cancel"${vm.cancelReason.trim() === "" || vm.busy !== null ? " disabled" : ""}>${esc(POST_D1.cancelButton)}</button>` +
    done + `</section>`;
}

/** "D1 sonrası kayıt" sihirbazı: 1 ön koşullar → 2 bülten ve sonuç (komut) → 3 kayıt (Python) + parite → 4 komutlar. */
export function renderPostD1Wizard(vm: PostD1WizardVM): string {
  const head = `<h2>${esc(POST_D1.title)}</h2><p class="small muted">${esc(POST_D1.intro)}</p>` +
    `<div class="actions"><button data-action="pd1-back">${esc(POST_D1.back)}</button></div>`;
  if (!vm.repoMode) return `${head}<p class="closed-state">${esc(TR.closedRegistry)}</p>`;
  const busy = (a: string) => (vm.busy === a ? " disabled" : "");
  const p = vm.preflight;
  const s1 = step(1,
    `<label>${esc(POST_D1.ticker)} <input type="text" data-role="pd1-ticker" value="${esc(vm.ticker)}" size="8" autocomplete="off"/></label> ` +
    `<button data-action="pd1-preflight"${busy("pd1-preflight")}>${esc(POST_D1.check)}</button>` + (p ? preflightBody(p) : ""));
  const through = p?.d1 ?? p?.first_trading_date ?? null;
  const s2 = step(2,
    `<p class="small muted">${esc(POST_D1.outcomesNote)}</p>` +
    (through ? `<p class="small muted">${esc(POST_D1.outcomesThrough(through))}</p>` : "") +
    (vm.outcomesTodo ? commandBlock(vm.outcomesTodo, "post-d1-outcomes-todo") : "") +
    `<div class="actions"><button data-action="pd1-preflight"${busy("pd1-preflight")}>${esc(POST_D1.recheck)}</button></div>`);
  const canFreeze = p !== null && p.ok && vm.busy === null;
  const s3 = step(3,
    `<button class="primary" data-action="pd1-freeze"${canFreeze ? "" : " disabled"}>${esc(POST_D1.freeze)}</button>` +
    (vm.frozen ? frozenBody(vm.frozen) : ""));
  const s4 = vm.frozen
    ? step(4, `<p class="small muted">${esc(POST_D1.todoTitle)}</p>` + commandBlock(vm.frozen.todo, "post-d1-record-todo") +
      `<p class="time-proof">${esc(POST_D1.timeProof)} ${esc(POST_D1.liveNote(vm.frozen.t_open ?? p?.t_open ?? TR.dash))}</p>`)
    : step(4, `<p class="small muted">${esc(POST_D1.todoTitle)}</p>`, "pending");
  return `<div class="post-d1-wizard" data-ticker="${esc(vm.ticker)}">${head}${s1}${s2}${s3}${s4}${cancelBody(vm)}` +
    `${vm.error ? renderError(vm.error) : ""}</div>`;
}

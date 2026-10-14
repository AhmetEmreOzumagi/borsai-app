// Sicil ekranı ve arz sayfası (SPEC_APP §3e sonu, §3g) saf render.
// Bütün değerler Rust komutlarından gelir (`registry_view`, `record_ceiling`, `streak_view`);
// koşullu sayılar YALNIZ dondurulmuş kayıttaki S'ten (U38) — ön uç hiçbir şey hesaplamaz.
import { esc } from "../dom";
import { POST_D1, REGISTRY, TR } from "../i18n/tr";
import type {
  CeilingSummary,
  ModelInfo,
  ModelRun,
  PathDisplayRow,
  PathParamsInfo,
  RecordCeiling,
  RecordRow,
  RegistryView,
  ScoreHints,
  StreakView,
  TickerRow,
} from "../types";
import { renderConditional, type PathCondVM } from "./ceiling";
import type { PostD1VM } from "./post_d1";
import { renderCeilingSummary } from "./summary";
import { sha8, sha12 } from "./format";
import { renderGroupA, renderGroupC, type ResultsView } from "./results";

export interface RecordPageVM {
  ticker: TickerRow;
  /** Seçili sekme (kayıt dizini). */
  selected: number;
  ceiling: RecordCeiling | null;
  /** Tavan serisi kartı (EK 3 §5.4, U62): Rust `record_summary`; S yalnız kayıttan. */
  summary?: CeilingSummary | null;
  /** D1 sonrası satırı (EK 3 §6.5): Rust `post_d1_view`; S yalnız `registry/post_d1/<T>/` kaydından. */
  postD1?: PostD1VM | null;
  streak: StreakView | null;
  jSelected: number;
  tab: "ceiling" | "return";
  hidden: string[];
  /** D1..D10 "seri sürüyor" beyanı: yalnız şerit etiketi (U52). */
  declared: boolean[];
  declDropped: boolean;
  /** Kayıttaki tavan yolu modellerinin gösterim türevleri (U38: değerler yalnız kayıttan). */
  pathDisplay: PathDisplayRow[];
  pathParams: PathParamsInfo[];
  pathCond: PathCondVM[];
  models: ModelInfo[];
  hints: ScoreHints | null;
  /** Ham kayıt JSON'u açıksa metni. */
  raw: string | null;
  cancelReason: string;
  cancelDone: string | null;
  today: string;
}

function kv(rows: [string, string][]): string {
  return `<table class="kv">${rows.map(([k, v]) => `<tr><th>${esc(k)}</th><td class="mono">${esc(v)}</td></tr>`).join("")}</table>`;
}

export function renderRegistryList(v: RegistryView): string {
  const head = `<h2>${esc(REGISTRY.title)}</h2><p class="small muted">${esc(REGISTRY.subtitle)}</p>` +
    `<p class="small mono repo-line">${esc(REGISTRY.repoLine(v.repo_root))}</p>` +
    `<div class="actions"><button class="primary" data-action="new-record">${esc(REGISTRY.newRecord)}</button></div>` +
    `<p class="small muted git-status">${esc(REGISTRY.gitStatus)}: ` +
    (v.git_status_registry.trim() === ""
      ? esc(REGISTRY.gitClean)
      : `</p><pre class="mono small">${esc(v.git_status_registry.trim())}</pre><p class="small muted">`) +
    `</p>` +
    `<p class="small muted proofs">${esc(REGISTRY.proofsTitle(v.proofs.length))}</p>`;
  if (!v.tickers.length) return `${head}<p class="muted empty-state">${esc(REGISTRY.empty)}</p>`;
  const rows = v.tickers.map((t) =>
    `<tr data-ticker="${esc(t.ticker)}"><td class="mono">${esc(t.ticker)}</td><td>${esc(t.company ?? TR.dash)}</td>` +
    `<td class="mono">${esc(t.first_trading_date ?? TR.dash)}</td><td>${t.records.length}</td><td>${t.n_active}</td>` +
    `<td class="post-d1-count">${t.n_post_d1_active ?? 0}</td>` +
    `<td class="small">${esc(t.ipo_status ?? TR.dash)}</td>` +
    `<td><button data-action="open-ticker" data-ticker="${esc(t.ticker)}">${esc(REGISTRY.open)}</button></td></tr>`,
  );
  return `${head}<table class="grid registry-table"><thead><tr><th>${esc(REGISTRY.colTicker)}</th><th>${esc(REGISTRY.colCompany)}</th>` +
    `<th>${esc(REGISTRY.colT)}</th><th>${esc(REGISTRY.colRecords)}</th><th>${esc(REGISTRY.colActive)}</th><th>${esc(REGISTRY.colPostD1)}</th>` +
    `<th>${esc(REGISTRY.colStatus)}</th><th></th></tr></thead><tbody>${rows.join("")}</tbody></table>` +
    `<p class="small muted">${esc(REGISTRY.ipos(v.ipos.length))}</p>` +
    `<p class="small muted">${esc(REGISTRY.proofNote)}</p>`;
}

function tabLabel(r: RecordRow, i: number): string {
  const at = r.recorded_at_istanbul ?? r.file;
  return r.record_type === "CANCELLATION" ? REGISTRY.cancelTab(at) : REGISTRY.recordTab(i + 1, at);
}

export function proofLine(r: RecordRow): string {
  if (r.push_proof) return REGISTRY.proofFound(sha12(r.push_proof.sha), r.push_proof.created_at ?? TR.dash);
  return REGISTRY.proofMissing;
}

function renderUnsupported(r: { model_id: string; params_sha256: string }[]): string {
  if (!r.length) return "";
  return `<div class="unsupported-models"><h4>${esc(REGISTRY.unsupportedTitle)}</h4><ul>` +
    r.map((m) => `<li data-model="${esc(m.model_id)}"><span class="mono">${esc(m.model_id)}</span> <span class="tag">${esc(REGISTRY.unsupportedNote)}</span></li>`).join("") +
    `</ul></div>`;
}

function renderCancelForm(r: RecordRow, vm: RecordPageVM): string {
  const t = r.first_trading_date;
  const blocked = t !== null && t !== undefined && vm.today >= t;
  return `<div class="cancel-form"><h4>${esc(REGISTRY.cancelButton)}</h4>` +
    `<p class="small muted">${esc(REGISTRY.cancelRuleNote)}</p>` +
    (blocked ? `<p class="warn-box cancel-blocked">${esc(REGISTRY.cancelBlocked(t ?? ""))}</p>` : "") +
    `<label>${esc(REGISTRY.cancelReason)}<br/><input type="text" data-role="cancel-reason" size="70" value="${esc(vm.cancelReason)}" autocomplete="off"/></label> ` +
    `<button data-action="cancel-record" data-file="${esc(r.file)}"${vm.cancelReason.trim() === "" ? " disabled" : ""}>${esc(REGISTRY.cancelButton)}</button></div>`;
}

/** Kayıttaki tavan yolu modelleri `ModelRun` biçimine çevrilir: render Grup A/C ile birebir aynı. */
export function recordPathRuns(c: RecordCeiling): ModelRun[] {
  return c.path_models.map((m) => ({
    model_id: m.model_id,
    params_sha256: m.params_sha256,
    kind: "ceiling_path" as const,
    status: (m.status === "PREDICTED" ? "PREDICTED" : m.status === "REFUSED" ? "REFUSED" : "ERROR") as ModelRun["status"],
    refusal: m.refusal,
    output: m.output,
  }));
}

function renderRecordPath(vm: RecordPageVM, c: RecordCeiling): string {
  if (!c.path_models.length) return `<p class="warn-box record-no-path">${esc(REGISTRY.pathMissing)}</p>`;
  const view: ResultsView = {
    runs: recordPathRuns(c),
    pathDisplay: vm.pathDisplay,
    pathParams: vm.pathParams,
    ceiling: null,
    hints: vm.hints,
    models: vm.models,
    hidden: [],
    scenario: null,
    f6: null,
    openCard: null,
    openWarnings: null,
    savedId: null,
    canSave: false,
    repoMode: true,
    official: true,
  };
  const stale = c.path_models
    .filter((m) => !m.sha_matches_embedded)
    .map((m) => `<p class="warn-box sha-mismatch" data-model="${esc(m.model_id)}">${esc(REGISTRY.pathShaMismatch(m.model_id))}</p>`)
    .join("");
  return `<div class="record-path"><h4>${esc(REGISTRY.pathTitle)}</h4>${stale}${renderGroupA(view)}${renderGroupC(view)}</div>`;
}

function renderRecordBody(r: RecordRow, vm: RecordPageVM): string {
  if (r.status === "UNREADABLE") return `<p class="error-box">${esc(REGISTRY.unreadable)}: ${esc(r.error ?? "")}</p>`;
  if (r.status === "UNSUPPORTED_VERSION") return `<p class="error-box">${esc(REGISTRY.unsupportedVersion(r.schema_version ?? ""))}</p>`;
  const cancelled = r.cancelled_by !== null;
  const rows: [string, string][] = [
    [REGISTRY.recordHead(""), r.file],
    [REGISTRY.recordedAt, r.recorded_at_istanbul ?? TR.dash],
    [REGISTRY.gitHead, sha12(r.git_head)],
    [REGISTRY.inputSha, sha12(r.input_sha256)],
    [REGISTRY.indexSha, sha12(r.models_index_sha256)],
    [REGISTRY.inputsPath, r.inputs_path ?? TR.dash],
    [REGISTRY.colT, r.first_trading_date ?? TR.dash],
    [REGISTRY.nModels, String(r.n_models)],
  ];
  const head =
    (cancelled
      ? `<p class="band-error cancelled-band"><strong>${esc(REGISTRY.cancelled)}</strong> ` +
        `${esc(REGISTRY.cancelledBy(r.cancelled_by?.reason ?? "", r.cancelled_by?.recorded_at_istanbul ?? ""))}</p>`
      : "") +
    (r.record_type === "CANCELLATION"
      ? `<p class="info-line">${esc(REGISTRY.cancels(r.cancels ?? ""))} · ${esc(r.reason ?? "")}</p>`
      : "");
  const git = `<p class="small proof-line">${esc(r.tracked ? REGISTRY.tracked : REGISTRY.untracked)}` +
    (r.added_commit ? ` · ${esc(REGISTRY.addedCommit(sha12(r.added_commit)))}` : "") +
    ` · <span class="proof">${esc(proofLine(r))}</span></p>` +
    `<p class="small muted">${esc(REGISTRY.proofNote)}</p>`;
  const cond =
    vm.ceiling && vm.ceiling.file === r.file
      ? `<p class="source-line small record-source">${esc(REGISTRY.recordSource(vm.ceiling.file))} · ` +
        `${esc(REGISTRY.recordShaLine(vm.ceiling.models.map((m) => `${m.model_id}=${sha8(m.params_sha256)}`).join(", ")))}</p>` +
        `<p class="small muted">${esc(REGISTRY.recordOnly)}</p>` +
        (vm.summary ? renderCeilingSummary({ summary: vm.summary, streak: vm.streak, declared: vm.declared }) : "") +
        renderRecordPath(vm, vm.ceiling) +
        renderConditional({ streak: vm.streak, cond: vm.ceiling.display, jSelected: vm.jSelected, tab: vm.tab, hidden: vm.hidden,
          declared: vm.declared, declDropped: vm.declDropped,
          pathAvailable: vm.pathParams.length > 0, pathCond: vm.pathCond, pathParams: vm.pathParams,
          recordWithoutPath: vm.ceiling.path_models.length === 0, postD1: vm.postD1 ?? null })
      : "";
  const raw = vm.raw ? `<details open class="raw-record"><summary>${esc(REGISTRY.rawRecord)}</summary><pre class="mono small">${esc(vm.raw)}</pre></details>`
    : `<button data-action="show-raw" data-file="${esc(r.file)}">${esc(REGISTRY.rawRecord)}</button>`;
  const cancelForm = !cancelled && r.record_type === "PREDICTION" ? renderCancelForm(r, vm) : "";
  return head + kv(rows) + git + renderUnsupported(r.unsupported_models) + cond + cancelForm + raw;
}

export function renderRecordPage(vm: RecordPageVM): string {
  const t = vm.ticker;
  const tabs = t.records
    .map((r, i) => {
      const cls = ["tab", i === vm.selected ? "active" : "", r.cancelled_by ? "record-cancelled" : ""].filter(Boolean).join(" ");
      return `<button class="${cls}" data-action="select-record" data-index="${i}">${esc(tabLabel(r, i))}</button>`;
    })
    .join("");
  const r = t.records[vm.selected];
  return `<h2>${esc(t.ticker)} · ${esc(t.company ?? "")}</h2>` +
    `<div class="actions"><button data-action="back-registry">${esc(REGISTRY.back)}</button> ` +
    `<button data-action="new-record">${esc(REGISTRY.newRecord)}</button> ` +
    `<button data-action="pd1-wizard" data-ticker="${esc(t.ticker)}">${esc(POST_D1.open)}</button></div>` +
    kv([
      [REGISTRY.colT, t.first_trading_date ?? TR.dash],
      [REGISTRY.colRecords, String(t.records.length)],
      [REGISTRY.nActive, String(t.n_active)],
    ]) +
    `<p class="small muted">${esc(REGISTRY.primaryNote)}</p>` +
    (vm.cancelDone ? `<p class="ok-box">${esc(vm.cancelDone)}</p>` : "") +
    `<div class="tabs record-tabs">${tabs}</div>` +
    (r ? `<section class="record" data-file="${esc(r.file)}">${renderRecordBody(r, vm)}</section>` : "");
}

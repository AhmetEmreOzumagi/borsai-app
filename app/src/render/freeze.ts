// Resmi "dondur" sihirbazı (SPEC_APP §3e) saf render: 6 adım, her adımın çıktısı ekranda kalır,
// sonra "Şimdi yapılacaklar". Uygulama komutları ÇALIŞTIRMAZ; blok kopyalanabilir metindir (U32).
import { esc } from "../dom";
import { FIELDS, FREEZE, SOURCE_KIND_TEXT, STAGES, type StageId } from "../i18n/tr";
import type { AppError, FreezeResult, InputsDocPreview, ManifestDoc, Preflight, SourceDocsView } from "../types";
import { renderError } from "../dom";
import { sha12 } from "./format";
import { renderTufeInfo } from "./summary";

export interface DocDraft {
  path: string;
  file_name: string;
  source_id: string;
  kind: string;
  document_id: string;
  published_at: string;
  published_at_basis: string;
  title: string;
}

export interface FieldDraftUI {
  source_id: string;
  quote: string;
  missing_reason: string;
  origin: string;
}

export interface FreezeVM {
  repoMode: boolean;
  hasResults: boolean;
  ticker: string;
  company: string;
  stage: StageId;
  /** Sonuç ekranındaki 20 form alanı (değerler değişmez: kayda giren = tahmin edilen). */
  values: Record<string, string | null>;
  docs: DocDraft[];
  copied: SourceDocsView | null;
  manifest: ManifestDoc | null;
  fields: Record<string, FieldDraftUI>;
  collectionRules: string;
  ftdSource: string;
  preflight: Preflight | null;
  preview: InputsDocPreview | null;
  written: InputsDocPreview | null;
  pit: string[] | null;
  acknowledged: boolean;
  frozen: FreezeResult | null;
  busy: string | null;
  error: AppError | null;
}

const KINDS = ["KAP_NOTIFICATION_PDF", "KAP_ATTACHMENT_PDF", "SPK_BULLETIN"];
const F3_ORIGINS = ["SOURCE_REPORTED", "SOURCE_REPORTED_APPROX", "CALCULATED_FROM_SOURCE_TOTALS", "CALCULATED_FROM_PRIMARY_TOTALS"];

function section(n: number, body: string, cls = ""): string {
  return `<section class="wizard-step ${cls}" data-step="${n}"><h3>${esc(FREEZE.step(n, FREEZE.steps[n - 1]))}</h3>${body}</section>`;
}

function kv(rows: [string, string][]): string {
  return `<table class="kv">${rows.map(([k, v]) => `<tr><th>${esc(k)}</th><td class="mono">${esc(v)}</td></tr>`).join("")}</table>`;
}

function busyOrRun(vm: FreezeVM, action: string, label: string, disabled = false): string {
  const on = vm.busy === action;
  return `<button data-action="${esc(action)}"${on || disabled ? " disabled" : ""}>${esc(on ? FREEZE.freezing : label)}</button>`;
}

// ---------------------------------------------------------------- adım 1

function step1(vm: FreezeVM): string {
  const p = vm.preflight;
  const body = `<div class="actions">${busyOrRun(vm, "preflight", FREEZE.run)}</div>` +
    (p
      ? (p.ok ? `<p class="ok-box">${esc(FREEZE.preflightOk)}</p>` : `<p class="band-error">${esc(FREEZE.preflightBlocked)}</p>`) +
        (p.blockers.length
          ? `<ul class="blockers">${p.blockers.map((b) => `<li data-blocker="${esc(b)}">${esc(FREEZE.blockerText[b] ?? b)}</li>`).join("")}</ul>`
          : "") +
        renderTufeInfo(p.tufe ?? null) +
        kv([
          [FREEZE.gitHead, sha12(p.git_head)],
          [FREEZE.indexSha, sha12(p.index_sha_repo)],
          [FREEZE.indexEmbedded, sha12(p.index_sha_embedded)],
          [FREEZE.borsaiFile, p.borsai_file ?? ""],
          [FREEZE.pythonPath, p.python_path],
        ]) +
        `<p class="small muted">${esc(FREEZE.statusInfo)}</p>` +
        `<pre class="mono small git-status">${esc(p.git_status_registry.trim())}</pre>`
      : "");
  return section(1, body);
}

// ---------------------------------------------------------------- adım 2

function docRow(d: DocDraft, i: number): string {
  const opts = KINDS.map((k) => `<option value="${esc(k)}"${k === d.kind ? " selected" : ""}>${esc(SOURCE_KIND_TEXT[k] ?? k)}</option>`).join("");
  const input = (key: keyof DocDraft, label: string, size: number) =>
    `<label class="small">${esc(label)}<br/><input type="text" data-doc="${i}" data-key="${esc(key)}" value="${esc(String(d[key]))}" size="${size}" autocomplete="off"/></label>`;
  return `<tr data-doc-row="${i}"><td class="mono small">${esc(d.file_name)}</td>` +
    `<td>${input("source_id", FREEZE.docSourceId, 18)}</td>` +
    `<td><label class="small">${esc(FREEZE.docKind)}<br/><select data-doc="${i}" data-key="kind">${opts}</select></label></td>` +
    `<td>${input("document_id", FREEZE.docDocumentId, 18)}</td>` +
    `<td>${input("published_at", FREEZE.docPublishedAt, 26)}</td>` +
    `<td>${input("published_at_basis", FREEZE.docBasis, 34)}</td>` +
    `<td>${input("title", FREEZE.docTitle, 18)}</td>` +
    `<td><button data-action="remove-doc" data-doc="${i}">${esc(FREEZE.docRemove)}</button></td></tr>`;
}

function step2(vm: FreezeVM): string {
  const table = vm.docs.length
    ? `<div class="scroll"><table class="grid compact docs-table"><tbody>${vm.docs.map(docRow).join("")}</tbody></table></div>`
    : `<p class="muted empty-state">${esc(FREEZE.noDocs)}</p>`;
  const copied = vm.copied
    ? `<p class="ok-box">${esc(FREEZE.copyDone(vm.copied.documents.length, vm.copied.rel_dir))}</p>` +
      `<ul class="copied-docs">${vm.copied.documents
        .map(
          (d) =>
            `<li data-source="${esc(d.source_id)}"><span class="mono">${esc(d.rel_path)}</span> · ${esc(FREEZE.docStateText[d.file_state] ?? d.file_state)}` +
            ` · ${esc(FREEZE.docStateText[d.manifest_state] ?? d.manifest_state)} · <span class="mono">${esc(sha12(d.sha256))}</span></li>`,
        )
        .join("")}</ul>`
    : "";
  const manifest = vm.manifest
    ? `<p class="small muted">${esc(FREEZE.manifestDocs(Object.keys(vm.manifest.documents).length))} · <span class="mono">${esc(vm.copied?.manifest_rel_path ?? "")}</span></p>`
    : "";
  return section(
    2,
    `<div class="actions"><button data-action="pick-docs">${esc(FREEZE.pickDocs)}</button> ` +
      busyOrRun(vm, "copy-docs", FREEZE.copyDocs, vm.docs.length === 0) +
      ` <button data-action="read-manifest">${esc(FREEZE.readManifest)}</button>` +
      `</div>${table}${copied}${manifest}`,
  );
}

// ---------------------------------------------------------------- adım 3

function fieldRow(vm: FreezeVM, name: string, label: string): string {
  const value = vm.values[name] ?? null;
  const d = vm.fields[name] ?? { source_id: "", quote: "", missing_reason: "", origin: "" };
  const ids = vm.manifest ? Object.keys(vm.manifest.documents) : [];
  const sel = `<select data-field-key="source_id" data-field="${esc(name)}"><option value="">${esc(FREEZE.pickSource)}</option>` +
    ids.map((id) => `<option value="${esc(id)}"${id === d.source_id ? " selected" : ""}>${esc(id)}</option>`).join("") +
    `</select>`;
  const origin =
    name === "total_demand_multiple" && value !== null
      ? `<select data-field-key="origin" data-field="${esc(name)}"><option value="">${esc(FREEZE.pickSource)}</option>` +
        F3_ORIGINS.map((o) => `<option value="${esc(o)}"${o === d.origin ? " selected" : ""}>${esc(o)}</option>`).join("") +
        `</select>`
      : "";
  const filled = value !== null && value !== "";
  const right = filled
    ? `<td>${sel}${origin}</td><td><input type="text" data-field-key="quote" data-field="${esc(name)}" value="${esc(d.quote)}" size="40" autocomplete="off"/></td>`
    : `<td class="muted small">${esc(FREEZE.colMissing)}</td><td><input type="text" data-field-key="missing_reason" data-field="${esc(name)}" value="${esc(d.missing_reason)}" size="40" autocomplete="off"/></td>`;
  return `<tr data-field-row="${esc(name)}" class="${filled ? "filled" : "empty"}"><td class="small">${esc(label)}<br/><span class="mono small">${esc(name)}</span></td>` +
    `<td class="mono value">${esc(filled ? String(value) : "")}</td>${right}</tr>`;
}

function step3(vm: FreezeVM): string {
  const ids = vm.manifest ? Object.keys(vm.manifest.documents) : [];
  const rows = FIELDS.map((f) => fieldRow(vm, f.name, f.label)).join("");
  const ftd = `<label class="small">${esc(FREEZE.ftdSource)}<br/><select data-role="ftd-source"><option value="">${esc(FREEZE.pickSource)}</option>` +
    ids.map((id) => `<option value="${esc(id)}"${id === vm.ftdSource ? " selected" : ""}>${esc(id)}</option>`).join("") +
    `</select></label>`;
  const rules = `<label class="small">${esc(FREEZE.collectionRules)}<br/><textarea data-role="collection-rules" rows="3" cols="100">${esc(vm.collectionRules)}</textarea></label>`;
  const p = vm.written ?? vm.preview;
  const problems = p && p.problems.length
    ? `<div class="band-error doc-problems"><strong>${esc(FREEZE.docProblems)}</strong><ul>${p.problems.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>`
    : "";
  const diff = p && p.diff.length
    ? `<h4>${esc(FREEZE.diffTitle)}</h4><pre class="mono small diff">${esc(p.diff.join("\n"))}</pre>`
    : "";
  const state = !p
    ? ""
    : p.written
      ? `<p class="ok-box doc-written">${esc(FREEZE.docWritten(p.rel_path, sha12(p.sha256)))}</p>`
      : p.identical
        ? `<p class="info-line doc-identical">${esc(FREEZE.docIdentical)}</p>`
        : p.exists
          ? `<p class="warn-box doc-exists">${esc(FREEZE.docExists)}</p>`
          : `<p class="info-line">${esc(FREEZE.docPath(p.rel_path))}</p>`;
  const previewText = vm.preview && !vm.written
    ? `<details class="doc-preview"><summary>${esc(FREEZE.docPreviewTitle)}</summary><pre class="mono small">${esc(vm.preview.text)}</pre></details>`
    : "";
  const confirm = p && p.exists && !p.identical && !p.written;
  return section(
    3,
    `<p class="small muted">${esc(FREEZE.fieldsTitle)}</p>` +
      `<div class="scroll"><table class="grid compact fields-table"><thead><tr><th>${esc(FREEZE.colField)}</th><th>${esc(FREEZE.colValue)}</th>` +
      `<th>${esc(FREEZE.colSource)}</th><th>${esc(FREEZE.colQuote)}</th></tr></thead><tbody>${rows}</tbody></table></div>` +
      `<div class="doc-meta">${ftd}${rules}</div>` +
      `<div class="actions">${busyOrRun(vm, "preview-doc", FREEZE.preview)} ` +
      busyOrRun(vm, "write-doc", confirm ? FREEZE.writeConfirm : FREEZE.writeDoc) +
      `</div>${state}${problems}${diff}${previewText}`,
  );
}

// ---------------------------------------------------------------- adım 4

function step4(vm: FreezeVM): string {
  const body = `<p class="small muted">${esc(FREEZE.pitNote)}</p>` +
    `<div class="actions">${busyOrRun(vm, "pit", FREEZE.pitRun, !vm.written?.written)}</div>` +
    (vm.pit === null
      ? ""
      : vm.pit.length === 0
        ? `<p class="ok-box pit-ok">${esc(FREEZE.pitOk)}</p>`
        : `<div class="band-error pit-fail"><strong>${esc(FREEZE.pitFail)}</strong><ul>${vm.pit.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>`);
  return section(4, body);
}

// ---------------------------------------------------------------- adım 5

function step5(vm: FreezeVM): string {
  const p = vm.preflight;
  // Uyarı, ön koşul adımında DENETLENEN T'yi gösterir; henüz koşmadıysa formdaki T.
  const t = p ? p.t : vm.values.first_trading_date ?? null;
  const level = p?.t_level ?? (t ? "NONE" : "YELLOW");
  const msg =
    level === "RED"
      ? `<p class="band-error t-red">${esc(FREEZE.tRed(t ?? "", p?.today_istanbul ?? ""))}</p>`
      : level === "YELLOW"
        ? `<p class="warn-box t-yellow">${esc(FREEZE.tYellow)}</p>`
        : `<p class="info-line t-none">${esc(FREEZE.tNone(t ?? ""))}</p>`;
  const ack = `<label class="chk"><input type="checkbox" data-action="acknowledge"${vm.acknowledged ? " checked" : ""}/> ${esc(FREEZE.acknowledge)}</label>`;
  return section(5, msg + ack, `t-level-${level.toLowerCase()}`);
}

// ---------------------------------------------------------------- adım 6

export function parityText(f: FreezeResult): string {
  const p = f.parity;
  const line = FREEZE.parityLine(p.n_matched, p.n_supported, String(p.max_abs), p.unsupported.length, p.unsupported.join(", "));
  const missing = p.missing_in_record.length
    ? ` · ${FREEZE.parityMissing(p.missing_in_record.length, p.missing_in_record.join(", "))}`
    : "";
  return line + missing;
}

function step6(vm: FreezeVM): string {
  // Ön koşullar (adım 1) geçmeden düğme açılmaz; komut da ön koşulları kendisi yeniden denetler (B3).
  const ready = vm.preflight?.ok === true && vm.pit !== null && vm.pit.length === 0 && vm.acknowledged && (vm.written?.written ?? false);
  const f = vm.frozen;
  const result = f
    ? `<p class="ok-box record-written">${esc(FREEZE.recordWritten(f.record_rel_path))}</p>` +
      `<p class="info-line record-models">${esc(FREEZE.recordModels(f.n_models))}</p>` +
      (f.parity.mismatches.length
        ? `<div class="band-error parity-mismatch">${f.parity.mismatches
            .map((m) => `<p>${esc(FREEZE.parityMismatch(`${m.model_id}: ${m.failures.join("; ")}`))}</p>`)
            .join("")}<p>${esc(FREEZE.parityRecordWins)}</p>` +
          (f.parity.incident_rel_path ? `<p class="mono small">${esc(FREEZE.parityIncident(f.parity.incident_rel_path))}</p>` : "") +
          `</div>`
        : "") +
      `<p class="parity-line mono">${esc(parityText(f))}</p>` +
      `<p class="small muted">${esc(FREEZE.parityNote)}</p>` +
      `<h4>${esc(FREEZE.todoTitle)}</h4><p class="small muted">${esc(FREEZE.todoNotRun)}</p>` +
      `<pre class="mono todo-block">${esc(f.todo.join("\n"))}</pre>` +
      `<div class="actions"><button data-action="copy-todo">${esc(FREEZE.copy)}</button> ` +
      `<button data-action="back-registry">${esc(FREEZE.done)}</button></div>` +
      `<p class="small muted">${esc(FREEZE.todoNote)}</p>`
    : "";
  return section(6, `<div class="actions">${busyOrRun(vm, "freeze", FREEZE.freezeButton, !ready)}</div>${result}`);
}

// ---------------------------------------------------------------- kabuk

export function renderFreezeWizard(vm: FreezeVM): string {
  const head = `<h2>${esc(FREEZE.title)}</h2><p class="small muted">${esc(FREEZE.intro)}</p>` +
    `<div class="actions"><button data-action="back-registry">${esc(FREEZE.done)}</button></div>`;
  if (!vm.repoMode) return `${head}<p class="closed-state">${esc(FREEZE.closed)}</p>`;
  if (!vm.hasResults) {
    return `${head}<p class="closed-state need-results">${esc(FREEZE.needResults)}</p>` +
      `<button data-action="go-inputs">${esc(FREEZE.goInputs)}</button>`;
  }
  const stageLabel = STAGES.find((s) => s.id === vm.stage)?.label ?? vm.stage;
  const ident = `<div class="wizard-ident">` +
    `<label class="small">${esc(FREEZE.ticker)}<br/><input type="text" data-role="wz-ticker" value="${esc(vm.ticker)}" size="10" autocomplete="off"/></label> ` +
    `<label class="small">${esc(FREEZE.company)}<br/><input type="text" data-role="wz-company" value="${esc(vm.company)}" size="46" autocomplete="off"/></label> ` +
    `<span class="small muted">${esc(FREEZE.stage)}: ${esc(stageLabel)}</span></div>`;
  return head + ident + (vm.error ? renderError(vm.error) : "") +
    step1(vm) + step2(vm) + step3(vm) + step4(vm) + step5(vm) + step6(vm);
}

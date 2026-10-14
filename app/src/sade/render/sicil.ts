// Sicil (pano `Sicil`): `registry_view` (kayıtlar, kanıt, payda) + `monitor_view` (sayımlar, makine kaydı, sınıflar)
// + `break_view` / `post_d1_records`. Uygulama sicile yazmaz; iptal ve sihirbazlar eski ekranlardır (K-UI-11). Kişisel
// modda kaynak gömülü sicil anlık görüntüsüdür (FAZ9_SNAPSHOT K-SNAP-3): giriş metni, şeritte repo durumu yerine kaynak,
// künyede kaynak satırı; repo modunda metinler aynen.
import { esc } from "../../dom";
import { SADE } from "../../i18n/tr";
import { dateTr, pct0, sha12 } from "../../render/format";
import type { PostD1RecordRow, RegistryView } from "../../types";
import type { BreakView, MonitorView } from "../types";
import { classLines, classText } from "./common";

export interface SicilVM {
  registry: RegistryView;
  monitor: MonitorView | null;
  ticker: string | null;
  tab: "PRE" | "BREAK" | "POST";
  brk: BreakView | null;
  post: PostD1RecordRow[];
  raw: string | null;
}

const S = SADE.sicil;

function strip(vm: SicilVM): string {
  const c = vm.monitor?.counts;
  const snap = vm.registry.snapshot ?? null;
  const clean = (vm.monitor?.git_status ?? vm.registry.git_status_registry) === "";
  const item = (label: string, value: string, sub: string, cls = "") =>
    `<div class="s-strip-item ${cls}"><div class="s-strip-label">${esc(label)}</div><div class="s-strip-value">${value}</div><div class="s-strip-sub">${esc(sub)}</div></div>`;
  return `<div class="s-strip">` +
    item(S.payda, `${c?.n_payda ?? vm.registry.ipos.length} <small>${esc(S.rows)}</small>`, S.paydaSub(c?.n_frozen ?? 0, c?.n_out_of_scope ?? 0)) +
    item(S.pre, `${c?.n_pre_listing_records ?? SADE.dash}`, S.preSub) +
    item(S.postD1, `${c?.n_post_d1_records ?? SADE.dash}`, S.postD1Sub) +
    item(S.machine, `${c?.n_machine_records ?? SADE.dash}`, S.machineSub) +
    item(S.proofs, `${c?.n_push_proofs ?? vm.registry.proofs.length}`, S.proofsSub) +
    (snap
      ? item(SADE.snapshot.source, `<span class="${snap.build_dirty ? "down" : "up"}">${esc(SADE.snapshot.sourceVal)}</span>`, SADE.snapshot.sourceSub(snap.build_sha7), "snap-source")
      : item(S.repo, `<span class="${clean ? "up" : "down"}">${esc(clean ? S.repoClean : S.repoDirty)}</span>`, S.repoSub)) +
    `</div>`;
}

function table(vm: SicilVM): string {
  const rows = [...vm.registry.tickers].sort((a, b) => (b.first_trading_date ?? "").localeCompare(a.first_trading_date ?? ""));
  const body = rows
    .map((t) => {
      const m = vm.monitor?.rows.find((r) => r.ticker === t.ticker);
      const sel = t.ticker === vm.ticker;
      const pre = t.n_active > 0 ? `<span class="mark-pass">✓ ${esc(S.nRecords(t.n_active))}</span>` : `<span class="muted">${esc(S.none)}</span>`;
      const post = t.n_post_d1_active > 0 ? esc(S.nRecords(t.n_post_d1_active)) : `<span class="muted">${esc(S.none)}</span>`;
      const brk = m && m.n_machine_records > 0 ? esc(S.machineRecord) : `<span class="muted">${esc(S.none)}</span>`;
      return `<tr class="clickable${sel ? " sel" : ""}" data-action="sicil-select" data-ticker="${esc(t.ticker)}"><td><div class="t-ticker">${esc(t.ticker)}</div>` +
        `<div class="t-company">${esc(t.company ?? "")}</div></td><td class="num">${esc(dateTr(t.first_trading_date))}</td><td>${pre}</td><td>${post}</td><td>${brk}</td>` +
        `<td><button class="s-link" data-action="sicil-select" data-ticker="${esc(t.ticker)}">${esc(S.open)}</button></td></tr>`;
    })
    .join("");
  const out = vm.monitor?.counts.n_out_of_scope ?? 0;
  return `<section class="s-panel grow-2 sicil-table"><div class="s-panel-head"><div><h2>${esc(S.tableTitle)}</h2><div class="s-panel-sub">${esc(S.tableSub)}</div></div></div>` +
    `<div class="s-scroll"><table class="s-table"><thead><tr><th>${esc(S.colIpo)}</th><th class="num">${esc(S.colD1)}</th><th>${esc(S.colPre)}</th><th>${esc(S.colPost)}</th>` +
    `<th>${esc(S.colBreak)}</th><th></th></tr></thead><tbody>${body}</tbody></table></div>` +
    `<p class="s-note" style="padding:12px 18px"><strong>${esc(S.outOfScope(out))}</strong> ${esc(S.outOfScopeSub)}</p></section>`;
}

function kv(rows: [string, string][]): string {
  return `<div class="s-kv sicil-kv">${rows.map(([k, v]) => `<div>${esc(k)}</div><div>${v}</div>`).join("")}</div>`;
}

function preTab(vm: SicilVM): string {
  const t = vm.registry.tickers.find((x) => x.ticker === vm.ticker);
  const r = t?.records.find((x) => x.record_type === "PREDICTION" && !x.cancelled_by) ?? t?.records[0];
  if (!t || !r) return `<p class="muted">${esc(S.none)}</p>`;
  const proof = r.push_proof
    ? `<span class="mark-pass">✓ ${esc(S.proofYes(dateTr(r.push_proof.created_at)))}</span>`
    : `<span class="muted">${esc(S.proofNo)}</span>`;
  const added = r.added_commit ? `<div class="s-note">${esc(S.addedBy(sha12(r.added_commit)))}</div>` : "";
  const m = vm.monitor?.rows.find((x) => x.ticker === vm.ticker);
  return kv([
    [S.file, `<span class="mono">${esc(r.file)}</span>`],
    [S.at, `${esc(dateTr(r.recorded_at_istanbul))}<div class="s-note">${esc(S.atBasis)}</div>`],
    [S.proof, `${proof}${added}`],
    [S.classRow, m ? `<div class="s-class">${classLines(m.classes, ["ceiling_hazard_v0", "v1_5_h99"])}</div>` : esc(SADE.dash)],
    [S.inputs, `<span class="mono">${esc(r.inputs_path ?? SADE.dash)}</span><div class="s-note mono">${esc(sha12(r.input_sha256))}</div>`],
    [S.modelSet, `${esc(S.modelSetVal(r.n_models))}<div class="s-note">${esc(S.indexSha(sha12(r.models_index_sha256)))}</div>`],
    [S.head, `<span class="mono">${esc(sha12(r.git_head))}</span>`],
  ]);
}

function breakTab(vm: SicilVM): string {
  const b = vm.brk;
  if (!b || !b.record_file) return `<p class="muted">${esc(S.none)}</p>`;
  return kv([
    [S.file, `<span class="mono">${esc(b.record_file)}</span>`],
    [S.produced, esc(dateTr(b.produced_at_utc))],
    [S.machineClass, esc(classText(b.class))],
    [S.pBreak, esc(b.status === "OK" ? pct0(b.p_f1) : SADE.dash)],
  ]);
}

function postTab(vm: SicilVM): string {
  if (!vm.post.length) return `<p class="muted">${esc(S.postNone)}</p>`;
  return kv(vm.post.map((p) => [p.file, `${esc(dateTr(p.recorded_at_istanbul))} · ${esc(p.record_type ?? SADE.dash)}`] as [string, string]));
}

function card(vm: SicilVM): string {
  if (!vm.ticker) return "";
  const t = vm.registry.tickers.find((x) => x.ticker === vm.ticker);
  const r = t?.records.find((x) => x.record_type === "PREDICTION") ?? null;
  const tabs = [
    ["PRE", S.tabPre(dateTr(r?.recorded_at_istanbul ?? null))],
    ["BREAK", vm.brk?.record_file ? S.tabBreak(dateTr(vm.brk.produced_at_utc)) : S.tabBreak(SADE.dash)],
    ["POST", vm.post.length ? S.tabPost : S.tabPostNone],
  ]
    .map(([id, label]) => `<button class="s-tab ${vm.tab === id ? "active" : ""}" data-action="sicil-tab" data-tab="${id}">${esc(label)}</button>`)
    .join("");
  const body = vm.tab === "PRE" ? preTab(vm) : vm.tab === "BREAK" ? breakTab(vm) : postTab(vm);
  const raw = vm.raw ? `<pre class="s-raw mono">${esc(vm.raw)}</pre>` : "";
  const snap = vm.registry.snapshot;
  const source = snap ? `<p class="s-note sicil-source" data-role="snapshot">${esc(SADE.snapshot.cardSource(snap.build_sha7))}</p>` : "";
  return `<section class="s-panel side sicil-card" style="flex:1 1 420px"><div class="s-panel-head"><div><div class="s-panel-sub">${esc(S.card)}</div><h2>${esc(vm.ticker)}</h2></div>` +
    `<button data-action="open-analysis" data-ticker="${esc(vm.ticker)}">${esc(S.openAnalysis)}</button></div><div class="s-panel-body">${source}<div class="s-tabs">${tabs}</div>${body}` +
    `<div class="s-actions"><button data-action="pd1-wizard" data-ticker="${esc(vm.ticker)}">${esc(S.pd1Wizard)}</button>` +
    `<button data-action="raw" data-ticker="${esc(vm.ticker)}">${esc(S.raw)}</button>` +
    `<button data-action="legacy-record" data-ticker="${esc(vm.ticker)}">${esc(S.cancel)}</button></div>` +
    `<p class="s-note">${esc(S.cancelNote)}</p>${raw}</div></section>`;
}

export function renderSicil(vm: SicilVM): string {
  return `<div class="s-main sicil"><div class="s-head-row"><div><h1 class="s-h1">${esc(S.title)}</h1><p class="s-lead">${esc(vm.registry.snapshot ? S.introSnapshot : S.intro)}</p></div>` +
    `<button class="primary" data-action="new-record">${esc(S.newRecord)}</button></div>${strip(vm)}` +
    `<div class="s-row">${table(vm)}${card(vm)}</div></div>`;
}

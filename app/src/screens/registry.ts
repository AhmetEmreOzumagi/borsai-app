// Sicil ekranı, arz sayfası ve resmi "dondur" sihirbazı (SPEC_APP §3e, §3g).
// Uygulama git'e yazmaz: "Şimdi yapılacaklar" bloğu yalnız kopyalanabilir metindir (U32).
import { open } from "@tauri-apps/plugin-dialog";

import { api, type PathSourceReq } from "../api";
import { asAppError, esc, renderError } from "../dom";
import { FIELDS, FREEZE, REGISTRY, TR } from "../i18n/tr";
import { renderFreezeWizard, type DocDraft, type FreezeVM } from "../render/freeze";
import { renderRecordPage, renderRegistryList } from "../render/registry";
import { renderPostD1Wizard, type PostD1WizardVM } from "../render/post_d1";
import { store } from "../state";
import type { FieldDraft, InputsDocReq, RecordCeiling, SourceDocReq, StreakView } from "../types";
import type { PathCondVM } from "../render/ceiling";
import type { Ctx } from "./ctx";

// ---------------------------------------------------------------- sihirbaz görünümü

function freezeVM(): FreezeVM {
  const w = store.freeze;
  const r = store.results;
  const values: Record<string, string | null> = {};
  for (const f of FIELDS) values[f.name] = r ? (r.inputs[f.name] ?? r.inputDates[f.name] ?? null) : null;
  return {
    repoMode: store.config?.repo_mode ?? false,
    hasResults: r !== null,
    ticker: w.ticker,
    company: w.company,
    stage: r?.stage ?? "POST_BOOKBUILD_PRE_LISTING",
    values,
    docs: w.docs,
    copied: w.copied,
    manifest: w.manifest,
    fields: w.fields,
    collectionRules: w.collectionRules,
    ftdSource: w.ftdSource,
    preflight: w.preflight,
    preview: w.preview,
    written: w.written,
    pit: w.pit,
    acknowledged: w.acknowledged,
    frozen: w.frozen,
    busy: w.busy,
    error: w.error,
  };
}

function inputsReq(vm: FreezeVM): InputsDocReq {
  const fields: Record<string, FieldDraft> = {};
  for (const f of FIELDS) {
    const d = vm.fields[f.name] ?? { source_id: "", quote: "", missing_reason: "", origin: "" };
    const value = vm.values[f.name];
    const filled = value !== null && value !== "";
    fields[f.name] = {
      value: filled ? value : null,
      missing_reason: filled ? null : d.missing_reason,
      source_id: filled ? d.source_id : null,
      quote: filled ? d.quote : null,
      origin: f.name === "total_demand_multiple" && filled ? d.origin : null,
      locator: null,
      cross_checks: [],
      checked_sources: [],
    };
  }
  return {
    ticker: vm.ticker,
    company: vm.company,
    stage: vm.stage,
    first_trading_date_source: vm.ftdSource === "" ? null : vm.ftdSource,
    collection_rules: vm.collectionRules.split("\n").map((x) => x.trim()).filter((x) => x !== ""),
    fields,
    collected_at: null,
  };
}

function docReqs(): SourceDocReq[] {
  return store.freeze.docs.map((d) => ({
    source_id: d.source_id.trim(),
    kind: d.kind,
    document_id: d.document_id.trim(),
    published_at: d.published_at.trim(),
    published_at_basis: d.published_at_basis.trim(),
    path: d.path,
    file_name: d.file_name,
    title: d.title.trim() === "" ? null : d.title.trim(),
    url: null,
    issuer: null,
  }));
}

function postD1WizardVM(): PostD1WizardVM {
  const w = store.postD1Wizard;
  return { repoMode: store.config?.repo_mode ?? false, ...w };
}

// ---------------------------------------------------------------- yükleme

async function loadRegistry(): Promise<void> {
  const s = store.registry;
  try {
    s.view = await api.registryView();
    s.error = null;
  } catch (e) {
    s.view = null;
    s.error = asAppError(e);
  }
}

/**
 * Resmi görünümde koşullu getiri (EK 2 §4.3): kaynak YALNIZ dondurulmuş kayıttır; tahmin yolu
 * (bütün modelleri çalıştıran komut) bu ekranda hiç çağrılmaz. Kullanıcı beyanı bu çağrıya girmez (U52).
 */
async function recordPathConditional(c: RecordCeiling, streak: StreakView | null, j: number): Promise<PathCondVM[]> {
  const obs = streak?.j_observed ?? null;
  const broken = (streak?.broken ?? false) && obs !== null && j === obs;
  const stateName = broken ? "AFTER_BREAK" : "STREAK_ONGOING";
  const jOrT = broken && obs !== null ? obs : j;
  const out: PathCondVM[] = [];
  for (const m of c.path_models) {
    if (m.status !== "PREDICTED" || !m.output) {
      out.push({ model_id: m.model_id, result: null, error: null });
      continue;
    }
    const source: PathSourceReq = { kind: "RECORD", ticker: c.ticker, file: c.file, output: null, params_sha256: null };
    try {
      out.push({ model_id: m.model_id, result: await api.pathConditional(m.model_id, source, jOrT, stateName), error: null });
    } catch (e) {
      out.push({ model_id: m.model_id, result: null, error: asAppError(e) });
    }
  }
  return out;
}

async function loadRecord(): Promise<void> {
  const s = store.registry;
  const t = s.view?.tickers.find((x) => x.ticker === s.ticker);
  const r = t?.records[s.selected];
  s.ceiling = null;
  s.summary = null;
  s.streak = null;
  s.pathDisplay = [];
  s.pathCond = [];
  s.postD1 = null;
  s.postD1Error = null;
  if (!t || !r) return;
  try {
    s.streak = await api.streakView(t.ticker);
    s.pathParams = await api.pathParams();
    if (r.record_type === "PREDICTION" && !r.cancelled_by && r.n_ceiling_models > 0) {
      const j = s.jSelected ?? s.streak.j_observed ?? 0;
      s.jSelected = j;
      const c = await api.recordCeiling(t.ticker, r.file, j);
      s.ceiling = c;
      // Tavan serisi kartı: S yalnız kayıttan (U38, U62); beyan komuta girmez
      s.summary = await api.recordSummary(t.ticker, r.file, j, s.streak.j_observed);
      const shown = c.path_models.filter((m) => m.status === "PREDICTED" && m.output !== null);
      s.pathDisplay = shown.length ? await api.pathDisplay(shown.map((m) => ({ model_id: m.model_id, output: m.output }))) : [];
      s.pathCond = s.tab === "return" ? await recordPathConditional(c, s.streak, j) : [];
      // D1 sonrası satırı (EK 3 §6.5): yalnız registry/post_d1/<T>/ kaydından; model yeniden çalıştırılmaz
      try {
        s.postD1 = await api.postD1View(t.ticker, j, s.postD1File);
      } catch (e) {
        s.postD1Error = asAppError(e);
      }
    }
    s.error = null;
  } catch (e) {
    s.error = asAppError(e);
  }
}

// ---------------------------------------------------------------- çizim

/** Kabuk bağlantısı: ekran içi geçişte (liste → arz sayfası → kayıt sekmesi → sihirbaz) bant yenilenir. */
let shell: Ctx | null = null;

function paint(root: HTMLElement): void {
  shell?.refreshShell();
  const s = store.registry;
  if (s.mode === "wizard") {
    root.innerHTML = renderFreezeWizard(freezeVM());
    return;
  }
  if (s.mode === "post_d1") {
    root.innerHTML = renderPostD1Wizard(postD1WizardVM());
    return;
  }
  if (!store.config?.repo_mode) {
    root.innerHTML = `<h2>${esc(REGISTRY.title)}</h2><p class="closed-state">${esc(TR.closedRegistry)}</p>`;
    return;
  }
  if (s.error && !s.view) {
    root.innerHTML = `<h2>${esc(REGISTRY.title)}</h2>${renderError(s.error)}`;
    return;
  }
  if (!s.view) {
    root.innerHTML = `<h2>${esc(REGISTRY.title)}</h2><p class="muted">${esc(TR.loading)}</p>`;
    return;
  }
  const t = s.view.tickers.find((x) => x.ticker === s.ticker);
  const body =
    s.mode === "record" && t
      ? renderRecordPage({
          ticker: t,
          selected: s.selected,
          ceiling: s.ceiling,
          summary: s.summary,
          postD1: { mode: "OFFICIAL", view: s.postD1, error: s.postD1Error },
          streak: s.streak,
          jSelected: s.jSelected ?? 0,
          tab: s.tab,
          hidden: [],
          declared: s.declared,
          declDropped: s.declDropped,
          pathDisplay: s.pathDisplay,
          pathParams: s.pathParams,
          pathCond: s.pathCond,
          models: store.info?.models ?? [],
          hints: store.hints,
          raw: s.raw,
          cancelReason: s.cancelReason,
          cancelDone: s.cancelDone,
          today: s.view.today_istanbul,
        })
      : renderRegistryList(s.view);
  root.innerHTML = body + (s.error ? renderError(s.error) : "");
}

// ---------------------------------------------------------------- eylemler

async function pickDocs(): Promise<void> {
  const picked = await open({ multiple: true, filters: [{ name: "PDF", extensions: ["pdf"] }] });
  const paths = Array.isArray(picked) ? picked : typeof picked === "string" ? [picked] : [];
  for (const p of paths) {
    const name = p.split("/").pop() ?? p;
    const doc: DocDraft = {
      path: p,
      file_name: name,
      source_id: "",
      kind: "KAP_NOTIFICATION_PDF",
      document_id: "",
      published_at: "",
      published_at_basis: "",
      title: "",
    };
    store.freeze.docs.push(doc);
  }
}

async function run(root: HTMLElement, action: string, fn: () => Promise<void>): Promise<void> {
  const w = store.freeze;
  w.busy = action;
  w.error = null;
  paint(root);
  try {
    await fn();
  } catch (e) {
    w.error = asAppError(e);
  } finally {
    w.busy = null;
    paint(root);
  }
}

function wizardActions(root: HTMLElement, ctx: Ctx, action: string, el: HTMLElement): void {
  const w = store.freeze;
  const vm = freezeVM();
  switch (action) {
    case "preflight":
      void run(root, "preflight", async () => {
        w.preflight = await api.freezePreflight(vm.values.first_trading_date ?? null);
      });
      break;
    case "pick-docs":
      void run(root, "pick-docs", pickDocs);
      break;
    case "remove-doc":
      w.docs.splice(Number(el.dataset.doc ?? "0"), 1);
      paint(root);
      break;
    case "copy-docs":
      void run(root, "copy-docs", async () => {
        w.copied = await api.copySourceDocs(vm.ticker, docReqs());
        w.manifest = w.copied.manifest;
      });
      break;
    case "preview-doc":
      void run(root, "preview-doc", async () => {
        w.written = null;
        w.preview = await api.previewInputsDoc(inputsReq(freezeVM()));
      });
      break;
    case "write-doc":
      void run(root, "write-doc", async () => {
        const confirm = (w.preview?.exists ?? false) && !(w.preview?.identical ?? false);
        w.written = await api.writeInputsDoc(inputsReq(freezeVM()), confirm);
        w.preview = w.written;
        w.pit = null;
      });
      break;
    case "pit":
      void run(root, "pit", async () => {
        w.pit = await api.inputsPitCheck(w.written?.rel_path ?? "");
      });
      break;
    case "acknowledge":
      w.acknowledged = (el as HTMLInputElement).checked;
      paint(root);
      break;
    case "freeze":
      void run(root, "freeze", async () => {
        w.frozen = await api.freezeRecord(w.written?.rel_path ?? "");
        store.registry.view = null;
        store.registry.ticker = w.frozen.ticker;
      });
      break;
    case "copy-todo":
      void navigator.clipboard?.writeText(w.frozen?.todo.join("\n") ?? "").catch(() => undefined);
      break;
    case "go-inputs":
      ctx.navigate("inputs");
      break;
  }
}

// ---------------------------------------------------------------- D1 sonrası sihirbazı (EK 3 §6.6)

/** Adım 1 (+ adım 2'nin komut bloğu): ön koşullar Rust'ta; T_open Python'dan; komut metni Rust'ın tek fonksiyonundan. */
async function postD1Preflight(): Promise<void> {
  const w = store.postD1Wizard;
  w.preflight = await api.postD1Preflight(w.ticker);
  const through = w.preflight.d1 ?? w.preflight.first_trading_date;
  w.outcomesTodo = through ? await api.postD1Todo("OUTCOMES", w.ticker, through) : null;
  if (!w.preflight.active_post_d1.includes(w.cancelFile)) w.cancelFile = w.preflight.active_post_d1[0] ?? "";
}

async function postD1Run(root: HTMLElement, action: string, fn: () => Promise<void>): Promise<void> {
  const w = store.postD1Wizard;
  w.busy = action;
  w.error = null;
  paint(root);
  try {
    await fn();
  } catch (e) {
    w.error = asAppError(e);
  } finally {
    w.busy = null;
    paint(root);
  }
}

function postD1Actions(root: HTMLElement, action: string, el: HTMLElement): boolean {
  const s = store.registry;
  const w = store.postD1Wizard;
  switch (action) {
    case "pd1-wizard":
      s.mode = "post_d1";
      if (w.ticker !== (el.dataset.ticker ?? w.ticker)) {
        store.postD1Wizard = { ...w, ticker: el.dataset.ticker ?? "", preflight: null, outcomesTodo: null, frozen: null, cancelled: null, error: null };
      }
      paint(root);
      return true;
    case "pd1-back":
      s.mode = s.ticker ? "record" : "list";
      void reloadRecord(root);
      return true;
    case "pd1-preflight":
      void postD1Run(root, action, postD1Preflight);
      return true;
    case "pd1-freeze":
      // Kayıt yazıcı Python'dur (K-P2-1 S4); ön koşullar Rust komutunda YENİDEN denetlenir. Commit/push yalnız komut metni.
      void postD1Run(root, action, async () => {
        w.frozen = await api.postD1Freeze(w.ticker);
        await postD1Preflight();
      });
      return true;
    case "pd1-cancel":
      void postD1Run(root, action, async () => {
        w.cancelled = await api.postD1Cancel(`registry/post_d1/${w.ticker}/${w.cancelFile}`, w.cancelReason);
        w.cancelReason = "";
        await postD1Preflight();
      });
      return true;
    case "pd1-copy": {
      const block = el.dataset.block ?? "";
      const lines = block === "post-d1-outcomes-todo" ? w.outcomesTodo : block === "post-d1-cancel-todo" ? w.cancelled?.todo : w.frozen?.todo;
      void navigator.clipboard?.writeText((lines ?? []).join("\n")).catch(() => undefined);
      return true;
    }
    default:
      return false;
  }
}

async function reloadRecord(root: HTMLElement): Promise<void> {
  await loadRecord();
  paint(root);
}

export function mount(root: HTMLElement, ctx: Ctx): void {
  const s = store.registry;
  shell = ctx;
  paint(root);
  if (store.config?.repo_mode && s.mode !== "wizard" && !s.view) {
    void (async () => {
      await loadRegistry();
      if (s.mode === "record") await loadRecord();
      paint(root);
    })();
  }

  root.oninput = (ev) => {
    const t = ev.target as HTMLInputElement | HTMLTextAreaElement;
    const w = store.freeze;
    if (t.dataset.role === "pd1-ticker") {
      store.postD1Wizard.ticker = t.value.trim().toLocaleUpperCase("tr");
      return;
    }
    if (t.dataset.role === "pd1-cancel-reason") {
      const button = root.querySelector<HTMLButtonElement>("[data-action=pd1-cancel]");
      store.postD1Wizard.cancelReason = t.value;
      if (button) button.disabled = t.value.trim() === "";
      return;
    }
    if (t.dataset.role === "cancel-reason") {
      const button = root.querySelector<HTMLButtonElement>("[data-action=cancel-record]");
      s.cancelReason = t.value;
      if (button) button.disabled = t.value.trim() === "";
      return;
    }
    if (t.dataset.role === "wz-ticker") w.ticker = t.value.trim().toLocaleUpperCase("tr");
    else if (t.dataset.role === "wz-company") w.company = t.value;
    else if (t.dataset.role === "collection-rules") w.collectionRules = t.value;
    else if (t.dataset.doc !== undefined && t.dataset.key) {
      const d = w.docs[Number(t.dataset.doc)];
      if (d) (d as unknown as Record<string, string>)[t.dataset.key] = t.value;
    } else if (t.dataset.field && t.dataset.fieldKey) {
      const d = (w.fields[t.dataset.field] ??= { source_id: "", quote: "", missing_reason: "", origin: "" });
      (d as unknown as Record<string, string>)[t.dataset.fieldKey] = t.value;
    }
  };

  root.onchange = (ev) => {
    const t = ev.target as HTMLInputElement | HTMLSelectElement;
    const w = store.freeze;
    if (t.dataset.role === "pd1-cancel-file") {
      store.postD1Wizard.cancelFile = t.value;
      return;
    }
    if (t.dataset.action === "select-j") {
      s.jSelected = Number(t.value);
      void reloadRecord(root);
      return;
    }
    if (t.dataset.action === "acknowledge") {
      wizardActions(root, ctx, "acknowledge", t);
      return;
    }
    if (t.dataset.role === "ftd-source") w.ftdSource = t.value;
    else if (t.dataset.doc !== undefined && t.dataset.key) {
      const d = w.docs[Number(t.dataset.doc)];
      if (d) (d as unknown as Record<string, string>)[t.dataset.key] = t.value;
    } else if (t.dataset.field && t.dataset.fieldKey) {
      const d = (w.fields[t.dataset.field] ??= { source_id: "", quote: "", missing_reason: "", origin: "" });
      (d as unknown as Record<string, string>)[t.dataset.fieldKey] = t.value;
    }
  };

  root.onclick = (ev) => {
    const b = (ev.target as HTMLElement).closest<HTMLElement>("[data-action]");
    if (!b || b.tagName === "SELECT") return;
    const action = b.dataset.action ?? "";
    if (postD1Actions(root, action, b)) return;
    switch (action) {
      case "open-ticker":
        s.ticker = b.dataset.ticker ?? null;
        s.mode = "record";
        s.selected = 0;
        s.jSelected = null;
        s.postD1File = null;
        s.raw = null;
        s.cancelDone = null;
        void reloadRecord(root);
        return;
      case "select-record":
        s.selected = Number(b.dataset.index ?? "0");
        s.jSelected = null;
        s.raw = null;
        void reloadRecord(root);
        return;
      case "back-registry":
        s.mode = "list";
        s.ticker = null;
        s.raw = null;
        void (async () => {
          await loadRegistry();
          paint(root);
        })();
        return;
      case "new-record":
        enterWizard();
        void loadManifest(root);
        return;
      case "read-manifest":
        void loadManifest(root);
        return;
      case "show-raw":
        void (async () => {
          try {
            const raw = await api.readRecordJson(s.ticker ?? "", b.dataset.file ?? "");
            s.raw = JSON.stringify(raw, null, 2);
          } catch (e) {
            s.error = asAppError(e);
          }
          paint(root);
        })();
        return;
      case "cancel-record":
        void (async () => {
          try {
            const t = s.view?.tickers.find((x) => x.ticker === s.ticker);
            const rec = t?.records.find((x) => x.file === b.dataset.file);
            const res = await api.cancelRecord(rec?.rel_path ?? "", s.cancelReason);
            s.cancelDone = REGISTRY.cancelDone(res.cancel_rel_path);
            s.cancelReason = "";
            s.error = null;
            await loadRegistry();
            await loadRecord();
          } catch (e) {
            s.error = asAppError(e);
          }
          paint(root);
        })();
        return;
      case "declare": {
        // Tek beyan türü: "seri sürüyor" (aç/kapat). Yalnız etiket; resmi j değişmez (U52-6).
        const h = Number(b.dataset.h ?? "0");
        s.declared[h - 1] = !s.declared[h - 1];
        void reloadRecord(root);
        return;
      }
      case "clear-declarations":
        s.declared = Array(10).fill(false);
        s.declDropped = false;
        void reloadRecord(root);
        return;
      case "post-d1-tab":
        // D1 sonrası kayıt sekmesi (iki etkin kayıt): birincil seçim skorlamada yapılır
        s.postD1File = b.dataset.file ?? null;
        void reloadRecord(root);
        return;
      case "cond-tab":
        // Getiri sekmesi: koşullu getiri yalnız kayıttan hesaplanır (U38/U49).
        s.tab = b.dataset.tab === "return" ? "return" : "ceiling";
        void reloadRecord(root);
        return;
      default:
        wizardActions(root, ctx, action, b);
    }
  };
}

function enterWizard(): void {
  store.registry.mode = "wizard";
  if (store.freeze.ticker === "") store.freeze.ticker = store.results?.tickerLabel ?? "";
  if (store.freeze.collectionRules === "") store.freeze.collectionRules = FREEZE.defaultRules;
}

/** Var olan MANIFEST (adım 2 daha önce koşmuşsa): kaynak seçimi için salt okuma. */
async function loadManifest(root: HTMLElement): Promise<void> {
  const w = store.freeze;
  if (w.ticker !== "") {
    try {
      w.manifest = await api.readSourceManifest(w.ticker);
    } catch {
      w.manifest = w.copied?.manifest ?? null;
    }
  }
  paint(root);
}

/** Sonuç ve girdi ekranlarındaki "Dondur akışına geç" düğmesi. */
export function openWizard(ctx: Ctx): void {
  enterWizard();
  ctx.navigate("registry");
}

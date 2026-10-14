// Girdi ekranı (SPEC_APP §3a, §3a.2): form durumu, anında Rust denetimi, f6 (repo/elle/boş), tahmin.
import { api } from "../api";
import { asAppError } from "../dom";
import { INPUTS, type StageId } from "../i18n/tr";
import { renderF6, renderFieldNotes, renderInputs, requirementText, type F6Mode, type InputsVM } from "../render/inputs";
import { declaredDays, resetView, store } from "../state";
import type { F6Doc } from "../types";
import type { Ctx } from "./ctx";
import { openWizard } from "./registry";

const DATE_FIELDS = ["first_trading_date", "bookbuilding_start", "bookbuilding_end"];

function vm(): InputsVM {
  const f = store.form;
  return { ...f, repoMode: store.config?.repo_mode ?? false };
}

function formFields(): Record<string, string> {
  const fields: Record<string, string> = { ...store.form.fields };
  if (store.form.f6.mode === "MANUAL") fields.f6_market20 = store.form.f6.manual;
  return fields;
}

async function runCheck(root: HTMLElement): Promise<void> {
  try {
    store.form.check = await api.checkForm(store.form.stage, formFields());
    store.form.error = null;
  } catch (e) {
    store.form.error = asAppError(e);
  }
  root.querySelectorAll<HTMLElement>("[data-notes]").forEach((n) => {
    const field = n.dataset.notes ?? "";
    n.innerHTML = renderFieldNotes(field, store.form.check, field === "f6_market20" ? {} : store.form.missingReasons);
  });
  root.querySelectorAll<HTMLElement>("[data-req]").forEach((n) => {
    n.textContent = requirementText(n.dataset.req ?? "", store.form.check);
    n.parentElement?.setAttribute("class", `req-${store.form.check?.requirements[n.dataset.req ?? ""] ?? "none"}`);
  });
}

function rerenderF6(root: HTMLElement): void {
  const slot = root.querySelector<HTMLElement>("[data-role=f6]");
  if (slot) slot.innerHTML = renderF6(vm());
}

async function computeF6(): Promise<void> {
  const f6 = store.form.f6;
  const t = (store.form.fields.first_trading_date ?? "").trim();
  f6.busy = true;
  f6.error = null;
  try {
    f6.market20 = await api.market20(t === "" ? null : t);
    f6.market20ForT = t;
  } catch (e) {
    f6.market20 = null;
    f6.error = asAppError(e);
  } finally {
    f6.busy = false;
  }
}

/** predict_all'a giden f6 ve kişisel kayda yazılacak f6 bloğu. */
function f6Doc(manualNormalized: string | null): F6Doc {
  const f6 = store.form.f6;
  if (f6.mode === "REPO_PYTHON" && f6.market20) {
    const r = f6.market20.record;
    return { value: r.f6, refusal: r.refusal, origin: "REPO_PYTHON", S0_date: r.S0_date, S20_date: r.S20_date, xu100_sha256: r.xu100_sha256, ref_date: r.ref_date };
  }
  if (f6.mode === "MANUAL") {
    return { value: manualNormalized, refusal: null, origin: "MANUAL", S0_date: null, S20_date: null, xu100_sha256: null, ref_date: null };
  }
  return { value: null, refusal: null, origin: "NONE", S0_date: null, S20_date: null, xu100_sha256: null, ref_date: null };
}

async function predict(root: HTMLElement, ctx: Ctx): Promise<void> {
  const form = store.form;
  if (!form.stage) return;
  form.busy = true;
  mount(root, ctx);
  try {
    const t = (form.fields.first_trading_date ?? "").trim();
    if (form.f6.mode === "REPO_PYTHON" && (!form.f6.market20 || form.f6.market20ForT !== t)) await computeF6();
    const check = await api.checkForm(form.stage, formFields());
    form.check = check;
    const f6 = f6Doc(check.normalized.f6_market20 ?? null);
    const runs = await api.predictAll(check.model_inputs, { value: f6.value, refusal: f6.refusal }, check.normalized.first_trading_date ?? null);
    const inputDates: Record<string, string | null> = {};
    for (const d of DATE_FIELDS) inputDates[d] = check.normalized[d] ?? null;
    const keepDays = store.results?.tickerLabel === form.tickerLabel.trim() ? declaredDays(store.view.declared) : [];
    store.results = {
      runs,
      inputs: check.model_inputs,
      inputDates,
      stage: form.stage,
      tickerLabel: form.tickerLabel.trim(),
      f6,
      source: "FORM",
      scenario: null,
      savedId: null,
    };
    resetView(keepDays);
    form.error = null;
    form.busy = false;
    ctx.navigate("results");
  } catch (e) {
    form.error = asAppError(e);
    form.busy = false;
    mount(root, ctx);
  }
}

async function prefill(root: HTMLElement, ctx: Ctx): Promise<void> {
  const sel = root.querySelector<HTMLSelectElement>("[data-role=prefill-ticker]");
  const ticker = sel?.value ?? "";
  if (!ticker) return;
  try {
    const doc = await api.readInputDocument(ticker);
    const fields: Record<string, string> = {};
    for (const [k, v] of Object.entries(doc.values)) fields[k] = v ?? "";
    store.form.fields = fields;
    store.form.missingReasons = doc.missing_reasons;
    store.form.stage = (doc.stage as StageId | null) ?? store.form.stage ?? "POST_BOOKBUILD_PRE_LISTING";
    store.form.tickerLabel = doc.ticker;
    store.form.prefillTicker = ticker;
    store.form.prefillMsg = INPUTS.prefillDone(doc.ticker, doc.company ?? "");
    store.form.error = null;
  } catch (e) {
    store.form.error = asAppError(e);
  }
  mount(root, ctx);
  await runCheck(root);
}

export function mount(root: HTMLElement, ctx: Ctx): void {
  root.innerHTML = renderInputs(vm());
  let timer: number | undefined;
  const schedule = () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => void runCheck(root), 180);
  };
  root.oninput = (ev) => {
    const t = ev.target as HTMLInputElement;
    if (t.dataset.field) {
      store.form.fields[t.dataset.field] = t.value;
      if (t.dataset.field === "first_trading_date") rerenderF6(root);
      schedule();
    } else if (t.dataset.role === "ticker-label") {
      store.form.tickerLabel = t.value;
    } else if (t.hasAttribute("data-f6-manual")) {
      store.form.f6.manual = t.value;
      schedule();
    }
  };
  root.onchange = (ev) => {
    const t = ev.target as HTMLInputElement;
    if (t.dataset.action === "stage") {
      store.form.stage = t.value as StageId;
      mount(root, ctx);
      void runCheck(root);
    } else if (t.dataset.action === "f6-mode") {
      store.form.f6.mode = t.value as F6Mode;
      rerenderF6(root);
      void runCheck(root);
    } else if (t.dataset.field && t.tagName === "SELECT") {
      store.form.fields[t.dataset.field] = t.value;
      schedule();
    } else if (t.dataset.role === "prefill-ticker") {
      store.form.prefillTicker = t.value;
    }
  };
  root.onclick = (ev) => {
    const b = (ev.target as HTMLElement).closest<HTMLElement>("[data-action]");
    if (!b || b.tagName === "INPUT") return;
    const action = b.dataset.action;
    if (action === "predict") void predict(root, ctx);
    if (action === "prefill") void prefill(root, ctx);
    if (action === "official-flow") openWizard(ctx);
    if (action === "f6-compute") {
      void (async () => {
        const p = computeF6();
        rerenderF6(root);
        await p;
        rerenderF6(root);
      })();
    }
    if (action === "apply-suggestion") {
      const field = b.dataset.field ?? "";
      store.form.fields[field] = b.dataset.value ?? "";
      const input = root.querySelector<HTMLInputElement>(`[data-field="${field}"]`);
      if (input) input.value = store.form.fields[field];
      void runCheck(root);
    }
  };
  if (store.config?.repo_mode && !store.form.tickers.length) {
    void api
      .listInputDocuments()
      .then((t) => {
        store.form.tickers = t;
        if (!store.form.prefillTicker && t.length) store.form.prefillTicker = t[0];
        if (t.length) mount(root, ctx);
      })
      .catch(() => undefined);
  }
  if (store.form.stage && !store.form.check) void runCheck(root);
}

/** Yüklenen kişisel kaydın girdilerini forma kopyalar (yeniden hesaplamak için "Tahmin et"). */
export function fillFormFromResults(): void {
  const r = store.results;
  if (!r) return;
  const fields: Record<string, string> = {};
  for (const [k, v] of Object.entries({ ...r.inputs, ...r.inputDates })) fields[k] = v ?? "";
  store.form.fields = fields;
  store.form.stage = r.stage;
  store.form.tickerLabel = r.tickerLabel;
  store.form.missingReasons = {};
  store.form.check = null;
  const f6 = store.form.f6;
  f6.mode = r.f6.origin;
  f6.manual = r.f6.origin === "MANUAL" ? r.f6.value ?? "" : "";
  f6.market20 =
    r.f6.origin === "REPO_PYTHON"
      ? {
          record: {
            ref_date: r.f6.ref_date ?? "",
            f6: r.f6.value,
            refusal: r.f6.refusal,
            S0_date: r.f6.S0_date,
            S20_date: r.f6.S20_date,
            close_S0: null,
            close_S20: null,
            calendar_sha256: null,
            xu100_sha256: r.f6.xu100_sha256,
          },
          t_unknown: !r.inputDates.first_trading_date,
        }
      : null;
  f6.market20ForT = r.inputDates.first_trading_date ?? "";
  f6.error = null;
}

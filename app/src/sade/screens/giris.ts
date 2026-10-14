// Yeni arz girişi ekranı: eski Girdi ekranıyla aynı komutlar ve aynı form durumu (`store.form`): `check_form` (anında
// denetim), `list_input_documents` / `read_input_document` (sicil belgesinden salt okuma kopya), `market20_via_python`,
// `predict_all`. Sade görünümde kullanıcı beyanı yoktur: yeni tahminde şerit etiketi temizlenir (K-UI-8).
import { api } from "../../api";
import { asAppError } from "../../dom";
import { INPUTS, type StageId } from "../../i18n/tr";
import type { F6Mode } from "../../render/inputs";
import { openWizard } from "../../screens/registry";
import { resetView, store } from "../../state";
import type { F6Doc } from "../../types";
import type { SadeCtx } from "../ctx";
import { renderGiris } from "../render/giris";

const DATE_FIELDS = ["first_trading_date", "bookbuilding_start", "bookbuilding_end"];

function formFields(): Record<string, string> {
  const fields: Record<string, string> = { ...store.form.fields };
  if (store.form.f6.mode === "MANUAL") fields.f6_market20 = store.form.f6.manual;
  return fields;
}

async function runCheck(): Promise<void> {
  try {
    store.form.check = await api.checkForm(store.form.stage, formFields());
    store.form.error = null;
  } catch (e) {
    store.form.error = asAppError(e);
  }
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

/** predict_all'a giden ve kişisel kayda yazılacak f6 bloğu (eski Girdi ekranıyla aynı kural). */
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

export function mount(main: HTMLElement, ctx: SadeCtx): void {
  const repoMode = store.config?.repo_mode ?? false;
  /** Yeniden çizim; odaktaki alan ve imleç korunur (anında denetim yazmayı kesmez). */
  const paint = () => {
    const active = document.activeElement as HTMLInputElement | null;
    const key = active?.dataset.field ?? active?.dataset.role ?? (active?.hasAttribute("data-f6-manual") ? "f6-manual" : null);
    const caret = active && typeof active.selectionStart === "number" ? active.selectionStart : null;
    main.innerHTML = renderGiris({ form: store.form, repoMode, hasResults: store.results !== null });
    if (key) {
      const sel = key === "f6-manual" ? "[data-f6-manual]" : `[data-field="${key}"], [data-role="${key}"]`;
      const next = main.querySelector<HTMLInputElement>(sel);
      if (next) {
        next.focus();
        if (caret !== null && typeof next.setSelectionRange === "function" && next.type === "text") next.setSelectionRange(caret, caret);
      }
    }
  };
  let timer: number | undefined;
  const schedule = () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => void runCheck().then(paint), 180);
  };
  const predict = async () => {
    const form = store.form;
    if (!form.stage) return;
    form.busy = true;
    paint();
    try {
      const t = (form.fields.first_trading_date ?? "").trim();
      if (form.f6.mode === "REPO_PYTHON" && (!form.f6.market20 || form.f6.market20ForT !== t)) await computeF6();
      const check = await api.checkForm(form.stage, formFields());
      form.check = check;
      const f6 = f6Doc(check.normalized.f6_market20 ?? null);
      const runs = await api.predictAll(check.model_inputs, { value: f6.value, refusal: f6.refusal }, check.normalized.first_trading_date ?? null);
      const inputDates: Record<string, string | null> = {};
      for (const d of DATE_FIELDS) inputDates[d] = check.normalized[d] ?? null;
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
      resetView();
      form.error = null;
      form.busy = false;
      ctx.go("sonuc");
    } catch (e) {
      form.error = asAppError(e);
      form.busy = false;
      paint();
    }
  };
  const prefill = async () => {
    const ticker = store.form.prefillTicker || store.form.tickers[0] || "";
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
    await runCheck();
    paint();
  };
  paint();
  main.oninput = (ev) => {
    const t = ev.target as HTMLInputElement;
    if (t.dataset.field) {
      store.form.fields[t.dataset.field] = t.value;
      schedule();
    } else if (t.dataset.role === "ticker-label") {
      store.form.tickerLabel = t.value.toLocaleUpperCase("tr");
    } else if (t.hasAttribute("data-f6-manual")) {
      store.form.f6.manual = t.value;
      schedule();
    }
  };
  main.onchange = (ev) => {
    const t = ev.target as HTMLSelectElement;
    if (t.dataset.field && t.tagName === "SELECT") {
      store.form.fields[t.dataset.field] = t.value;
      schedule();
    } else if (t.dataset.role === "prefill-ticker") {
      store.form.prefillTicker = t.value;
    }
  };
  main.onclick = (ev) => {
    const b = (ev.target as HTMLElement).closest<HTMLElement>("[data-action]");
    if (!b || b.tagName === "INPUT" || b.tagName === "SELECT") return;
    switch (b.dataset.action) {
      case "stage":
        store.form.stage = (b.dataset.stage as StageId | undefined) ?? null;
        void runCheck().then(paint);
        paint();
        break;
      case "predict":
        void predict();
        break;
      case "prefill":
        void prefill();
        break;
      case "official":
        openWizard(ctx.legacy);
        break;
      case "f6-mode":
        store.form.f6.mode = (b.dataset.mode as F6Mode | undefined) ?? "NONE";
        void runCheck().then(paint);
        paint();
        break;
      case "f6-compute":
        void (async () => {
          const p = computeF6();
          paint();
          await p;
          paint();
        })();
        break;
      case "apply-suggestion": {
        const field = b.dataset.field ?? "";
        store.form.fields[field] = b.dataset.value ?? "";
        void runCheck().then(paint);
        break;
      }
    }
  };
  if (repoMode && !store.form.tickers.length) {
    void api
      .listInputDocuments()
      .then((t) => {
        store.form.tickers = t;
        if (!store.form.prefillTicker && t.length) store.form.prefillTicker = t[0];
        paint();
      })
      .catch(() => undefined);
  }
  if (store.form.stage && !store.form.check) void runCheck().then(paint);
}

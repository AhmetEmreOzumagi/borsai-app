// Sonuç ekranı (SPEC_APP §3b, §3c, §3g). Sayılar: predict_all (ya da kişisel kayıttaki çıktı),
// ceiling_display (koşulsuz ve seçilen j), streak_view; ön uç yalnız biçimlendirir.
import { api, type PathSourceReq, type SaveScenarioReq } from "../api";
import { asAppError, esc, renderError } from "../dom";
import { RESULTS } from "../i18n/tr";
import { renderConditional, type PathCondVM } from "../render/ceiling";
import { groupB, isPathModel, renderResults } from "../render/results";
import { renderCeilingSummary } from "../render/summary";
import { declaredDays, store } from "../state";
import type {
  AppError,
  CeilingDisplay,
  CeilingSummary,
  ModelRun,
  PathDisplayRow,
  PathParamsInfo,
  StreakView,
} from "../types";
import type { Ctx } from "./ctx";
import { fillFormFromResults } from "./inputs";
import { openWizard } from "./registry";

function sVectors(runs: ModelRun[]): { model_id: string; S: number[] }[] {
  return groupB(runs)
    .filter((r) => r.status === "PREDICTED" && Array.isArray(r.output?.S))
    .map((r) => ({ model_id: r.model_id, S: (r.output?.S ?? []) as number[] }));
}

interface Derived {
  /** Tavan serisi kartı (EK 3 §5): Rust `ceiling_summary`. */
  summary: CeilingSummary | null;
  ceiling0: CeilingDisplay | null;
  streak: StreakView | null;
  cond: CeilingDisplay | null;
  pathDisplay: PathDisplayRow[];
  pathParams: PathParamsInfo[];
  pathCond: PathCondVM[];
  error: AppError | null;
}

const EMPTY: Derived = { summary: null, ceiling0: null, streak: null, cond: null, pathDisplay: [], pathParams: [], pathCond: [], error: null };

function pathRuns(runs: ModelRun[]): ModelRun[] {
  return runs.filter(isPathModel);
}

/**
 * Koşullu getiri (EK 2 §4.3): durum 2 yalnız seri bozulduğunda VE seçilen j gözlenen j iken;
 * başka her seçim durum 1'dir (varsayımsal j etiketiyle). Kullanıcı beyanı bu seçime GİRMEZ (U52).
 */
async function pathConditional(r: NonNullable<typeof store.results>, streak: StreakView | null, j: number): Promise<PathCondVM[]> {
  const obs = streak?.j_observed ?? null;
  const broken = (streak?.broken ?? false) && obs !== null && j === obs;
  const stateName = broken ? "AFTER_BREAK" : "STREAK_ONGOING";
  const jOrT = broken && obs !== null ? obs : j;
  const out: PathCondVM[] = [];
  for (const run of pathRuns(r.runs).filter((x) => !store.view.hidden.includes(x.model_id))) {
    if (run.status !== "PREDICTED" || !run.output) {
      out.push({ model_id: run.model_id, result: null, error: null });
      continue;
    }
    const source: PathSourceReq = {
      kind: "OUTPUT",
      ticker: r.tickerLabel === "" ? null : r.tickerLabel,
      file: null,
      output: run.output,
      params_sha256: run.params_sha256,
    };
    try {
      out.push({ model_id: run.model_id, result: await api.pathConditional(run.model_id, source, jOrT, stateName), error: null });
    } catch (e) {
      out.push({ model_id: run.model_id, result: null, error: asAppError(e) });
    }
  }
  return out;
}

async function derive(): Promise<Derived> {
  const r = store.results;
  if (!r) return EMPTY;
  try {
    const sv = sVectors(r.runs);
    const ceiling0 = await api.ceilingDisplay(sv, 0, r.inputs.ipo_price_tl ?? null);
    const streak = await api.streakView(r.tickerLabel === "" ? null : r.tickerLabel);
    const j = store.view.jSelected ?? streak.j_observed ?? 0;
    store.view.jSelected = j;
    const cond = j === 0 ? ceiling0 : await api.ceilingDisplay(sv, j, null);
    const shown = pathRuns(r.runs).filter((x) => x.status === "PREDICTED" && x.output !== null);
    const pathDisplay = shown.length
      ? await api.pathDisplay(shown.map((x) => ({ model_id: x.model_id, output: x.output })))
      : [];
    const pathParams = await api.pathParams();
    const pathCond = store.view.tab === "return" ? await pathConditional(r, streak, j) : [];
    // Kart: kişisel kayıttaki çıktılar da yeniden hesaplanmadan gider; TÜFE satırı T'den (EK 3 §3.3)
    const summary = await api.ceilingSummary(r.runs, j, streak.j_observed, r.inputDates.first_trading_date ?? null);
    return { summary, ceiling0, streak, cond, pathDisplay, pathParams, pathCond, error: null };
  } catch (e) {
    return { ...EMPTY, error: asAppError(e) };
  }
}

function paint(root: HTMLElement, d: Derived): void {
  const r = store.results;
  if (store.info && !store.info.integrity_ok) {
    root.innerHTML = `<h2>${esc(RESULTS.title)}</h2><div class="band-error">${esc(RESULTS.integrityBand)}</div>`;
    return;
  }
  // Kart: beyan yalnız etiket olarak aynen taşınır; resmi verinin önündeyse koşullu satır boş kalır (U52)
  const card = d.summary ? renderCeilingSummary({ summary: d.summary, streak: d.streak, declared: store.view.declared }) : "";
  const main = renderResults({
    summaryHtml: card,
    runs: r?.runs ?? [],
    pathDisplay: d.pathDisplay,
    pathParams: d.pathParams,
    ceiling: d.ceiling0,
    hints: store.hints,
    models: store.info?.models ?? [],
    hidden: store.view.hidden,
    scenario: r?.scenario ?? null,
    f6: r?.f6 ?? null,
    openCard: store.view.openCard,
    openWarnings: store.view.openWarnings,
    savedId: r?.savedId ?? null,
    canSave: r?.source === "FORM",
    repoMode: store.config?.repo_mode ?? false,
  });
  const cond = r
    ? renderConditional({ streak: d.streak, cond: d.cond, jSelected: store.view.jSelected ?? 0, tab: store.view.tab, hidden: store.view.hidden,
        declared: store.view.declared, declDropped: store.view.declDropped,
        pathAvailable: d.pathParams.length > 0, pathCond: d.pathCond, pathParams: d.pathParams, recordWithoutPath: false,
        // senaryoda D1 bülteni yok: D1 sonrası satırı yalnız resmi kayıttan (EK 3 §6.5; elle D1 girdisi yok, K-P2-1 S5)
        postD1: { mode: "SCENARIO", view: null, error: null } })
    : "";
  root.innerHTML = `<h2>${esc(RESULTS.title)}</h2>${main}${cond}${d.error ? renderError(d.error) : ""}`;
}

async function save(root: HTMLElement, d: Derived): Promise<void> {
  const r = store.results;
  if (!r) return;
  const title = root.querySelector<HTMLInputElement>("[data-role=save-title]")?.value.trim() || `${r.tickerLabel || RESULTS.watermark} ${r.stage}`;
  const hasDays = store.view.declared.some((x) => x === true);
  const req: SaveScenarioReq = {
    title,
    stage: r.stage,
    ticker_label: r.tickerLabel,
    inputs: r.inputs,
    input_dates: r.inputDates,
    f6: r.f6,
    observed_streak_user: hasDays ? { ticker: r.tickerLabel || null, days: declaredDays(store.view.declared) } : null,
  };
  try {
    const s = await api.saveScenario(req);
    r.savedId = s.scenario_id;
    paint(root, d);
  } catch (e) {
    paint(root, { ...d, error: asAppError(e) });
  }
}

export function mount(root: HTMLElement, ctx: Ctx): void {
  let d: Derived = EMPTY;
  const refresh = async () => {
    d = await derive();
    paint(root, d);
  };
  paint(root, d);
  if (store.results) void refresh();
  root.onchange = (ev) => {
    const t = ev.target as HTMLInputElement;
    if (t.dataset.action === "toggle-model") {
      const id = t.dataset.model ?? "";
      store.view.hidden = t.checked ? store.view.hidden.filter((x) => x !== id) : [...store.view.hidden, id];
      paint(root, d);
    } else if (t.dataset.action === "select-j") {
      store.view.jSelected = Number(t.value);
      void refresh();
    }
  };
  root.onclick = (ev) => {
    const b = (ev.target as HTMLElement).closest<HTMLElement>("[data-action]");
    if (!b || b.tagName === "INPUT" || b.tagName === "SELECT") return;
    const id = b.dataset.model ?? null;
    switch (b.dataset.action) {
      case "go-inputs":
        ctx.navigate("inputs");
        break;
      case "to-inputs":
        fillFormFromResults();
        ctx.navigate("inputs");
        break;
      case "official-flow":
        openWizard(ctx);
        break;
      case "card":
        store.view.openCard = store.view.openCard === id ? null : id;
        store.view.openWarnings = null;
        paint(root, d);
        break;
      case "warnings":
        store.view.openWarnings = store.view.openWarnings === id ? null : id;
        store.view.openCard = null;
        paint(root, d);
        break;
      case "close-panel":
        store.view.openCard = null;
        store.view.openWarnings = null;
        paint(root, d);
        break;
      case "save-scenario":
        void save(root, d);
        break;
      case "open-group-b":
        root.querySelector("details.group-b-details")?.setAttribute("open", "");
        root.querySelector("details.group-b-details")?.scrollIntoView();
        break;
      case "cond-tab":
        // Getiri sekmesine geçişte koşullu getiri Rust'tan istenir (ön uçta hesap yok).
        store.view.tab = b.dataset.tab === "return" ? "return" : "ceiling";
        void refresh();
        break;
      case "declare": {
        // Tek beyan türü: "seri sürüyor" (aç/kapat). Yalnız etiket; j değişmez (U52-6).
        const h = Number(b.dataset.h ?? "0");
        store.view.declared[h - 1] = !store.view.declared[h - 1];
        void refresh();
        break;
      }
      case "clear-declarations":
        store.view.declared = Array(10).fill(false);
        store.view.declDropped = false;
        void refresh();
        break;
    }
  };
}

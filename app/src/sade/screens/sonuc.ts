// Tahmin sonucu ekranı (senaryo): `ceiling_display(S, 0 | j)`, `ceiling_summary(runs, 0, null, t)`, `headline_gate`,
// `perf_view`. Hesaplayıcının j düğmesi yalnız `ceiling_display(S, j)`'yi yeniden çağırır (K-UI-8); ön uçta hesap yok.
import { api } from "../../api";
import { asAppError, renderError } from "../../dom";
import { groupB } from "../../render/results";
import { fillFormFromResults } from "../../screens/inputs";
import { openWizard } from "../../screens/registry";
import { scenarioRequestWithoutDeclaration, store } from "../../state";
import type { AppError, CeilingDisplay, CeilingSummary, ModelRun } from "../../types";
import { sadeApi } from "../api";
import type { SadeCtx } from "../ctx";
import { renderSonuc } from "../render/sonuc";
import { sade } from "../state";

function sVectors(runs: ModelRun[]): { model_id: string; S: number[] }[] {
  return groupB(runs)
    .filter((r) => r.status === "PREDICTED" && Array.isArray(r.output?.S))
    .map((r) => ({ model_id: r.model_id, S: (r.output?.S ?? []) as number[] }));
}

export function mount(main: HTMLElement, ctx: SadeCtx): void {
  let summary: CeilingSummary | null = null;
  let disp0: CeilingDisplay | null = null;
  let dispJ: CeilingDisplay | null = null;
  let error: AppError | null = null;
  const paint = () => {
    main.innerHTML = renderSonuc({
      results: store.results,
      summary,
      disp0,
      dispJ,
      j: sade.sonucJ,
      gate: sade.gate,
      perf: sade.perf,
      hints: store.hints,
      integrityOk: store.info?.integrity_ok ?? true,
      repoMode: store.config?.repo_mode ?? false,
      savedId: store.results?.savedId ?? null,
      errorHtml: error ? `<div class="s-legacy">${renderError(error)}</div>` : "",
    });
  };
  const loadJ = async () => {
    const r = store.results;
    if (!r) return;
    try {
      dispJ = sade.sonucJ === 0 ? disp0 : await api.ceilingDisplay(sVectors(r.runs), sade.sonucJ, null);
      error = null;
    } catch (e) {
      error = asAppError(e);
    }
  };
  const load = async () => {
    const r = store.results;
    if (!r) return;
    try {
      const [s, d0, g, p] = await Promise.all([
        api.ceilingSummary(r.runs, 0, null, r.inputDates.first_trading_date ?? null),
        api.ceilingDisplay(sVectors(r.runs), 0, r.inputs.ipo_price_tl ?? null),
        sade.gate ? Promise.resolve(sade.gate) : sadeApi.headlineGate(),
        sade.perf ? Promise.resolve(sade.perf) : sadeApi.perfView().catch(() => null),
      ]);
      summary = s;
      disp0 = d0;
      sade.gate = g;
      sade.perf = p;
      await loadJ();
    } catch (e) {
      error = asAppError(e);
    }
  };
  paint();
  void load().then(paint);
  main.onclick = (ev) => {
    const b = (ev.target as HTMLElement).closest<HTMLElement>("[data-action]");
    if (!b || b.tagName === "INPUT") return;
    switch (b.dataset.action) {
      case "calc-j":
        sade.sonucJ = Number(b.dataset.j ?? "0");
        void loadJ().then(paint);
        break;
      case "edit-inputs":
        if (store.results?.source === "SCENARIO") fillFormFromResults();
        ctx.go("giris");
        break;
      case "official":
        openWizard(ctx.legacy);
        break;
      case "save": {
        const r = store.results;
        if (!r) return;
        const title = main.querySelector<HTMLInputElement>("[data-role=save-title]")?.value.trim() || r.tickerLabel;
        void api
          .saveScenario(scenarioRequestWithoutDeclaration(r, title))
          .then((s) => {
            r.savedId = s.scenario_id;
            error = null;
          })
          .catch((e) => {
            error = asAppError(e);
          })
          .then(paint);
        break;
      }
    }
  };
}

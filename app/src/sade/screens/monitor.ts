// Monitör ekranı: `monitor_view` + `headline_gate` + `perf_view` (repo modu ya da kişisel modda gömülü sicil anlık görüntüsü;
// K-UI-13, FAZ9_SNAPSHOT K-SNAP-2).
import { asAppError, esc, renderError } from "../../dom";
import { SADE } from "../../i18n/tr";
import { store } from "../../state";
import { sadeApi } from "../api";
import type { SadeCtx } from "../ctx";
import { closedScreen } from "../render/common";
import { renderMonitor } from "../render/monitor";
import { dataSource, sade } from "../state";

export async function loadMonitor(): Promise<void> {
  try {
    const [m, g, p] = await Promise.all([sadeApi.monitorView(), sadeApi.headlineGate(), sadeApi.perfView()]);
    sade.monitor = m;
    sade.gate = g;
    sade.perf = p;
    sade.monitorError = null;
  } catch (e) {
    sade.monitorError = asAppError(e);
  }
}

export function mount(main: HTMLElement, ctx: SadeCtx): void {
  const closed = closedScreen(dataSource(store.config), store.config?.snapshot);
  if (closed) {
    main.innerHTML = closed;
    return;
  }
  const paint = () => {
    if (sade.monitor) {
      main.innerHTML = renderMonitor({ view: sade.monitor, gate: sade.gate, perf: sade.perf, selected: sade.selected, filter: sade.filter });
    } else if (sade.monitorError) {
      main.innerHTML = `<div class="s-main"><div class="s-legacy">${renderError(sade.monitorError)}</div></div>`;
    } else {
      main.innerHTML = `<div class="s-main"><p class="s-note">${esc(SADE.loading)}</p></div>`;
    }
  };
  paint();
  void loadMonitor().then(() => {
    paint();
    ctx.refreshTop();
  });
  main.onclick = (ev) => {
    const b = (ev.target as HTMLElement).closest<HTMLElement>("[data-action]");
    if (!b) return;
    switch (b.dataset.action) {
      case "select":
        sade.selected = b.dataset.ticker ?? null;
        paint();
        break;
      case "filter":
        sade.filter = b.dataset.filter === "STREAK" ? "STREAK" : "ALL";
        paint();
        break;
      case "open-analysis":
        ctx.openAnalysis(b.dataset.ticker ?? "");
        break;
    }
  };
}

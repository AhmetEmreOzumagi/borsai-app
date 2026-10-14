// Model performansı ekranı: `perf_view` + `headline_gate`. Bağımsız modda gömülü scores.json ile geçmiş test satırları
// çalışır; D1 sonrası ve kırılma bölümleri repo modunda repodan, kişisel modda gömülü sicil anlık görüntüsünden
// (FAZ9_SNAPSHOT K-SNAP-2; o zaman veri şeridi kaynağı söyler); ikisi de yoksa repo modu ister (K-UI-13).
import { asAppError, esc, renderError } from "../../dom";
import { SADE } from "../../i18n/tr";
import { store } from "../../state";
import { sadeApi } from "../api";
import type { SadeCtx } from "../ctx";
import { renderPerf } from "../render/perf";
import { dataSource, sade } from "../state";

export function mount(main: HTMLElement, _ctx: SadeCtx): void {
  const paint = () => {
    if (sade.perf) {
      const snapshot = dataSource(store.config) === "SNAPSHOT" ? (store.config?.snapshot ?? null) : null;
      main.innerHTML = renderPerf({ perf: sade.perf, gate: sade.gate, repoMode: store.config?.repo_mode ?? false, snapshot });
    } else if (sade.perfError) {
      main.innerHTML = `<div class="s-main"><div class="s-legacy">${renderError(sade.perfError)}</div></div>`;
    } else {
      main.innerHTML = `<div class="s-main"><p class="s-note">${esc(SADE.loading)}</p></div>`;
    }
  };
  paint();
  void Promise.all([sadeApi.perfView(), sadeApi.headlineGate()])
    .then(([p, g]) => {
      sade.perf = p;
      sade.gate = g;
      sade.perfError = null;
    })
    .catch((e) => {
      sade.perfError = asAppError(e);
    })
    .then(paint);
}

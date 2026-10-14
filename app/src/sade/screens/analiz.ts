// Analiz ekranı (resmi görünüm): `arz_view`, `break_view`, `arz_streak`, `record_summary(T, file, j, jObserved)`,
// `record_ceiling(T, file, j)` (S yalnız dondurulmuş kayıttan; U38) ve kayıt varsa `post_d1_view`. j varsayılanı bültende
// gözlenen j'dir (`arz_streak`: `streak_view` ile aynı okuyucu, veri kökünden); "Gözlenene dön" seçimi sıfırlar (K-UI-8).
// Kullanıcı beyanı yok. Kişisel modda bütün okumalar gömülü sicil anlık görüntüsünden (FAZ9_SNAPSHOT K-SNAP-2).
// FAZ9_UI_FIX K-FIX-1: arz seçilmemişken takipteki arzların listesi (monitör satırları); üst bardaki "Analiz" sekmesi ve
// "Tüm arzlar" kabukta arzı boşaltır (`data-go="analiz"`); arz değiştirici (`arz-switch`) doğrudan açar.
import { api } from "../../api";
import { asAppError, esc, renderError } from "../../dom";
import { SADE } from "../../i18n/tr";
import { store } from "../../state";
import type { CeilingSummary, PostD1View, RecordCeiling, StreakView } from "../../types";
import { sadeApi } from "../api";
import type { SadeCtx } from "../ctx";
import { renderAnaliz, renderAnalizPick } from "../render/analiz";
import { closedScreen } from "../render/common";
import { dataSource, sade } from "../state";
import { loadMonitor } from "./monitor";

export function mount(main: HTMLElement, ctx: SadeCtx): void {
  const closed = closedScreen(dataSource(store.config), store.config?.snapshot);
  if (closed) {
    main.innerHTML = closed;
    return;
  }
  let streak: StreakView | null = null;
  let summary: CeilingSummary | null = null;
  let ceiling: RecordCeiling | null = null;
  let postD1: PostD1View | null = null;
  const loadingHtml = `<div class="s-main"><p class="s-note">${esc(SADE.loading)}</p></div>`;
  const pickRows = () => (sade.monitor?.rows ?? []).map((r) => ({ ticker: r.ticker, company: r.company, first_trading_date: r.first_trading_date }));
  const paint = () => {
    if (!sade.ticker) {
      main.innerHTML = sade.monitor ? renderAnalizPick(pickRows()) : sade.monitorError ? `<div class="s-main"><div class="s-legacy">${renderError(sade.monitorError)}</div></div>` : loadingHtml;
      return;
    }
    if (sade.arzError) {
      main.innerHTML = `<div class="s-main"><div class="s-legacy">${renderError(sade.arzError)}</div></div>`;
      return;
    }
    if (!sade.arz || sade.arz.row.ticker !== sade.ticker) {
      main.innerHTML = loadingHtml;
      return;
    }
    main.innerHTML = renderAnaliz({
      arz: sade.arz,
      brk: sade.breakView,
      streak,
      summary,
      ceiling,
      postD1,
      j: sade.arzJ ?? streak?.j_observed ?? 0,
      gate: sade.gate,
      tickers: pickRows(),
    });
  };
  const loadJ = async () => {
    const t = sade.ticker;
    const file = sade.arz?.row.record_file ?? null;
    if (!t || !file) return;
    const j = sade.arzJ ?? streak?.j_observed ?? 0;
    try {
      [summary, ceiling] = await Promise.all([api.recordSummary(t, file, j, streak?.j_observed ?? null), api.recordCeiling(t, file, j)]);
      postD1 = sade.arz?.post_d1_files.length ? await api.postD1View(t, j, null).catch(() => null) : null;
      sade.arzError = null;
    } catch (e) {
      sade.arzError = asAppError(e);
    }
  };
  const load = async () => {
    const t = sade.ticker;
    if (!t) {
      if (!sade.monitor) await loadMonitor();
      return;
    }
    try {
      const [arz, brk, st, g] = await Promise.all([
        sadeApi.arzView(t),
        sadeApi.breakView(t).catch(() => null),
        sadeApi.arzStreak(t),
        sade.gate ? Promise.resolve(sade.gate) : sadeApi.headlineGate(),
        sade.monitor ? Promise.resolve() : loadMonitor(), // arz değiştirici için takipteki arzlar (K-FIX-1)
      ]);
      sade.arz = arz;
      sade.breakView = brk;
      sade.gate = g;
      streak = st;
      sade.arzError = null;
      await loadJ();
    } catch (e) {
      sade.arzError = asAppError(e);
    }
  };
  paint();
  void load().then(() => {
    paint();
    ctx.refreshTop();
  });
  main.onclick = (ev) => {
    const b = (ev.target as HTMLElement).closest<HTMLElement>("[data-action]");
    if (!b) return;
    switch (b.dataset.action) {
      case "pick":
        ctx.openAnalysis(b.dataset.ticker ?? "");
        break;
      case "calc-j":
        sade.arzJ = Number(b.dataset.j ?? "0");
        void loadJ().then(paint);
        break;
      case "calc-observed":
        sade.arzJ = null;
        void loadJ().then(paint);
        break;
    }
  };
  main.onchange = (ev) => {
    const s = ev.target as HTMLSelectElement;
    if (s.dataset.role === "arz-switch") ctx.openAnalysis(s.value);
  };
}

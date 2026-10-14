// Sicil ekranı: `registry_view` + `monitor_view` (sayımlar) + seçili arz için `break_view` ve `post_d1_records`. Ham kayıt
// `read_record_json`. İptal, D1 sonrası sihirbazı ve dondur sihirbazı eski ekranlardır; sade kabukta açılır (K-UI-11).
// FAZ9_UI_FIX K-FIX-2: satır ya da "Aç" tıklanınca künye seçilen arzla yeniden çizilir; görünür alanın dışındaysa sayfa
// künyenin başına kayar (prefers-reduced-motion açıksa anında; `scroll-margin-top` üst barı açıkta bırakır).
import { api } from "../../api";
import { asAppError, esc, renderError } from "../../dom";
import { SADE } from "../../i18n/tr";
import { openWizard } from "../../screens/registry";
import { store } from "../../state";
import type { AppError, PostD1RecordRow, RegistryView } from "../../types";
import { sadeApi } from "../api";
import type { SadeCtx } from "../ctx";
import { closedScreen } from "../render/common";
import { renderSicil } from "../render/sicil";
import { dataSource, sade } from "../state";
import type { BreakView } from "../types";
import { loadMonitor } from "./monitor";

/** Künye görünür alanın tamamen içindeyse dokunma; değilse başına kaydır (yumuşak; hareket azaltılmışsa anında). */
export function revealCard(main: HTMLElement): void {
  const card = main.querySelector<HTMLElement>(".sicil-card");
  if (!card || typeof card.scrollIntoView !== "function") return;
  const r = card.getBoundingClientRect();
  const bar = document.querySelector<HTMLElement>("header.s-top")?.getBoundingClientRect().height ?? 0;
  if (r.top >= bar && r.bottom <= window.innerHeight) return;
  const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
  card.scrollIntoView({ block: "start", behavior: reduced ? "auto" : "smooth" });
}

export function mount(main: HTMLElement, ctx: SadeCtx): void {
  // repo modu ya da kişisel modda gömülü sicil anlık görüntüsü (FAZ9_SNAPSHOT K-SNAP-2); sihirbazlar repo modu ister
  const closed = closedScreen(dataSource(store.config), store.config?.snapshot);
  if (closed) {
    main.innerHTML = closed;
    return;
  }
  let registry: RegistryView | null = null;
  let brk: BreakView | null = null;
  let post: PostD1RecordRow[] = [];
  let error: AppError | null = null;
  const paint = () => {
    if (error) {
      main.innerHTML = `<div class="s-main"><div class="s-legacy">${renderError(error)}</div></div>`;
      return;
    }
    if (!registry) {
      main.innerHTML = `<div class="s-main"><p class="s-note">${esc(SADE.loading)}</p></div>`;
      return;
    }
    main.innerHTML = renderSicil({ registry, monitor: sade.monitor, ticker: sade.sicilTicker, tab: sade.sicilTab, brk, post, raw: sade.sicilRaw });
  };
  const loadTicker = async () => {
    const t = sade.sicilTicker;
    if (!t) return;
    [brk, post] = await Promise.all([sadeApi.breakView(t).catch(() => null), api.postD1Records(t).catch(() => [] as PostD1RecordRow[])]);
  };
  const load = async () => {
    try {
      [registry] = await Promise.all([api.registryView(), sade.monitor ? Promise.resolve() : loadMonitor()]);
      if (!sade.sicilTicker) {
        const first = [...registry.tickers].sort((a, b) => (b.first_trading_date ?? "").localeCompare(a.first_trading_date ?? ""))[0];
        sade.sicilTicker = first?.ticker ?? null;
      }
      await loadTicker();
    } catch (e) {
      error = asAppError(e);
    }
  };
  paint();
  void load().then(paint);
  main.onclick = (ev) => {
    const b = (ev.target as HTMLElement).closest<HTMLElement>("[data-action]");
    if (!b) return;
    const t = b.dataset.ticker ?? "";
    switch (b.dataset.action) {
      case "sicil-select":
        sade.sicilTicker = t;
        sade.sicilRaw = null;
        void loadTicker().then(() => {
          paint();
          revealCard(main);
        });
        break;
      case "sicil-tab":
        sade.sicilTab = b.dataset.tab === "BREAK" ? "BREAK" : b.dataset.tab === "POST" ? "POST" : "PRE";
        paint();
        break;
      case "raw": {
        const rec = registry?.tickers.find((x) => x.ticker === t)?.records.find((r) => r.record_type === "PREDICTION");
        if (!rec) return;
        void api
          .readRecordJson(t, rec.file)
          .then((v) => {
            sade.sicilRaw = JSON.stringify(v, null, 2);
          })
          .catch((e) => {
            error = asAppError(e);
          })
          .then(paint);
        break;
      }
      case "open-analysis":
        ctx.openAnalysis(t);
        break;
      case "new-record":
        openWizard(ctx.legacy);
        break;
      case "pd1-wizard": {
        const w = store.postD1Wizard;
        store.registry.mode = "post_d1";
        store.registry.ticker = t;
        if (w.ticker !== t) {
          store.postD1Wizard = { ...w, ticker: t, preflight: null, outcomesTodo: null, frozen: null, cancelled: null, error: null };
        }
        ctx.go("sihirbaz");
        break;
      }
      case "legacy-record": {
        const tk = registry?.tickers.find((x) => x.ticker === t);
        const idx = tk ? tk.records.findIndex((r) => r.record_type === "PREDICTION") : -1;
        store.registry.mode = "record";
        store.registry.ticker = t;
        store.registry.selected = idx < 0 ? 0 : idx;
        store.registry.view = null;
        ctx.go("sihirbaz");
        break;
      }
    }
  };
}
